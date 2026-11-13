"""Additive source channels only; fixed current source datums and R12."""
import hashlib,json,math
from pathlib import Path
from hardware.cad.two_board_installation_06.r15_right_ground.curves import Wire
H=Path(__file__).resolve().parent;R=H.parents[3];B=H.parent
inventory=json.loads((B/'r19_panel_inventory/inventory.json').read_text());rows=[];lines=[]
angle=129.6;T=[math.cos(math.radians(angle)),math.sin(math.radians(angle)),0]
for name,sid in [('tap','S05'),('auto','S06')]:
 e=next(e for e in inventory['wires'] if e['target']=='button_'+name+':1');w=Wire(e['source_xy_mm']+[27.04]);w.arc([0,0,1],T,12,90)
 rows.append(dict(id=sid,source=e['source'],target=e['target'],net=e['net'],points_mm=[p.tolist() for p in w.points],primitives=w.primitives))
 lines.append('module source_'+sid+'(r=.6){')
 for a,b in zip(w.points,w.points[1:]):lines.append('hull(){translate('+json.dumps(a.tolist())+')rotate([11,7,3])sphere(r=r,$fn=24);translate('+json.dumps(b.tolist())+')rotate([11,7,3])sphere(r=r,$fn=24);}')
 lines.append('}')
lines.append('module source_pair(r=.6){source_S05(r);source_S06(r);}')
lines.append('module scene0_source_channel(){source_pair(.9);}')
(H/'exits.scad').write_text('\n'.join(lines)+'\n')
report={'status':'UNVERIFIED_PLASTIC_ONLY_RELIEF','source_azimuth_degrees':angle,'receiving_radius_mm':.6,'cut_radius_mm':.9,'cut_inscribed_margin_after_chord_error_mm':.9*math.cos(math.pi/24)**2-12*(1-math.cos(math.radians(1.5)))-.6,'edges':rows,'completed_panel_edges':0,'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),B/'r19_panel_inventory/inventory.json',B/'r35_input_exit_audit/bound.json',B/'r15_right_ground/curves.py']}}
assert report['cut_inscribed_margin_after_chord_error_mm']>=.25
(H/'exits.json').write_text(json.dumps(report,indent=2)+'\n');print(report['cut_inscribed_margin_after_chord_error_mm'])
