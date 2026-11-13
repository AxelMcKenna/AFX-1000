"""Retain TC02 C3 geometry while separating actual mount interfaces from obsolete box."""
import json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent; REPO=ROOT.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
 source=REPO/'hardware/cad/a12/trill_mount_candidate/report.json'
 r=json.loads(source.read_text()); tc=REPO/'hardware/cad/a12/trill_front_bay/generated/analysis.json'; t=json.loads(tc.read_text())
 assert t['origin_mm']==[82,158,20] and r['actual_width_depth_mm']==[53.848,21.844]
 centres=t['mount_centres_mm']; bodies=[]
 for row in r['component_terminal_reserves']:
  b=row['box_mm'].copy(); b[1]+=34.5;b[2]-=10.6;bodies.append(dict(id=row['id'],box_mm=b))
 tails=[dict(id=p['id'],xy_mm=[p['xy_mm'][0],p['xy_mm'][1]+34.5]) for p in r['tail_reserves']]
 assert len(bodies)==13 and len(tails)==36
 c=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [source,tc,REPO/'hardware/cad/two_board_print_01/housing.scad',REPO/'hardware/cad/two_board_print_01/captured.scad',Path(__file__)]},origin_mm=t['origin_mm'],size_mm=[53.848,21.844,1.6],mount_centres_mm=centres,components=bodies,tails=tails,communication_pads=[dict(p,world_xy_mm=[p['world_xy_mm'][0],p['world_xy_mm'][1]+34.5]) for p in r['communication_pads']],mount=dict(current_through_hole_mm=2.4,current_nut_pocket_AF_mm=4.2,current_pocket_z_mm=[-.1,1.8],current_head_envelope_mm=[4.5,2.5],current_head_z_mm=[21.6,24.1],obsolete_TC02_shank_mm=2.5,obsolete_TC02_blind_pilot_mm=2.05,fastener_selected=False,reason='M2.5 cannot pass current nominal2.4 hole. M2-class through fastener is only a candidate; exact head, nut AF/height, length, engagement, retention and insulation require drawing/qualification.'),limits=r['model_limits'],physical_qualified=False,fabrication_released=False)
 (ROOT/'contract.json').write_text(json.dumps(c,indent=2)+'\n')
 s='// Source-derived nominal C3 board and explicit project allocations; no mounting hardware.\n'
 s+='r25_mounts='+json.dumps(centres)+';\nr25_bodies='+json.dumps([p['box_mm'] for p in bodies])+';\nr25_tails='+json.dumps([p['xy_mm'] for p in tails])+';\n'
 s+='''module touch_c3_board(){difference(){translate([82,158,20])cube([53.848,21.844,1.6]);for(p=r25_mounts)translate([p[0],p[1],19.99])cylinder(d=3.2,h=1.62,$fn=128);}}
module touch_c3_components(){for(b=r25_bodies)translate([b[0],b[1],b[2]])cube([b[3],b[4],b[5]]);}
module touch_c3_tails(){for(p=r25_tails)translate([p[0],p[1],17])cylinder(r=.8,h=3,$fn=64);}
module touch_c3_receiving(){touch_c3_board();touch_c3_components();touch_c3_tails();}
'''
 (ROOT/'module.scad').write_text(s)
if __name__=='__main__':build()
