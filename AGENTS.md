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
