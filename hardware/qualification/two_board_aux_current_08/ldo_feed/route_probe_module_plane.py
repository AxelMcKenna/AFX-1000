"""Virtual feed routes with explicit proposed AGND-only cutback scope; not acceptance."""
import json,math
from pathlib import Path
from shapely.geometry import Point,box,LineString
from shapely.affinity import translate
from shapely.ops import unary_union,nearest_points
from ..routed.plan import shape,sha,astar
H=Path(__file__).resolve().parent;c=json.loads((H/'capture-02/capture.json').read_text());q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());qi=set(q['retained_object_uuids']);qz={z['zone_uuid'] for z in q['plane_exclusions']};removed=set(json.loads((H.parent/'ldo_local/native-07/review.json').read_text())['added_copper_uuids']);objects=[];by={}
for o in c['objects']:
 if o['uuid'] in removed:continue
 gs={l:shape(g) for l,g in o['layers'].items()}
 if o.get('ref')=='P_C907':gs={l:translate(g,-1,0) for l,g in gs.items()}
 objects.append((o,gs))
 if o.get('ref'):by[o['ref']+'.'+o['pin']]=(o,gs)
net='/P_power_supply/AUX_PREREG5';vias={'IN':([186.6,125.8],net),'INreturn':([185.8,125.3],'PWR_AGND'),'EN':([193.6,128.5],net),'ENreturn':([192.9,129.0],'PWR_AGND')}
for name,(xy,n) in vias.items():objects.append(({'uuid':'via:'+name,'net':n},{l:Point(xy).buffer(.3) for l in ['F.Cu','B.Cu']}))
ref={l:unary_union([shape(z['polygons']) for z in c['zones'] if z['layer']==r and z['net']=='PWR_AGND' and z['uuid'] not in qz]) for l,r in [('F.Cu','In1.Cu'),('B.Cu','In6.Cu')]};envelope=box(184.8,124.5,194.5,129.5);rows=[];sourcegroup=by['P_C102.1'][0]['group'];sourceB=unary_union([gs['B.Cu'] for o,gs in objects if o.get('group')==sourcegroup and 'B.Cu' in gs]);jobs=[('source5V','via:IN','B.Cu',.3,net,sourceB,Point(vias['IN'][0]).buffer(.3)),('via:IN','P_C907.1','F.Cu',.3,net,Point(vias['IN'][0]).buffer(.3),by['P_C907.1'][1]['F.Cu']),('P_C907.1','P_U102.8','F.Cu',.3,net,by['P_C907.1'][1]['F.Cu'],by['P_U102.8'][1]['F.Cu']),('P_C907.2','P_U102.9','F.Cu',.4,'PWR_AGND',by['P_C907.2'][1]['F.Cu'],by['P_U102.9'][1]['F.Cu']),('via:EN','P_U102.5','F.Cu',.2,net,Point(vias['EN'][0]).buffer(.3),by['P_U102.5'][1]['F.Cu'])]
for source,target,layer,w,n,start,end in jobs:
 obs=[gs[layer].buffer(.202+w/2) for o,gs in objects if layer in gs and (o['net']!=n or o['uuid'] in qi)]
 for z in c['zones']:
  if z['layer']!=layer or z['net']==n:continue
  g=shape(z['polygons'])
  if z['net']=='PWR_AGND' and z['uuid'] not in qz:g=g.difference(envelope)
  obs.append(g.buffer(.202+w/2))
 blocked=unary_union(obs);allowed=ref[layer].buffer(-w/2-.002001).difference(blocked.buffer(.000001));ga=start.intersection(allowed);gb=end.intersection(allowed);path=None;nodes=0
 if not ga.is_empty and not gb.is_empty:
  a,b=nearest_points(ga,gb);path,nodes=astar(list(a.coords)[0],list(b.coords)[0],blocked,ref[layer],w,margin=5,step=.025)
 row={'source':source,'target':target,'layer':layer,'net':n,'width_mm':w,'path_mm':path,'search_nodes':nodes,'source_area_mm2':ga.area,'target_area_mm2':gb.area};rows.append(row);print(source,target,bool(path),nodes,flush=True)
 if path:
  g=LineString(path).buffer(w/2);row['length_mm']=LineString(path).length;objects.append(({'uuid':'route:'+source,'net':n},{layer:g}))
r={'source_capture_sha256':sha(H/'capture-02/capture.json'),'script_sha256':sha(Path(__file__)),'new_C907_center_mm':[186.5,126.6],'removed_only_owned_track_UUIDs':sorted(removed),'proposed_AGND_only_cutback_scope_mm':list(envelope.bounds),'vias':vias,'routes':rows,'candidate_board_authored':False,'qualified':False};(H/'route-probe.json').write_text(json.dumps(r,indent=2)+'\n')
