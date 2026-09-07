"""Local-only authenticated planning API. The desktop window owns its lifetime."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, urlencode
import base64
import csv
import hashlib
import io
import json
import mimetypes
import os
import secrets
import threading
import time
import urllib.request
import uuid

from planner import generate, review, DEFAULTS
from formats import import_file, export_kmz, export_split
from terrain import apply_terrain
from processing import Processing
from transfer import KdeMtp, transfer, restore_original, DATA as TRANSFER_DATA, save_json

ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('ODP_DATA_DIR',str(Path.home()/'.local/share/opendroneplanner')))


class Service(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,port=0,offline=False):
        self.token=secrets.token_urlsafe(32); self.offline=offline; self.jobs={}; self.pool=ThreadPoolExecutor(max_workers=3)
        self.stop_event=threading.Event(); self.usb_lock=threading.Lock(); self.data_lock=threading.Lock(); self.started=time.time()
        for folder in ('missions','presets','terrain','exports'): (DATA/folder).mkdir(parents=True,exist_ok=True,mode=0o700)
        super().__init__(('127.0.0.1',port),Handler)
        self.origin=f'http://127.0.0.1:{self.server_port}'
        self.processing=Processing(DATA);self.native=False;self.downloads={}
    def job(self,work):
        ident=uuid.uuid4().hex; future=self.pool.submit(work); self.jobs[ident]=future
        # Drop only completed old jobs; active copies must remain queryable.
        if len(self.jobs)>100:
            for k,f in list(self.jobs.items()):
                if f.done() and k!=ident: self.jobs.pop(k)
                if len(self.jobs)<=75: break
        return dict(job=ident)
    def usb(self,work):
        if self.offline: raise ValueError('Controller access is disabled in this test session.')
        if not self.usb_lock.acquire(blocking=False): raise ValueError('Controller is busy. Wait for the current operation.')
        try: return work()
        finally: self.usb_lock.release()


class Handler(BaseHTTPRequestHandler):
    server: Service
    def log_message(self,*args): pass
    def respond(self,value,status=200,mime='application/json'):
        data=json.dumps(value,allow_nan=False).encode() if mime=='application/json' else value
        self.send_response(status); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(data)))
        self.send_header('Cross-Origin-Resource-Policy','same-origin'); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers(); self.wfile.write(data)
    def authorized(self):
        if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}': return False
        origin=self.headers.get('Origin')
        return (not origin or origin==self.server.origin) and secrets.compare_digest(self.headers.get('X-ODP-Token',''),self.server.token)
    def do_GET(self):
        if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}': return self.respond({'error':'Invalid host'},403)
        path=urlsplit(self.path).path
        if self.headers.get('Sec-Fetch-Site') not in (None,'same-origin','none'):
            return self.respond({'error':'Cross-origin access refused'},403)
        if path=='/session.js':
            return self.respond(('window.ODP_TOKEN='+json.dumps(self.server.token)+';').encode(),mime='text/javascript')
        if path.startswith('/webodm/'):
            if not secrets.compare_digest(path.removeprefix('/webodm/'),self.server.processing.bridge) or not self.server.processing.ready: return self.respond({'error':'Start WebODM first'},403)
            self.send_response(302);self.send_header('Set-Cookie','sessionid='+self.server.processing.session+'; Path=/; HttpOnly; SameSite=Strict');self.send_header('Location',f'http://127.0.0.1:{self.server.processing.port}/dashboard/');self.end_headers();return
        if path.startswith('/api/'):
            ticket=parse_qs(urlsplit(self.path).query).get('ticket',[''])[0]
            grant=self.server.downloads.get(ticket)
            download_ok=path=='/api/processing/download' and grant and grant['expires']>time.time() and grant['query']==urlsplit(self.path).query.split('&ticket=')[0]
            if not self.authorized() and not download_ok: return self.respond({'error':'Session token required'},403)
            try:
                if path=='/api/status': result=dict(name='OpenDronePlanner',version='2.0.0',root=str(ROOT),pid=os.getpid(),offline=self.server.offline,defaults=DEFAULTS)
                elif path=='/api/processing/status': result=self.server.processing.status()
                elif path=='/api/processing/captures': result=self.server.processing.captures()
                elif path=='/api/processing/options': result=self.server.processing.options()
                elif path=='/api/processing/log':
                    q=parse_qs(urlsplit(self.path).query);result=self.server.processing.log(q['id'][0],q['run'][0])
                elif path.startswith('/api/processing/download'):
                    q=parse_qs(urlsplit(self.path).query);cid=q['id'][0];kind=q['kind'][0]
                    if kind=='report': data=self.server.processing.report(cid);name='flight-report.html';mime='text/html'
                    elif kind=='packet': data=self.server.processing.package(cid);name='flight-delivery.zip';mime='application/zip'
                    elif kind=='prepared':
                        file=self.server.processing.delivery_path(q['delivery'][0]);self.send_response(200);self.send_header('Content-Type','application/zip');self.send_header('Content-Length',str(file.stat().st_size));self.send_header('Content-Disposition','attachment; filename="complete-flight-delivery.zip"');self.end_headers()
                        with file.open('rb') as source:
                            while chunk:=source.read(1024*1024):self.wfile.write(chunk)
                        return
                    elif kind=='asset':
                        with self.server.processing.asset_response(cid,q['run'][0],q['asset'][0]) as upstream:
                            self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Disposition','attachment; filename="'+q['asset'][0]+'"');self.send_header('Cache-Control','no-store')
                            if upstream.headers.get('Content-Length'):self.send_header('Content-Length',upstream.headers['Content-Length'])
                            self.end_headers()
                            while chunk:=upstream.read(1024*1024):self.wfile.write(chunk)
                        return
                    else:raise ValueError('Unknown download.')
                    self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.send_header('Content-Disposition','attachment; filename="'+name+'"');self.end_headers();self.wfile.write(data);return
                elif path=='/api/library': result={kind:[{**json.loads(p.read_text()),'id':p.stem} for p in (DATA/kind).glob('*.json')] for kind in ('missions','presets')}
                elif path=='/api/draft': result=json.loads((DATA/'draft.json').read_text()) if (DATA/'draft.json').exists() else None
                elif path=='/api/profile': result=json.loads((DATA/'profile.json').read_text()) if (DATA/'profile.json').exists() else None
                elif path.startswith('/api/job/'):
                    future=self.server.jobs.get(path.rsplit('/',1)[-1])
                    if future is None: raise ValueError('Job not found.')
                    result=dict(done=future.done())
                    if future.done(): result['result']=future.result()
                else: return self.respond({'error':'Not found'},404)
                return self.respond(result)
            except Exception as e: return self.respond({'error':str(e)},400)
        target=(ROOT/'web/dist'/('index.html' if path=='/' else path.lstrip('/'))).resolve()
        if not target.is_relative_to(ROOT/'web/dist') or not target.is_file(): return self.respond({'error':'Not found'},404)
        return self.respond(target.read_bytes(),mime=mimetypes.guess_type(target)[0] or 'application/octet-stream')
    def do_POST(self):
        if not self.authorized(): return self.respond({'error':'Session token or origin invalid'},403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if urlsplit(self.path).path=='/api/processing/upload':
                q=parse_qs(urlsplit(self.path).query)
                return self.respond(self.server.processing.upload(q['id'][0],q['name'][0],int(q['offset'][0]),int(q['total'][0]),self.rfile,length))
            if not 0<length<=40*1024*1024: raise ValueError('Request must be under 40 MB.')
            body=json.loads(self.rfile.read(length)); path=urlsplit(self.path).path
            if path=='/api/processing/download-ticket':
                q=urlencode({k:str(body[k]) for k in ('id','kind','run','asset','delivery') if k in body});ticket=secrets.token_urlsafe(32)
                self.server.downloads={k:v for k,v in self.server.downloads.items() if v['expires']>time.time()}
                self.server.downloads[ticket]={'query':q,'expires':time.time()+120}
                result={'url':'/api/processing/download?'+q+'&ticket='+ticket}
            elif path=='/api/processing/delivery': result=self.server.job(lambda:self.server.processing.build_delivery(body))
            elif path=='/api/processing/create': result=self.server.processing.create(body)
            elif path=='/api/processing/notes': result=self.server.processing.notes(body)
            elif path=='/api/processing/start': result=self.server.job(lambda:self.server.processing.start(body))
            elif path=='/api/processing/stop':
                if self.server.processing.active():raise ValueError('Cancel or finish active processing before stopping the engine.')
                result=self.server.job(self.server.processing.stop)
            elif path=='/api/processing/submit': result=self.server.job(lambda:self.server.processing.submit(body))
            elif path=='/api/processing/refresh': result=self.server.processing.refresh(body['id'])
            elif path=='/api/processing/control': result=self.server.processing.control(body)
            elif path=='/api/processing/open':
                if not self.server.processing.ready:raise ValueError('Start processing first.')
                url=self.server.origin+'/webodm/'+self.server.processing.bridge
                if self.server.native:self.server.processing.open_request=url
                result={'url':url,'native':self.server.native}
            elif path=='/api/draft':
                review(body['mission'])
                with self.server.data_lock: save_json(DATA/'draft.json',body['mission'])
                result=dict(saved=True)
            elif path=='/api/generate': result=generate(body['mission'])
            elif path=='/api/review': result=review(body['mission'])
            elif path=='/api/import':
                result=import_file(body['name'],base64.b64decode(body['data'],validate=True))
                if result.get('profile'): save_json(DATA/'profile.json',result['profile'])
            elif path=='/api/save':
                kind=body.get('kind','missions')
                if kind not in ('missions','presets'): raise ValueError('Unknown library type.')
                ident=body.get('id') or uuid.uuid4().hex
                if not ident or any(c not in 'abcdef0123456789' for c in ident): raise ValueError('Invalid mission ID.')
                value=body['value']
                if kind=='missions': review(value)
                save_json(DATA/kind/(ident+'.json'),value); result=dict(id=ident)
            elif path=='/api/archive':
                kind=body['kind']; ident=body['id']
                if kind not in ('missions','presets') or not ident or any(c not in 'abcdef0123456789' for c in ident): raise ValueError('Invalid library item.')
                original=DATA/kind/(ident+'.json'); original.rename(original.with_suffix('.archived')); result=dict(archived=True)
            elif path=='/api/terrain-file':
                data=base64.b64decode(body['data'],validate=True)
                if len(data)>28*1024*1024: raise ValueError('Crop the DEM to less than 28 MB before importing.')
                ident=hashlib.sha256(data).hexdigest(); (DATA/'terrain'/(ident+'.tif')).write_bytes(data); result=dict(id=ident)
            elif path=='/api/terrain': result=self.server.job(lambda:apply_terrain(body['mission'],body['source'],DATA/'terrain',self.server.stop_event))
            elif path=='/api/search':
                query=str(body['query'])[:250]
                def search():
                    req=urllib.request.Request('https://nominatim.openstreetmap.org/search?'+urlencode(dict(q=query,format='json',limit=5)),headers={'User-Agent':'OpenDronePlanner/1.0 (local desktop mission planner)'})
                    with urllib.request.urlopen(req,timeout=20) as r: return json.load(r)
                result=self.server.job(search)
            elif path=='/api/export':
                m=body['mission']; kind=body.get('format','kmz')
                if kind=='kmz': data=export_kmz(m)
                elif kind=='split': data=export_split(m)
                else: raise ValueError('Unknown export type.')
                result=dict(data=base64.b64encode(data).decode(),extension='zip' if kind=='split' else 'kmz')
            elif path=='/api/controller': result=self.server.job(lambda:self.server.usb(lambda:dict(slots=[dict(device=s.device,folder=s.folder) for s in KdeMtp().discover()])))
            elif path=='/api/transfer':
                if body.get('original'):
                    data=base64.b64decode(body['mission']['sourceOriginal'],validate=True)
                else: data=export_kmz(body['mission'])
                export=DATA/'exports'/('mission-'+uuid.uuid4().hex+'.kmz'); export.write_bytes(data)
                def send():
                    outcome=self.server.usb(lambda:transfer(export,KdeMtp()))
                    return dict(status=outcome['status'],waypoints=outcome['waypoints'],sha256=outcome['sha256'])
                result=self.server.job(send)
            elif path=='/api/restore': result=self.server.job(lambda:self.server.usb(lambda:restore_original(KdeMtp())))
            elif path=='/api/reset-slot':
                if self.server.offline: raise ValueError('Controller operations are disabled.')
                def reset():
                    p=TRANSFER_DATA/'settings.json'
                    if p.exists(): p.rename(TRANSFER_DATA/('settings-'+uuid.uuid4().hex+'.previous'))
                    return dict(reset=True)
                result=self.server.usb(reset)
            else: return self.respond({'error':'Not found'},404)
            self.respond(result)
        except Exception as e: self.respond({'error':str(e)},400)


def start(port=0,offline=False):
    service=Service(port,offline); thread=threading.Thread(target=service.serve_forever,daemon=True); thread.start(); return service


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8765); parser.add_argument('--offline',action='store_true'); args=parser.parse_args()
    service=start(args.port,args.offline); print(service.origin,flush=True)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        service.stop_event.set(); service.shutdown(); service.server_close()
