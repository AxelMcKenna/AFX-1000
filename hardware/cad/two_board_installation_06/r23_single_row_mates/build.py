from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;REPO=HERE.parents[3]
manifest=BASE/'r7/interface-manifest.json';capture=REPO/'hardware/cad/two_board_print_01/capture.json';audit=HERE/'board-audit.json';m=json.loads(manifest.read_text());cap=json.loads(capture.read_text());a=json.loads(audit.read_text());refs={h['reference'] for h in a['headers']};assert len(refs)==11
rows=[]
for i in m['interfaces']:
 if i['reference'] not in refs:continue
 ref=i['reference'];n=len(i['pads']);cx=sum(p['xy'][0] for p in i['pads'])/n;cy=i['pads'][0]['xy'][1];length=8.5 if n==3 else 13.6;wafer=length
 female=[[cx-length/2,cy-1.5,10.5,cx+length/2,cy+1.5,25.5]]
 male=[[cx-wafer/2,cy-1.5,8.35,cx+wafer/2,cy+1.5,11.3]]
 pins=[]
 tails=[[p["xy"][0]-.34,p["xy"][1]-.34,5.0,p["xy"][0]+.34,p["xy"][1]+.34,8.35] for p in i["pads"]]
 for p in sorted(i['pads'],key=lambda p:int(p['pin'])):
  used=not(ref=='D_J2003' and p['pin']=='1');target=('pot_'+['input','output','low','mid','high','scene_depth','x_level','x_pitch','scene_time','scene_resonance'][int(ref[3:])-1020]+':'+p['pin']) if n==3 else {'1':None,'2':'button_scene_9:1','3':'settings:W3.1','4':'release:W1.1','5':'release:W4.1'}[p['pin']]
  pins.append(dict(board_pin=p['pin'],assigned_female_position_from_west=int(p['pin']),xy_mm=p['xy'],net=p['net'],populated=used,receiver=target,wire_exit_receiving_mm=p['xy']+[26.15] if used else None))
 rows.append(dict(ref=ref,male='M20-9770346' if n==3 else 'M20-9770546',female='M20-1060300' if n==3 else 'M20-1060500',terminal='M20-1180046',qty_terminals=sum(p['populated'] for p in pins),pin_map=pins,center_xy=[cx,cy],orientation='assignedposition1 at smallestX; housing triangle at smallestX',female_boxes=female,male_wafer_receiving_boxes=male,tail_receiving_boxes=tails,withdrawal_boxes=[b[:5]+[b[5]+7.5] for b in female]))
assert len(rows)==11 and sum(r['qty_terminals'] for r in rows)==34
sources=[manifest,capture,audit,HERE/'audit_board.py',Path(__file__),HERE/'primary-sources.json',BASE/'r11_distribution/reference/alpha5853.pdf']+list((HERE/'reference').glob('*.pdf'))
out=dict(source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},choices=rows,confirmed=dict(family_mating=True,nominal_pad_pattern=True,wire_size_and_insulation_range=True),receiving_assumptions=dict(body_halfwidth_mm=1.5,length_registration_allowance_min_mm=0.38,seated_female_bottom_z_mm=[10.5,11.3],female_top_z_max_mm=25.5,wafer_height_project_range_mm=[2.44,2.64],withdrawal_stroke_mm=7.5,withdrawn_female_top_z_max_mm=33.0),not_qualified=['actual seated stack and datum registration','positive retention and polarization (none provided by this pair)','grasp/tool approach','wire emergence and service movement','crimp tooling/setup/pull acceptance','finished PCB hole and actual pin tolerances','root full assembly fit'],wire_contract=dict(part="Alpha5854",awg=24,od_range_mm=[1.016,1.2446],receiving_diameter_mm=1.3,min_bend_radius_mm=13,crimp_insulation_range_mm=[.9,1.6],crimp_conductor_height_mm=[.83,.89],strip_length_mm=[3,4],hand_tool="Z20-320",qualification="manufacturer dimensions compatible; setup and pull test open"),fabrication_released=False,bom_changed=False,pcb_changed=False)
(HERE/'mate-contract.json').write_text(json.dumps(out,indent=2)+'\n')
sc=['// Conditional package receiving boxes, not exact manufactured solids.','module sr_box(b){translate([b[0],b[1],b[2]])cube([b[3]-b[0],b[4]-b[1],b[5]-b[2]]);}']
for r in rows:sc.append('module sr_'+r['ref']+'(){'+''.join('sr_box('+json.dumps(b)+');' for b in r['female_boxes']+r['male_wafer_receiving_boxes']+r['tail_receiving_boxes'])+'}')
sc.append('module single_row_mates(){'+''.join('sr_'+r['ref']+'();' for r in rows)+'}')
sc.append('module single_row_withdrawal(){'+''.join('sr_box('+json.dumps(b)+');' for r in rows for b in r['withdrawal_boxes'])+'}')
obs=[[xy[0],xy[1],z[0],xy[2],xy[3],z[1]] for ref,xy,z in cap['component_envelopes']+cap['tail_envelopes'] if ref not in refs]
obs += [[r['xy'][0],r['xy'][1],r['z'][0],r['xy'][2],r['xy'][3],r['z'][1]] for r in cap['context']]
sc.append('module other_captured_allocations(){'+''.join('sr_box('+json.dumps(b)+');' for b in obs)+'}')
(HERE/'mates.scad').write_text('\n'.join(sc)+'\n');print('11 candidate pairs;34 populated contacts/35positions; originalPCB/BOM untouched')
