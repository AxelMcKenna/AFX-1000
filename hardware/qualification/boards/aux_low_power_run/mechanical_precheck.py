"""New receiver/bypass screen against captured CP01 native meshes; no CAD launch.

This is a placement precheck against the named historical mesh snapshot, not a
new full assembly receiving run or a physical dimensional acceptance.
"""

import json
from pathlib import Path

import numpy as np

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.electronics.rail_disconnect.revision28.u28_band_mesh_screen import contains, hits, triangles

from .route_e28 import WORK, sha

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]


def run():
    out=ROOT/"generated/mechanical-precheck.json"
    assert not out.exists()
    pcb=WORK/"generated/eight-layer-stage/rail_disconnect.kicad_pcb"
    tree=read_sexpr(pcb.read_text())
    datum=[8,108.5,5.0]
    bounds={}
    for fp in children(tree,"footprint"):
        ref=next(p[2] for p in children(fp,"property") if p[1]=="Reference")
        if ref not in ("U43","C86"):
            continue
        assert first(fp,"layer")[1]=="B.Cu"
        b=courtyard(fp,"B.CrtYd")
        projection=1.2 if ref=="U43" else 1.05
        bounds[ref]=[b[0]-100+datum[0],b[1]-100+datum[1],datum[2]-projection,
                     b[2]-100+datum[0],b[3]-100+datum[1],datum[2]]
    cp=REPO/"hardware/cad/a12/thermal/enlarged_base_pot/generated"
    meshes=[cp/(name+".stl") for name in ("eb_carrier_geometry","eb_attachment_geometry","eb_metal_geometry",
        "eb_interface_geometry","eb_retained_power_review","ei_controls_geometry","ei_all_ports_geometry",
        "ei_trill_frontbay_geometry","ps_body_geometry","ps_stack","cp_pot_hardware_review")]
    hashes={str(p):sha(p) for p in [pcb,Path(__file__),ROOT/"sources/sn74aup1g17.pdf",*meshes]}
    expanded={ref:[b[0]-.25,b[1]-.25,b[2]-.45,b[3]+.25,b[4]+.25,b[5]+.45] for ref,b in bounds.items()}
    results={}
    failures=[]
    for path in meshes:
        ts=triangles(path)
        rows={}
        for ref,b in expanded.items():
            count=hits(ts,b)
            inside=contains(ts,(np.array(b[:3])+np.array(b[3:]))/2)
            rows[ref]=dict(surface_intersections=count,center_inside=inside)
            if count or inside:
                failures.append(dict(mesh=path.name,ref=ref,**rows[ref]))
        results[path.name]=rows
    control=contains(triangles(meshes[0]),[133,156,1])
    assert control
    assert all(sha(Path(p))==h for p,h in hashes.items())
    out.write_text(json.dumps(dict(source_sha256=hashes,board_datum_mm=datum,nominal_body_courtyard_boxes_mm=bounds,
        expanded_boxes_mm=expanded,XY_guard_mm=.25,Z_guard_mm=.45,
        U43_primary_DCK_height_max_mm=1.1,U43_project_seating_allowance_mm=.1,
        C86_body_plus_seat_receiving_mm=1.05,positive_floor_control_detected=control,
        checks=results,observed_intersections=failures,captured_mesh_screen_clear=not failures,
        historical_meshes_do_not_establish_current_full_assembly_or_manufacturer_acceptance=True,
        native_CAD_executables_launched=0,physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("New receiver captured-mesh screen clear:",not failures,"findings",failures,flush=True)


if __name__=="__main__":
    run()
