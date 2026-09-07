# Desktop releases

The desktop build includes Python, Qt, the planner, the local API and geometry dependencies. Users do not need Node, Python, Git or a terminal to run an installed desktop release.

Download the installer for the computer from GitHub Releases:

- Windows x64: run the Setup EXE. It installs for the current user and creates desktop and Start menu shortcuts.
- macOS Apple Silicon or Intel: open the matching DMG and drag OpenDronePlanner to Applications.
- Ubuntu 24.04+ and compatible Debian systems: open the DEB in the package installer. The application is available in the application menu.

Releases are currently unsigned. Windows SmartScreen and macOS Gatekeeper can require explicit user approval. No signing certificate or Apple developer subscription is purchased or assumed. Check the release's SHA-256 files and download only from this repository. A clean, warning-free signed install is not claimed.

## Processing prerequisite

Planning and export run immediately. Local reconstruction also needs a working Docker installation with Linux containers. Install Docker Desktop on Windows/macOS, or Docker Engine and Compose on Linux, before starting the processing engine. Allocate sufficient memory and disk to Docker. The ODP node is capped at 16 GB; large projects need more memory than a small example survey and may need dataset splitting in WebODM. Official engine images are downloaded on first use and occupy several GB. First use needs internet access.

CPU processing is the default. The pinned processing images target Linux x64. Apple Silicon runs them through Docker's x64 emulation; the desktop app itself is native ARM64. CUDA is optional for supported NVIDIA hardware with Docker GPU access. Apple/AMD GPUs are not CUDA devices. CPU processing remains available.

The desktop does not start at login. Close the app to stop its processing services and local ports. During an upload, active reconstruction or delivery build, finish/cancel that operation before closing. Data stays on disk. Reopening after an interrupted session reconnects to the running ODP stack when available.

## Controller compatibility

Planning, KMZ export, capture intake and processing are cross-platform. Automatic DJI controller replacement currently uses KDE MTP on Linux and requires the system KDE/Python USB packages. Windows/macOS users export KMZ and use their controller's file-transfer workflow. No unsupported native USB implementation is claimed.

## Build and verification

The `Desktop installers` workflow builds on Windows x64, macOS Intel, macOS ARM64 and Ubuntu x64. It launches each bundled app against isolated data, loads the real root interface, opens the processing workspace, captures the rendered window and verifies that the port closes after exit. Logs, screenshots and installers are retained as build artifacts. These launch checks do not establish field flight behavior or reconstruction performance on every OS/GPU.

Source build: install `packaging/requirements.txt`, run `npm ci`, `npm run build`, then `python packaging/build.py`. Run `python packaging/selftest.py` on the built platform. Linux packages use `packaging/linux.py`; Windows uses Inno Setup; macOS uses `hdiutil`.
