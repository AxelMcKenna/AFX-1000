"""Verify bounded holder-only relief; no printed strength or service claim."""
import hashlib,json,math,struct
from collections import defaultdict
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
e=json.loads((H/'exits.json').read_text());sources={}
for name,digest in e['source_sha256'].items():assert sha(R/name)==digest;sources[name]=digest
inventory=json.loads((H.parent/'r19_panel_inventory/inventory.json').read_text())
for name,digest in inventory['source_sha256'].items():assert sha(R/name)==digest;sources[name]=digest
assert e['source_azimuth_degrees']==129.6 and e['receiving_radius_mm']==.6 and e['cut_radius_mm']==.9
assert e['cut_inscribed_margin_after_chord_error_mm']>=.25
assert {(x['source'],x['target']) for x in e['edges']}=={('D_J2001:9','button_tap:1'),('D_J2001:11','button_auto:1')}
for edge in e['edges']:
 row=next(row for row in inventory['wires'] if row['source']==edge['source'] and row['target']==edge['target']);assert row['net']==edge['net']
 assert edge['points_mm'][0]==row['source_xy_mm']+[27.04]
 assert len(edge['primitives'])==1 and edge['primitives'][0]['radius_mm']==12 and edge['primitives'][0]['tangent']==[0.,0.,1.]
rows={}
for case in ['holder_positive','removed','nonplastic','mount_posts','bearing_layer','lead_bores','source_holder']:
 folder=H/'native'/(case+'-r1');v=json.loads((folder/'result.json').read_text());assert not v['runtime_failure']
 for name,digest in v['source_sha256'].items():assert sha(R/name)==digest;sources[name]=digest
 if case in ['holder_positive','removed']:assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
 else:assert v['empty'] and v['mesh'] is None
 rows[case]={'mesh':v['mesh'],'empty':v['empty'],'artifact_sha256':{str(p.relative_to(R)):sha(p) for p in sorted(folder.iterdir()) if p.is_file()}}
# Surface connectivity after the same zero-area exclusion as native audit.
raw=(H/'native/holder_positive-r1/holder_positive.stl').read_bytes();neighbors=defaultdict(set)
for i in range(struct.unpack_from('<I',raw,80)[0]):
 row=struct.unpack_from('<12fH',raw,84+50*i);a,b,c=(tuple(row[j:j+3]) for j in (3,6,9))
 cross=[(b[(k+1)%3]-a[(k+1)%3])*(c[(k+2)%3]-a[(k+2)%3])-(b[(k+2)%3]-a[(k+2)%3])*(c[(k+1)%3]-a[(k+1)%3]) for k in range(3)]
 if sum(v*v for v in cross)<1e-24:continue
 for x,y in [(a,b),(b,c),(c,a)]:neighbors[x].add(y);neighbors[y].add(x)
remaining=set(neighbors);components=0
while remaining:
 components+=1;todo=[remaining.pop()]
 while todo:
  for point in neighbors[todo.pop()]:
   if point in remaining:remaining.remove(point);todo.append(point)
assert components==1
for p in [Path(__file__),H/'exits.json',H/'holder.scad',H/'exits.scad']:sources[str(p.relative_to(R))]=sha(p)
removed=rows['removed']['mesh']['volume_mm3'];remaining_volume=rows['holder_positive']['mesh']['volume_mm3']
out={'status':'LOCAL_PLASTIC_RELIEF_CLEAR_FULL_ROUTE_PENDING','removed_plastic_mm3':removed,'removed_fraction_of_original_volume':removed/(removed+remaining_volume),'connected_boundary_components':components,'unchanged_protected_regions':['Both full original mounting posts','All four lead bores','Full6x6mm switch-seat footprint upper0.5mm layer'],'nonplastic_cut_overlap':False,'printed_strength_qualified':False,'retention_qualified':False,'opening_slack_qualified':False,'completed_panel_edges':0,'cases':rows,'source_sha256':sources}
(H/'verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('source_sha256','cases')}))
