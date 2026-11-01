"""Exact port/native pin/drill contract and named primary-body supplement."""

import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr

from .capture import ROOT, sha, write


def build():
    out = ROOT / "supplement"
    if out.exists():
        raise RuntimeError("New receiving contract output required")
    base = ROOT / "inputs/hardware/qualification/boards"
    pcb = base / "startup_negative_circuit/physical_layout/negative_startup_physical.kicad_pcb"
    ports = base / "nf_connector_receiving265/ports-v2.json"
    tree = read_sexpr(pcb.read_text())
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    checks = []
    for port in json.loads(ports.read_text())["ports"]:
        fp = fps[port["ref"]]
        actual = {}
        raw_nets = {}
        for p in children(fp, "pad"):
            net = first(p, "net")[-1] if children(p, "net") else None
            raw_nets[str(p[1])] = net
            actual[str(p[1])] = None if net is None or net.startswith("unconnected-(") else net.lstrip("/")
        assert actual == port["physical_pads"], (port["ref"], actual, port["physical_pads"])
        assert list(map(float, first(fp, "at")[1:3])) == port["anchor_mm"]
        drills = {str(p[1]): float(first(p, "drill")[1]) for p in children(fp, "pad")}
        if port["ref"] in {"J2", "J4"}:
            assert set(drills.values()) == {2.2}
        checks.append(
            dict(
                ref=port["ref"],
                physical_pads=actual,
                raw_native_nets=raw_nets,
                drills_mm=drills,
                actual_native_layer=first(fp, "layer")[1],
                anchor_mm=port["anchor_mm"],
            )
        )
    for ref, u in [("H101", 61), ("H102", 90)]:
        fp = fps[ref]
        assert list(map(float, first(fp, "at")[1:3])) == [u, 21]
        pads = children(fp, "pad")
        assert len(pads) == 1 and pads[0][2] == "np_thru_hole" and float(first(pads[0], "drill")[1]) == 2.6
    out.mkdir()
    script = """// Named supplements; no replacement of the initial failed receiving study.
include <../tail_shape/checks.scad>
su_case="none";
// Exact KEMET max L1.75/W.95/T.95, plus declared .1 seat; native B90 pose.
module su_new_cap_bodies(m=0){for(x=[25.6,27.4])translate([x-.475-m,182.26-m,17.625-m])cube([.95+2*m,1.05+2*m,1.75+2*m]);}
module su_C203_2_tail(m=0){for(b=fr_tails)if(b[0]=="FPC91_C203.2")fr_boxes([b],"all",m);}
module su_actual_minimum_PCB(force_d=2.1){for(b=fr_boards)if(b[0]=="NF265")translate(b[1])rotate([90,0,0])difference(){translate([0,0,-1.76])cube([149,39,1.76]);for(h=b[3])fr_drill([h[0],h[1],(h[5]=="J2"||h[5]=="J4")?force_d:((h[5]=="H101"||h[5]=="H102")?2.5:h[2]),(h[5]=="J2"||h[5]=="J4")?force_d:((h[5]=="H101"||h[5]=="H102")?2.5:h[3]),h[4]]);}}
if(su_case=="actual_C401_C402_primary_body_geometry")intersection(){su_new_cap_bodies();su_new_cap_bodies(.01);}
if(su_case=="actual_C401_C402_tail_margin_collision")intersection(){su_new_cap_bodies();su_C203_2_tail(.45);}
if(su_case=="actual_C401_body_positive_control")intersection(){su_new_cap_bodies();translate([25.5,182.5,18.4])cube([.2,.2,.2]);}
if(su_case=="actual_force_minimum_bores_collision")intersection(){su_actual_minimum_PCB();nc265_world()nc265_force_gauges();}
if(su_case=="actual_mount_minimum_bores_collision")intersection(){su_actual_minimum_PCB();nc265_world()nc265_mount_gauges();}
if(su_case=="actual_old_force_bore_failure_witness")intersection(){su_actual_minimum_PCB(1);nc265_world()nc265_force_gauges();}
"""
    (out / "checks.scad").write_text(script)
    write(
        out / "contract.json",
        dict(
            port_native_checks=checks,
            actual_mechanical_NPTH_nominal_mm=2.6,
            receiving_finished_mount_min_mm=2.5,
            actual_force_nominal_drill_mm=2.2,
            receiving_finished_force_min_mm=2.1,
            strip_bundle_max_mm=1.4,
            relative_centering_mm=0.3,
            geometry_reserve_mm=0.005,
            force_radial_gauge_margin_mm=0.045,
            source_sha256={str(p): sha(p) for p in [Path(__file__), pcb, ports]},
            C401_C402_primary_body_max_mm=[1.75, 0.95, 0.95],
            cap_seat_requirement_mm=0.1,
            new_cap_primary_source="captured KEMET X7R Table1A CJ and Table2A; NC265 input primary PDF",
            tail_margin_for_primary_body_study_mm=0.45,
            port_and_drill_contract_exact=True,
            global_harness_qualified=False,
            manufacturing_accepted=False,
        ),
    )
    print(
        json.dumps(
            dict(
                ports=len(checks),
                physical_pads=sum(len(p["physical_pads"]) for p in checks),
                mechanical_mounts=2,
            )
        )
    )


if __name__ == "__main__":
    build()
