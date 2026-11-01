"""Bind a closed E28 layout to a conservative captured-assembly Boolean case.

The envelope includes0.15mm XY/Z placement allowance,1.8mm maximum PCB thickness
and2mm above-board component allowance. Old PCB material at the deliberate join
is excluded. This is a captured-model receiving screen, not physical acceptance.
"""

import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, read_sexpr, sexpr

from .route_e28 import REPO, WORK, sha


def run():
    source=WORK/"generated/final-leaf-joins/rail_disconnect.kicad_pcb"
    native=WORK/"generated/native-closed-control-layout"
    parent=WORK/"generated/control-wing-return-smoothed/rail_disconnect.kicad_pcb"
    review=json.loads((native/"review.json").read_text())
    drc=json.loads((native/"drc.json").read_text())
    assert review["uncapped_missing_connections"]==0
    assert review["source_sha256"][str(source)]==sha(source)
    assert not any(r["severity"]=="error" for r in drc["violations"])
    assert not drc["schematic_parity"] and review["status"]["counts"]["erc"]==0
    assert review["status"]["all_native_rule_checks_enabled"]
    # All post-wing work changed copper only: the mechanical placement remains
    # exactly the previously screened U38/C81 layout.
    assert [sexpr(f) for f in children(read_sexpr(source.read_text()),"footprint")]==[
        sexpr(f) for f in children(read_sexpr(parent.read_text()),"footprint")]
    cp=REPO/"hardware/cad/a12/thermal/enlarged_base_pot/generated"
    meshes=[cp/(name+".stl") for name in ("eb_carrier_geometry","eb_attachment_geometry","eb_metal_geometry",
        "eb_interface_geometry","eb_retained_power_review","ei_controls_geometry","ei_all_ports_geometry",
        "ei_trill_frontbay_geometry","ps_body_geometry","ps_stack","cp_pot_hardware_review")]
    model_path=REPO/"hardware/cad/a12/enclosure_growth/nf265_fpc91/generated/model.json"
    model=json.loads(model_path.read_text())
    out=WORK/"generated/closed-layout-receiving"
    out.mkdir(exist_ok=False)
    scene=out/"receiving.scad"
    lines=['mode="clearance";','module wing_envelope(){',
        ' translate([12.85,163.00001,4.85]) cube([70.3,5.64999,4.10]);','}',
        'module retained(){ union(){']
    lines += [' import('+json.dumps(str(p))+');' for p in meshes]
    for group in ("boxes","mates","tails"):
        for row in model[group]:
            _,x,y,z,dx,dy,dz=row
            lines.append(' translate('+json.dumps([x-.45,y-.45,z])+') cube('+json.dumps([dx+.9,dy+.9,dz])+');')
    for board in model["boards"]:
        x,y,z=board["origin"]
        width,height=board["size"]
        lines.append(' translate('+json.dumps([x-.45,y-.9,z])+') cube('+json.dumps([width+.9,1.8,height])+');')
    lines += ['}}','if(mode=="positive") intersection(){wing_envelope();translate([20,165,5.1])cube([.5,.5,.5]);}',
              'else intersection(){wing_envelope();retained();}']
    scene.write_text('\n'.join(lines)+'\n')
    sources=[source,parent,native/"review.json",native/"drc.json",model_path,Path(__file__),scene,*meshes]
    (out/"manifest.json").write_text(json.dumps(dict(entry=str(scene),input_sha256={str(p):sha(p) for p in sources},
        expected_positive_volume_mm3=.125,wing_world_bounds_mm=[12.85,163.00001,4.85,83.15,168.65,8.95],
        XY_and_Z_placement_allowance_mm=.15,max_board_thickness_mm=1.8,upper_component_allowance_mm=2.,
        front_connector_XY_allowance_mm=.45,minimum_front_connector_gap_after_allowances_mm=.9,
        deliberate_old_PCB_join_excluded=True,captured_CP01_meshes=11,current_NF_FPC_receiving_boxes=True,
        native_Mac_apps_launched=0,full_updated_whole_unit_receiving=False,
        physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("Staged conservative captured-assembly clearance case and positive witness")


if __name__=="__main__":
    run()
