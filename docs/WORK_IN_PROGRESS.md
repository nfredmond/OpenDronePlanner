# Capture, processing and distribution upgrade

Requested: complete Plan / Fly / Process / Present workflow; CPU default with optional NVIDIA CUDA; downloadable Windows, macOS and Linux installers; public GitHub release and installed desktop shortcut.

Implementation underway in this checkout only. Preserve existing Linux controller transfer and private user data. Existing WebODM installation at ~/WebODM and other projects' NodeODM containers are independent and must be retained.

Design: ODP owns a separate on-demand Compose project using official WebODM and NodeODX images. CPU is portable; CUDA is explicit and tested before selection. Embed full upstream WebODM in a native tab to retain all advanced viewers, GCPs, measurements and options. Add a flight-linked capture library, streaming file import with checksums, processing presets and live options, persistent jobs, report/manifest delivery. No automatic flight, paid service, or invented survey accuracy.

Distribution: bundled Python/Qt frontend app through native CI builds, platform installers and release checksums. Processing requires a local container engine. Document GPU and OS-specific USB boundaries. Do not call untested installers verified.

Next: implement manager/backend and processing UI, native tab/lifecycle, real sample reconstruction and GPU evidence, tests and deliberate mutations, installer builds and public release. Source privacy audit before every push. Memory is not being updated.
