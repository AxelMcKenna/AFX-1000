"""Independent group, filled-reference and contact-location review of selected r4."""
import json,collections,hashlib
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
from shapely import make_valid
from hardware.fabrication.route_nf_surface import shape
R=Path(__file__).resolve().parent;REPO=R.parents[3]
b=json.loads((R/'capture-baseline/capture.json').read_text());a=json.loads((R/'capture-after-r4/capture.json').read_text());routing=json.loads((R/'candidate-r4/routing.json').read_text());native=json.loads((R/'native-r4/review.json').read_text())
for cap in [b,a]:
 for f,h in cap['source_sha256'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,f
for f,h in native['source_sha256'].items():assert hashlib.sha256((REPO/f).read_bytes()).hexdigest()==h,f
old,new=[{v['uuid']:v for v in c['objects']}for c in [b,a]];after={u:k for k,vs in a['all_groups'].items()for u in vs};merged=collections.defaultdict(list)
for k,vs in b['all_groups'].items():
 dst={after[u]for u in vs if u in after};assert len(dst)==1,(k,dst);assert all(u in new for u in vs);merged[next(iter(dst))].append(k)
merges=[]
for k,olds in merged.items():
 if len(olds)==1:continue
 net=old[b['all_groups'][olds[0]][0]]['net'];assert net in ['LINK_SCL','LINK_SDA','LINK_AGND']
 groups=[]
 for gid in olds:
  members=b['all_groups'][gid];assert all(old[u]['net']==net for u in members)
  groups.append({'group':gid,'all_member_uuids':members,'pads':[{k:old[u].get(k)for k in ['ref','pin','uuid','position_mm']}for u in members if old[u]['kind']=='PAD']})
 merges.append({'net':net,'old_groups':groups,'after_group':k})
assert {m['net']:len(m['old_groups'])for m in merges}=={'LINK_SCL':3,'LINK_SDA':3,'LINK_AGND':2}
main=next(o['group']for o in a['objects']if o.get('ref')=='D_U1001'and o.get('pin')=='20')
def refs(c):
 fields=collections.defaultdict(list);ground=[o for o in c['objects']if o['net']=='LINK_AGND']
 for z in c['zones']:
  if z['net']!='LINK_AGND' or z['keepout']:continue
  for p in z['polygons']:
   g=Polygon(p['outer'],p['holes']);assert g.is_valid
   hits={o['group']for o in ground if o['group']and o['layers'].get(z['layer'])and g.buffer(.0015).intersection(shape(o['layers'][z['layer']])).area>1e-9}
   # Same-layer overlap with another connected zone can supply the anchor.
   if not hits:
    for zz in c['zones']:
     if zz['net']=='LINK_AGND'and zz['layer']==z['layer']and zz['uuid']!=z['uuid']:
      q=shape(zz['polygons'])
      if g.intersection(q).area>1e-9:
       hits|={o['group']for o in ground if o['group']and o['layers'].get(z['layer'])and q.buffer(.0015).intersection(shape(o['layers'][z['layer']])).area>1e-9}
   if not hits:continue
   assert len(hits)==1,(z['uuid'],hits)
   fields[(z['layer'],next(iter(hits)))].append(g)
 return {k:unary_union(v)for k,v in fields.items()}
f0,f1=refs(b),refs(a);layers=a['copper_layers']
def adjacent(layer):
 i=layers.index(layer);return{layers[j]for j in [i-1,i+1]if 0<=j<len(layers)}
def transition_holes(objects,net):
 hs=[]
 for o in objects.values():
  if o['net']!=net:continue
  if o['kind']=='PCB_VIA':hs.append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
  elif o['kind']=='PAD'and any(o['drill_mm']):
   hs.extend(shape(ps).buffer(.215)for ps in o['layers'].values()if ps)
 return unary_union(hs)
holes0={};holes1={};retained=[]
reference_before={l:unary_union([v for (ll,_),v in f0.items()if ll in adjacent(l)])for l in layers}
reference_after={l:unary_union([v for (ll,_),v in f1.items()if ll in adjacent(l)])for l in layers}
for uid,o in old.items():
 if o['kind']!='PCB_TRACK'or o['net']=='LINK_AGND':continue
 net=o['net'];layer,=o['layers'];adj=adjacent(layer)
 if net not in holes0:holes0[net]=transition_holes(old,net);holes1[net]=transition_holes(new,net)
 g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(holes0[net])
 before=reference_before[layer];afterfield=reference_after[layer];covered=g.intersection(before)
 loss=covered.difference(afterfield.buffer(.0015)).area
 if covered.area>1e-8:retained.append({'uuid':uid,'net':net,'layer':layer,'previous_covered_mm2':covered.area,'lost_mm2':loss})
newrefs=[]
for v in routing['routes']:
 net=v['net'];g=LineString(v['path_mm']).buffer(v['width_mm']/2).difference(holes1[net]);field=unary_union([p for (l,gid),p in f1.items()if l in adjacent(v['layer'])and gid==main]);missing=g.difference(field.buffer(.0015));newrefs.append({'name':v['name'],'layer':v['layer'],'uncovered_mm2':missing.area,'uncovered_bounds':list(missing.bounds)if not missing.is_empty else[]})
oldzones={z['uuid']for z in b['zones']};contacts=[]
for z in a['zones']:
 if z['uuid']in oldzones:continue
 g=shape(z['polygons']);hit=[]
 for o in b['objects']:
  if o['net']=='LINK_AGND'and o['layers'].get(z['layer'])and g.buffer(.0015).intersection(shape(o['layers'][z['layer']])).area>1e-9:hit.append({k:o.get(k)for k in ['uuid','ref','pin','position_mm','kind','group']})
 contacts.append({'zone':z['uuid'],'layer':z['layer'],'authored_outline':z['authored_outline'],'filled_area_mm2':g.area,'contacts':hit,'existing_zone_overlap_mm2':sum(g.intersection(shape(zz['polygons'])).area for zz in b['zones']if zz['net']=='LINK_AGND'and zz['layer']==z['layer'])})
 assert any(o.get('ref')=='A_J402'and o.get('pin')=='1'for o in hit)
 assert not any(o.get('ref')=='A_J402'and o.get('pin')=='7'for o in hit)
paths=[Path(__file__),R/'native-r4/review.json',R/'capture-baseline/capture.json',R/'capture-after-r4/capture.json',R/'candidate-r4/routing.json',REPO/'hardware/fabrication/staging/audio-main-integration-04b/audio-leg-connections.csv',REPO/'hardware/electronics/processor_carrier/README.md',REPO/'hardware/electronics/converter/README.md']
report={'scope':'Proposed continuous control return at scheduled A_J402.1; noise/high-current/system-ground qualification remains open','source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'all_original_native_groups_preserved':True,'only_approved_net_groups_merged':merges,'new_reference_cases':newrefs,'new_ground_contacts':contacts,'retained_reference_cases':retained,'maximum_retained_loss_mm2':max(x['lost_mm2']for x in retained),'full_noise_acceptance':False}
(R/'return-review-r4.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'new_refs':newrefs,'retained_cases':len(retained),'max_loss':report['maximum_retained_loss_mm2'],'ground_contacts':contacts},indent=2)[:3500]);assert all(v['uncovered_mm2']<1e-6 for v in newrefs);assert all(v['lost_mm2']<1e-6 for v in retained)
