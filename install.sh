#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
command -v uv >/dev/null || { echo 'Install uv first: https://docs.astral.sh/uv/'; exit 1; }
command -v npm >/dev/null || { echo 'Node.js 20.19+ or 22.12+ is required.'; exit 1; }
/usr/bin/python3 -c 'import PyQt6.QtWebEngineWidgets, dbus, gi' || {
  echo 'Ubuntu packages needed: python3-pyqt6.qtwebengine python3-dbus python3-gi kio-extras'; exit 1;
}
uv venv --allow-existing --python /usr/bin/python3 --system-site-packages .venv
uv pip install --python .venv/bin/python -r requirements.txt
npm ci
npm run build
/usr/bin/python3 install_desktop.py
printf 'OpenDronePlanner is ready. Open its desktop shortcut.\n'
