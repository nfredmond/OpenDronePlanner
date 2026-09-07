"""Mutate isolated copies, including a no-op control that must survive."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
# One target regression per behavior keeps a stale unrelated failure from hiding a survivor.
changes=[
 ('comment control','planner.py','Coordinates are longitude','Coordinates use longitude','test_planner.PlanningTests.test_grid_avoids_hole_and_stays_inside',True),
 ('exclusion geometry','planner.py','.difference(unary_union(exclusions))','','test_planner.PlanningTests.test_grid_avoids_hole_and_stays_inside',False),
 ('crosshatch','planner.py',"if s['crosshatch'] else",'if False else','test_planner.PlanningTests.test_crosshatch_adds_second_grid',False),
 ('orbit radius','planner.py',"s['radius']*math.sin(a)","s['radius']*2*math.sin(a)",'test_planner.PlanningTests.test_orbit_radius_and_heading',False),
 ('edited crossing','planner.py','if route.intersects(poly.buffer(-.05)):', 'if False:', 'test_planner.PlanningTests.test_review_blocks_exclusion_crossing',False),
 ('split continuity','planner.py','start=end-1','start=end','test_planner.PlanningTests.test_split_keeps_every_leg_and_budget',False),
 ('altitude ceiling','planner.py',"if any(p['alt']>s['maxAltitude'] for p in ps):",'if False:','test_planner.PlanningTests.test_invalid_numbers_and_altitude_ceiling',False),
 ('finish consistency','formats.py',"('finishAction',s['finish'])","('finishAction','noAction')",'test_planner.PlanningTests.test_export_roundtrip_actions_and_finish',False),
 ('unsupported action guard','planner.py',"if any(p.get('unsupported') for p in ps):",'if False:','test_planner.PlanningTests.test_unsupported_actions_and_absolute_height_block_export',False),
 ('entity guard','formats.py',"if '\\x00' in text or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():",'if False:','test_planner.PlanningTests.test_xml_entities_refused',False),
 ('GeoJSON exclusions','formats.py',"'exclusion' if feature.get('properties',{}).get('role')=='exclusion' else 'area'","'area'",'test_planner.PlanningTests.test_geojson_exclusion_and_point_fields',False),
 ('relative terrain math','terrain.py',"+h-heights[0]","+h",'test_planner.PlanningTests.test_local_terrain_and_missing_coverage',False),
 ('missing elevations','terrain.py','if not math.isfinite(height) or not -500<=height<=9000:', 'if False:','test_planner.PlanningTests.test_missing_terrain_never_becomes_zero',False),
 ('API token','server.py',"secrets.compare_digest(self.headers.get('X-ODP-Token',''),self.server.token)",'True','test_server.ApiTests.test_token_and_origin_required',False),
 ('disk draft','server.py',"save_json(DATA/'draft.json',body['mission'])",'pass','test_server.ApiTests.test_draft_is_saved_outside_browser_origin',False),
 ('library identity','server.py',"{**json.loads(p.read_text()),'id':p.stem}","{'id':p.stem,**json.loads(p.read_text())}",'test_server.ApiTests.test_library_identity_survives_saved_project_id',False),
 ('API host','server.py',"if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}':",'if False:','test_server.ApiTests.test_bad_host_and_traversal',False),
 ('offline USB','server.py',"if self.offline: raise ValueError('Controller access is disabled in this test session.')",'if False: pass','test_server.ApiTests.test_offline_blocks_controller_mutation',False),
]
results=[]
for name,file,before,after,test,survives in changes:
    with tempfile.TemporaryDirectory(prefix='odp-mutation-') as td:
        scratch=Path(td)
        for path in ROOT.glob('*.py'):(scratch/path.name).write_text(path.read_text())
        path=scratch/file;source=path.read_text();assert before in source,name;path.write_text(source.replace(before,after))
        run=subprocess.run([sys.executable,'-B','-m','unittest','-v',test],cwd=scratch,capture_output=True,text=True,timeout=30,env=os.environ|{'PYTHONDONTWRITEBYTECODE':'1','ODP_DATA_DIR':td+'/data'})
        survived=run.returncode==0
        assert survived==survives and (survived or 'FAIL:' in run.stderr),(name,run.stderr)
        print(name,'SURVIVED' if survived else 'CAUGHT',flush=True)
        results.append(dict(name=name,survived=survived,evidence=run.stderr))
(ROOT/'evidence').mkdir(exist_ok=True)
(ROOT/'evidence/planner-mutations.json').write_text(json.dumps(results,indent=2))
