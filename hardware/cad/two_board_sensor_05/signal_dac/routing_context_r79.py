"""Actual-pad-side bounded input routing, with explicit via escape geometry."""
import json,math,uuid,hashlib
from pathlib import Path
from itertools import chain
from hardware.cad.two_board_sensor_05.signal_dac.return_paths import v_paths
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.cad.two_board_sensor_05.signal_dac.visibility_path import visibility_path
from hardware.electronics.common.sexpr import read_sexpr,sexpr,a
import hardware.fabrication.route_nf_surface as S
R=Path(__file__).resolve().parent;I=R.parent/'signal_input';S.SIGNAL_LAYERS=('F.Cu','B.Cu','In3.Cu','In5.Cu')
c=json.loads((R/'capture-r78/capture.json').read_text());screen=S.Screen(c);obj={o['uuid']:o for o in c['objects']};routes=[];vias=[];blocked=[];cache={}
ground_returns=[]
in1=unary_union([S.shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']=='In1.Cu'])
return_field=unary_union([S.shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']=='In1.Cu'])
# The new route will receive physical LINK_AGND corridors on In4/In6.
# Existing In1 is retained; all native filled-field checks remain mandatory.
return_field=return_field.buffer(.000002)
# Reference the introduced front copper. Existing pad/track copper is retained;
# sensitive-net exclusions remain source-derived and explicitly accounted.
baseline=json.loads((I/'capture-r7/capture.json').read_text())
from hardware.cad.two_board_sensor_05.signal_dac.sensitive_placement import validated_exclusions
placement=json.loads((R/'candidate-r53/routing.json').read_text())
for name,digest in placement['source_sha256'].items():assert hashlib.sha256((R.parents[3]/name).read_bytes()).hexdigest()==digest
moved_masks={row['net']:row['geometry']for row in validated_exclusions(baseline,c,placement['supplemental_lowcap_exclusions'])}

front_dynamic_key=None;front_dynamic=None
front_allow={};sensitive={o['net']for o in c['objects']if o.get('ref')in ['A_U301','A_U302','A_U303','A_U304']and o.get('pin')in ['2','6']}
keep=unary_union([S.shape(z['polygons'])for z in c['zones']if z['keepout']and not z['prohibit_tracks']and z['layer']=='In1.Cu'])
inner_allow={};prospective_holes=[];prospective_fields={}
in4=unary_union([S.shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']=='In4.Cu'])
base_legal=screen.legal
def ref_legal(net,layer,path):
 global front_dynamic_key,front_dynamic
 if not base_legal(net,layer,path):return False
 if layer!='F.Cu':return True
 if net not in front_allow:
  copper=unary_union([S.shape(o['layers']['F.Cu'])for o in c['objects']if o['net']==net and o['layers'].get('F.Cu')])
  holes=unary_union([S.shape(ps).buffer(.215)for o in c['objects']if o['net']==net and(o['kind']=='PCB_VIA'or o['kind']=='PAD'and any(o['drill_mm']))for ps in o['layers'].values()if ps])
  lowcap=unary_union([S.shape(ps).buffer(.5)for o in baseline['objects']if o['net']==net for l,ps in o['layers'].items()if l in ['F.Cu','B.Cu']and ps]).intersection(keep)if net in sensitive else Point().buffer(0)
  lowcap=lowcap.union(moved_masks.get(net,Point().buffer(0)))
  front_allow[net]=in1.buffer(.000002).union(copper).union(holes).union(lowcap)
 key=(net,tuple(tuple(p)for p in prospective_holes))
 if key!=front_dynamic_key:
  # Planning hypothesis only: final audit requires exact native same-net via and independently proven physical return.
  front_dynamic=prep(front_allow[net].union(unary_union([Point(p).buffer(.515)for p in prospective_holes])).buffer(-.100001));front_dynamic_key=key
 return front_dynamic.covers(LineString(path))
screen.legal=ref_legal
obs=[(o,S.shape(ps))for o in c['objects']for ps in o['layers'].values()if ps];tree=STRtree([g for _,g in obs])
proof=json.loads((R/'transitions-r78.json').read_text())
# Old returns are revalidated against actual native copper, including bounded alternate paths.
protected_returns=Point().buffer(0)
def vialegal(p,net):
 pt=Point(p)
 if pt.distance(protected_returns)<.64:return False
 if any(math.dist(p,q)<.86 for q in ground_returns):return False
 for ix in tree.query(pt.buffer(.52)):
  o,g=obs[int(ix)]
  if o['net']==net and o['kind']=='PCB_TRACK':continue
  if o['net']==net and o['kind']=='PAD'and not any(o['drill_mm']):
   # Same-net copper may join the pad; keep the 0.3 mm drill at least 0.12 mm off the solder land.
   if pt.distance(g)<.27:return False
   continue
  if pt.distance(g)<.51:return False
 if any(o['kind']=='PCB_VIA'and math.dist(p,o['position_mm'])<.86 for o in c['objects']):return False
 if any(math.dist(p,v['at'])<.86 for v in vias):return False
 return not any(n!=net and pt.distance(g)<.62 for n,l,g in screen.added)
main=next(o['group']for o in c['objects']if o.get('ref')=='D_U1001'and o.get('pin')=='20')
existing_returns=[o['position_mm']for o in c['objects']if o['kind']=='PCB_VIA'and o['net']=='LINK_AGND'and o['group']==main and all(o['layers'].get(l)for l in ['In1.Cu','In4.Cu','In6.Cu'])]
def return_site(p):
 for v in ground_returns+existing_returns:
  if .86<=math.dist(p,v)<=2.5 and any(LineString(path).length<=2.5 and LineString(path).buffer(.1).difference(Point(p).buffer(.515)).difference(return_field).area<1e-6 for path in chain(S.candidate_paths(p,v),v_paths(p,v))):return v
 for i,j in return_offsets:
  q=[round(p[0]+i,6),round(p[1]+j,6)];pt=Point(q)
  if not return_field.covers(pt.buffer(.31)):continue
  if not any(LineString(path).length<=2.5 and LineString(path).buffer(.1).difference(Point(p).buffer(.515)).difference(return_field).area<1e-6 for path in chain(S.candidate_paths(p,q),v_paths(p,q))):continue
  if any(obs[int(ix)][0]['kind']=='PAD'and not any(obs[int(ix)][0]['drill_mm'])and pt.distance(obs[int(ix)][1])<.27 for ix in tree.query(pt.buffer(.28))):continue
  # A ground via may join a same-net trace; the separate solder-land drill clearance above still applies.
  if any(obs[int(ix)][0]['net']!='LINK_AGND'and pt.distance(obs[int(ix)][1])<.51 for ix in tree.query(pt.buffer(.52))):continue
  if any(o['kind']=='PCB_VIA'and math.dist(q,o['position_mm'])<.86 for o in c['objects']):continue
  if any(math.dist(q,v['at'])<.86 for v in vias):continue
  if any(math.dist(q,g)<.86 for g in ground_returns):continue
  if any(n!='LINK_AGND'and pt.distance(g)<.62 for n,l,g in screen.added):continue
  return q
 return None
return_offsets=sorted([(i*.25,j*.25)for i in range(-10,11)for j in range(-10,11)if .9<=math.hypot(i*.25,j*.25)<=2.5],key=lambda x:math.hypot(*x))
def options(g,net,layer):
 global prospective_holes
 out=[{'at':v['at'],'uid':v['from_pad'],'spur':None}for v in vias if v['net']==net and v['from_pad']in g]
 terminal=next((u for u in g if u in ['3fc2ffa6-61fb-58c1-bcf9-5e0e178c3cc2','8b2f4e85-d144-5826-b2ec-488de293f7d8']),None)
 for u in ([terminal]if terminal else g):
  o=obj[u]
  if terminal:
   if layer=='In3.Cu':out.append({'at':o['position_mm']if u=='3fc2ffa6-61fb-58c1-bcf9-5e0e178c3cc2'else o['end_mm'],'uid':u,'spur':None})
   continue
  if o['kind']=='PCB_TRACK':
   o={**o,'position_mm':[(o['position_mm'][i]+o['end_mm'][i])/2 for i in [0,1]]}
  elif o['kind']not in ['PAD','PCB_VIA']:continue
  if o['layers'].get(layer):out.append({'at':o['position_mm'],'uid':u,'spur':None});continue
  sides=[l for l in ['F.Cu','B.Cu']if o['layers'].get(l)]
  for side in sides:
   p=o['position_mm'];key=(u,side)
   if key not in cache and o.get('ref')=='A_U304'and o.get('pin')=='5':
    q=[128.075,74.405];prospective_holes=[q]
    assert vialegal(q,net);ret=return_site(q);assert ret is not None
    ref_legal(net,side,[p,[p[0]-.001,p[1]]])
    window=Point(p).buffer(5)
    obstacles=unary_union([g.buffer(distance)for other,g,distance in screen.geometry[side]if other!=net and g.intersects(window)])
    domain=front_allow[net].union(Point(q).buffer(.515)).buffer(-.100001).intersection(window).difference(obstacles)
    path=visibility_path(domain,p,q)
    assert path is not None and screen.legal(net,side,path)and LineString(path).distance(Point(ret))>.51
    cache[key]=[(q,path)];print('visibility escape',net,q,path,flush=True)
   if key not in cache:
    valid=[];legal=[];pts=sorted(([round(p[0]+i*.2,6),round(p[1]+j*.2,6)]for i in range(-40,41)for j in range(-40,41)),key=lambda q:math.dist(p,q))
    if o.get('ref')=='A_U304'and o.get('pin')=='5':
     # Sample the measured narrow opening between original B.Cu feedback objects.
     pts=sorted(pts+[[round(127.4+i*.05,6),round(74.1+j*.05,6)]for i in range(25)for j in range(13)],key=lambda q:math.dist(p,q))
    for q in pts:
     if math.dist(p,q)>8:break
     if not vialegal(q,net):continue
     ret=return_site(q)
     if ret is None:continue
     legal.append((q,ret));prospective_holes=[q]
     paths=[x for x in S.candidate_paths(p,q)if LineString(x).length<11.5 and screen.legal(net,side,x)]
     paths=[x for x in paths if LineString(x).distance(Point(ret))>.51]
     if paths:valid.append((q,min(paths,key=lambda x:LineString(x).length)))
     if len(valid)==6:break
    if not valid:
     for q,ret in legal[:16]:
      prospective_holes=[q]
      path=screen.grid_path(net,side,p,q,budget=16000)
      if path is not None and LineString(path).length<13.5 and LineString(path).distance(Point(ret))>.62:valid.append((q,path))
      if len(valid)>=3:break
    print('escape',net,o.get('ref'),o.get('pin'),side,len(valid),flush=True)
    cache[key]=valid
   for q,path in cache[key]:
    prospective_holes=[q]
    ret=return_site(q)
    if ret is not None and vialegal(q,net)and screen.legal(net,side,path)and LineString(path).distance(Point(ret))>.51:out.append({'at':q,'uid':u,'spur':path,'side':side,'return':ret})
 return out
def route_layers(net):return ('F.Cu','B.Cu','In3.Cu','In5.Cu')
