"""Synthetic geometry and archive regressions. Never access a controller."""
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon,LineString
import planner as p
import formats as f
import terrain as t


def mission():
    # Synthetic fixture around a public geographic coordinate; never for flight.
    return dict(version=1,name='SYNTHETIC TEST - NOT FOR FLIGHT',mode='survey',settings=deepcopy(p.DEFAULTS),
                shapes=[dict(kind='area',coords=[[-121,39],[-120.998,39],[-120.998,39.002],[-121,39.002]])],
                points=[],home=[-121,39],heightMode='relativeToStartPoint',
                profile=dict(aircraft='67',sub='0',name='Synthetic profile',namespace=f.W,config=f'<wpml:missionConfig xmlns:wpml="{f.W}"><wpml:finishAction>noAction</wpml:finishAction><wpml:droneInfo><wpml:droneEnumValue>67</wpml:droneEnumValue><wpml:droneSubEnumValue>0</wpml:droneSubEnumValue></wpml:droneInfo></wpml:missionConfig>'))


class PlanningTests(unittest.TestCase):
    def test_grid_avoids_hole_and_stays_inside(self):
        m=mission();hole=[[-120.9994,39.0005],[-120.9988,39.0005],[-120.9988,39.0015],[-120.9994,39.0015]]
        m['shapes'].append(dict(kind='exclusion',coords=hole));m['settings']['autoAngle']=False;m['settings']['angle']=0
        result=p.generate(m);fwd,_=p.projection(m['shapes'][0]['coords'])
        area=Polygon([fwd(*c) for c in m['shapes'][0]['coords']],[list(fwd(*c) for c in hole)])
        route=LineString([fwd(w['lon'],w['lat']) for w in result['points']])
        self.assertGreater(len(result['points']),20)
        self.assertTrue(area.buffer(.002).covers(route),'route left boundary or entered excluded area')
        self.assertEqual(p.review(result)['errors'],[])

    def test_crosshatch_adds_second_grid(self):
        m=mission();m['settings']['autoAngle']=False;single=p.generate(m);m['settings']['angle']=90;perpendicular=p.generate(m);m['settings']['angle']=0;m['settings']['crosshatch']=True;double=p.generate(m)
        self.assertEqual(len(double['points']),len(single['points'])+len(perpendicular['points']))
        self.assertAlmostEqual(double['area'],single['area'])

    def test_orbit_radius_and_heading(self):
        m=mission();m['mode']='orbit';m['shapes']=[dict(kind='poi',coords=[[-121,39]])]
        out=p.generate(m);self.assertEqual(len(out['points']),37)
        for point in out['points']:
            az,_,d=p.GEOD.inv(-121,39,point['lon'],point['lat'])
            self.assertAlmostEqual(d,50,places=2)
            self.assertAlmostEqual(((point['heading']-az)%360),180,places=5)

    def test_review_blocks_exclusion_crossing(self):
        m=mission();m['points']=[p.waypoint([-121,39.001],m['settings']),p.waypoint([-120.998,39.001],m['settings'])]
        m['shapes'].append(dict(kind='exclusion',coords=[[-120.9995,39.0005],[-120.999,39.0005],[-120.999,39.0015],[-120.9995,39.0015]]))
        self.assertTrue(any('exclusion' in e for e in p.review(m)['errors']))
        with self.assertRaisesRegex(ValueError,'exclusion'):f.export_kmz(m)

    def test_split_keeps_every_leg_and_budget(self):
        m=p.generate(mission());m['settings']['maxPoints']=20
        parts=p.split_mission(m);self.assertGreater(len(parts),1)
        joined=[]
        for i,part in enumerate(parts):
            self.assertLessEqual(len(part['points']),20)
            self.assertLessEqual(p.review(part)['seconds'],900)
            if i:self.assertEqual(parts[i-1]['points'][-1],part['points'][0])
            joined+=part['points'] if i==0 else part['points'][1:]
        self.assertEqual(joined,m['points'])

    def test_invalid_numbers_and_altitude_ceiling(self):
        m=mission();m['settings']['speed']=float('nan')
        with self.assertRaisesRegex(ValueError,'speed'):p.generate(m)
        m=p.generate(mission());m['points'][0]['alt']=500
        self.assertTrue(any('ceiling' in e for e in p.review(m)['errors']))

    def test_export_roundtrip_actions_and_finish(self):
        m=p.generate(mission());m['points']=m['points'][:8]
        for i,w in enumerate(m['points']):w.update(heading=i*10,gimbal=-80+i,hover=i,action=['none','takePhoto','startRecord','stopRecord'][i%4])
        m['points'][0]['gimbalEnd']=-45
        data=f.export_kmz(m)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in ('wpmz/template.kml','wpmz/waylines.wpml'):
                root=ET.fromstring(z.read(name));self.assertEqual(root.findtext('.//{*}finishAction'),'goHome')
                self.assertEqual(root.findtext('.//{*}droneEnumValue'),'67')
                indexes=[int(w.findtext('{*}index')) for w in root.findall('.//{*}Placemark')]
                self.assertEqual(indexes,list(range(8)))
        imported=f.import_file('test.kmz',data)
        for a,b in zip(m['points'],imported['points']):
            for key in ('alt','speed','gimbal','heading','hover','action'):
                self.assertEqual(a[key],b[key],key)
            self.assertAlmostEqual(a['lon'],b['lon'],places=8)
            self.assertFalse(b.get('unsupported'))
        self.assertEqual(imported['points'][0]['gimbalEnd'],-45)

    def test_unsupported_actions_and_absolute_height_block_export(self):
        m=p.generate(mission());m['points']=m['points'][:3];m['points'][0]['unsupported']=['focus']
        with self.assertRaisesRegex(ValueError,'Imported actions'):f.export_kmz(m)
        del m['points'][0]['unsupported'];m['heightMode']='WGS84'
        with self.assertRaisesRegex(ValueError,'absolute-height'):f.export_kmz(m)

    def test_xml_entities_refused(self):
        with self.assertRaisesRegex(ValueError,'Unsafe XML'):f.import_file('bad.kml',b'<!DOCTYPE kml [<!ENTITY a "x">]><kml>&a;</kml>')

    def test_geojson_exclusion_and_point_fields(self):
        value=dict(type='FeatureCollection',features=[dict(type='Feature',properties={'role':'exclusion'},geometry={'type':'Polygon','coordinates':[[[-121,39],[-120.99,39],[-120.99,39.01],[-121,39]]]}),dict(type='Feature',properties={'alt':80,'speed':4,'action':'stopRecord'},geometry={'type':'Point','coordinates':[-121,39]})])
        out=f.import_file('test.json',json.dumps(value).encode())
        self.assertEqual(out['shapes'][0]['kind'],'exclusion');self.assertEqual(out['points'][0]['alt'],80);self.assertEqual(out['points'][0]['action'],'stopRecord')

    def test_local_terrain_and_missing_coverage(self):
        m=mission();m['settings']['dense']=False;m=p.generate(m);m['points']=m['points'][:5]
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'abc.tif';transform=from_origin(-121.01,39.01,.0001,.0001)
            values=np.tile(np.arange(200,dtype='float32')[:,None],(1,200))+500
            with rasterio.open(path,'w',driver='GTiff',height=200,width=200,count=1,dtype='float32',crs='EPSG:4326',transform=transform,nodata=-9999) as ds:ds.write(values,1)
            out=t.apply_terrain(m,'abc',Path(td))
            self.assertTrue(out['settings']['terrain']);self.assertGreater(len(out['points']),len(m['points']))
            for w in out['points']:self.assertAlmostEqual(w['alt']+out['settings']['homeElevation']-w['ground'],60)
            m['home']=[-122,39]
            with self.assertRaisesRegex(ValueError,'cover'):t.apply_terrain(m,'abc',Path(td))

    def test_missing_terrain_never_becomes_zero(self):
        m=p.generate(mission());m['points']=m['points'][:2]
        def response(request,timeout):
            from urllib.parse import urlsplit,parse_qs
            coords=json.loads(parse_qs(urlsplit(request.full_url).query)['geometry'][0])['points']
            samples=[dict(locationId=i,location=dict(x=c[0],y=c[1]),value=-1000000,attributes=dict(VerticalDatum='test'),resolution=1) for i,c in enumerate(coords)]
            return io.StringIO(json.dumps(dict(samples=samples)))
        with patch('terrain.urllib.request.urlopen',side_effect=response):
            with self.assertRaisesRegex(ValueError,'no elevation'):t.apply_terrain(m,'usgs',Path('/unused'))

if __name__=='__main__':unittest.main()
