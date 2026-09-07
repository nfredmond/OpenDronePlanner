"""Bounded import and independently generated DJI WPML exports."""
from copy import deepcopy
import base64
import io
import json
import time
import xml.etree.ElementTree as ET
import zipfile
from planner import DEFAULTS, coord, settings, waypoint, review, split_mission
from transfer import validate, MAX_FILE

K='http://www.opengis.net/kml/2.2'; W='http://www.dji.com/wpmz/1.0.2'
ET.register_namespace('',K); ET.register_namespace('wpml',W)


def xml(data):
    if len(data)>64*1024*1024: raise ValueError('XML exceeds 64 MB.')
    text=data.decode('utf-8-sig')
    if '\x00' in text or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper(): raise ValueError('Unsafe XML declaration.')
    return ET.fromstring(text)


def local(el): return el.tag.split('}')[-1]


def text(el,name,default=None): return el.findtext('.//{*}'+name,default)


def import_file(name,data):
    if len(data)>MAX_FILE: raise ValueError('Import exceeds 20 MB.')
    m=dict(version=1,name=name.rsplit('.',1)[0],mode='survey',settings=deepcopy(DEFAULTS),shapes=[],points=[],home=None,profile=None,heightMode='relativeToStartPoint')
    if name.lower().endswith('.json'):
        value=json.loads(data)
        if value.get('version')==1 and 'points' in value:
            review(value); return value
        features=value.get('features',[value])
        for feature in features:
            g=feature.get('geometry',feature); kind=g.get('type'); cs=g.get('coordinates')
            if kind=='Polygon':
                m['shapes'].append(dict(kind='exclusion' if feature.get('properties',{}).get('role')=='exclusion' else 'area',coords=[coord(c) for c in cs[0]]))
                m['shapes'] += [dict(kind='exclusion',coords=[coord(c) for c in ring]) for ring in cs[1:]]
            elif kind=='LineString': m['shapes'].append(dict(kind='corridor',coords=[coord(c) for c in cs]))
            elif kind=='Point':
                p=waypoint(coord(cs),m['settings'])
                props=feature.get('properties',{})
                for key in ('alt','speed','gimbal','heading','action','hover'):
                    if key in props: p[key]=props[key]
                m['points'].append(p)
        if not m['shapes'] and not m['points']: raise ValueError('No supported geometry in this GeoJSON.')
        return m
    if name.lower().endswith('.kmz'):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos=z.infolist()
            if len(infos)>128 or sum(i.file_size for i in infos)>64*1024*1024: raise ValueError('Archive exceeds import limits.')
            if 'wpmz/waylines.wpml' in z.namelist():
                validate(data); root=xml(z.read('wpmz/waylines.wpml'))
                template=xml(z.read('wpmz/template.kml'))
                config=root.find('.//{*}missionConfig')
                m['profile']=dict(aircraft=text(config,'droneEnumValue'),sub=text(config,'droneSubEnumValue','0'),
                                  namespace=next((e.tag[1:].split('}')[0] for e in root.iter() if local(e)=='missionConfig'),W),
                                  config=ET.tostring(config,encoding='unicode'),name='Aircraft '+text(config,'droneEnumValue','unknown'))
                m['settings']['finish']=text(config,'finishAction','goHome')
                m['settings']['lost']=text(config,'executeRCLostAction','goBack')
                m['heightMode']=text(root,'executeHeightMode','relativeToStartPoint')
                folders=root.findall('.//{*}Folder')
                if len(folders)!=1: raise ValueError('This KMZ has multiple executable routes. Import one route at a time.')
                for point in root.findall('.//{*}Placemark'):
                    c=coord([float(v) for v in text(point,'coordinates','').split(',')])
                    p=waypoint(c,m['settings']); p['alt']=float(text(point,'executeHeight','60'))
                    p['speed']=float(text(point,'waypointSpeed',text(root,'autoFlightSpeed','3.5')))
                    p['action']='none'; p['gimbal']=float(text(point,'gimbalPitchAngle','-90'))
                    heading=point.find('.//{*}waypointHeadingParam')
                    if heading is not None and text(heading,'waypointHeadingMode')!='followWayline': p['heading']=float(text(heading,'waypointHeadingAngle','0'))
                    unsupported=[]; camera_actions=[]
                    for group in point.findall('.//{*}actionGroup'):
                        group_actions=group.findall('{*}action')
                        if group_actions and all(text(a,'actionActuatorFunc')=='gimbalEvenlyRotate' for a in group_actions):
                            start=int(text(group,'actionGroupStartIndex','-1')); end=int(text(group,'actionGroupEndIndex','-1'))
                            if start==len(m['points']) and end in (start,start+1):
                                p['gimbalEnd']=float(text(group_actions[-1],'gimbalPitchRotateAngle',str(p['gimbal'])))
                                continue
                        if text(group,'actionTriggerType')!='reachPoint' or text(group,'actionGroupStartIndex')!=text(group,'actionGroupEndIndex'):
                            unsupported.append('spanning/interval action group'); continue
                        acts=[]
                        for act in group.findall('{*}action'):
                            kind=text(act,'actionActuatorFunc')
                            if kind=='gimbalRotate': p['gimbal']=float(text(act,'gimbalPitchRotateAngle','-90'))
                            elif kind=='hover': p['hover']+=float(text(act,'hoverTime','0'))
                            elif kind in ('takePhoto','startRecord','stopRecord'): acts.append(kind)
                            else: unsupported.append(kind or 'unknown action')
                        if len(acts)>1: unsupported.append('multiple camera actions at one point')
                        elif acts: camera_actions.extend(acts); p['action']=acts[0]
                    if len(camera_actions)>1: unsupported.append('multiple camera actions at one point')
                    if unsupported: p['unsupported']=unsupported
                    m['points'].append(p)
                if m['points']:
                    p=m['points'][0]
                    for key,pk in [('altitude','alt'),('speed','speed'),('gimbal','gimbal'),('action','action')]: m['settings'][key]=p[pk]
                m['sourceOriginal']=base64.b64encode(data).decode()
                m['importNotes']=['Executable waylines imported. The original KMZ is retained for unchanged transfer.']
                tf=text(template,'finishAction')
                if tf!=m['settings']['finish']: m['importNotes'].append('Original template and executable finish actions differ. The editor uses the executable action; regenerated export makes both consistent.')
                return m
            candidates=[i.filename for i in infos if i.filename.lower().endswith('.kml')]
            if not candidates: raise ValueError('KMZ contains no KML.')
            root=xml(z.read(candidates[0]))
    else: root=xml(data)
    for el in root.iter():
        kind=local(el)
        if kind not in ('Polygon','LineString','Point'): continue
        if kind=='Polygon':
            outer=el.find('.//{*}outerBoundaryIs/{*}LinearRing/{*}coordinates')
            if outer is not None:
                cs=[coord([float(v) for v in c.split(',')]) for c in (outer.text or '').split()]
                m['shapes'].append(dict(kind='area',coords=cs))
            for inner in el.findall('.//{*}innerBoundaryIs/{*}LinearRing/{*}coordinates'):
                m['shapes'].append(dict(kind='exclusion',coords=[coord([float(v) for v in c.split(',')]) for c in (inner.text or '').split()]))
        else:
            cs=[coord([float(v) for v in c.split(',')]) for c in text(el,'coordinates','').split()]
            if kind=='Point': m['points'] += [waypoint(c,m['settings']) for c in cs]
            elif cs: m['shapes'].append(dict(kind='corridor',coords=cs))
    if not m['points'] and not m['shapes']: raise ValueError('No polygon, line or waypoint in this file.')
    return m


def sub(parent,name,value=None,ns=W):
    e=ET.SubElement(parent,'{'+ns+'}'+name)
    if value is not None: e.text=str(value)
    return e


def export_kmz(m):
    report=review(m)
    if report['errors']: raise ValueError(' '.join(report['errors']))
    s=settings(m['settings']); ps=m['points']; profile=m['profile']; namespace=profile.get('namespace',W)
    if len(ps)>int(s['maxPoints']): raise ValueError('Too many points for one flight. Use split mission export.')
    def w(parent,name,value=None): return sub(parent,name,value,namespace)
    def config(doc):
        cfg=xml(profile['config'].encode())
        for name,value in [('finishAction',s['finish']),('executeRCLostAction',s['lost']),('exitOnRCLost','executeLostAction'),('flyToWaylineMode','safely'),('globalTransitionalSpeed',s['speed'])]:
            el=cfg.find('{*}'+name)
            if el is None: w(cfg,name,value)
            else: el.text=str(value)
        doc.append(cfg)
    def document(template):
        root=ET.Element('{'+K+'}kml'); doc=sub(root,'Document',ns=K)
        sub(doc,'name',m['name'],K); w(doc,'author','OpenDronePlanner'); w(doc,'createTime',int(time.time()*1000)); w(doc,'updateTime',int(time.time()*1000))
        config(doc); folder=sub(doc,'Folder',ns=K); w(folder,'templateId',0)
        if template:
            w(folder,'templateType','waypoint'); coordinate=w(folder,'waylineCoordinateSysParam')
            w(coordinate,'coordinateMode','WGS84'); w(coordinate,'heightMode','relativeToStartPoint'); w(folder,'globalHeight',s['altitude'])
            w(folder,'caliFlightEnable',0); w(folder,'gimbalPitchMode','usePointSetting')
        else:
            w(folder,'executeHeightMode','relativeToStartPoint'); w(folder,'waylineId',0)
            w(folder,'distance',round(report['distance'],3)); w(folder,'duration',round(report['seconds'],3))
        w(folder,'autoFlightSpeed',s['speed'])
        for i,p in enumerate(ps):
            pm=sub(folder,'Placemark',ns=K); pt=sub(pm,'Point',ns=K)
            sub(pt,'coordinates',f'{p["lon"]:.10f},{p["lat"]:.10f}',K); w(pm,'index',i)
            if template:
                w(pm,'useGlobalHeight',0); w(pm,'height',p['alt']); w(pm,'ellipsoidHeight',p['alt'])
                w(pm,'useGlobalSpeed',0); w(pm,'useGlobalHeadingParam',0); w(pm,'useGlobalTurnParam',0); w(pm,'gimbalPitchAngle',p['gimbal'])
            else: w(pm,'executeHeight',p['alt'])
            w(pm,'waypointSpeed',p['speed']); heading=w(pm,'waypointHeadingParam')
            w(heading,'waypointHeadingMode','followWayline' if p['heading'] is None else 'smoothTransition')
            w(heading,'waypointHeadingAngle',p['heading'] or 0); w(heading,'waypointPoiPoint','0,0,0')
            w(heading,'waypointHeadingAngleEnable',int(p['heading'] is not None)); w(heading,'waypointHeadingPathMode','followBadArc')
            turn=w(pm,'waypointTurnParam'); w(turn,'waypointTurnMode','toPointAndStopWithContinuityCurvature' if s['straight'] else 'toPointAndPassWithContinuityCurvature')
            w(turn,'waypointTurnDampingDist',0 if s['straight'] else .2); w(pm,'useStraightLine',int(s['straight']))
            group=w(pm,'actionGroup'); w(group,'actionGroupId',i*2); w(group,'actionGroupStartIndex',i); w(group,'actionGroupEndIndex',i)
            w(group,'actionGroupMode','sequence'); trigger=w(group,'actionTrigger'); w(trigger,'actionTriggerType','reachPoint')
            def action(kind,params):
                a=w(group,'action'); w(a,'actionId',len(group.findall('{*}action'))-1); w(a,'actionActuatorFunc',kind)
                ap=w(a,'actionActuatorFuncParam')
                for key,val in params.items(): w(ap,key,val)
            action('gimbalRotate',dict(gimbalHeadingYawBase='aircraft',gimbalRotateMode='absoluteAngle',gimbalPitchRotateEnable=1,
                    gimbalPitchRotateAngle=p['gimbal'],gimbalRollRotateEnable=0,gimbalRollRotateAngle=0,gimbalYawRotateEnable=0,
                    gimbalYawRotateAngle=0,gimbalRotateTimeEnable=0,gimbalRotateTime=0,payloadPositionIndex=0))
            if p['hover']: action('hover',dict(hoverTime=p['hover']))
            if p['action']!='none': action(p['action'],dict(payloadPositionIndex=0,fileSuffix='ODP',useGlobalPayloadLensIndex=1))
            if p.get('gimbalEnd') is not None and i<len(ps)-1:
                group=w(pm,'actionGroup'); w(group,'actionGroupId',i*2+1); w(group,'actionGroupStartIndex',i); w(group,'actionGroupEndIndex',i+1)
                w(group,'actionGroupMode','sequence'); trigger=w(group,'actionTrigger'); w(trigger,'actionTriggerType','betweenAdjacentPoints')
                action('gimbalEvenlyRotate',dict(gimbalPitchRotateAngle=p['gimbalEnd'],payloadPositionIndex=0))
        return ET.tostring(root,encoding='utf-8',xml_declaration=True)
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('wpmz/template.kml',document(True)); archive.writestr('wpmz/waylines.wpml',document(False))
    data=stream.getvalue(); validate(data); return data


def export_split(m):
    parts=split_mission(m); stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        for i,part in enumerate(parts): z.writestr(f'flight-{i+1:02d}.kmz',export_kmz(part))
        z.writestr('README.txt',f'{len(parts)} separate flights. Each shares an endpoint with the next. Launch each manually after battery replacement. Review all flights in DJI Fly. Estimates exclude wind and aircraft acceleration.')
    return stream.getvalue()
