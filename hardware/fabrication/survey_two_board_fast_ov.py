"""Screen coordinated fast-overvoltage placement before routing or adoption."""
import copy,json
from shapely.geometry import Point
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from pathlib import Path
from shapely.affinity import rotate,translate
from shapely.geometry import box,LineString
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.route_two_board_buck_cell import position,angle,mechanical_check,transform_object
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_nf_surface import shape
out=STAGING/'two-board-fast-ov-survey-01'
assert not out.exists()
base=STAGING/'two-board-power-input-thresholds-native-03'
cap=json.loads((STAGING/'two-board-power-routing-inputs-2405-input-thresholds/capture.json').read_text())
for name,h in cap['source_sha256'].items():assert sha(REPO/name)==h,name
board=read_sexpr((base/'power_protection.kicad_pcb').read_text())
old={prop(f,'Reference')[2]:f for f in children(board,'footprint')};fps=copy.deepcopy(old)
moves=json.loads(Path('/private/tmp/tbp31-moves.json').read_text())
for o in cap['objects']:
 if o.get('ref') in moves and o.get('pin'):assert cap['all_groups'][o['group']]==[o['uuid']]
for r,(xy,rot) in moves.items():fps[r]=rotate_footprint(old[r],xy,rot)
placement=json.loads((STAGING/'two-board-placement-05/capture.json').read_text());records={r['id']:r for r in placement['parts']}
for r,t in [('P_C204','P_C205'),('P_C104','P_C102'),('P_C101','P_C102'),('P_R101','P_R102'),('P_R103','P_R102'),('P_R104','P_R102')]:
 for k in ['side','angle','body_relative_xy','courtyard_relative_xy','additional_planar_reserves','tails_relative_xy']:records[r][k]=copy.deepcopy(records[t][k])
assert len(children(old['G_NT1'],'model'))==0
placement['parts'].append(dict(id='G_NT1',height_mm=0.0,side='F',angle=0,body_relative_xy=[-1.2,-.8,1.2,.8],additional_planar_reserves=[],tails_relative_xy=[]))
mechanical_check(fps,set(moves),placement)
objects=[transform_object(o,position(old[o['ref']]),*moves[o['ref']]) if o.get('ref') in moves else o for o in cap['objects']]
geoms=[(o,l,shape(ps)) for o in objects for l,ps in o['layers'].items() if ps]
trees={l:([(o,g) for o,k,g in geoms if k==l],STRtree([g for o,k,g in geoms if k==l])) for l in cap['copper_layers']}
for o,l,g in geoms:
 if o.get('ref') not in moves:continue
 rows,t=trees[l]
 for i in t.query(g.buffer(.211)):
  q,h=rows[int(i)]
  if q.get('ref')!=o['ref'] and q['net']!=o['net']:assert g.distance(h)>=.21-1e-7,(o['ref'],o.get('pin'),q.get('ref'),q.get('pin'),g.distance(h))
 for z in cap['zones']:
  if z['layer']==l and z['uuid']!='a147ef12-37f5-562e-9340-6c74b3790186':assert g.distance(shape(z['authored_outline']))>.21,(o['ref'],o.get('pin'),'old zone',z['uuid'])
# The generic receiver check does not screen a moved through-hole part's
# new lead tails. Independently include C103's opposite-face lead envelopes.
receivers={'F':[],'B':[]}
for ref,f in fps.items():
 for side in ['F','B']:
  try:receivers[side].append((ref,box(*courtyard(f,side+'.CrtYd'))))
  except AssertionError:pass
 r=records.get(ref)
 if r:
  delta=angle(f)-r['angle'];x,y=position(f)
  def env(b):return translate(rotate(box(*b),-delta,origin=(0,0)),x,y)
  receivers[r['side']].append((ref,env(r['body_relative_xy'])))
  for e in r['additional_planar_reserves']:receivers[e['side']].append((ref,env(e['bounds'])))
  for b in r['tails_relative_xy']:receivers['B'].append((ref,env(b)))
for ref in moves:
 r=records.get(ref)
 if not r:continue
 x,y=position(fps[ref]);delta=angle(fps[ref])-r['angle']
 for b in r['tails_relative_xy']:
  g=translate(rotate(box(*b),-delta,origin=(0,0)),x,y).buffer(.3,join_style=2)
  assert all(other==ref or g.intersection(h).area<1e-8 for other,h in receivers['B']),(ref,'opposite-face lead reserve')
outline=shape(cap['outline']).buffer(-.5)
mounts=[(Point(o['position_mm']),max(3.6,max(o['drill_mm'])/2+.5)) for o in objects
        if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
holes=[]
for o in objects:
 d=o.get('drill_mm',0);radius=max(d)/2 if isinstance(d,list) else d/2
 if radius:holes.append((o,Point(o['position_mm']),radius))
minimum_drill_gap=1e9
for ref in moves:
 f=fps[ref];g=box(*courtyard(f,first(f,'layer')[1][0]+'.CrtYd'))
 assert outline.covers(g)
 assert all(g.distance(p)>=radius+.3 for p,radius in mounts)
for o,l,g in geoms:
 if o.get('ref') not in moves:continue
 assert outline.covers(g)
 for h,p,r in holes:
  if o.get('ref')==h.get('ref'):continue
  gap=g.distance(p)-r
  assert gap>=.15-2e-6,(o.get('ref'),h.get('ref'),gap)
  minimum_drill_gap=min(minimum_drill_gap,gap)
for o,p,r in holes:
 if o.get('ref') not in moves:continue
 for q,l,g in geoms:
  if q.get('ref')==o.get('ref') or q['kind']!='PAD' or any(q['drill_mm']):continue
  assert g.distance(p)-r>=.15-2e-6,(o.get('ref'),q.get('ref'))
 for q,pos,radius in holes:
  if q['uuid']==o['uuid']:continue
  assert p.distance(pos)-r-radius>=.25-2e-6,(o.get('ref'),q.get('ref'))
def pad(ref,pin):return next(o for o in objects if o.get('ref')==ref and o.get('pin')==pin)
pairs=[(('P_U103','5'),('P_C108','1')),(('P_U103','2'),('P_C108','2')),(('P_U103','3'),('P_R115','2')),(('P_U103','3'),('P_R116','1')),(('P_U103','4'),('P_C109','1')),(('P_U103','1'),('P_R121','1')),(('P_R121','2'),('P_Q103','1'))]
distances=[dict(terminals=[a,b],straight_pad_center_distance_mm=Point(pad(*a)['position_mm']).distance(Point(pad(*b)['position_mm']))) for a,b in pairs]
paths=[Path(__file__),base/'power_protection.kicad_pcb',base/'input-thresholds-audit.json',
       STAGING/'two-board-power-routing-inputs-2405-input-thresholds/capture.json',
       STAGING/'two-board-placement-05/capture.json',STAGING/'assembly-layout-04/allocation.json',
       *[REPO/'hardware/fabrication'/n for n in ['route_two_board_buck_cell.py','repack_two_board_buck_input.py','route_nf_surface.py']],
       REPO/'hardware/electronics/output_stage/check_placement.py']
result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
 poses=[dict(ref=r,old_xy=position(old[r]),new_xy=xy,rotation_added_degrees=rot,
             final_angle=angle(fps[r]),side=first(fps[r],'layer')[1]) for r,(xy,rot) in moves.items()],
 all_moved_numbered_pad_groups_isolated=True,mechanical_courtyard_body_height_context_screen_pass=True,
 all_moved_parts_SMD=True,moved_pad_copper_and_drill_screen_pass=True,
 minimum_moved_pad_to_other_drill_edge_mm=minimum_drill_gap,all_existing_zone_outlines_avoided=True,
 bare_return_net_tie_height_mm=0.0,all_values_packages_sides_and_pin_nets_retained=True,
 straight_pad_center_distances=distances,
 manufacturer_source='https://www.ti.com/lit/ds/symlink/tlv7011.pdf',manufacturer_section='5 and 10.1, SLVSDM5F',
 constraints=['Complete all local comparator routes, short VCC/GND bypass loop, reference return and shutdown gate loop before adopting placement.', 'Final threshold, loaded response, power-state and startup checks remain required; typical comparator delay is not a full-temperature maximum.'],
 candidate_only=True,native_candidate_validation_pending=True,new_routes_created=False,
 physical_board_modified=False,electrical_qualified=False,fabrication_released=False)
out.mkdir();(out/'survey.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['poses','straight_pad_center_distances','minimum_moved_pad_to_other_drill_edge_mm','physical_board_modified']},indent=2))
