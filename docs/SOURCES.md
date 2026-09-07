# Sources and dependency notes

Inspected during the September 2026 implementation:

- [WaypointMap test editor](https://test.waypointmap.com/Home/Editor): observed UI, drawing, generation, advanced controls and export workflow.
- [WaypointMap premium description](https://test.waypointmap.com/Home/Premium): advertised premium capabilities. No paid source, installer or access restriction was bypassed.
- [DJI WPML reference source](https://github.com/dji-sdk/Cloud-API-Doc/tree/master/docs/en/60.api-reference/00.dji-wpml): waypoint structure, action groups, height references, mission configuration. Its enterprise support tables do not establish consumer DJI Fly compatibility.
- [Leaflet reference](https://leafletjs.com/reference): map layers, markers, drawing primitives and box selection bounds. Leaflet is BSD-2-Clause.
- [Shapely](https://shapely.readthedocs.io/): planar geometry, clipping, validity and coverage. BSD-3-Clause; GEOS has its own LGPL license.
- [pyproj](https://pyproj4.github.io/pyproj/stable/): geographic/projected transforms and geodesic distances. MIT, with PROJ dependencies.
- [rasterio](https://rasterio.readthedocs.io/): raster CRS, bounds, nodata and sample access. BSD-3-Clause, with GDAL and other bundled dependency licenses.
- [Qt for Python/PyQt licensing](https://www.riverbankcomputing.com/software/pyqt/): system PyQt6/Qt WebEngine dependencies retain GPL/commercial and Qt licensing. ODP source is MIT; distributing a packaged Qt/PyQt runtime requires following those dependencies' licenses. The installer uses system packages, rather than redistributing a proprietary runtime.
- [USGS 3DEP service](https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer): live source, vertical datum, sample resolution, and bare-earth elevation description.
- [Esri Get Samples](https://developers.arcgis.com/rest/services-reference/enterprise/get-samples/): multipoint elevation query, returned sample identities and coordinates. ODP validates identity, coordinates, datum and completeness before applying elevations.
- [USGS elevation accuracy](https://www.usgs.gov/faqs/how-accurate-elevation-data-elevation-point-query-service): elevation estimates differ from survey control and vary by source.
- [OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/), [Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/), [OSM attribution](https://www.openstreetmap.org/copyright): interactive use with visible attribution; no offline bulk tile scraping.
- [KDE MTP implementation](https://github.com/KDE/kio-extras/blob/master/mtp/kiod_module/mtpstorage.cpp): shared KDE MTP operations, asynchronous copy signals, staging and rename.

The planner sends no data to an AI service. There are no commercial API keys. Public map/elevation/search services have availability and usage constraints; local raster terrain remains usable without their availability.
