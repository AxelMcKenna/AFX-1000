"""Find last-bias escape candidates after removing only identified agent-added obstacles."""
import copy,json,hashlib,math
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union,nearest_points
from shapely.strtree import STRtree
from hardware.cad.two_board_sensor_05.signal_dac import adc_context_r90 as C
R=Path(__file__).resolve().parent;base=C.c;original=json.loads((R.parent/'signal_input/capture-r7/capture.json').read_text());original_ids={o['uuid']for o in original['objects']};rows=[];net='/A_ADC/BIAS_SHIFT_R'
for ref,pin,blocking_net in [('A_U107','11',None)]:
 removed=[o for o in base['objects']if o['net']==blocking_net and o['uuid']not in original_ids];ids={o['uuid']for o in removed};assert not ids&original_ids
 C.c={**base,'objects':[o for o in base['objects']if o['uuid']not in ids]};C.screen=C.S.Screen(C.c);C.base_legal=C.screen.legal;C.screen.legal=C.ref_legal;C.front_allow.clear();C.front_dynamic_key=None
 C.obs=[(o,C.S.shape(ps))for o in C.c['objects']for ps in o['layers'].values()if ps];C.tree=STRtree([g for _,g in C.obs]);o=next(o for o in C.c['objects']if o.get('ref')==ref and o.get('pin')==pin);start=o['position_mm'];window=Point(start).buffer(5)
 C.prospective_holes=[];C.ref_legal(net,'F.Cu',[start,[start[0]-.001,start[1]]]);obstacles=unary_union([g.buffer(d)for n,g,d in C.screen.geometry['F.Cu']if n!=net and g.intersects(window)])
 free=C.front_allow[net].buffer(-.100001).intersection(window).difference(obstacles);parts=list(free.geoms)if hasattr(free,'geoms')else[free];component=next(g for g in parts if g.covers(Point(start)));target=component.buffer(.615)
 obs=[]
 for item,g in C.obs:
  if item['net']==net and item['kind']=='PCB_TRACK':continue
  if not g.intersects(target.buffer(1)):continue
  limit=.27 if item['net']==net and item['kind']=='PAD'and not any(item['drill_mm'])else .51;obs.append(g.buffer(limit))
 obs.extend(Point(item['position_mm']).buffer(.86)for item in C.c['objects']if item['kind']=='PCB_VIA'and Point(item['position_mm']).distance(target)<1)
 available=target.difference(unary_union(obs));parts=list(available.geoms)if hasattr(available,'geoms')else[available];found=[]
 print(ref,'candidate area',available.area,'removed agent objects',len(ids),flush=True)
 for poly in sorted(parts,key=lambda p:-p.area):
  if poly.area<1e-7:continue
  inset=poly.buffer(-.005);inset=inset if not inset.is_empty else poly
  points=[inset.representative_point(),nearest_points(inset,Point(start))[0]]
  for point in points:
   q=[round(point.x,6),round(point.y,6)]
   if not C.vialegal(q,net):
    print('REJECT via',q,flush=True);continue
   ret=C.return_site(q)
   if ret is None:
    print('REJECT return',q,flush=True);continue
   C.prospective_holes=[q];domain=C.front_allow[net].union(Point(q).buffer(.515)).buffer(-.100001).intersection(window).difference(obstacles);path=C.visibility_path(domain,start,q,max_nodes=2048)
   if path is None or not C.screen.legal(net,'F.Cu',path):
    print('REJECT continuous escape',q,ret,flush=True);continue
   affected=[]
   for item in removed:
    via_hit=any(C.S.shape(ps).distance(Point(q))<.51 for ps in item['layers'].values()if ps)
    surface_hit=item['layers'].get('F.Cu')and C.S.shape(item['layers']['F.Cu']).distance(LineString(path))<.31
    if via_hit or surface_hit:affected.append(item['uuid'])
   record={'reference':ref,'pin':pin,'source_pad_uuid':o['uuid'],'at':q,'return_at':ret,'path_mm':path,'path_length_mm':LineString(path).length,'removed_net':blocking_net,'directly_affected_agent_uuids':affected};found.append(record);print('FOUND',record,flush=True)
 rows.append({'reference':ref,'pin':pin,'removed_agent_net':blocking_net,'hypothetical_removed_agent_uuids':sorted(ids),'candidates':found})
paths=[Path(__file__),R/'adc_context_r90.py',R/'capture-r89/capture.json',R.parent/'signal_input/capture-r7/capture.json'];report={'planning_only':True,'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'endpoints':rows}
(R/'adc-bias-access-r90b.json').write_text(json.dumps(report,indent=2)+'\n')
