"""Screen a five-part input-stage placement candidate before routing or adoption."""
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
out=STAGING/'two-board-input-stage-survey-01'
assert not out.exists()
base=STAGING/'two-board-power-input-controls-native-02'
cap=json.loads((STAGING/'two-board-power-routing-inputs-2440-input-controls/capture.json').read_text())
for name,h in cap['source_sha256'].items():assert sha(REPO/name)==h,name
board=read_sexpr((base/'power_protection.kicad_pcb').read_text())
old={prop(f,'Reference')[2]:f for f in children(board,'footprint')};fps=copy.deepcopy(old)
moves={'P_Q101':([190.3,114.8],90),'P_Q102':([191.2,120.4],180),'P_C103':([218.5,121],0),'G_NT1':([198.7,132.2],0),'P_C104':([202.4,122.4],0)}
for o in cap['objects']:
 if o.get('ref') in moves and o.get('pin'):assert cap['all_groups'][o['group']]==[o['uuid']]
for r,(xy,rot) in moves.items():fps[r]=rotate_footprint(old[r],xy,rot)
placement=json.loads((STAGING/'two-board-placement-05/capture.json').read_text());records={r['id']:r for r in placement['parts']}
for k in ['side','angle','body_relative_xy','courtyard_relative_xy','additional_planar_reserves','tails_relative_xy']: records['P_C204'][k]=copy.deepcopy(records['P_C205'][k])
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
  if z['layer']==l:assert g.distance(shape(z['authored_outline']))>.21,(o['ref'],o.get('pin'),'old zone',z['uuid'])
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
pairs=[(('P_Q102','3'),('P_Q101','4')),(('P_Q102','2'),('P_Q101','3')),
       (('P_Q102','1'),('P_U101','4')),(('P_Q101','5'),('P_U101','1')),
       (('P_C104','1'),('P_U101','18')),(('P_C103','1'),('P_U101','18'))]
distances=[dict(terminals=[a,b],straight_pad_center_distance_mm=Point(pad(*a)['position_mm']).distance(Point(pad(*b)['position_mm']))) for a,b in pairs]
paths=[Path(__file__),base/'power_protection.kicad_pcb',base/'input-controls-audit.json',
       STAGING/'two-board-power-routing-inputs-2440-input-controls/capture.json',
       STAGING/'two-board-placement-05/capture.json',STAGING/'assembly-layout-04/allocation.json',
       *[REPO/'hardware/fabrication'/n for n in ['route_two_board_buck_cell.py','repack_two_board_buck_input.py','route_nf_surface.py']],
       REPO/'hardware/electronics/output_stage/check_placement.py']
result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
 poses=[dict(ref=r,old_xy=position(old[r]),new_xy=xy,rotation_added_degrees=rot,
             final_angle=angle(fps[r]),side=first(fps[r],'layer')[1]) for r,(xy,rot) in moves.items()],
 all_moved_numbered_pad_groups_isolated=True,mechanical_courtyard_body_height_context_screen_pass=True,
 moved_C103_back_lead_reserves_screen_pass=True,moved_pad_copper_and_drill_screen_pass=True,
 minimum_moved_pad_to_other_drill_edge_mm=minimum_drill_gap,all_existing_zone_outlines_avoided=True,
 bare_return_net_tie_height_mm=0.0,all_values_packages_sides_and_pin_nets_retained=True,
 straight_pad_center_distances=distances,
 manufacturer_source='https://www.ti.com/lit/ds/symlink/tps2663.pdf',manufacturer_section='9.6.1, SLVSE94G',
 constraints=[
 'This is a geometric candidate, not a selected electrical layout. Prove a short Q102/Q101 pulldown loop and feasible gate/DRV routes before applying it.',
 'Q101 drain-to-IN must use an adequate short force plane. The current candidate has an 8mm-class pad-center distance; compare rotation/placement alternatives before accepting that path.',
 'The larger C103 moves about 20mm from the OUT pad. C104 stays local; both output and return distribution and transient behavior require review.',
 'C101 remains at its old remote position. Resolve the IN_SYS bypass loop and voltage dividers together with the source layout.',
 'The G_NT1 location is provisional; verify return-star topology and actual current/thermal capacity before accepting it.',
 'Accept the fabrication stack and size force paths for at least twice the intended full-load current; check installed thermal dissipation and exact component tolerances.'],
 candidate_only=True,native_candidate_validation_pending=True,new_routes_created=False,
 physical_board_modified=False,electrical_qualified=False,fabrication_released=False)
out.mkdir();(out/'survey.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['poses','straight_pad_center_distances','minimum_moved_pad_to_other_drill_edge_mm','physical_board_modified']},indent=2))
