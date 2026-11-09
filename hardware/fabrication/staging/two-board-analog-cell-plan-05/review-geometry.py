"""Independent geometry screen of the proposed analog cell routing, excluding zones."""
import sys,json,math,copy
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from shapely.geometry import LineString,Point
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import read_sexpr,children,first
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.route_two_board_buck_cell import transform_object,position,mechanical_check
from hardware.fabrication.route_nf_surface import shape
PLAN=Path(__file__).resolve().parent
CAP=STAGING/'two-board-power-routing-inputs-2237-permission-04/capture.json'
BASE=STAGING/'two-board-power-permission-native-04/power_protection.kicad_pcb'
POSE=STAGING/'two-board-analog-cell-native-poses-04'
cap=json.loads(CAP.read_text());p=json.loads((PLAN/'placement.json').read_text());routes=json.loads((PLAN/'routes.json').read_text());poses=json.loads((POSE/'poses.json').read_text())
assert not routes['deferred'] and routes['moves']==p['moves']
for report in [cap,poses]:
 for name,digest in report['source_sha256'].items():assert sha(REPO/name)==digest,name
for name,digest in poses['artifact_sha256'].items():assert sha(POSE/name)==digest,name
oldfps={prop(f,'Reference')[2]:f for f in children(read_sexpr(BASE.read_text()),'footprint')}
fps={prop(f,'Reference')[2]:f for f in children(read_sexpr((POSE/'native-poses.kicad_pcb').read_text()),'footprint')}
posemap={r['ref']:r for r in poses['poses']}
retire=set(p['retired_objects']);assert retire==set(routes['retired_objects'])
removed=[o for o in cap['objects'] if o['uuid'] in retire]
assert len(removed)==len(retire) and all(o['kind'] in ['PCB_TRACK','PCB_VIA'] for o in removed)
objects=[];moved=[];errors=[]
for old in cap['objects']:
 if old['uuid'] in retire:continue
 o=old
 if old.get('ref') in p['moves']:
  ref=old['ref'];xy,rot,flip=p['moves'][ref];o=transform_object(old,position(oldfps[ref]),xy,rot)
  if flip:o['layers']={('B.Cu' if l=='F.Cu' else 'F.Cu' if l=='B.Cu' else l):ps for l,ps in o['layers'].items()}
  native=next(n for n in posemap[ref]['pads'] if n['pin']==o['pin'])
  err=math.dist(o['position_mm'],native['xy']);assert err<1e-7
  assert native['net']==o['net'] and set(o['layers'])=={posemap[ref]['side']}
  moved.append(o);errors.append(err)
 objects.append(o)
placementpath=STAGING/'two-board-placement-05/capture.json';placement=json.loads(placementpath.read_text())
allowed_sides={r['ref']:r for r in p['reconciled_existing_passive_sides']}
for r in placement['parts']:
 if r['id'] in fps and r['id'] not in p['moves'] and r['side']!=first(fps[r['id']],'layer')[1][0]:
  a=allowed_sides[r['id']];assert a['old_side']==r['side'] and a['current_side']==first(fps[r['id']],'layer')[1][0] and not r['tails_relative_xy']
  b=r['body_relative_xy'];assert abs(b[0]+b[2])<1e-7 and abs(b[1]+b[3])<1e-7
  r['side']=a['current_side']
mechanical_check(fps,set(p['moves']),placement)
seed=json.loads((PLAN/'seed.json').read_text());owners={ref:cell[0] for cell in seed['cells'] for ref in cell}
def foreign(net,owner,o):
 return o['net']!=net or (net=='PWR_AGND' and owners.get(o.get('ref'))!=owner)
rows={l:[(o,shape(o['layers'][l])) for o in objects if o['layers'].get(l)] for l in cap['copper_layers']};trees={l:STRtree([g for o,g in rr]) for l,rr in rows.items()}
new=routes['routes']+routes['connections'];assert len(routes['routes'])==len(routes['vias'])
paired=list(zip(routes['routes'],routes['vias']))+[(dict(owner=v['owner'],ref=v['ref'],pin=v['pin']),v) for v in routes['extra_quiet_vias']]
vias=[v for r,v in paired]
assert len({tuple(v['position_mm']) for v in vias})==len(vias)
outline=shape(cap['outline']);checks=0
for i,r in enumerate(new):
 line=LineString(r['path_mm']);w=r['width_mm'];assert w==.2 and line.length>0
 assert outline.buffer(-.61).covers(line)
 for j in trees[r['layer']].query(line.buffer(.312)):
  o,g=rows[r['layer']][int(j)]
  if foreign(r['net'],r['owner'],o):assert line.distance(g)>=.31-1e-7,('track-old',i,r.get('label'),o['uuid'],line.distance(g))
  checks+=1
 for s in new[i+1:]:
  if r['layer']!=s['layer']:continue
  if r['net']!=s['net'] or (r['net']=='PWR_AGND' and r['owner']!=s['owner']):assert line.distance(LineString(s['path_mm']))>=.41-1e-7,('track-pair',r,s)
  checks+=1
for i,(r,v) in enumerate(paired):
 point=Point(v['position_mm']);assert outline.buffer(-.81).covers(point)
 if 'path_mm' in r:assert math.dist(r['path_mm'][-1],v['position_mm'])<1e-7 and r['net']==v['net']
 for l in cap['copper_layers']:
  for j in trees[l].query(point.buffer(.512)):
   o,g=rows[l][int(j)]
   if foreign(v['net'],r['owner'],o):assert point.distance(g)>=.51-1e-7,('via-old',i,o['uuid'],point.distance(g))
   if o['kind']=='PAD' and not any(o['drill_mm']):assert point.distance(g)>=.3-1e-7,('via-SMD-drill',i,o['uuid'])
   checks+=1
 for o in objects:
  d=o.get('drill_mm',0);radius=(max(d) if isinstance(d,list) else d)/2
  if radius:assert point.distance(Point(o['position_mm']))>=.15+radius+.26-1e-7,('drill-hole',i,o['uuid'])
 for s in new:
  if v['net']!=s['net'] or (v['net']=='PWR_AGND' and r['owner']!=s['owner']):assert point.distance(LineString(s['path_mm']))>=.61-1e-7,('via-new-track',i,s.get('label'))
 for rr,vv in paired[i+1:]:
  minimum=.81 if (v['net']!=vv['net'] or (v['net']=='PWR_AGND' and r['owner']!=rr['owner'])) else .56
  assert math.dist(v['position_mm'],vv['position_mm'])>=minimum-1e-7,('via-pair',i,vv)
for o in moved:
 for l,ps in o['layers'].items():
  g=shape(ps);assert outline.buffer(-.5).covers(g)
  for j in trees[l].query(g.buffer(.212)):
   other,h=rows[l][int(j)]
   if other['uuid']==o['uuid']:continue
   if foreign(o['net'],owners[o['ref']],other):assert g.distance(h)>=.21-1e-7,('moved-pad',o['ref'],o['pin'],other['uuid'],g.distance(h))
restorations=[]
for r in routes['connections']:
 if 'power-good restoration' not in r['label']:continue
 endpoint=Point(r['path_mm'][-1]);contacts=[]
 for o,g in rows[r['layer']]:
  if o['net']==r['net'] and o['uuid'] not in retire and endpoint.distance(g)<1e-7:contacts.append(o['uuid'])
 assert contacts
 restorations.append(dict(label=r['label'],net=r['net'],layer=r['layer'],contact_mm=r['path_mm'][-1],retained_contact_objects=contacts))
inputs=[Path(__file__),CAP,BASE,PLAN/'placement.json',PLAN/'seed.json',PLAN/'routes.json',PLAN/'revise-routes.py',POSE/'poses.json',POSE/'native-poses.kicad_pcb',placementpath,STAGING/'assembly-layout-04/allocation.json',REPO/'hardware/fabrication/route_two_board_buck_cell.py',REPO/'hardware/fabrication/route_nf_surface.py']
report=dict(source_sha256={str(f.relative_to(REPO)):sha(f) for f in inputs},passed=True,moved_footprints=len(p['moves']),moved_pads=len(moved),maximum_native_pad_position_error_mm=max(errors),retired_tracks=sum(o['kind']=='PCB_TRACK' for o in removed),retired_vias=sum(o['kind']=='PCB_VIA' for o in removed),routes=len(new),tracks=sum(len(r['path_mm'])-1 for r in new),vias=len(vias),nearby_copper_and_route_pair_checks=checks,power_good_restoration_contacts=restorations,quiet_ground_owners_checked=sorted(set(owners.values())),scope='Candidate pad/track/via geometry and provisional moved-part mechanical envelopes. Zones are excluded; no board-wide connectivity, native DRC, quiet island ownership, adjacent return coverage or fabrication approval is claimed.',native_board_authoring_pending=True,quiet_zone_construction_pending=True,fabrication_released=False)
(PLAN/'geometry-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','moved_footprints','moved_pads','retired_tracks','retired_vias','routes','tracks','vias','nearby_copper_and_route_pair_checks']}))
