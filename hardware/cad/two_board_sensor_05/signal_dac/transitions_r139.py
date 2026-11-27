"""Native proof of every input-stage signal transition's local return path."""
import json,math,hashlib
from itertools import chain
from hardware.cad.two_board_sensor_05.signal_dac.return_paths import v_paths
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.fabrication.route_nf_surface import shape,candidate_paths
R=Path(__file__).resolve().parent;I=R.parent/'signal_input';b=json.loads((I/'capture-r7/capture.json').read_text());c=json.loads((R/'capture-r139/capture.json').read_text());r=json.loads((R/'candidate-r98/routing.json').read_text());r['transitions']+=json.loads((R/'candidate-r107/routing.json').read_text())['transitions'];r['transitions']+=json.loads((R/'candidate-r125/routing.json').read_text())['transitions'];r['transitions']+=json.loads((R/'candidate-r139/routing.json').read_text())['transitions'];objects={o['uuid']:o for o in c['objects']};main=next(o['group']for o in c['objects']if o.get('ref')=='D_U1001'and o.get('pin')=='20')
fields={l:unary_union([shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']==l])for l in ['In1.Cu','In4.Cu','In6.Cu']};rows=[]
for x in r['transitions']:
 x={**x,'distance_mm':math.dist(x['signal_at'],x['return_at'])}
 v_path_keys=set()
 o=objects[x['return_uuid']];assert o['group']==main and o['net']=='LINK_AGND'
 signal=next(v for v in c['objects']if v['kind']in ['PAD','PCB_VIA']and (v['net'].startswith(('/A_DAC/','/A_ADC/'))or v['net']=='/D_LED/LED_39')and math.dist(v['position_mm'],x['signal_at'])<1e-6)
 hole=unary_union([shape(ps)for ps in signal['layers'].values()]).buffer(.215)
 corridor=LineString([x['signal_at'],x['return_at']]).buffer(.1).difference(hole)
 contact={l:field.intersection(shape(o['layers'][l])).area for l,field in fields.items()};missing={l:corridor.difference(field.buffer(2e-6)).area for l,field in fields.items()}
 paths=[]
 for path in candidate_paths(x['signal_at'],x['return_at']):
  line=LineString(path)
  if line.length>2.5+1e-9:continue
  area=line.buffer(.1).difference(hole)
  gaps={l:area.difference(f.buffer(2e-6)).area for l,f in fields.items()}
  if all(v>1e-6 for v in contact.values()) and all(v<1e-6 for v in gaps.values()):paths.append((line.length,path,gaps))
 if not paths and all(v>1e-6 for v in contact.values()):
  for path in v_paths(x['signal_at'],x['return_at']):
   line=LineString(path);area=line.buffer(.1).difference(hole);gaps={l:area.difference(f.buffer(2e-6)).area for l,f in fields.items()}
   if line.length<=2.5+1e-9 and all(v<1e-6 for v in gaps.values()):paths.append((line.length,path,gaps));v_path_keys.add(tuple(tuple(q)for q in path))
 proposed={**x,'direct_corridor_uncovered_mm2':missing}
 if not paths:
  for alternative in objects.values():
   if alternative['net']!='LINK_AGND'or alternative['kind']!='PCB_VIA'or alternative['group']!=main or math.dist(x['signal_at'],alternative['position_mm'])>2.5:continue
   if not all(alternative['layers'].get(l)for l in fields):continue
   contacts={l:f.intersection(shape(alternative['layers'][l])).area for l,f in fields.items()}
   if not all(v>1e-6 for v in contacts.values()):continue
   for family,path in chain((('existing',p)for p in candidate_paths(x['signal_at'],alternative['position_mm'])),(('v',p)for p in v_paths(x['signal_at'],alternative['position_mm']))):
    line=LineString(path)
    if line.length>2.5+1e-9:continue
    area=line.buffer(.1).difference(hole);gaps={l:area.difference(f.buffer(2e-6)).area for l,f in fields.items()}
    if all(v<1e-6 for v in gaps.values()):
     paths.append((line.length,path,gaps));o=alternative;contact=contacts
     if family=='v':v_path_keys.add(tuple(tuple(q)for q in path))
     x={**x,'return_at':o['position_mm'],'return_uuid':o['uuid'],'distance_mm':math.dist(x['signal_at'],o['position_mm']),'kind':'verified alternate native ground via'}
     break
   if paths:break
 assert paths,('no continuous local return within allocation',x,missing)
 length,path,gaps=min(paths,key=lambda v:v[0])
 rows.append({**x,'signal_uuid':signal['uuid'],'signal_net':signal['net'],'signal_native_group':signal['group'],'authored_proposed_return':proposed,'same_native_group':main,'direct_plane_contact_mm2':contact,'direct_corridor_uncovered_mm2':missing,'verified_bounded_v_fallback':tuple(tuple(q)for q in path)in v_path_keys,'verified_return_corridor_path_mm':path,'verified_return_corridor_length_mm':length,'corridor_uncovered_mm2':gaps})
old={(z['uuid'],z['layer']):z for z in b['zones']};changes=[]
for z in c['zones']:
 k=(z['uuid'],z['layer']);g=shape(z['polygons']);p=shape(old[k]['polygons'])if k in old else Point().buffer(0);lost=p.difference(g).area;gain=g.difference(p).area
 if lost+gain>1e-7:changes.append({'uuid':k[0],'layer':k[1],'net':z['net'],'new_zone':k not in old,'lost_mm2':lost,'gained_mm2':gain})
paths=[Path(__file__),R/'return_paths.py',R/'test_return_paths.py',I/'capture-r7/capture.json',R/'capture-r139/capture.json',R/'candidate-r139/routing.json',R/'candidate-r98/routing.json',R/'candidate-r107/routing.json',R/'candidate-r125/routing.json'];result={'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'transitions':rows,'plane_fill_changes':changes,'maximum_local_return_distance_mm':max(v['distance_mm']for v in rows),'noise_qualified':False};(R/'transitions-r139.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps([x for x in rows if any(v>1e-6 for v in x['corridor_uncovered_mm2'].values())],indent=2));assert all(v<1e-6 for x in rows for v in x['corridor_uncovered_mm2'].values());print('PASS',len(rows),'local return corridors within 2.5 mm')
