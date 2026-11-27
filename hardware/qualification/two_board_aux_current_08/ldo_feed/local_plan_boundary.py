"""Bounded local IN/EN route, with explicit optional main-ground cutback envelope."""
import json
from pathlib import Path
from shapely.geometry import box,Point,LineString
from shapely.ops import unary_union,nearest_points
from ..routed.plan import shape,sha,astar
from ..main_feeds.routing_zones import obstacles
H=Path(__file__).resolve().parent;c=json.loads((H/'capture-02/capture.json').read_text());by={o['ref']+'.'+o['pin']:o for o in c['objects'] if o.get('ref')};q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());qi=set(q['retained_object_uuids']);qz={z['zone_uuid'] for z in q['plane_exclusions']};net='/P_power_supply/AUX_PREREG5';w=.2;regions=box(185,122,197,133);ref=unary_union([shape(z['polygons']) for z in c['zones'] if z['layer']=='In1.Cu' and z['net']=='PWR_AGND' and z['uuid'] not in qz]);rows=[]
for source,target,end in [('P_U102.8','P_U102.5',shape(by['P_U102.5']['layers']['F.Cu'])),('P_U102.5','proposed_supply_via',Point(193.6,128.5).buffer(.3))]:
 start=shape(by[source]['layers']['F.Cu']);assert by[source]['net']==net
 for change in [False,True]:
  envelope=box(189.2,128.4,191.8,129.1) if change else box(0,0,0,0)
  boardobs=unary_union([shape(o['layers']['F.Cu']).buffer(.302) for o in c['objects'] if 'F.Cu' in o['layers'] and (o['net']!=net or o['uuid'] in qi)])
  zobs=[]
  for z in c['zones']:
   if z['layer']!='F.Cu' or z['net']==net:continue
   g=shape(z['polygons'])
   if z['net']=='PWR_AGND' and z['uuid'] not in qz:g=g.difference(envelope)
   zobs.append(g.buffer(.302))
  blocked=unary_union([boardobs,*zobs]);allowed=ref.buffer(-.102).difference(blocked);ga=start.intersection(allowed);gb=end.intersection(allowed);path=None;nodes=0
  if not ga.is_empty and not gb.is_empty:
   a,b=nearest_points(ga,gb);path,nodes=astar(list(a.coords)[0],list(b.coords)[0],blocked,ref,w,margin=5,step=.025)
  rows.append({'source':source,'target':target,'net':net,'width_mm':w,'optional_AGND_cutback':change,'cutback_envelope_mm':list(envelope.bounds),'path_mm':path,'search_nodes':nodes,'source_legal_area_mm2':ga.area,'target_legal_area_mm2':gb.area});print(source,target,change,bool(path),nodes,flush=True)
(H/'local-plan.json').write_text(json.dumps({'source_capture_sha256':sha(H/'capture-02/capture.json'),'script_sha256':sha(Path(__file__)),'rows':rows,'qualified':False},indent=2)+'\n')
