"""Launch the built app, exercise its entry UI, then verify its port is closed."""
import json,os,platform,socket,subprocess,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
if platform.system()=='Darwin':exe=root/'dist/OpenDronePlanner.app/Contents/MacOS/OpenDronePlanner'
else:exe=root/'dist/OpenDronePlanner'/('OpenDronePlanner.exe' if os.name=='nt' else 'OpenDronePlanner')
with tempfile.TemporaryDirectory(prefix='odp-bundle-test-') as tmp:
 report=root/'release'/('launch-'+platform.system()+'.json');report.parent.mkdir(exist_ok=True)
 r=subprocess.run([str(exe),'--offline','--self-test',str(report)],env={**os.environ,'ODP_DATA_DIR':tmp},timeout=120)
 assert r.returncode==0,('App launch failed',r.returncode)
 d=json.loads(report.read_text());assert d['passed'],d
 with socket.socket() as s:assert s.connect_ex(('127.0.0.1',d['port']))!=0,'Port remained open after app exit'
 print(json.dumps(d,indent=2))
