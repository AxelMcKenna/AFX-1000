"""First manufacturer-radius connector escape study; not a complete harness."""
from pathlib import Path
import json,math,hashlib
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
REPO=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
g=json.loads((BASE/'r12_ground/ground-routes.json').read_text())
contract={'wire':'Alpha5853 26AWG7/34 PTFE','manufacturer_url':'https://www.alphawire.com/products/wire/hook-up-wire/premium/5853','local_evidence':'hardware/cad/two_board_installation_06/r11_distribution/reference/alpha5853.pdf','evidence_location':'Properties / Physical & Mechanical Properties / Bend Radius','supplier_radius_diameter_multiplier':10,'supplier_max_wire_OD_mm':1.0922,'supplier_radius_at_max_OD_mm':10.922,'selected_centerline_radius_mm':12,'modeled_wire_radius_mm':.6,'minimum_modeled_inside_radius_mm':11.4,'interpretation':'12mm centerline conservatively exceeds 10x maximum OD even if supplier bend radius is interpreted at wire inside surface. Static formed harness only; repeated flex/lid service remains unqualified.','scope':'Four selected dual-row connector root escape turns only. D_J2003 exact mate remains unselected; no complete endpoint route is claimed.','fabrication_released':False}
roots={r:p for r,p in g['endpoints_mm'].items() if r.startswith(('D_J2001:','D_J2002:'))}
lines=['// Manufacturer-radius vertical-to-horizontal exit study.','$fn=24;','exit_angle=0;', 'module formed_segment(a,b){hull(){translate(a)sphere(r=.6);translate(b)sphere(r=.6);}}']
for i,(root,p) in enumerate(roots.items()):
    name=root.replace(':','_');lines.append('module panel_ground_exit_'+name+'(az=0){')
    for n in range(30):
        def pt(k):
            t=math.radians(k*3);return [12*(1-math.cos(t)),12*math.sin(t)]
        a,b=pt(n),pt(n+1)
        lines.append('formed_segment(['+f'{p[0]}+{a[0]}*cos(az),{p[1]}+{a[0]}*sin(az),{p[2]+a[1]}'+'],['+f'{p[0]}+{b[0]}*cos(az),{p[1]}+{b[0]}*sin(az),{p[2]+b[1]}'+']);')
    lines.append('}')
lines.append('module panel_ground_formed_exits(az=0){'+''.join('panel_ground_exit_'+r.replace(':','_')+'(az);' for r in roots)+'}')
lines.append('module panel_ground_selected_exits(){panel_ground_exit_D_J2002_15(250);panel_ground_exit_D_J2002_16(270);}')
contract['selected_exit_azimuth_degrees']={'D_J2002:15':250,'D_J2002:16':270}
contract['proposed_feed_membership']={'D_J2002:15':'19 non-scene buttons','D_J2002:16':'10 scene buttons plus settings/release commons'}
contract['proposed_unused_ground_pins']=['D_J2001:15','D_J2001:16','D_J2003:1']
contract['proposed_membership_implementation']='Exit geometry only; chain adjacency remains under development. Do not substitute an electrical netlist yet.'
(HERE/'exits.scad').write_text('\n'.join(lines)+'\n')
contract['root_start_mm']=roots
contract['arc_degrees']=90
contract['sampling_degrees']=3
contract['maximum_chord_sagitta_mm']=12*(1-math.cos(math.radians(1.5)))
contract['source_sha256']={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),BASE/'r12_ground/ground-routes.json',BASE/'r11_distribution/reference/alpha5853.pdf']}
(HERE/'exit-contract.json').write_text(json.dumps(contract,indent=2)+'\n')
print('4 radius12 connector escape arcs generated; chord sagitta',contract['maximum_chord_sagitta_mm'])
