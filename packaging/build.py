"""Bundle the native application on the target OS. No flight data is collected."""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
if sys.platform=='darwin':
    # rasterio and pyproj wheels can carry different, identically named PROJ dylibs.
    # Give pyproj's private copies unique install names before dependency analysis.
    import pyproj
    package=Path(pyproj.__file__).parent
    libraries=list(package.rglob('*.dylib'));names={p.name:'odp_pyproj_'+p.name for p in libraries}
    for lib in libraries:lib.rename(lib.with_name(names[lib.name]))
    for binary in [*package.rglob('*.so'),*package.rglob('*.dylib')]:
        lines=subprocess.check_output(['otool','-L',str(binary)],text=True).splitlines()[1:]
        for line in lines:
            old=line.strip().split(' (',1)[0];base=Path(old).name
            if base in names:subprocess.run(['install_name_tool','-change',old,old.rsplit('/',1)[0]+'/'+names[base],str(binary)],check=True)
        if binary.suffix=='.dylib':subprocess.run(['install_name_tool','-id','@rpath/'+binary.name,str(binary)],check=True)
        subprocess.run(['codesign','--force','--sign','-',str(binary)],check=True)
args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--name','OpenDronePlanner','--exclude-module','PyQt6','--exclude-module','PyQt5','--collect-all','rasterio','--collect-all','pyproj','--collect-all','shapely','--collect-data','PySide6']
for source,dest in [('web/dist','web/dist'),('web/public/icon.svg','web/public'),('mtp_io.py','.'),('transfer.py','.'),('controller_discover.py','.'),('LICENSE','.'),('docs/THIRD_PARTY.md','docs')]:args+=['--add-data',str(ROOT/source)+':'+dest]
if sys.platform=='darwin':args+=['--osx-bundle-identifier','org.opendroneplanner.desktop']
subprocess.run(args+[str(ROOT/'desktop.py')],cwd=ROOT,check=True)
