# Release handoff

Source upgrade is implemented and undergoing final release acceptance. Main public repository: https://github.com/nfredmond/OpenDronePlanner . Preserve all private application data and independent WebODM installations.

CPU and CUDA reconstructions of the public Brighton Beach 18-photo dataset completed. The first CPU run had a now-fixed one-thread startup cap, so do not claim a fair speed comparison. Orthomosaic and point cloud were opened in native WebODM. Corrected installers passed four-platform bundled launch checks in run 34074302500. The release workflow now rebuilds tagged source and creates a draft release with installers, checksums and native launch evidence.

Current source UI QA: unit odp-final-qa.service, PID 3424215, app port 45633, WebODM port 42425, window {9bbd91d8-903f-4cb7-9f3e-d9eee6cef34c}. It runs corrected CPU mode with eight threads. Public test capture 9556924b1cfa4789a0f869a1d1dad897. A third reconstruction is being submitted to test active-job close protection and preserved Results scroll/checkbox state. Previous GPU run 3758c8a09e8845c4b6c0c3ba92b5ddf3 completed. Temporary /tmp/odp_api.py accesses the app without printing its token.

Remaining: native full delivery ZIP and printable report export, 390px processing layout, finish final runtime acceptance, commit/tag/push v2.0.0, inspect four final installer launch records/screenshots, publish draft release, close QA stack normally and verify desktop shortcut/no autostart. All app source changes currently belong to this session. No subagents were spawned. Latest logs/screenshots under ignored evidence/. Do not publish private mission headers in screenshots.
