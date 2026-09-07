"""Mission geometry and review. Coordinates are longitude, latitude; distances meters."""
from copy import deepcopy
import heapq
import math
from pyproj import CRS, Transformer, Geod
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import transform, unary_union
from shapely.affinity import rotate

GEOD = Geod(ellps='WGS84')
DEFAULTS = dict(altitude=60, speed=3.5, gimbal=-90, frontOverlap=80, sideOverlap=75,
                sensorWidth=9.6, sensorHeight=7.2, focalLength=6.7, imageWidth=4032,
                interval=3, spacing=0, angle=0, autoAngle=True, dense=True,
                action='takePhoto', straight=True, finish='goHome', lost='goBack',
                batteryMinutes=20, reserve=25, maxPoints=99, radius=50, orbitPoints=36,
                corridorWidth=40, crosshatch=False, referenceWindows=False,
                terrain=False, homeElevation=None, clearance=20, maxAltitude=120)


def number(value, label, low, high):
    if isinstance(value, bool):
        raise ValueError(f'{label} must be a number.')
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label} must be between {low} and {high}.')
    return value


def coord(c):
    return [number(c[0], 'Longitude', -180, 180), number(c[1], 'Latitude', -85, 85)]


def settings(raw):
    s = DEFAULTS | raw
    limits = dict(altitude=(1,1500), speed=(.1,20), gimbal=(-90,30), frontOverlap=(10,95),
                  sideOverlap=(10,95), sensorWidth=(1,60), sensorHeight=(1,60), focalLength=(1,200),
                  imageWidth=(100,30000), interval=(.5,60), spacing=(0,500), angle=(-360,360),
                  radius=(2,5000), orbitPoints=(8,500), corridorWidth=(2,2000),
                  batteryMinutes=(1,120), reserve=(0,80), maxPoints=(2,2000), clearance=(0,500),
                  maxAltitude=(1,1500))
    for key, bounds in limits.items():
        s[key] = number(s[key], key, *bounds)
    if s['action'] not in ('none','takePhoto','startRecord','stopRecord'):
        raise ValueError('Unknown camera action.')
    if s['finish'] not in ('goHome','noAction','autoLand','gotoFirstWaypoint'):
        raise ValueError('Unknown finish action.')
    if s['lost'] not in ('goBack','hover','landing'):
        raise ValueError('Unknown signal-loss action.')
    return s


def projection(coords):
    if not coords:
        raise ValueError('Draw an area or add waypoints first.')
    cs = [coord(c) for c in coords]
    lon, lat = cs[0]
    if any(GEOD.inv(lon,lat,*c)[2] > 100000 for c in cs):
        raise ValueError('A mission must fit within 100 km of its first point. Split this area.')
    crs = CRS.from_proj4(f'+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m')
    return (Transformer.from_crs(4326,crs,always_xy=True).transform,
            Transformer.from_crs(crs,4326,always_xy=True).transform)


def footprint(s):
    w = s['altitude'] * s['sensorWidth'] / s['focalLength']
    h = s['altitude'] * s['sensorHeight'] / s['focalLength']
    return dict(width=w, height=h, spacing=s['spacing'] or w*(1-s['sideOverlap']/100),
                photoSpacing=h*(1-s['frontOverlap']/100), gsd=w/s['imageWidth']*100)


def waypoint(c,s,**extra):
    return dict(lon=c[0],lat=c[1],alt=s['altitude'],speed=s['speed'],gimbal=s['gimbal'],
                heading=None,action=s['action'],hover=0,ground=None,**extra)


def connector(a,b,allowed):
    """Route transit legs inside the survey polygon, including around exclusions."""
    if allowed.buffer(.001).covers(LineString([a,b])):
        return [b]
    vertices = [a,b] + list(allowed.exterior.coords)[:-1]
    for ring in allowed.interiors:
        vertices += list(ring.coords)[:-1]
    if len(vertices)>350:
        raise ValueError('Boundary too detailed for routing. Simplify it to fewer than 350 vertices.')
    queue=[(0,0)]; costs={0:0}; prev={}
    while queue:
        cost,i=heapq.heappop(queue)
        if cost!=costs[i]: continue
        if i==1: break
        for j,p in enumerate(vertices):
            if j==i: continue
            d=math.dist(vertices[i],p)
            if cost+d>=costs.get(j,float('inf')): continue
            if allowed.buffer(.001).covers(LineString([vertices[i],p])):
                costs[j]=cost+d; prev[j]=i; heapq.heappush(queue,(cost+d,j))
    if 1 not in costs:
        raise ValueError('Exclusions disconnect the flight area. Plan separate missions.')
    route=[]; i=1
    while i:
        route.append(vertices[i]); i=prev[i]
    return route[::-1]


def generate(m):
    m=deepcopy(m); s=settings(m.get('settings',{})); m['settings']=s
    shapes=m.get('shapes',[]); mode=m.get('mode','survey')
    allcoords=[c for sh in shapes for c in sh['coords']]
    forward,inverse=projection(allcoords)
    fp=footprint(s); points=[]
    if mode=='orbit':
        center=next((sh['coords'][0] for sh in shapes if sh['kind']=='poi'),None)
        if center is None: raise ValueError('Place a point of interest for the orbit.')
        x,y=forward(*center)
        for i in range(int(s['orbitPoints'])+1):
            a=2*math.pi*i/int(s['orbitPoints'])
            c=inverse(x+s['radius']*math.sin(a),y+s['radius']*math.cos(a))
            p=waypoint(c,s); p['heading']=((math.degrees(a)+180+180)%360)-180; points.append(p)
    else:
        areas=[]; exclusions=[]
        for sh in shapes:
            cs=[forward(*coord(c)) for c in sh['coords']]
            if sh['kind']=='corridor':
                if len(cs)<2: raise ValueError('A corridor needs two or more points.')
                areas.append(LineString(cs).buffer(s['corridorWidth']/2,cap_style=2,join_style=2))
            elif sh['kind'] in ('area','exclusion'):
                if len(cs)<3: raise ValueError('An area needs at least three corners.')
                poly=Polygon(cs)
                if not poly.is_valid or poly.area<1: raise ValueError('A boundary crosses itself or has no area. Edit its corners.')
                (exclusions if sh['kind']=='exclusion' else areas).append(poly)
        if not areas: raise ValueError('Draw a survey boundary or corridor first.')
        allowed=unary_union(areas).difference(unary_union(exclusions))
        polys=list(allowed.geoms) if hasattr(allowed,'geoms') else [allowed]
        if any(p.geom_type!='Polygon' or p.is_empty for p in polys): raise ValueError('No usable survey area remains.')
        for poly in polys:
            angle=s['angle']
            if s['autoAngle']:
                ring=list(poly.minimum_rotated_rectangle.exterior.coords)
                a,b=max(zip(ring,ring[1:]),key=lambda ab:math.dist(*ab))
                angle=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))
            for heading in ([angle,angle+90] if s['crosshatch'] else [angle]):
                rotated=rotate(poly,-heading,origin=(0,0)); bounds=rotated.bounds
                count=max(1,math.ceil((bounds[3]-bounds[1])/fp['spacing']))
                if count>1000: raise ValueError('Too many flight legs. Increase spacing or reduce the area.')
                dy=(bounds[3]-bounds[1])/count; previous=None
                for row in range(count):
                    y=bounds[1]+dy*(row+.5)
                    clipped=rotated.intersection(LineString([(bounds[0]-1,y),(bounds[2]+1,y)]))
                    lines=list(clipped.geoms) if hasattr(clipped,'geoms') else [clipped]
                    lines=sorted([l for l in lines if l.geom_type=='LineString' and l.length>.01],key=lambda l:l.bounds[0],reverse=bool(row%2))
                    for line in lines:
                        start,end=list(line.coords)[::len(line.coords)-1]
                        if row%2: start,end=end,start
                        n=max(1,math.ceil(math.dist(start,end)/fp['photoSpacing'])) if s['dense'] else 1
                        if n+len(points)>10000: raise ValueError('Plan exceeds 10,000 points. Increase spacing or split the area.')
                        leg=[(start[0]+(end[0]-start[0])*i/n,y) for i in range(n+1)]
                        real=[rotate(Point(c),heading,origin=(0,0)).coords[0] for c in leg]
                        if previous is not None:
                            for c in connector(previous,real[0],poly)[:-1]:
                                p=waypoint(inverse(*c),s); p['action']='none'; points.append(p)
                        for i,c in enumerate(real):
                            p=waypoint(inverse(*c),s)
                            if s['referenceWindows'] and n>=4 and i in (n//2-1,n//2,n//2+1):
                                p['gimbal']=-90; p['hover']=s['interval'] if i==n//2 else 0
                            points.append(p)
                        previous=real[-1]
        m['area']=allowed.area
    if m.get('reverse'): points.reverse()
    m['points']=points; m['terrainSource']=None
    return m


def distance(a,b):
    return GEOD.inv(a['lon'],a['lat'],b['lon'],b['lat'])[2]


def validate_mission(m):
    s=settings(m.get('settings',{})); ps=m.get('points',[])
    if len(ps)>10000: raise ValueError('Maximum 10,000 waypoints per project.')
    for p in ps:
        coord([p['lon'],p['lat']])
        for key,lo,hi in [('alt',-500,10000),('speed',.1,20),('gimbal',-90,30),('hover',0,600)]:
            number(p[key],f'Waypoint {key}',lo,hi)
        if p.get('gimbalEnd') is not None: number(p['gimbalEnd'],'End gimbal',-90,30)
        if p.get('heading') is not None: number(p['heading'],'Heading',-180,180)
        if p['action'] not in ('none','takePhoto','startRecord','stopRecord'): raise ValueError('Unknown waypoint action.')
        if p.get('ground') is not None: number(p['ground'],'Ground elevation',-500,9000)
    if ps: projection([[p['lon'],p['lat']] for p in ps])
    return s,ps


def review(m):
    s,ps=validate_mission(m); errors=[]; warnings=[]
    if len(ps)<2: errors.append('Add at least two waypoints.')
    if not m.get('profile'): errors.append('Import a DJI KMZ once to establish the aircraft profile.')
    total=sum(distance(a,b) for a,b in zip(ps,ps[1:]))
    seconds=sum(math.hypot(distance(a,b),b['alt']-a['alt'])/a['speed'] for a,b in zip(ps,ps[1:]))+sum(p['hover']+(2 if p['action']=='takePhoto' else 0) for p in ps)
    home=m.get('home')
    transit=0
    if home and ps:
        h=dict(lon=coord(home)[0],lat=coord(home)[1]); transit=(distance(h,ps[0])+distance(ps[-1],h))/s['speed']
    else: warnings.append('Set the takeoff point to include outbound and return distance in estimates.')
    if any(p['alt']>s['maxAltitude'] for p in ps): errors.append('A waypoint exceeds your configured altitude ceiling relative to takeoff.')
    if any(p['alt']<=0 for p in ps): warnings.append('Some waypoints are at or below takeoff elevation. Check the terrain profile.')
    if s['terrain']:
        if not home or s['homeElevation'] is None or any(p.get('ground') is None for p in ps):
            errors.append('Terrain following needs a takeoff point and complete terrain samples. Load terrain first.')
        else:
            if any(p['alt']+s['homeElevation']-p['ground']<s['clearance'] for p in ps): errors.append('A waypoint is below your minimum terrain clearance.')
    if any(p.get('unsupported') for p in ps): errors.append('Imported actions are not editable here. Clear unsupported actions explicitly or transfer the original KMZ unchanged.')
    if m.get('heightMode','relativeToStartPoint')!='relativeToStartPoint': errors.append('Imported absolute-height mission: convert to takeoff-relative heights before DJI Fly export.')
    exclusions=[sh for sh in m.get('shapes',[]) if sh['kind']=='exclusion']
    if ps and exclusions:
        f,_=projection([[p['lon'],p['lat']] for p in ps]); route=LineString([f(p['lon'],p['lat']) for p in ps])
        for sh in exclusions:
            poly=Polygon([f(*coord(c)) for c in sh['coords']])
            if not poly.is_valid: errors.append('An exclusion polygon is invalid.'); continue
            if route.intersects(poly.buffer(-.05)): errors.append('A flight leg crosses an exclusion. Reroute it before export.'); break
    if exclusions and home: warnings.append('Exclusion checks cover listed waypoints only. Check the takeoff-to-first-point and return-home paths separately in DJI Fly.')
    fp=footprint(s)
    if not s['dense'] and s['action']=='takePhoto': warnings.append('Photos only at the listed waypoints. Enable dense photo points for along-track coverage.')
    if s['action']=='none': warnings.append('No automatic photos: configure timed shots in DJI Fly if needed.')
    if not s['straight']: warnings.append('Curved turns can leave the drawn segments. Exclusion checks use straight segments; review turn clearance in DJI Fly.')
    if s['gimbal']!=-90: warnings.append('Coverage and GSD assume a nadir camera. Oblique coverage differs.')
    if fp['photoSpacing']/s['speed']<s['interval']: warnings.append('Requested speed leaves less than the camera interval between photos. Slow down or reduce overlap.')
    warnings.append('Terrain is bare-earth estimation, not obstacle detection. Trees, wires, airspace and weather require field review.')
    warnings.append('DJI Fly acceptance of generated files must be checked on your controller. This software does not arm or fly the aircraft.')
    usable=s['batteryMinutes']*60*(1-s['reserve']/100)
    return dict(errors=list(dict.fromkeys(errors)),warnings=warnings,distance=total,seconds=seconds+transit,
                photoCount=sum(p['action']=='takePhoto' for p in ps),waypoints=len(ps),footprint=fp,
                area=m.get('area',0),batteryUsableSeconds=usable,estimatedBatteries=max(1,math.ceil((seconds+transit)/usable)))


def split_mission(m):
    """Split with one shared endpoint, accounting for each sortie's home transit."""
    s,ps=validate_mission(m); maximum=int(s['maxPoints']); budget=s['batteryMinutes']*60*(1-s['reserve']/100)
    if len(ps)<2: raise ValueError('Need at least two waypoints.')
    parts=[]; start=0
    while start<len(ps)-1:
        end=start+2
        while end<=len(ps) and end-start<=maximum:
            test=deepcopy(m); test['points']=ps[start:end]
            if review(test)['seconds']>budget: break
            end+=1
        end-=1
        if end<start+2: raise ValueError('Even a two-point sortie exceeds the battery budget. Adjust the route or takeoff point.')
        part=deepcopy(m); part['points']=deepcopy(ps[start:end]); part['name']=f'{m.get("name","Mission")} · {len(parts)+1}'
        parts.append(part); start=end-1
    return parts
