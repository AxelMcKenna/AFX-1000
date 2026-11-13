"""Exact constant-length source-half deformation in a restricted planar family.

The direct solder exit and its first two arcs stay fixed. The downstream west
straight, quarter-circle and north straight change together. No clearance or
outgoing-half deformation is inferred from this analytic construction.
"""
import hashlib
import json
import math
from pathlib import Path
H=Path(__file__).resolve().parent
R=H.parents[3]
c=json.loads((H.parent/'r29_touch_inline/route-draft.json').read_text())
k=2-math.pi/2
rows=[]
for e in c['edges']:
    p=e['segments'][0]['primitives']
    a, arc, b=p[-3:]
    assert a['kind']=='line' and arc['kind']=='arc' and b['kind']=='line'
    assert arc['angle_degrees']==90 and arc['radius_mm']==13
    assert arc['tangent']==[-1.,0.,0.] and arc['normal']==[0.,1.,0.]
    anchor=a['start'];terminal=b['end']
    dx=anchor[0]-terminal[0];dy=terminal[1]-anchor[1]
    assert dx>=13 and dy>=13
    old_length=dx+dy-k*13
    # With endpoint shifted +Y*t and circle radius r:
    # L(t,r)=dx+dy+t-(2-pi/2)*r. Therefore r=13+t/k.
    # Both straights must remain nonnegative: r<=dx; r<=dy+t.
    maximum=min(k*(dx-13),(dy-13)/(1/k-1))
    samples=[]
    for i in range(101):
        t=maximum*i/100;r=13+t/k
        west=dx-r;north=dy+t-r
        assert west>=-1e-10 and north>=-1e-10 and r>=13
        assert abs(west+math.pi*r/2+north-old_length)<1e-10
        # Tangents remain west then north at each circular join.
        samples.append({'travel_mm':t,'radius_mm':r,'west_straight_mm':max(0,west),'north_straight_mm':max(0,north)})
    assert 13+24/k>min(dx,dy+24)
    rows.append({'id':e['id'],'anchor_mm':anchor,'terminal_mm':terminal,
                 'fixed_downstream_length_mm':old_length,
                 'max_positive_y_travel_in_this_family_mm':maximum,
                 'last_pose':samples[-1],
                 'positive_24mm_motion_in_this_family':False})
r={'status':'ANALYTIC_SOURCE_ONLY_FAMILY_NO_CLEARANCE_PASS',
   'formula':'radius(t)=13+t/(2-pi/2); west=dx-radius; north=dy+t-radius',
   'constant_length_and_radius_verified':True,
   'fixed_source_exit_and_terminal_tangent_preserved':True,
   'simultaneous_four_wire_travel_limit_mm':min(x['max_positive_y_travel_in_this_family_mm'] for x in rows),
   'sampled_identity_checks_per_wire':101,
   'rows':rows,'collision_verified':False,'wire_separation_verified':False,
   'outgoing_halves_deformed':False,'three_dimensional_lift_deformed':False,
   'not_global_infeasibility':'24 mm fails this single-quarter-circle family only; a different 3D deformation or added installed slack may work.',
   'completed_touch_wires':0,
   'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),H.parent/'r29_touch_inline/route-draft.json']}}
(H/'bend-family.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'source_family_limit_mm':r['simultaneous_four_wire_travel_limit_mm'],'limits':[x['max_positive_y_travel_in_this_family_mm'] for x in rows]}))
