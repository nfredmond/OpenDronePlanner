# OpenDronePlanner 2.0 release handoff

Released publicly: https://github.com/nfredmond/OpenDronePlanner/releases/tag/v2.0.0 . Application source is tagged at 6ad68b4. Subsequent main commits add verification documentation and screenshots only. Final installer run 34075631306 and tagged-source Checks both succeeded.

The release includes Windows x64 Setup EXE, macOS ARM64/Intel DMGs, Ubuntu 24.04+ x64 DEB, SHA256SUMS.txt and native-launch-evidence.zip. All four native bundled apps opened their real root interface, reached Process and closed the app port. Their screenshots were inspected. GitHub's four asset digests match the published checksums. Builds are unsigned. Docker is an additional reconstruction prerequisite; automatic controller replacement remains Linux/KDE only.

The desktop shortcut is installed and was tested by physically clicking its Plasma desktop icon. Version 2.0.0 opened from this checkout and retained the user's mission plus all public sample capture records. No ODP login startup entry exists. Closing the full processing app stopped its five owned containers and both loopback ports. Independent installations and Docker volumes were preserved.

Real public Brighton Beach reconstruction evidence: 18 photos, 61.9 MB, all GPS. First CPU run completed but had a now-corrected one-thread cap. CUDA run completed using RTX 4070 Ti SUPER and eight CPU threads. A final corrected eight-thread CPU run also completed. These are not controlled speed or accuracy benchmarks. Orthomosaic, point cloud and textured model were viewed in native WebODM. The Results delivery button exported real maps, rasters, point cloud and quality PDF with matching checksums. Report notes saved and HTML printed to a reviewed PDF. See docs/VERIFICATION.md.

Private data remain under ~/.local/share/opendroneplanner and Docker volumes odp-processing_*. Public sample capture ID 9556924b1cfa4789a0f869a1d1dad897 contains three completed runs. Three text sidecars entered during a folder-picker QA error; they are documented and were not reconstructed. Original user flight files, credentials, controller identities and private screenshots are excluded from public source.

The authenticated API in docs/API.md provides agent access. Preserve input custody, active-job close protection, CPU defaults and optional GPU probing. Do not send synthetic missions to hardware. No aircraft was flown in this upgrade. Video, multispectral, thermal, GCP and non-Linux reconstruction workflows are upstream capabilities, not fully validated field workflows here.

No required release work remains. See docs/DISTRIBUTION.md and docs/PROCESSING.md for user instructions. Temporary QA scripts under /tmp are not installed application dependencies. No subagents were used and memory was not modified.
