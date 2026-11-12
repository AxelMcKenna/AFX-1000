"""Native proof of every input-stage signal transition's local return path."""
import json,math,hashlib
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.fabrication.route_nf_surface import shape
R=Path(__file__).resolve().parent;I=R.parent/'i2c_routing';b=json.loads((I/'capture-after-r4/capture.json').read_text());c=json.loads((R/'capture-r7/capture.json').read_text());r=json.loads((R/'candidate-r7/routing.json').read_text());objects={o['uuid']:o for o in c['objects']};main=next(o['group']for o in c['objects']if o.get('ref')=='D_U1001'and o.get('pin')=='20')
fields={l:unary_union([shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']==l])for l in ['In1.Cu','In4.Cu','In6.Cu']};rows=[]
for x in r['transitions']:
 o=objects[x['return_uuid']];assert o['group']==main and o['net']=='LINK_AGND'
 signal=next(v for v in c['objects']if v['kind']in ['PAD','PCB_VIA']and v['net'].startswith('/A_INPUT/')and math.dist(v['position_mm'],x['signal_at'])<1e-6)
 hole=unary_union([shape(ps)for ps in signal['layers'].values()]).buffer(.215)
 corridor=LineString([x['signal_at'],x['return_at']]).buffer(.1).difference(hole)
 contact={l:field.intersection(shape(o['layers'][l])).area for l,field in fields.items()};missing={l:corridor.difference(field.buffer(.0015)).area for l,field in fields.items()}
 assert all(v>1e-6 for v in contact.values()),(x,contact)
 rows.append({**x,'same_native_group':main,'direct_plane_contact_mm2':contact,'corridor_uncovered_mm2':missing})
old={(z['uuid'],z['layer']):z for z in b['zones']};changes=[]
for z in c['zones']:
 k=(z['uuid'],z['layer']);g=shape(z['polygons']);p=shape(old[k]['polygons'])if k in old else Point().buffer(0);lost=p.difference(g).area;gain=g.difference(p).area
 if lost+gain>1e-7:changes.append({'uuid':k[0],'layer':k[1],'net':z['net'],'new_zone':k not in old,'lost_mm2':lost,'gained_mm2':gain})
paths=[Path(__file__),I/'capture-after-r4/capture.json',R/'capture-r7/capture.json',R/'candidate-r7/routing.json'];result={'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'transitions':rows,'plane_fill_changes':changes,'maximum_local_return_distance_mm':max(v['distance_mm']for v in rows),'noise_qualified':False};(R/'transitions-r7.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps([x for x in rows if any(v>1e-6 for v in x['corridor_uncovered_mm2'].values())],indent=2));assert all(v<1e-6 for x in rows for v in x['corridor_uncovered_mm2'].values());print('PASS',len(rows),'local returns')
