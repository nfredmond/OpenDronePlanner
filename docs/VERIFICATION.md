# Verification record

## Software checks

- TypeScript strict compilation and production bundle built locally.
- Forty-one Python tests exercise geometry, archive import/export, the local API, staged MTP replacement and native drop-copy behavior. All fixtures are synthetic and no regression test touches physical USB hardware.
- Planner/API mutation probes include an unchanged comment control that survives, plus failed variants for exclusion routing, crosshatch, orbit radius, edited exclusion crossings, split continuity, altitude ceiling, end-action consistency, unknown imported actions, XML declarations, GeoJSON exclusions, terrain math, missing terrain, API token, host validation, persistent draft and disabled controller access.
- The original transfer mutation probes retain checks for validation, aircraft identity, remembered slot/storage, transfer locking, durable backup, concurrent device edits, corrupt readback, restoration, unresolved recovery and backup checksums.
- npm production dependency audit reported no known vulnerabilities at the time of checking.

## Observed interfaces

- Inspected WaypointMap's test editor through the user's open browser tab. Drew a temporary research rectangle, opened advanced controls, generated a route and inspected the export workflow. Reset the temporary research geometry afterward.
- Entered ODP through its root page in Chrome. Drew a synthetic survey rectangle and takeoff point, generated 98 waypoints, changed the first waypoint's height, saved the mission and saw it in the library. Loaded a synthetic aircraft profile through the file chooser while retaining the drawn route.
- The restarted Chrome test page was subsequently blocked by the automation inspector. No browser security setting was changed to bypass it. Native Qt desktop inspection continued.
- The native ODP window rendered correctly. Its real file chooser imported the synthetic survey project with USGS terrain, and the map showed its 98 points and relative flight/ground profile.
- Live USGS 3DEP batch sampling returned all 98 route elevations and the takeoff elevation in approximately 4.5 seconds for the synthetic survey. The service reported NAVD88 and 1 m source resolution. This proves query and mapping behavior at that location, not universal coverage or survey accuracy.

The installed desktop and export checks are recorded below.

## Boundaries of this evidence

The transport was previously exercised against a connected DJI controller, including backup restoration, replacement and independent byte readback. That work preceded this planner extension. No synthetic/generated QA flight has been installed on a physical controller, and no aircraft has been flown during planner development.

Unit tests do not establish DJI Fly firmware acceptance, camera timing in flight, battery performance, airspace authorization, obstacle clearance or terrain survey accuracy. Unknown imported actions remain explicit blockers for rewritten export. The original input remains available for unchanged transfer.

Test screenshots, real flight data, device identifiers and backup receipts are intentionally excluded from the public source history. Public screenshots contain explicitly labeled synthetic planning examples or identified public sample reconstruction outputs.

## Native export and lifecycle checks

The native **Export DJI KMZ** button opened a save dialog and wrote a 98-waypoint synthetic mission. Independent archive parsing confirmed 98 executable points, the intended `goHome` end action, and no structural review errors. The flight/ground profile retained real USGS sample provenance in the ODP project; the KMZ carries the resulting takeoff-relative heights.

Closing the first native test window through its normal close action ended its process and released its port. The browser development service is separate and is stopped explicitly after testing.

## Narrow layout and installation

The native window was inspected at approximately 390 CSS pixels wide, both with the map visible and with the planning panel open. This caught and fixed header overlap and map controls appearing above the sidebar. The final narrow screenshots show reachable planning controls and a separate map view.

The installer was exercised in the clean OpenDronePlanner checkout. It created its own virtual environment, built the frontend and installed both desktop shortcuts. The original local development history is preserved separately; public history starts from the audited source export.

Saved-project identity is covered by a regression and mutation probe, preventing a reopened draft from losing the saved-library identity.

The installed desktop icon was launched and its listening process was matched to the clean OpenDronePlanner checkout through `/api/status` and the process working directory. Closing that window released its exact port; reopening the icon restored the saved draft. No ODP or Waypoint Transfer entry was found in the user's login autostart configuration. Small imported routes now fit at higher display zoom, with basemap tiles enlarged only beyond their native resolution.

## Processing upgrade, 2026-09-06

The native Qt app imported the public Brighton Beach dataset through its real folder chooser: 18 original JPEGs, 61.9 MB, with GPS metadata read from every photo. Source: https://github.com/pierotofy/drone_dataset_brighton_beach . This is an external public software-test dataset, not a user flight. Three unrelated license/metadata text files entered the test capture during an earlier incorrect folder selection; they were retained as sidecars and not submitted to reconstruction. The intake error exposed a stale UI file list, which was fixed along with duplicate-name preflight handling.

The first complete CPU run processed all 18 images and returned orthophoto.tif, dsm.tif, dtm.tif, georeferenced_model.laz, textured_model.zip, textured_model.glb, cameras.json, shots.geojson, report.pdf and all.zip. Its engine quality report states 18/18 reconstructed images, 1,472,297 dense points and 1.59 cm average GSD. These are engine-reported metrics, not an independent accuracy assessment. The run was unintentionally capped at one CPU thread by a NodeODX startup argument; the argument was corrected and a regression/mutation probe added. Do not use this run as a fair CPU/GPU speed comparison.

The completed orthomosaic was opened through the embedded WebODM dashboard's View Map control and appeared over the basemap. The separate bundled Linux application opened its real planning interface, and closing it released port 38987. The source window also displayed the generated point cloud in WebODM. Closing it normally stopped all five ODP containers and released both its app and WebODM ports, while retaining the capture and results.

CUDA device access was tested inside the official GPU image using Docker CDI. It reported the RTX 4070 Ti SUPER, driver 595.84 and 16,376 MiB. The same 18-photo capture then completed using the GPU image and eight CPU threads. Engine logs identify NVIDIA detection, SM 8.9 and CUDA-enabled OpenMVS depth estimation. WebODM recorded 237,537 ms, 18 processed images, 1,168,831 dense points and 1.5933 cm GSD. The output set includes the orthomosaic, DSM, DTM, point cloud, textured model, camera records and quality PDF. This is an actual reconstruction, not only a device probe. Different point counts are engine results, not an accuracy ranking. This computer uses a user-local NVIDIA toolkit and refreshes its CDI specification only when CUDA is requested; no ODP boot/login startup is added.

All four initial installer builds succeeded, then explicit launch checks exposed missing Linux runtime libraries, colliding macOS geospatial libraries and macOS bundle resource symlinks. The corrected build at commit 2edcac9 passed real bundled-app launch checks on all four native CI platforms in run 34074302500. Each root interface opened Process and closed its port on exit. Final tagged assets are rebuilt from the release source. Build success alone is not listed as a working installer.


The complete Python suite has 55 tests. Deliberate processing mutations caught path and Windows filename rejection, input checksums, chunk offsets, duplicates, disk headroom, report escaping, truncated output downloads, output allowlists, CPU thread limits, CPU/GPU separation, loopback binding, failed GPU probes, unsupported options, failed-start cleanup, jobs on later API pages, and scoped/expiring download tickets. No-op controls survived. The first offset fixture and portable-filename fixture were too weak; mutation testing exposed them and the fixtures were corrected. Planner and controller mutation checks also passed with surviving no-op controls.

These tests mock Docker at the boundary. They cannot prove reconstruction quality, USB behavior on other operating systems, all NVIDIA generations, or video/multispectral/thermal/GCP processing. Those upstream workflows are accessible but have not been validated here with representative real data. Linux CPU and CUDA photo reconstructions provide the narrower live evidence described above.


The final native Results journey exposed a five-second scroll reset during polling. Results now preserves scroll, selected output checkboxes and the open log. Before/after native screenshots across multiple polls show the selected point-cloud output and scroll position retained while the new CPU run advances. Attempting normal close during that run displayed the active-processing guard and left the engine running.

The Results delivery button opened the native save dialog and wrote a 58,952,623-byte ZIP of real CUDA-run outputs. It contains orthophoto.tif, georeferenced_model.laz, dtm.tif, dsm.tif, report.pdf, ODP report, capture manifest and output checksums. ZIP CRCs and all five SHA-256 checks matched independent reads. Rasterio opened the three rasters with EPSG:32615; orthomosaic 4180×3378 with four bands, DSM/DTM 2507×2026. The capture has no linked private flight. Report findings and limitations saved through the UI. At 390 CSS pixels, the processing library, engine controls, report form and tabs remain readable and reachable.

The 390px report journey reached both delivery buttons. The printable-report button saved HTML through the native file dialog; Qt/Chromium rendered it and printed a five-page PDF. All pages were inspected, including findings, limitations, recorded photo positions, per-run metrics/options, and the complete original-media checksum table. This is a printable processing record; it is not an independently certified survey report.

A final CPU run with the corrected eight-thread limit also completed all 18 photos and the full output set. WebODM recorded 429,087 ms and 1,410,427 dense points. This run proves the corrected CPU configuration works; these few sequential runs are not a controlled performance or accuracy benchmark. The tagged-source Checks workflow passed.

The full WebODM tab reopened all three completed runs after engine restart. The latest CPU orthomosaic and textured 3D model rendered in its native viewers. Engine option search found orthophoto-resolution and Add populated the editable options. The final app console contained the Qt rendering-backend fallback notice and upstream viewer initialization messages; no application JavaScript errors were observed in this journey.


## Final release acceptance

Release v2.0.0 uses application source 6ad68b4. Installer workflow [34075631306](https://github.com/nfredmond/OpenDronePlanner/actions/runs/34075631306) completed successfully on Linux x64, Windows x64, macOS ARM64 and macOS Intel. All four actual bundled launch reports say plan=true and process=true; their screenshots were inspected. The checks verify that app ports close. The release contains native launch evidence, four platform installers and SHA-256 checksums. Each checksum matched GitHub's uploaded-asset digest. Tagged-source CI Checks also passed.

The installed Plasma desktop icon was clicked directly. It launched version 2.0.0 from the intended checkout with ordinary controller access enabled, restored the existing mission, and retained all three completed sample runs. The processing engine remained stopped until requested. There were zero ODP entries in user autostart or persistent user-systemd configuration. The previous full engine close stopped all five owned services and released app port 45633 and WebODM port 42425. These runtime port numbers are evidence only; future launches choose free ports.

Installer launch evidence is narrower than clean-computer end-to-end reconstruction on every platform. The free unsigned Windows/macOS installers can show operating-system approval prompts. Docker setup is separate. No Windows/macOS automatic controller transfer or universal aircraft/firmware compatibility is claimed.
