"""Terrain sampling: explicit source, complete coverage, never fabricate elevations."""
from copy import deepcopy
import json
import math
import threading
import time
from pathlib import Path
import urllib.request
from urllib.parse import urlencode
from planner import coord, distance


def densify(m, spacing=30):
    m=deepcopy(m); out=[]; ps=m['points']
    for a,b in zip(ps,ps[1:]):
        out.append(a); count=math.ceil(distance(a,b)/spacing)
        if count+len(out)>10000: raise ValueError('Terrain sampling would exceed 10,000 points. Reduce the route extent.')
        for i in range(1,count):
            p=deepcopy(a); t=i/count
            for k in ('lat','lon','alt'): p[k]=a[k]+(b[k]-a[k])*t
            p['action']='none'; p['hover']=0; out.append(p)
    if ps: out.append(ps[-1])
    m['points']=out; return m


def apply_terrain(m, source, dem_dir: Path, cancel=None):
    if not m.get('home'): raise ValueError('Set the takeoff point on the map before loading terrain.')
    if len(m.get('points',[]))<2: raise ValueError('Generate a route before loading terrain.')
    m=densify(m); coords=[coord(m['home'])]+[coord([p['lon'],p['lat']]) for p in m['points']]
    if source=='usgs':
        if len(coords)>1500: raise ValueError('USGS lookup is limited to 1,500 samples. Use a local GeoTIFF for this route.')
        cancel=cancel or threading.Event(); deadline=time.monotonic()+120
        heights=[]; datums=set(); resolutions=[]
        for start in range(0,len(coords),100):
            if cancel.is_set() or time.monotonic()>deadline: raise ValueError('Terrain lookup cancelled or exceeded two minutes. Use a local GeoTIFF.')
            batch=coords[start:start+100]
            params=dict(f='json',geometry=json.dumps(dict(points=batch,spatialReference=dict(wkid=4326))),
                        geometryType='esriGeometryMultipoint',returnFirstValueOnly='true',
                        interpolation='RSP_BilinearInterpolation',outFields='VerticalDatum')
            url='https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/getSamples?'+urlencode(params)
            request=urllib.request.Request(url,headers={'User-Agent':'OpenDronePlanner/1.0'})
            with urllib.request.urlopen(request,timeout=20) as response: result=json.load(response)
            samples=result.get('samples',[])
            if len(samples)!=len(batch): raise ValueError('USGS returned no elevation for part of the route. Use a local terrain file.')
            indexed={int(sample['locationId']):sample for sample in samples}
            if set(indexed)!=set(range(len(batch))): raise ValueError('USGS returned incomplete or duplicate sample identities.')
            for i,c in enumerate(batch):
                sample=indexed[i]; location=sample['location']
                if abs(location['x']-c[0])>1e-6 or abs(location['y']-c[1])>1e-6: raise ValueError('USGS sample coordinates did not match the requested route.')
                try: height=float(sample.get('value',-1000000))
                except (TypeError,ValueError): raise ValueError('USGS returned no elevation for part of the route.') from None
                if not math.isfinite(height) or not -500<=height<=9000: raise ValueError('USGS returned no elevation for part of the route. Use a local terrain file.')
                datum=sample.get('attributes',{}).get('VerticalDatum')
                if not datum: raise ValueError('USGS did not identify the vertical datum. Use a local terrain file.')
                datums.add(datum); heights.append(height); resolutions.append(float(sample.get('resolution',0)))
        if len(datums)!=1: raise ValueError('USGS samples cross vertical datums. Use a consistent local DEM.')
        label='USGS 3DEP · '+next(iter(datums))+' · source resolution '+str(round(max(resolutions),1))+' m · sampled ≤30 m'
    else:
        if not source or not all(c in 'abcdef0123456789' for c in source): raise ValueError('Invalid terrain file identifier.')
        import rasterio
        from pyproj import Transformer
        with rasterio.open(dem_dir/(source+'.tif')) as ds:
            if not ds.crs: raise ValueError('GeoTIFF has no coordinate reference system.')
            if ds.count<1: raise ValueError('GeoTIFF has no elevation band.')
            unit=(ds.units[0] or '').lower()
            if unit and unit not in ('m','metre','meter','metres','meters'): raise ValueError('Convert this DEM vertical units to meters before importing.')
            f=Transformer.from_crs(4326,ds.crs,always_xy=True)
            xy=[f.transform(*c) for c in coords]
            if any(not (ds.bounds.left<=x<ds.bounds.right and ds.bounds.bottom<y<=ds.bounds.top) for x,y in xy): raise ValueError('The terrain raster does not cover the entire route and takeoff point.')
            heights=[]
            for sample in ds.sample(xy,indexes=1,masked=True):
                if sample.mask[0] or not math.isfinite(float(sample[0])) or not -500<=float(sample[0])<=9000: raise ValueError('Terrain has missing elevation cells along this route.')
                heights.append(float(sample[0]))
        label='Local GeoTIFF · band 1 in meters · sampled ≤30 m'
    m['settings']['homeElevation']=heights[0]; m['settings']['terrain']=True
    for p,h in zip(m['points'],heights[1:]):
        p['ground']=h; p['alt']=round(m['settings']['altitude']+h-heights[0],3)
    m['terrainSource']=label; return m
