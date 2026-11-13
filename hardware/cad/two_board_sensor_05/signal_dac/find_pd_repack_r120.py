"""Find last-bias escape candidates after removing only identified agent-added obstacles."""
import copy,json,hashlib,math
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union,nearest_points
from shapely.strtree import STRtree
from hardware.cad.two_board_sensor_05.signal_dac import adc_context_r108 as C
R=Path(__file__).resolve().parent;base=copy.deepcopy(C.c);original=json.loads((R.parent/'signal_input/capture-r7/capture.json').read_text());original_ids={o['uuid']for o in original['objects']};rows=[];net='/A_ADC/BIAS_SHIFT_R'
from shapely.affinity import translate,rotate
pose=next(x for x in json.loads((R/'pd-courtyard-r119.json').read_text())['accepted']if x['translation_mm']==[.8,-.8]);assert pose['world_rotation_degrees']==270
removed_stub_ids={'718b29e7-1ba2-58be-8881-8126cfeebf60','f684c170-6e78-5642-9206-0e97f42c9885'}
def point_transform(p):return [75.8+(p[1]-66),65.2-(p[0]-75)]
for item in base['objects']:
 if item.get('ref')=='A_D101':
  item['position_mm']=point_transform(item['position_mm'])
  for layer,ps in item['layers'].items():
   g=translate(rotate(C.S.shape(ps),270,origin=(75,66)),xoff=.8,yoff=-.8);item['layers'][layer]=[{'outer':list(g.exterior.coords)[:-1],'holes':[list(r.coords)[:-1]for r in g.interiors]}]
 if item['uuid']in removed_stub_ids:
  item['position_mm']=point_transform(item['position_mm']);g=LineString([item['position_mm'],item['end_mm']]).buffer(item['width_mm']/2+.000002);item['layers']={'B.Cu':[{'outer':list(g.exterior.coords)[:-1],'holes':[]}]}
for ref,pin,blocking_net in [('A_U101','7',None)]:
 removed=[o for o in base['objects']if o['net']==blocking_net and o['uuid']not in original_ids];ids={o['uuid']for o in removed};assert not ids&original_ids
 C.c={**base,'objects':[o for o in base['objects']if o['uuid']not in ids]};C.screen=C.S.Screen(C.c);C.base_legal=C.screen.legal;C.screen.legal=C.ref_legal;C.front_allow.clear();C.front_dynamic_key=None
 C.obs=[(o,C.S.shape(ps))for o in C.c['objects']for ps in o['layers'].values()if ps];C.tree=STRtree([g for _,g in C.obs]);o=next(o for o in C.c['objects']if o.get('ref')==ref and o.get('pin')==pin);start=o['position_mm'];net=o['net'];window=Point(start).buffer(5)
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
 ground_obstacles=[]
 for item,g in C.obs:
  if not g.intersects(target.buffer(3)):continue
  if item['net']!='LINK_AGND':ground_obstacles.append(g.buffer(.51))
  elif item['kind']=='PAD'and not any(item['drill_mm']):ground_obstacles.append(g.buffer(.27))
 ground_obstacles += [Point(item['position_mm']).buffer(.86)for item in C.c['objects']if item['kind']=='PCB_VIA']
 ground_free=C.return_field.buffer(-.310001).intersection(target.buffer(2.5)).difference(unary_union(ground_obstacles))
 candidates=[];tested=0;budget=1500
 from hardware.cad.two_board_sensor_05.signal_dac.return_paths import v_paths
 for poly in parts:
  if poly.area<1e-7:continue
  minx,miny,maxx,maxy=poly.bounds
  points=[poly.representative_point()]+[Point(round(minx+i*.025,6),round(miny+j*.025,6))for i in range(int((maxx-minx)/.025)+1)for j in range(int((maxy-miny)/.025)+1)]
  for point in points:
   if tested>=budget:break
   if not poly.buffer(-.002).covers(point):continue
   tested+=1
   q=[round(point.x,6),round(point.y,6)]
   if not C.vialegal(q,net):continue
   existing=C.return_site(q)
   if existing is not None:
    C.prospective_holes=[q];domain=C.front_allow[net].union(Point(q).buffer(.515)).buffer(-.100001).intersection(window).difference(obstacles).difference(Point(existing).buffer(.610001));escape=C.visibility_path(domain,start,q,max_nodes=2048)
    if escape is not None and C.screen.legal(net,'F.Cu',escape):
     retpaths=[p for p in [*C.S.candidate_paths(q,existing),*v_paths(q,existing)]if LineString(p).length<=2.5 and LineString(p).buffer(.1).difference(Point(q).buffer(.515)).difference(C.return_field).area<1e-6]
     assert retpaths
     record={'at':q,'return_at':existing,'escape':escape,'return_path':min(retpaths,key=lambda p:LineString(p).length),'existing_native_return':any(math.dist(existing,o['position_mm'])<1e-6 for o in C.c['objects']if o['kind']=='PCB_VIA'and o['net']=='LINK_AGND')};candidates.append(record);print('FOUND EXISTING RETURN',record,flush=True);break
   gs=ground_free.intersection(point.buffer(2.5)).difference(point.buffer(.86));gps=list(gs.geoms)if hasattr(gs,'geoms')else[gs]
   for gp in gps:
    if gp.area<1e-6:continue
    inset=gp.buffer(-.005);inset=inset if not inset.is_empty else gp
    for pt in [inset.representative_point(),nearest_points(inset,point)[0]]:
     ret=[round(pt.x,6),round(pt.y,6)]
     paths=[path for path in [*C.S.candidate_paths(q,ret),*v_paths(q,ret)]if LineString(path).length<=2.5 and LineString(path).buffer(.1).difference(Point(q).buffer(.515)).difference(C.return_field).area<1e-6]
     if not paths:continue
     C.prospective_holes=[q];domain=C.front_allow[net].union(Point(q).buffer(.515)).buffer(-.100001).intersection(window).difference(obstacles).difference(Point(ret).buffer(.610001));path=C.visibility_path(domain,start,q,max_nodes=2048)
     if path is None or not C.screen.legal(net,'F.Cu',path):continue
     record={'at':q,'return_at':ret,'escape':path,'return_path':min(paths,key=lambda p:LineString(p).length)};candidates.append(record);print('FOUND',record,flush=True)
     break
    if candidates:break
   if candidates:break
  if candidates:break
 record={'planning_only':True,'placement_hypothesis':{'reference':'A_D101','world_rotation_degrees':270,'translation_mm':[.8,-.8]},'removed_stub_ids':sorted(removed_stub_ids),'physical_source_board_unchanged':True,'reference':ref,'pin':pin,'net':net,'source_pad_uuid':o['uuid'],'source_position_mm':start,'max_signal_samples':budget,'tested_signal_samples':tested,'available_area_mm2':available.area,'candidates':candidates,'result':'candidate_found'if candidates else'budget_exhausted'if tested>=budget else'no_candidate_in_bounded_family','source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'adc_context_r108.py',R/'capture-r107/capture.json',R/'transitions-r107.json',R/'visibility_path.py',R/'return_paths.py']}}
 out=R/f'pd-access-r120-{ref}.json';assert not out.exists();out.write_text(json.dumps(record,indent=2)+'\n');print('CHECKPOINT',ref,record['result'],tested,flush=True)

