"""Local capture custody and an on-demand, isolated official WebODM stack."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import html
import http.client
import io
import json
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
import urllib.request
import uuid
import zipfile
from transfer import save_json

IMAGES={'.jpg','.jpeg','.png','.tif','.tiff','.dng'}
VIDEOS={'.mp4','.mov','.lrv','.ts'}
SIDECARS={'.srt','.txt','.csv','.json','.geojson','.kml','.kmz','.pdf'}
PRESETS={
 'preview':{'name':'Quick preview','options':{'fast-orthophoto':True,'feature-quality':'low','pc-quality':'low','orthophoto-resolution':10}},
 'survey':{'name':'Map and elevation','options':{'dsm':True,'dtm':True,'pc-classify':True,'orthophoto-resolution':3,'dem-resolution':5}},
 'model':{'name':'Detailed 3D model','options':{'dsm':True,'mesh-octree-depth':11,'pc-quality':'high','skip-3dmodel':False}},
 'vegetation':{'name':'Multispectral / vegetation','options':{'dsm':True,'radiometric-calibration':'camera+sun'}},
 'custom':{'name':'Custom processing','options':{}}
}
WEB_IMAGE='webodm/webodm_webapp@sha256:ed7b1aa0e40f594539ea5dc6dfeb7ecedd85f13259163974528ef9a1bd78bc1f'
DB_IMAGE='webodm/webodm_db@sha256:03f18ec0089325ec2b8975ba1781277bcdc212b6d86c9de33f6409d313e90430'
CPU_IMAGE='webodm/nodeodx@sha256:80250f727dfcf8a90a0a259f0e50f8eedb0f180754243b69137e37b5608d788d'
GPU_IMAGE='webodm/nodeodx@sha256:ea25acb44e5534c8367b1e967755db51244f0c89d2db7c16f5f94097553b6648'
STATUS={10:'Queued',20:'Processing',30:'Failed',40:'Completed',50:'Canceled'}


def now(): return datetime.now(timezone.utc).isoformat()
def ident(value):
    if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{32}',value): raise ValueError('Invalid capture identifier.')
    return value

def filename(value):
    if not isinstance(value,str) or not value or len(value)>180 or value in ('.','..') or re.search(r'[/\\\x00-\x1f\x7f";]',value): raise ValueError('Invalid file name.')
    return value


class Processing:
    def __init__(self,data):
        self.root=Path(data)/'processing';self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.lock=threading.RLock();self.engine_lock=threading.Lock();self.busy=threading.Event()
        self.submit_lock=threading.Lock()
        self.ready=False;self.message='Processing is stopped. Start it when you need it.';self.token=None;self.session=None;self.mode='cpu';self.port=0
        self.bridge=secrets.token_urlsafe(32);self.compose_path=self.root/'compose.json';self.open_request=None
        self.config_path=self.root/'settings.json'
        if not self.config_path.exists(): save_json(self.config_path,{'secret':secrets.token_urlsafe(48),'user':'odp-local','password':secrets.token_urlsafe(40),'gpu':'cpu','threads':min(8,os.cpu_count() or 2)})
        self.config=json.loads(self.config_path.read_text())
    def capture_path(self,cid): return self.root/'captures'/ident(cid)
    def read(self,cid): return json.loads((self.capture_path(cid)/'capture.json').read_text())
    def write(self,c): save_json(self.capture_path(c['id'])/'capture.json',c)
    def save_run(self,cid,run):
        with self.lock:
            latest=self.read(cid);index=next((i for i,r in enumerate(latest['runs']) if r['id']==run['id']),None)
            if index is None:latest['runs'].append(run)
            else:latest['runs'][index]=run
            self.write(latest)
    def captures(self):
        return sorted([json.loads(p.read_text()) for p in (self.root/'captures').glob('*/capture.json')],key=lambda c:c['created'],reverse=True)
    def create(self,body):
        cid=uuid.uuid4().hex;p=self.capture_path(cid);(p/'media').mkdir(parents=True,mode=0o700)
        c={'id':cid,'name':str(body.get('name') or 'Flight capture')[:160],'created':now(),'mission':body.get('mission'),'files':[],'runs':[],'notes':'','client':'','operator':'','findings':'','limitations':''}
        self.write(c);return c
    def notes(self,body):
        with self.lock:
            c=self.read(body['id'])
            for key in ('name','notes','client','operator','findings','limitations'): c[key]=str(body.get(key,c.get(key,'')))[:20000]
            self.write(c);return c
    def upload(self,cid,name,offset,total,stream,length):
        filename(name);p=self.capture_path(cid);c=self.read(cid)
        if Path(name).suffix.lower() not in IMAGES|VIDEOS|SIDECARS: raise ValueError('Unsupported media or sidecar format.')
        if not 0<total<=64*1024**3 or not 0<length<=8*1024**2 or offset<0 or offset+length>total: raise ValueError('Invalid upload chunk size.')
        if shutil.disk_usage(self.root).free<length+1024**3: raise ValueError('Keep at least 1 GB free. Import stopped before the disk filled.')
        key=hashlib.sha256(name.encode()).hexdigest();part=p/(key+'.upload')
        with self.lock:
            c=self.read(cid)
            if any(f['name'].casefold()==name.casefold() for f in c['files']): raise ValueError('This name already exists in the capture. Use a new capture for another flight.')
            if offset==0:
                with part.open('wb'): pass
            if not part.exists() or part.stat().st_size!=offset: raise ValueError('Upload offset mismatch. Retry this file from the beginning.')
            remaining=length
            with part.open('ab') as dest:
                while remaining:
                    block=stream.read(min(1024*1024,remaining))
                    if not block: raise ValueError('Upload interrupted; retry the file.')
                    dest.write(block);remaining-=len(block)
                dest.flush();os.fsync(dest.fileno())
            if offset+length<total:return {'received':offset+length}
            with part.open('rb') as source:digest=hashlib.file_digest(source,'sha256').hexdigest()
            target=p/'media'/name;part.replace(target)
            meta=self.metadata(target);entry={'name':name,'size':total,'sha256':digest,'kind':'photo' if target.suffix.lower() in IMAGES else 'video' if target.suffix.lower() in VIDEOS else 'sidecar',**meta}
            c=self.read(cid);c['files'].append(entry);self.write(c);return {'received':total,'file':entry}
    def metadata(self,path):
        if path.suffix.lower() not in IMAGES:return {}
        try:
            from PIL import Image
            with Image.open(path) as im:
                ex=im.getexif();result={'width':im.width,'height':im.height,'camera':str(ex.get(272,'')).strip('\x00 '),'captured':str(ex.get(36867,ex.get(306,'')))}
                gps=ex.get_ifd(34853)
                def coord(v):return float(v[0])+float(v[1])/60+float(v[2])/3600
                if gps.get(2) and gps.get(4):result['gps']=[coord(gps[4])*(-1 if gps.get(3)=='W' else 1),coord(gps[2])*(-1 if gps.get(1)=='S' else 1)]
                return result
        except Exception as e:return {'metadataWarning':'Metadata unavailable: '+str(e)[:160]}
    def command(self,args,timeout=120,input=None):
        try:r=subprocess.run(['docker',*args],input=input,text=True,capture_output=True,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        except FileNotFoundError:raise ValueError('Install and start Docker Desktop or Docker Engine, then retry. Planning works without Docker.')
        if r.returncode:raise ValueError((r.stderr or r.stdout)[-2500:])
        return r.stdout
    def compose(self,*args,timeout=120,input=None):return self.command(['compose','-p','odp-processing','-f',str(self.compose_path),*args],timeout,input)
    def status(self):return {'ready':self.ready,'message':self.message,'mode':self.mode,'url':f'http://127.0.0.1:{self.port}' if self.ready else None,'presets':PRESETS,'freeGB':round(shutil.disk_usage(self.root).free/1024**3,1),'platform':platform.system(),'threads':self.config['threads'],'busy':self.busy.is_set()}
    def compose_config(self,mode,port):
        env={'WO_BROKER':'redis://broker:6379','WO_SECRET_KEY':self.config['secret'],'WO_HOST':'127.0.0.1','WO_PORT':str(port),'WO_DEFAULT_NODES':'1','WEB_CONCURRENCY':'2'}
        web={'platform':'linux/amd64','image':WEB_IMAGE,'restart':'no','volumes':['media:/webodm/app/media'],'environment':env}
        node={'platform':'linux/amd64','image':GPU_IMAGE if mode!='cpu' else CPU_IMAGE,'restart':'no','volumes':['node-data:/var/www/data'],'command':['--max-concurrency','1'],'mem_limit':'16g','cpus':float(self.config['threads'])}
        if mode=='cuda':node['gpus']='all'
        if mode=='cdi':node['devices']=['nvidia.com/gpu=all']
        return {'services':{'db':{'platform':'linux/amd64','image':DB_IMAGE,'restart':'no','volumes':['db:/var/lib/postgresql/data']},'broker':{'image':'redis:7.0.10','restart':'no'},'node-odx-1':node,
          'webapp':{**web,'ports':[f'127.0.0.1:{port}:8000'],'entrypoint':['/bin/bash','-c','/webodm/wait-for-postgres.sh db /webodm/wait-for-it.sh -t 0 broker:6379 -- /webodm/start.sh'], 'depends_on':['db','broker','node-odx-1']},
          'worker':{**web,'entrypoint':['/bin/bash','-c','/webodm/wait-for-postgres.sh db /webodm/wait-for-it.sh -t 0 broker:6379 -- /webodm/wait-for-it.sh -t 0 webapp:8000 -- /webodm/worker.sh start'],'depends_on':['webapp']}},'volumes':{'db':{},'media':{},'node-data':{}}}
    def start(self,body):
        if not self.engine_lock.acquire(False):raise ValueError('The engine is already starting or stopping.')
        try:
            if self.ready: return self.status()
            mode=body.get('mode','cpu')
            if mode not in ('cpu','cuda'):raise ValueError('Choose CPU or CUDA.')
            self.config['threads']=max(1,min(os.cpu_count() or 2,int(body.get('threads',self.config['threads']))));save_json(self.config_path,self.config)
            self.message='Checking Docker and preparing the processing engine. First download can take several minutes.'
            self.command(['info','--format','{{.ServerVersion}}'])
            if self.compose_path.exists():
                running=self.compose('ps','--status','running','-q')
                if running.strip():
                    previous=json.loads(self.compose_path.read_text());self.port=int(previous['services']['webapp']['ports'][0].split(':')[1])
                    node=previous['services']['node-odx-1'];self.mode='cdi' if node.get('devices') else 'cuda' if node.get('gpus') else 'cpu'
                    self.authenticate();self.ready=True;self.message='Reconnected to the existing processing session. Finish its runs before changing acceleration.';return self.status()
            if mode=='cuda':
                self.command(['pull',GPU_IMAGE],1800)
                failures=[]
                for flags,m in [(['--gpus','all'],'cuda'),(['--device','nvidia.com/gpu=all'],'cdi')]:
                    try:
                        self.command(['run','--rm',*flags,'--entrypoint','nvidia-smi',GPU_IMAGE,'-L']);mode=m;break
                    except ValueError as e:failures.append(str(e))
                else:raise ValueError('CUDA is unavailable in Docker. Install the NVIDIA Container Toolkit / enable WSL2 GPU support, or choose CPU. '+failures[-1])
            with socket.socket() as s:s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
            save_json(self.compose_path,self.compose_config(mode,self.port));self.mode=mode
            self.compose('up','-d',timeout=1800)
            self.message='WebODM is preparing its database and viewers.'
            deadline=time.monotonic()+240
            while time.monotonic()<deadline:
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{self.port}/',timeout=3) as r:
                        if r.status==200:break
                except Exception:time.sleep(2)
            else:raise ValueError('WebODM did not become ready. Check the engine log and Docker memory allocation.')
            self.authenticate();self.ready=True;self.message='WebODM and ODX are ready. '+('CPU processing.' if mode=='cpu' else 'CUDA container access confirmed. Supported stages use the GPU.')
            return self.status()
        except Exception as e:
            self.message='Engine start failed: '+str(e);raise
        finally:self.engine_lock.release()
    def authenticate(self):
        # The local account and cookie are created inside this dedicated database only.
        script='''import json
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from rest_framework_jwt.settings import api_settings
c=json.loads(%r)
u,created=get_user_model().objects.get_or_create(username=c['user'])
u.is_superuser=True;u.is_staff=True;u.set_password(c['password']);u.save()
s=SessionStore();s['_auth_user_id']=str(u.pk);s['_auth_user_backend']='django.contrib.auth.backends.ModelBackend';s['_auth_user_hash']=u.get_session_auth_hash();s.save()
p=api_settings.JWT_PAYLOAD_HANDLER(u)
print('ODP_AUTH:'+json.dumps({'token':api_settings.JWT_ENCODE_HANDLER(p),'session':s.session_key}))
'''%json.dumps({'user':self.config['user'],'password':self.config['password']})
        out=self.compose('exec','-T','webapp','python','manage.py','shell',input=script)
        value=json.loads(next(x[9:] for x in out.splitlines() if x.startswith('ODP_AUTH:')));self.token=value['token'];self.session=value['session']
    def api(self,path,body=None,method=None):
        if not self.token:raise ValueError('Start processing first.')
        data=None if body is None else json.dumps(body).encode()
        req=urllib.request.Request(f'http://127.0.0.1:{self.port}/api/'+path,data=data,method=method,headers={'Authorization':'JWT '+self.token,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code==401:
                login=urllib.request.Request(f'http://127.0.0.1:{self.port}/api/token-auth/',data=json.dumps({'username':self.config['user'],'password':self.config['password']}).encode(),headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(login,timeout=30) as r:self.token=json.load(r)['token']
                req.remove_header('Authorization');req.add_header('Authorization','JWT '+self.token)
                with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
            detail=e.read().decode(errors='replace')[:1500]
            raise ValueError(f'WebODM {e.code}: {detail}')
    def options(self):return self.api('processingnodes/options/')
    def run_path(self,c,run):return f"projects/{run['project']}/tasks/{run['task']}/"
    def submit(self,body):
        if not self.ready:raise ValueError('Start processing first.')
        if self.busy.is_set():raise ValueError('A capture is already uploading. Wait for it to finish.')
        c=self.read(body['id']);media=[f for f in c['files'] if Path(f['name']).suffix.lower() in IMAGES|VIDEOS|{'.srt'} or f['name'] in ('gcp_list.txt','geo.txt')]
        if sum(f['kind']=='photo' for f in media)<2 and not any(f['kind']=='video' for f in media):raise ValueError('Import at least two photos or one video. Other records stay in the capture archive.')
        preset=body.get('preset','survey')
        if preset not in PRESETS:raise ValueError('Unknown processing preset.')
        overrides=body.get('options',{})
        if not isinstance(overrides,dict):raise ValueError('Engine options must be an object.')
        opts={**PRESETS[preset]['options'],**overrides,'max-concurrency':self.config['threads']}
        available=self.options();available=available.get('options',[]) if isinstance(available,dict) else available
        names={o['name'] for o in available}
        if not set(opts)<=names:raise ValueError('Options not supported by this engine: '+', '.join(sorted(set(opts)-names)))
        if not self.submit_lock.acquire(False):raise ValueError('Another upload is active.')
        self.busy.set()
        run={'id':uuid.uuid4().hex,'created':now(),'preset':preset,'mode':self.mode,'options':opts,'status':'Uploading','uploaded':0,'total':len(media)}
        try:
            project=self.api('projects/',{'name':c['name'],'description':'OpenDronePlanner capture '+c['id']})
            run['project']=project['id']
            task=self.api(f"projects/{project['id']}/tasks/",{'name':c['name'],'partial':True,'auto_processing_node':True,'options':[{'name':k,'value':v} for k,v in opts.items()]})
            run['task']=task['id'];self.save_run(c['id'],run)
            for f in media:
                p=self.capture_path(c['id'])/'media'/f['name']
                with p.open('rb') as source:
                    if hashlib.file_digest(source,'sha256').hexdigest()!=f['sha256']:raise ValueError('An imported file changed on disk: '+f['name'])
                self.send_file(self.run_path(c,run)+'upload/',p)
                run['uploaded']+=1;self.save_run(c['id'],run)
            response=self.api(self.run_path(c,run)+'commit/',{})
            run['status']=STATUS.get(response.get('status'),'Queued');self.save_run(c['id'],run);return self.read(c['id'])
        except Exception as e:
            run['status']='Upload failed';run['error']=str(e)
            self.save_run(c['id'],run);raise
        finally:self.busy.clear();self.submit_lock.release()
    def send_file(self,path,file):
        boundary='odp'+uuid.uuid4().hex
        head=(f'--{boundary}\r\nContent-Disposition: form-data; name="images"; filename="{file.name}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
        tail=f'\r\n--{boundary}--\r\n'.encode();conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=180)
        try:
            conn.putrequest('POST','/api/'+path);conn.putheader('Authorization','JWT '+self.token);conn.putheader('Content-Type','multipart/form-data; boundary='+boundary);conn.putheader('Content-Length',str(len(head)+file.stat().st_size+len(tail)));conn.endheaders();conn.send(head)
            with file.open('rb') as f:
                while b:=f.read(1024*1024):conn.send(b)
            conn.send(tail);response=conn.getresponse();content=response.read()
            if response.status>=300:raise ValueError('WebODM rejected '+file.name+': '+content.decode(errors='replace')[:500])
        finally:conn.close()
    def refresh(self,cid):
        with self.lock:
            c=self.read(cid)
            if not self.ready:return c
            for run in c['runs']:
                if 'task' not in run or run['status'] in ('Uploading','Upload failed'):continue
                t=self.api(self.run_path(c,run));run.update(status=STATUS.get(t.get('status'),'Queued'),progress=t.get('running_progress',0),assets=t.get('available_assets',[]),error=t.get('last_error'),processingTime=t.get('processing_time'),imagesCount=t.get('images_count'),statistics=t.get('statistics'))
            self.write(c);return c
    def control(self,body):
        c=self.read(body['id']);run=next(r for r in c['runs'] if r['id']==body['run'])
        action=body['action']
        if action not in ('cancel','restart'):raise ValueError('Unsupported task action.')
        if self.busy.is_set():raise ValueError('Wait for the current upload to finish.')
        self.api(self.run_path(c,run)+action+'/',{});return self.refresh(c['id'])
    def log(self,cid,rid):
        c=self.read(cid);run=next(r for r in c['runs'] if r['id']==rid)
        return self.api(self.run_path(c,run)+'output/?line=0')
    def stop(self):
        if self.busy.is_set():raise ValueError('Wait for the capture upload to finish.')
        if self.compose_path.exists():self.compose('stop',timeout=90)
        self.ready=False;self.token=None;self.session=None;self.message='Processing stopped. Captures and results are retained.';return self.status()
    def active(self):
        if self.busy.is_set():return True
        if not self.ready:return False
        projects=self.api('projects/')
        projects=projects.get('results',[]) if isinstance(projects,dict) else projects
        for project in projects:
            tasks=self.api(f"projects/{project['id']}/tasks/")
            tasks=tasks.get('results',[]) if isinstance(tasks,dict) else tasks
            if any(not t.get('partial') and t.get('status') in (None,10,20) for t in tasks):return True
        return False
    def asset_response(self,cid,rid,asset):
        c=self.read(cid);r=next(x for x in c['runs'] if x['id']==rid)
        if asset not in r.get('assets',[]):raise ValueError('This output is not available.')
        filename(asset)
        req=urllib.request.Request(f'http://127.0.0.1:{self.port}/api/'+self.run_path(c,r)+'download/'+asset,headers={'Authorization':'JWT '+self.token})
        return urllib.request.urlopen(req,timeout=120)
    def report(self,cid):
        c=self.read(cid);e=lambda x:html.escape(str(x or ''));rows=''.join(f"<tr><td>{e(f['name'])}</td><td>{e(f['kind'])}</td><td>{f['size']:,}</td><td><code>{f['sha256']}</code></td></tr>" for f in c['files'])
        runs=''.join(f"<section><h2>{e(r.get('status'))} · {e(r.get('created'))}</h2><p>Engine mode: {e(r['mode'])}. Task: {e(r.get('task'))}</p><pre>{e(json.dumps(r.get('options'),indent=2))}</pre><p>Available outputs: {e(', '.join(r.get('assets',[])) or 'None recorded')}</p><p>{e(r.get('error'))}</p></section>" for r in c['runs'])
        mission=c.get('mission') or {};pts=mission.get('points',[])
        return f'''<!doctype html><html><meta charset="utf-8"><title>{e(c['name'])} | ODP report</title><style>body{{font:15px/1.6 system-ui;max-width:1000px;margin:50px auto;color:#173732;padding:24px}}h1{{font-size:38px}}h2{{border-bottom:1px solid #ddd}}table{{border-collapse:collapse;width:100%;font-size:11px}}td,th{{text-align:left;padding:8px;border-bottom:1px solid #ddd;overflow-wrap:anywhere}}code{{font-size:9px}}pre{{white-space:pre-wrap}}section{{break-inside:avoid}}@media print{{body{{margin:0}}}}</style><p>OPENDRONEPLANNER · FLIGHT AND PROCESSING RECORD</p><h1>{e(c['name'])}</h1><p>Prepared {e(now())}<br>Client: {e(c.get('client'))}<br>Operator: {e(c.get('operator'))}</p><h2>Field record</h2><p>{e(c.get('notes')).replace(chr(10),'<br>')}</p><p>Linked plan: {e(mission.get('name','No plan linked'))}. Planned waypoints: {len(pts)}. Imported files: {len(c['files'])}.</p><h2>Findings</h2><p>{e(c.get('findings') or 'No reviewer findings entered.').replace(chr(10),'<br>')}</p><h2>Limitations and review</h2><p>{e(c.get('limitations') or 'No independent accuracy assessment recorded.').replace(chr(10),'<br>')}</p><p>Processing completion does not establish survey accuracy. Review coordinate and vertical references, independent checkpoints, image coverage and artifacts before relying on measurements. The linked route is a plan, not proof of the actual flight. This report includes location and media metadata.</p>{runs}<h2>Original media manifest</h2><table><thead><tr><th>Name</th><th>Kind</th><th>Bytes</th><th>SHA-256</th></tr></thead><tbody>{rows}</tbody></table></html>'''.encode()
    def package(self,cid):
        c=self.read(cid);buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('report.html',self.report(cid));z.writestr('capture-manifest.json',json.dumps(c,indent=2));z.writestr('README.txt','Open report.html in a browser and print to PDF. This packet contains private flight and media metadata. Large imagery and processing outputs are downloaded separately from ODP or WebODM. Checksums identify original imported media; they do not certify positional accuracy.\n')
            if c.get('mission'):z.writestr('flight.odp.json',json.dumps(c['mission'],indent=2))
        return buf.getvalue()
