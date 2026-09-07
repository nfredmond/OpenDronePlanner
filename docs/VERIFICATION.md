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

Test screenshots, real flight data, device identifiers and backup receipts are intentionally excluded from the public source history. Public screenshots, if included, contain only explicitly labeled synthetic planning examples.

## Native export and lifecycle checks

The native **Export DJI KMZ** button opened a save dialog and wrote a 98-waypoint synthetic mission. Independent archive parsing confirmed 98 executable points, the intended `goHome` end action, and no structural review errors. The flight/ground profile retained real USGS sample provenance in the ODP project; the KMZ carries the resulting takeoff-relative heights.

Closing the first native test window through its normal close action ended its process and released its port. The browser development service is separate and is stopped explicitly after testing.

## Narrow layout and installation

The native window was inspected at approximately 390 CSS pixels wide, both with the map visible and with the planning panel open. This caught and fixed header overlap and map controls appearing above the sidebar. The final narrow screenshots show reachable planning controls and a separate map view.

The installer was exercised in the clean OpenDronePlanner checkout. It created its own virtual environment, built the frontend and installed both desktop shortcuts. The original local development history is preserved separately; public history starts from the audited source export.

Saved-project identity is covered by a regression and mutation probe, preventing a reopened draft from losing the saved-library identity.

The installed desktop icon was launched and its listening process was matched to the clean OpenDronePlanner checkout through `/api/status` and the process working directory. Closing that window released its exact port; reopening the icon restored the saved draft. No ODP or Waypoint Transfer entry was found in the user's login autostart configuration. Small imported routes now fit at higher display zoom, with basemap tiles enlarged only beyond their native resolution.
