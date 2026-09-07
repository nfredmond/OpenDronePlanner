"""Isolated copies; deliberate no-op must survive before real probes count."""
from pathlib import Path
import os,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent
CASES=[
 ('no-op control','Local capture custody','Local imagery custody',True),
 ('path traversal',"if not isinstance(value,str) or not value or len(value)>180", "if False and (not isinstance(value,str) or not value or len(value)>180",False),
 ('byte checksum',"hashlib.file_digest(source,'sha256').hexdigest()","'0'*64",False),
 ('offset ordering','part.stat().st_size!=offset','False',False),
 ('duplicate name',"any(f['name'].casefold()==name.casefold() for f in c['files'])",'False',False),
 ('disk headroom','shutil.disk_usage(self.root).free<length+1024**3','False',False),
 ('HTML escaping','html.escape(str(x or \'\'))',"str(x or '')",False),
 ('complete output bytes','if expected and size!=expected:', 'if False:',False),
 ('delivery asset allowlist',"if not set(selected)<=set(run.get('assets',[])):",'if False:',False),
 ('thread cap',"'--max_concurrency',str(self.config['threads'])","'--max_concurrency','1'",False),
 ('CPU mode',"if mode=='cuda':node['gpus']='all'","if mode in ('cpu','cuda'):node['gpus']='all'",False),
 ('loopback only',"f'127.0.0.1:{port}:8000'","f'0.0.0.0:{port}:8000'",False),
 ('GPU probe',"else:raise ValueError('CUDA is unavailable in Docker. Install the NVIDIA Container Toolkit / enable WSL2 GPU support, or choose CPU. '+failures[-1])","else:return self.status()",False),
 ('input custody',"if hashlib.file_digest(source,'sha256').hexdigest()!=f['sha256']:","if False:",False),
 ('unsupported options','if not set(opts)<=names:','if False:',False),
 ('full WebODM jobs',"t.get('status') in (None,10,20)","t.get('status') in (None,10)",False),
]
# Keep the path mutation syntactically valid and specifically disable validation.
CASES[1]=('path traversal',"raise ValueError('Invalid file name.')","return value",False)
with tempfile.TemporaryDirectory(prefix='odp-processing-mutations-') as tmp:
 d=Path(tmp)
 for f in ROOT.glob('*.py'):shutil.copy2(f,d/f.name)
 source=(d/'processing.py').read_text()
 for name,old,new,survives in CASES:
  assert old in source,name
  (d/'processing.py').write_text(source.replace(old,new,1))
  r=subprocess.run([sys.executable,'-B','-m','unittest','test_processing'],cwd=d,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  alive=r.returncode==0;print(name+': '+('SURVIVED' if alive else 'CAUGHT'),flush=True)
  if alive!=survives:print(r.stdout+r.stderr);sys.exit(1)

with tempfile.TemporaryDirectory(prefix='odp-ticket-mutations-') as tmp:
 d=Path(tmp)
 for f in ROOT.glob('*.py'):shutil.copy2(f,d/f.name)
 source=(d/'server.py').read_text()
 for name,old,new in [
  ('ticket query scope',"grant['query']==urlsplit(self.path).query.split('&ticket=')[0]",'True'),
  ('ticket expiration',"grant['expires']>time.time()",'True'),
  ('ticket identity',"self.server.downloads.get(ticket)","next(iter(self.server.downloads.values()),None)")]:
  assert old in source,name
  (d/'server.py').write_text(source.replace(old,new,1))
  r=subprocess.run([sys.executable,'-B','-m','unittest','test_server.ApiTests.test_processing_download_ticket_is_scoped_and_expires'],cwd=d,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  print(name+': '+('CAUGHT' if r.returncode else 'SURVIVED'),flush=True)
  if not r.returncode:sys.exit(1)
