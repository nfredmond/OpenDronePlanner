# OpenDronePlanner

Local desktop mission planner, extended from Waypoint Transfer. Python backend, TypeScript/Leaflet frontend, native Qt6 shell. Use the current checkout and read README.md, docs/API.md and docs/VERIFICATION.md first.

## Boundaries

- Keep actual flight files, controller identity, backups, downloaded terrain and private screenshots outside the public repository. Test fixtures must say synthetic and never be sent to hardware.
- Controller discovery is read-only; copying a plan changes a saved DJI Fly flight. Obtain task-specific authorization for real controller mutation. Never arm or fly an aircraft.
- Keep transfer.py and mtp_io.py backup, staging, readback, recovery and identity checks. Do not replace them with an unverified file-copy shortcut.
- Structural WPML validation is not DJI Fly or aircraft execution proof. Preserve unknown states. Never fill missing terrain with zero or silently drop unknown actions.
- Use local/free tools. Do not provision paid services.
- Check other sessions and git state before edits. Own disjoint files if delegation is expressly requested.

## Work and verification

Run `npm run build` for frontend changes. Python commands use `.venv/bin/python`, created with system Qt access by install.sh. No global pip modifications.

`ODP_DATA_DIR=/tmp/odp-test .venv/bin/python server.py --port 8765 --offline` runs an isolated UI test server. Confirm `/api/status` root and PID against the listening process. Enter through the root page and exercise the controls. Native launch: `./launch-planner.sh --offline`. Browser test mode requires Ctrl+C to stop its port; normal desktop close stops its service.

Run the targeted unittest modules and mutation checks listed in README. Mutation runners work in isolated temporary copies and never touch USB. A no-op control must survive before trusting killed mutations. Test reports cannot establish actual flight behavior.

Document expensive findings and remaining work here in docs. Commit natural checkpoints. Do not publish private local history when preparing public exports.

## Processing and distribution

The app now has Plan / Export & controller / Process & present workflows. Read docs/PROCESSING.md and docs/DISTRIBUTION.md. `processing.py` owns capture custody and a dedicated `odp-processing` Compose stack. `web/src/processing.ts` owns its UI. `desktop.py` embeds full WebODM and owns the loopback service lifetime.

Preserve existing independent WebODM installations and their Docker volumes. ODP's containers use restart=no. CPU is the default, CUDA is optional and must pass a real Docker device probe. Pinned engine images currently run linux/amd64, including emulation on Apple Silicon. Do not claim every stage uses GPU or equate startup with successful reconstruction.

Capture originals, settings/credentials, Docker volumes, reports and delivery archives are private data. Do not commit them. A checksum proves byte identity, not positional accuracy. Do not invent checkpoint or flight evidence. Test reconstructions use identified public sample photos in local application data, not synthetic images presented as flight records.

Use the authenticated processing API documented in docs/API.md for agent access. Never print session tokens or generated engine credentials. `--offline` disables controller access; it does not disable Docker or internet maps. Finish/cancel active jobs before stopping the owned stack. App close checks upstream jobs, including those created in the full WebODM tab.

Run test_processing and check_processing_mutations.py alongside the planner/server/transfer checks. Installer builds must launch the bundled root UI, reach Process, record the native screenshot and verify the port closes. A successful build alone does not prove startup. The tag workflow creates a draft release; review four platform results before publishing. Public releases must contain binaries from the tagged source, checksums and launch evidence.
