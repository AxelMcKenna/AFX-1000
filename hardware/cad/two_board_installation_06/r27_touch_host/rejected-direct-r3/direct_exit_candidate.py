"""Bounded four-pad direct-wire emergence study; no complete touch harness."""
import json,math,hashlib
from pathlib import Path
import numpy as np
from hardware.cad.two_board_installation_06.r15_right_ground.curves import Wire
H=Path(__file__).resolve().parent;R=H.parents[3]
rows=[]
for i,(x,angle) in enumerate(zip([230,232.54,235.08,237.62],[204,188,172,156]),1):
 w=Wire([x,59,9.6]);w.line([x,59,12.5]);az=math.radians(angle);T=np.array([math.cos(az),math.sin(az),0]);w.arc([0,0,1],T,13,90)
 # Rotate in XY to four separated westbound lanes with tangent continuity.
 N=np.array([T[1],-T[0],0]) if angle>180 else np.array([-T[1],T[0],0]);w.arc(T,N,13,abs(180-angle));w.line([175,w.p[1],w.p[2]])
 rows.append(dict(id='TH'+str(i),source='D_J1009:'+str(i),points_mm=[p.tolist() for p in w.points],primitives=w.primitives))
files=[Path(__file__),R/'hardware/cad/two_board_print_01/capture.json',H.parent/'r26_touch_mount/contract.json',H.parent/'r15_right_ground/curves.py']
c=dict(edges=rows,wire_radius_mm=.65,minimum_bend_radius_mm=13,wire='Alpha5854 24AWG',source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},termination='Proposed direct-solder only; receiving free-wire startZ9.6, prepared conductor/fillet/strain acceptance unqualified',completed_touch_wires=0,completed_panel_edges=0,physical_qualified=False)
(H/'direct-exits.json').write_text(json.dumps(c,indent=2)+'\n')
s=[]
for row in rows:
 s.append('module touch_exit_'+row['id']+'(){')
 for a,b in zip(row['points_mm'],row['points_mm'][1:]):s.append('hull(){translate('+json.dumps(a)+')sphere(r=.65,$fn=32);translate('+json.dumps(b)+')sphere(r=.65,$fn=32);}')
 s.append('}')
s.append('module touch_direct_exits(){'+''.join('touch_exit_'+r['id']+'();' for r in rows)+'}')
(H/'direct-exits.scad').write_text('\n'.join(s)+'\n')
