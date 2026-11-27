"""Conservative same-face 1206 bypass placement screen around main LDO."""
import json,math
from pathlib import Path
from shapely.geometry import box,Point,Polygon,shape as geo_shape
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..routed.plan import sha,shape
H=Path(__file__).resolve().parent;BASE=H.parent/'main_ldo/native-03'
def run():
 c=json.loads((H/'capture-01/capture.json').read_text());t=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());occupied=[];unknown=[]
 for f in children(t,'footprint'):
  if first(f,'layer')[1]!='F.Cu':continue
  ref=next(p[2] for p in children(f,'property') if p[1]=='Reference');at=first(f,'at');x,y=map(float,at[1:3]);angle=float(at[3]) if len(at)>3 else 0;points=[]
  for tag in ['fp_line','fp_rect','fp_poly','fp_circle','fp_arc']:
   for e in children(f,tag):
    if first(e,'layer')[1]!='F.CrtYd':continue
    if tag=='fp_arc':raise ValueError('Unsupported courtyard arc '+ref)
    if tag=='fp_circle':
     cx,cy=map(float,first(e,'center')[1:3]);ex,ey=map(float,first(e,'end')[1:3]);r=math.hypot(ex-cx,ey-cy);points.extend([(cx-r,cy-r),(cx+r,cy+r)])
    elif tag=='fp_poly':points.extend(tuple(map(float,v[1:3])) for v in first(e,'pts')[1:])
    else:
     for name in ['start','end']:points.extend(tuple(map(float,v[1:3])) for v in children(e,name))
  if points:
   xs,ys=zip(*points);occupied.append(translate(rotate(box(min(xs),min(ys),max(xs),max(ys)),-angle,origin=(0,0)),x,y))
  else:unknown.append(ref);occupied.append(Point(x,y).buffer(10))
 for o in c['objects']:
  drill=o.get('drill_mm',0);drill=max(drill) if isinstance(drill,list) else drill
  if drill:occupied.append(Point(o['position_mm']).buffer(drill/2+.25))
 for z in c['zones']:
  if z['keepout']:occupied.append(shape(z['authored_outline']))
 for path in [H.parent/'main_feeds/contact-keepouts.json',H.parent/'vin_escape/main-mount-keepouts.json']:
  for f in json.loads(path.read_text())['features']:
   if f['properties'].get('board','power')=='power' and 'F.Cu' in f['properties']['layers']:occupied.append(geo_shape(f['geometry']))
 occ=prep(unary_union(occupied));foreign={net:prep(unary_union([shape(o['layers']['F.Cu']) for o in c['objects'] if 'F.Cu' in o['layers'] and o['net']!=net]+[shape(z['polygons']) for z in c['zones'] if z['layer']=='F.Cu' and z['net']!=net and not z['keepout']]).buffer(.2)) for net in ['/P_power_supply/AUX_PREREG5','PWR_AGND']};by={o['ref']+'.'+o['pin']:o for o in c['objects'] if o.get('ref')};inputpos=by['P_U102.8']['position_mm'];legal=[]
 for angle in [0,90,180,270]:
  for ix in range(920,991):
   for iy in range(605,681):
    x,y=ix/5,iy/5;court=translate(rotate(box(-2.3,-1.15,2.3,1.15),angle,origin=(0,0)),x,y)
    if occ.intersects(court):continue
    pads=[translate(rotate(box(-1.475-.575,-.9,-1.475+.575,.9),angle,origin=(0,0)),x,y),translate(rotate(box(1.475-.575,-.9,1.475+.575,.9),angle,origin=(0,0)),x,y)]
    if any(foreign[net].intersects(pg) for pg,net in zip(pads,['/P_power_supply/AUX_PREREG5','PWR_AGND'])):continue
    legal.append({'position_mm':[x,y],'geometric_angle_degrees':angle,'positive_pad_center_mm':list(pads[0].centroid.coords)[0],'supply_distance_mm':pads[0].distance(Point(inputpos))})
 legal.sort(key=lambda x:x['supply_distance_mm']);report={'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'capture_sha256':sha(H/'capture-01/capture.json'),'script_sha256':sha(Path(__file__)),'unknown_courtyard_fail_closed_refs':unknown,'legal_placements':legal[:30],'total_legal':len(legal),'qualified':False};(H/'screen.json').write_text(json.dumps(report,indent=2)+'\n');print('legal',len(legal),legal[:3])
if __name__=='__main__':run()
