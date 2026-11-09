"""Verify references and unchanged supply/quiet fields after startup-cell joins."""
import json
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-startup-references-native-04'
OUT=STAGING/'two-board-power-startup-cells-native-03'
BEFORE=STAGING/'two-board-power-routing-inputs-2210-startup-references-04/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2199-startup-cells-03/capture.json'


def run():
 paths=[BEFORE,AFTER,OUT/'startup-cell-routing.json',OUT/'startup-cell-review.json',BASE/'startup-reference-coverage.json']
 before,after,r,audit,prior=[json.loads(p.read_text()) for p in paths]
 assert audit['all_other_native_groups_preserved'] and audit['closed_connections']==11
 for path,d in zip(paths,[before,after,r,audit,prior]):
  for n,h in d['source_sha256'].items():
   p=Path(n);assert sha(p if p.is_absolute() else REPO/p)==h,(path,n)
 aliases=audit['generated_pad_identity_aliases']
 for o in after['objects']:o['uuid']=aliases.get(o['uuid'],o['uuid']);o['group']=aliases.get(o['group'],o['group'])
 old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
 unanchored=[]
 def fields(c):
  result={};excluded=[]
  contacts={l:[(o['group'],shape(o['layers'][l])) for o in c['objects'] if o['net']=='PWR_AGND' and o['layers'].get(l)] for l in c['copper_layers']}
  for z in c['zones']:
   if z['net']!='PWR_AGND':continue
   for p in z['polygons']:
    g=Polygon(p['outer'],p['holes']);groups={gid for gid,s in contacts[z['layer']] if g.buffer(.0015).intersection(s).area>1e-9}
    # Do not credit copper without a direct native-object contact as a return.
    # Record it and require exact preservation across the candidate change.
    if not groups:
     excluded.append(dict(zone_uuid=z['uuid'],layer=z['layer'],polygon=p,area_mm2=g.area));continue
    assert len(groups)==1,(z['uuid'],groups)
    result.setdefault((z['layer'],next(iter(groups))),[]).append(g)
  unanchored.append(excluded)
  return {k:unary_union(ps) for k,ps in result.items()}
 f0,f1=fields(before),fields(after)
 assert unanchored[0]==unanchored[1], 'Unanchored ground fragments changed'
 layers=before['copper_layers'];holes={}
 for o in old.values():
  if o['kind']=='PCB_VIA':holes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
 holes={n:unary_union(ps) for n,ps in holes.items()};coverage=[]
 for u,o in old.items():
  if u in r['retired_objects'] or o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
  assert o['position_mm']==new[u]['position_mm'] and o['end_mm']==new[u]['end_mm'] and o['width_mm']==new[u]['width_mm']
  layer,=o['layers'];i=layers.index(layer);adj={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)}
  g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(holes.get(o['net'],Polygon()))
  if g.is_empty:continue
  for (l,gid),field in f0.items():
   if l not in adj or g.difference(field.buffer(.0015)).area>=1e-6:continue
   anchors=[x for x in before['all_groups'][gid] if x in new];assert anchors
   target=f1[(l,new[anchors[0]]['group'])];missing=g.difference(target.buffer(.0015)).area
   coverage.append(dict(track_uuid=u,net=o['net'],reference_layer=l,uncovered_mm2=missing))
 newholes={}
 for o in new.values():
  if o['kind']=='PCB_VIA':newholes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
  elif o['kind']=='PAD' and any(o['drill_mm']):
   for ps in o['layers'].values():
    if ps:newholes.setdefault(o['net'],[]).append(shape(ps).buffer(.215))
 newholes={n:unary_union(ps) for n,ps in newholes.items()}
 main=next(o['group'] for o in new.values() if o.get('ref')=='P_C103' and o.get('pin')=='2');newrefs=[]
 for rr in r['routes']:
  if rr['net']=='PWR_AGND':continue
  assert rr['layer'] in ['F.Cu','B.Cu']
  reference='In6.Cu' if rr['layer']=='B.Cu' else 'In1.Cu'
  g=LineString(rr['path_mm']).buffer(rr['width_mm']/2).difference(newholes.get(rr['net'],Polygon()))
  field=f1[(reference,main)];missing=g.difference(field.buffer(.0015)).area
  newrefs.append(dict(label=rr['label'],reference_layer=reference,uncovered_mm2=missing))
 z0,z1=[{z['uuid']:z for z in c['zones']} for c in [before,after]]
 supplies=[u for u,z in z0.items() if z['net']!='PWR_AGND'];assert len(supplies)==11
 assert all(z0[u]==z1[u] for u in supplies)
 quietpaths=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']
 quietids={u for p in quietpaths for q in json.loads(p.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
 assert all(z0[u]==z1[u] for u in quietids)
 assert prior['startup_references_complete'] and prior['digital_own_quiet_reference_complete']
 # The full current startup paths are measured directly in the current field.
 startupmanifest=BASE/'startup-reference-routing.json';startup=[]
 for rr in json.loads(startupmanifest.read_text())['routes']:
  if rr['net']=='PWR_AGND':continue
  i=layers.index(rr['layer']);adj={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)}
  field=unary_union([v for (l,gid),v in f1.items() if l in adj and gid==main])
  g=LineString(rr['path_mm']).buffer(rr['width_mm']/2).difference(holes.get(rr['net'],Polygon()))
  startup.append(dict(label=rr['label'],uncovered_mm2=g.difference(field.buffer(.0015)).area))
 sources=[Path(__file__),*paths,*quietpaths,startupmanifest,REPO/'hardware/fabrication/route_nf_surface.py']
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},retained_reference_cases=coverage,retained_reference_complete=all(x['uncovered_mm2']<1e-6 for x in coverage),new_non_ground_paths=newrefs,new_reference_complete=all(x['uncovered_mm2']<1e-6 for x in newrefs),prior_startup_paths=startup,prior_startup_reference_complete=all(x['uncovered_mm2']<1e-6 for x in startup),all_eleven_supply_planes_unchanged=True,all_seven_quiet_network_fields_unchanged=True,digital_own_quiet_reference_preserved=True,projection_only=True,loaded_electrical_thermal_qualified=False,fabrication_released=False)
 result.update(unanchored_fragments_excluded=unanchored[1],unanchored_fragments_unchanged=True)
 with (OUT/'startup-cell-reference-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(dict(retained_cases=len(coverage),retained_gaps=[x for x in coverage if x['uncovered_mm2']>=1e-6],new_paths=len(newrefs),new_gaps=[x for x in newrefs if x['uncovered_mm2']>=1e-6],prior_startup_gaps=[x for x in startup if x['uncovered_mm2']>=1e-6])))


if __name__=='__main__':run()
