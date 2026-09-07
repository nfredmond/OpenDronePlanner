# WaypointMap feature coverage

Observed in the signed-in test editor and public premium description on 2026-09-06. Premium controls were disabled in the source service; their labels and public descriptions establish advertised behavior, not hands-on verification of its implementation. No paid software or private source was copied.

| Observed capability | ODP implementation |
|---|---|
| Polygon / rectangle / multiple areas | Map drawing tools; editable boundary handles |
| POI and orbit | POI tool and Orbit mission pattern |
| Manual waypoint placement/editing | Waypoint tool and Route editor |
| Undo / redo / group selection | History, Ctrl-click, Select all, Shift-drag group/zoom |
| Location search; map/satellite | Nominatim search, coordinates, OSM/Esri/USGS basemaps |
| Simple quality / overlap | Explicit front and side overlap, photo density and camera assumptions |
| Altitude, speed, metric/imperial | Plan settings and per-point editing; meters internally |
| Leg spacing; auto and custom direction | Overlap spacing or override, longest-edge or chosen angle |
| Reverse / straight legs | Route reversal and straight-stop turn setting |
| Camera gimbal and per-point photo/video actions | Global generation defaults and grouped/per-point edits |
| Generate every point | Dense photo positions derived from front overlap |
| Nadir reference windows | Optional middle-of-leg nadir window; no GPS accuracy claim |
| KML / KMZ import | Boundaries and executable DJI waypoints; unknown actions block rewritten export |
| Terrain-aware altitude | USGS or local raster, ≤30 m route sampling, relative-takeoff conversion and profile |
| Save/load mission | Local library, autosaved draft, portable ODP project |
| Save presets | Local named settings presets |
| Mission time and splitting | Point limit plus battery budget, shared split endpoints, home transit estimates |
| End action; KMZ download | Explicit finish/lost-signal policy in both template and executable XML |
| Automatic controller installer | Existing Linux/KDE backup, staged copy, readback and recovery; native transfer utility |
| API access | Local CLI and authenticated loopback API |

ODP also adds corridors, exclusion routing/checks, route animation, GeoJSON/CSV/KML exports and a printable field brief. The original website's linked photogrammetry, point-cloud-editing and airspace websites are separate products, not built-in editor functions. ODP does not claim to replace those independent services.

The public consumer aircraft list is not used as proof of ODP compatibility. Profiles come from imported files. Software verification and actual DJI Fly/aircraft acceptance are kept separate in VERIFICATION.md.
