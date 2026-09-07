#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python || ! -f web/dist/index.html ]]; then
  kdialog --error 'OpenDronePlanner is not built yet. Run ./install.sh in its folder.'
  exit 1
fi
exec .venv/bin/python desktop.py "$@"
