OpenDronePlanner now carries a project from flight planning through local reconstruction and a deliverable archive.

- Plan survey, corridor and waypoint missions; export DJI KMZ and field records.
- Import flight photos/videos and sidecars, retain original checksums and photo positions, and keep processing runs linked to the plan.
- Run official ODX/WebODM locally with CPU or optional NVIDIA CUDA. Open the full WebODM workspace inside the app.
- Download completed maps, elevation rasters, point clouds, models and engine reports. Build a delivery ZIP with selected outputs, reviewer report and checksums.
- Install bundled desktop apps on Windows x64, macOS Apple Silicon/Intel, and Ubuntu 24.04+ x64. No Python, Node or Git setup is needed for the bundled app.

## Download and open

Windows: run `OpenDronePlanner-Windows-x64-Setup.exe`. Mac: open the DMG matching Apple Silicon or Intel and drag the app to Applications. Ubuntu/compatible Debian: open `OpenDronePlanner-Linux-x64.deb` in the package installer. Launch from the desktop shortcut or application menu. No login startup is installed.

These free builds are unsigned. Windows SmartScreen or macOS Gatekeeper may require approval. Reconstruction needs Docker with Linux containers installed once; first start downloads the engine images. CPU works without NVIDIA hardware. CUDA requires Docker GPU access and accelerates supported stages. Automatic controller replacement currently uses Linux/KDE; Windows/Mac users export KMZ for their controller transfer workflow.

Native launch checks run on all four build platforms and include screenshots and port-closure checks. The real 18-photo Brighton Beach dataset completed on both CPU and CUDA on Ubuntu; orthomosaic and point-cloud viewers were inspected. This does not establish survey accuracy, aircraft execution, every upstream workflow, or reconstruction performance on every OS.

See [installation](https://github.com/nfredmond/OpenDronePlanner/blob/main/docs/DISTRIBUTION.md), [processing](https://github.com/nfredmond/OpenDronePlanner/blob/main/docs/PROCESSING.md), and [verification](https://github.com/nfredmond/OpenDronePlanner/blob/main/docs/VERIFICATION.md). `SHA256SUMS.txt` identifies the installer bytes; `native-launch-evidence.zip` contains platform launch records and screenshots.
