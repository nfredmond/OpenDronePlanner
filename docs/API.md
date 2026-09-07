# Local API and command-line tools

The easiest agent interface needs no running server:

```bash
.venv/bin/python cli.py import input.kmz -o mission.json
.venv/bin/python cli.py review mission.json
.venv/bin/python cli.py generate mission.json -o generated.json
.venv/bin/python cli.py export generated.json -o flight.kmz
.venv/bin/python cli.py split generated.json -o flights.zip
```

These commands never access USB. `generate` uses the project's shapes and settings. `export` uses its executable points and blocks red review errors.

## Project format

`version: 1`, `name`, `mode` (`survey`, `corridor`, `orbit`, `manual`), `settings`, `shapes`, `points`, `home`, `profile`, `heightMode`. Coordinates are `[longitude, latitude]`, WGS84 degrees. Distances, speeds and elevations are meters and meters/second internally, regardless of display units.

Shapes use `kind: area | exclusion | corridor | poi` and `coords`. Waypoints use `lon`, `lat`, `alt` relative to takeoff, `speed`, `gimbal`, `heading` or null for follow-route, `action: none | takePhoto | startRecord | stopRecord`, `hover`, `ground` or null, and optional `gimbalEnd`. `profile` comes from a known-good DJI mission; do not guess a consumer aircraft identifier. `sourceOriginal`, when present, is the base64 original KMZ and may contain private flight data.

## HTTP service

The desktop binds only `127.0.0.1` on a dynamically assigned port. For a fixed development port:

```bash
ODP_DATA_DIR=/tmp/odp-dev .venv/bin/python server.py --port 8765 --offline
```

GET `/session.js` from the same origin supplies a short-lived token. API requests require `X-ODP-Token`, the correct Host header and matching Origin when supplied. Cross-origin browser resource requests are rejected. Do not publish the token or expose the service beyond loopback.

| Endpoint | Method | Body/result |
|---|---|---|
| `/api/status` | GET | App version, checkout root, PID, defaults, offline flag |
| `/api/library` | GET | Local missions and presets |
| `/api/profile` | GET | Last imported aircraft profile |
| `/api/draft` | GET/POST | Read current draft; write `{mission}` |
| `/api/import` | POST | `{name, data}` base64 KMZ/KML/JSON; returns project |
| `/api/generate` | POST | `{mission}`; returns generated project |
| `/api/review` | POST | `{mission}`; returns errors, warnings and estimates |
| `/api/save` | POST | `{kind: missions or presets, id?, value}`; returns ID |
| `/api/archive` | POST | `{kind, id}`; retains an `.archived` file locally |
| `/api/terrain-file` | POST | `{data}` base64 GeoTIFF; returns content ID |
| `/api/terrain` | POST | `{mission, source: usgs or terrain ID}`; returns job |
| `/api/search` | POST | `{query}`; Nominatim search job |
| `/api/export` | POST | `{mission, format: kmz or split}`; base64 data |
| `/api/job/{id}` | GET | `{done, result?}`; failed jobs return an error |
| `/api/controller` | POST | Discovery job; no flight mutation |
| `/api/transfer` | POST | `{mission, original: boolean}`; backs up and replaces a saved flight |
| `/api/restore` | POST | Restores the recorded controller backup |
| `/api/reset-slot` | POST | Archives the remembered slot choice |

`--offline` blocks every controller operation. Terrain and controller work run in background workers and expose pollable jobs. No shell command or arbitrary-path execution endpoint exists.
