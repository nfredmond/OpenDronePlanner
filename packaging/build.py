"""Bundle the native application on the target OS. No flight data is collected."""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--name','OpenDronePlanner','--exclude-module','PyQt6','--exclude-module','PyQt5','--collect-all','rasterio','--collect-all','pyproj','--collect-all','shapely','--collect-data','PySide6']
for source,dest in [('web/dist','web/dist'),('web/public/icon.svg','web/public'),('mtp_io.py','.'),('transfer.py','.'),('controller_discover.py','.'),('LICENSE','.'),('docs/THIRD_PARTY.md','docs')]:args+=['--add-data',str(ROOT/source)+':'+dest]
if sys.platform=='darwin':args+=['--osx-bundle-identifier','org.opendroneplanner.desktop']
subprocess.run(args+[str(ROOT/'desktop.py')],cwd=ROOT,check=True)
