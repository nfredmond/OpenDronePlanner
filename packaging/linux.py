from pathlib import Path
import shutil,subprocess
root=Path(__file__).resolve().parents[1];stage=root/'build/deb';app=stage/'opt/opendroneplanner'
shutil.copytree(root/'dist/OpenDronePlanner',app,dirs_exist_ok=True)
(stage/'DEBIAN').mkdir(parents=True,exist_ok=True)
(stage/'DEBIAN/control').write_text('Package: opendroneplanner\nVersion: 2.0.0\nSection: science\nPriority: optional\nArchitecture: amd64\nMaintainer: OpenDronePlanner contributors\nDepends: libegl1, libopengl0, libxkbcommon0, libxcb-cursor0, libnss3, libasound2t64, libxcomposite1, libxdamage1, libxrandr2, libxtst6, libxkbcommon-x11-0, libxcb-icccm4, libxcb-keysyms1, libxcb-image0, libxcb-render-util0, libxcb-xinerama0, libx11-xcb1\nRecommends: python3-dbus, python3-gi, kio-extras\nDescription: Local drone flight planning, capture processing and reporting\n')
entry='[Desktop Entry]\nType=Application\nName=OpenDronePlanner\nExec=/opt/opendroneplanner/OpenDronePlanner\nIcon=/opt/opendroneplanner/_internal/web/public/icon.svg\nTerminal=false\nCategories=Science;Geography;\n'
launcher=stage/'usr/share/applications/opendroneplanner.desktop';launcher.parent.mkdir(parents=True,exist_ok=True);launcher.write_text(entry)
(root/'release').mkdir(exist_ok=True)
subprocess.run(['dpkg-deb','--root-owner-group','--build',str(stage),str(root/'release/OpenDronePlanner-Linux-x64.deb')],check=True)
