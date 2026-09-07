"""Install user-level desktop entries. No login startup or system files."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent
apps=Path.home()/'.local/share/applications'; apps.mkdir(parents=True,exist_ok=True)
try:desktop=Path(subprocess.check_output(['xdg-user-dir','DESKTOP'],text=True).strip())
except (OSError,subprocess.CalledProcessError):desktop=Path.home()/'Desktop'
desktop.mkdir(parents=True,exist_ok=True)

def quoted(path):
    return '"'+str(path).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$')+'"'

for name,label,script,comment,icon in [
    ('opendroneplanner','OpenDronePlanner','launch-planner.sh','Plan flights, transfer KMZ, process imagery and prepare reports',str(ROOT/'web/public/icon.svg')),
    ('waypoint-transfer','Waypoint Transfer','launch.sh','Drop a KMZ to back up and replace a saved DJI controller flight','mark-location')]:
    body=f'[Desktop Entry]\nType=Application\nName={label}\nComment={comment}\nExec={quoted(ROOT/script)}\nIcon={icon}\nTerminal=false\nCategories=Science;Geography;\nStartupNotify=false\n'
    for path in (apps/(name+'.desktop'),desktop/(label+'.desktop')):
        path.write_text(body);path.chmod(0o755)
subprocess.run(['update-desktop-database',str(apps)],check=False)
print('Desktop shortcuts installed. Nothing added to autostart.')
