"""Additive bows free reserved signal contacts without changing ground adjacency."""
from pathlib import Path
import json,math,hashlib,numpy as np
from hardware.cad.two_board_installation_06.r15_right_ground.curves import Wire
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;REPO=HERE.parents[3]
source=BASE/'r15_right_ground/right-routes.json';original=json.loads(source.read_text());ids=['R02','R06','R08','R10'];edges=[]
for e in original['edges']:
 if e['id'] not in ids:continue
 a,b=np.array(e['points_mm'][0]),np.array(e['points_mm'][-1]);delta=b-a;L=np.linalg.norm(delta);T=delta/L;N=np.array([0,0,-1]);assert abs(T@N)<1e-8
 R=18;half=math.asin(L/(2*R));w=Wire(a);w.arc(math.cos(half)*T+math.sin(half)*N,math.sin(half)*T-math.cos(half)*N,R,math.degrees(2*half));assert np.linalg.norm(w.p-b)<1e-7
 edges.append(dict(e,points_mm=[p.tolist() for p in w.points],primitives=w.primitives))
sources=[Path(__file__),source,BASE/'r15_right_ground/curves.py',BASE/'r12_ground/ground-routes.json'];out=dict(source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},edges=edges,replaces_wires=ids,adjacency_unchanged=True,wire_radius_mm=.6,minimum_required_radius_mm=12,fabrication_released=False)
(HERE/'bows.json').write_text(json.dumps(out,indent=2)+'\n');lines=['use <../r15_right_ground/right.scad>']
for e in edges:
 lines.append('module bowed_'+e['id']+'(){')
 for a,b in zip(e['points_mm'],e['points_mm'][1:]):lines.append('hull(){translate('+json.dumps(a)+')sphere(r=.6,$fn=32);translate('+json.dumps(b)+')sphere(r=.6,$fn=32);}')
 lines.append('}')
lines.append('module corrected_ground_bows(){'+''.join('bowed_'+id+'();' for id in ids)+'}')
lines.append('module corrected_ground_scene_links(){'+''.join(('bowed_' if e['id'] in ids else 'panel_ground_')+e['id']+'();' for e in original['edges'][1:10])+'}')
lines.append('module unaffected_right_ground(){'+''.join('panel_ground_'+e['id']+'();' for e in original['edges'] if e['id'] not in ids)+'}')
(HERE/'bows.scad').write_text('\n'.join(lines)+'\n')

datums=json.loads((BASE/'r12_ground/ground-routes.json').read_text())['endpoints_mm']
terminals={k:v for k,v in datums.items() if k.startswith('button_') and k.endswith(':1')};assert len(terminals)==29
(HERE/'terminals.scad').write_text('module all_signal_terminal_receiving(){'+''.join('translate('+json.dumps(v)+')sphere(r=.6,$fn=32);' for v in terminals.values())+'}\n')
