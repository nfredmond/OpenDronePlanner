# Third-party software

ODP source is MIT licensed. Bundled desktop releases use PySide6 and Qt under their LGPL/GPL/commercial upstream terms, including Qt WebEngine and Chromium notices. PyInstaller retains its bootloader exception. The bundle keeps libraries separate so they can be replaced. Source and notices: https://code.qt.io/cgit/pyside/pyside-setup.git/ and https://code.qt.io/cgit/qt/ . Qt license texts are retained with the installed PySide6 package.

Leaflet is BSD-2-Clause. Shapely is BSD-3-Clause, rasterio BSD-3-Clause, pyproj MIT, Pillow HPND, NumPy BSD-3-Clause, PROJ MIT, GDAL MIT-style. See the distributions' LICENSE files for dependencies and exceptions.

WebODM, NodeODX and ODX run as separate, unmodified official containers downloaded when processing is requested. They are AGPL-3.0 software, not ODP-authored engines. Their source, license, contributor and trademark notices remain available at https://github.com/WebODM/WebODM , https://github.com/WebODM/NodeODX , and https://github.com/WebODM/ODX . ODP does not remove attribution or provide access to paid hosted engines. Optional NVIDIA runtime components retain NVIDIA's terms.

Map data and imagery retain provider attribution and terms. Downloadable reports contain user data and should be reviewed before sharing.
