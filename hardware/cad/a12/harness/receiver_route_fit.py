"""Whole selected J4-to-J13 pair, including cuts, joints and native PCB bores.

Checks the geometric route only. Forming/strain relief, cut slack, solder and
fabrication processes, current/voltage/return behavior and physical assembly
remain separate. The source E28 candidate still has 45 electrical opens.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.generate import REPO, sha
from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.cad.a12.repaired import outline, packet
from hardware.cad.a12.thermal.verify import binary_stl
from hardware.electronics.common.sexpr import read_sexpr

ROOT = Path(__file__).resolve().parent
SEARCH = ROOT / "ear_connector_search"
OUT = ROOT / "generated/receiver-full-route"
SUPPORT = ROOT / "generated/receiver-ear-support"


def bind_report(path, hashes):
    data = json.loads(path.read_text())
    hashes[str(path.relative_to(REPO))] = sha(path)
    for key in ["source_sha256", "evidence_inputs_sha256", "evidence_sha256"]:
        hashes.update(data.get(key, {}))
    return data


def generate():
    selected = SEARCH / "generated/selected-paths.json"
    route = json.loads(selected.read_text())
    hashes = {str(selected.relative_to(REPO)): sha(selected)}
    for key, base in [("source_sha256", SEARCH), ("captured_input_sha256", SEARCH / "inputs")]:
        for name, digest in route[key].items():
            p = base / name
            assert sha(p) == digest, ("Stale route input", name)
            hashes[str(p.relative_to(REPO))] = digest
    dense = SEARCH / "generated/dense-points.json"
    assert sha(dense) == route["dense_points_sha256"]
    hashes[str(dense.relative_to(REPO))] = sha(dense)
    support = bind_report(SUPPORT / "verification.json", hashes)
    assert support["local_post_and_head_fit_clear"] and not support["changed_inputs"]
    source = bind_report(ROOT / "generated/selected-exit-selected-refined-pair/verification.json", hashes)
    assert source["local_formed_escape_clear"] and not source["changed_inputs"]
    assert route["wire_insulation_OD_max_mm"] == 1.7526
    assert route["independent_position_allocation_each_wire_mm"] == 0.65
    assert route["separate_required_clearance_mm"] == 0.25 and route["separate_geometry_reserve_mm"] == 0.005
    required = 9.6393
    assert math.isclose(route["minimum_required_true_centerline_radius_mm"], required, abs_tol=1e-9)
    assert route["maximum_native_chord_error_bound_mm"] < 0.001
    assert route["dense_pair_clearance_lower_estimate_mm"] > 0
    native, other, fresh = snapshot()
    hashes.update(fresh)
    physical = packet(
        {
            "P03": REPO / "hardware/electronics/power_distribution/p03/candidates/aux-u10-combined",
            "E28": REPO / "hardware/electronics/rail_disconnect/revision28/generated/r58-joint-work",
        }
    )
    native.update(physical)
    hashes.update(physical["source_sha256"])
    base_path = ROOT / "generated/receiver-awg18/analysis.json"
    base = json.loads(base_path.read_text())
    hashes.update(base["source_sha256"])
    hashes[str(base_path.relative_to(REPO))] = sha(base_path)
    ear_path = ROOT / "generated/receiver-ear/analysis.json"
    ear = json.loads(ear_path.read_text())
    hashes.update(ear["source_sha256"])
    hashes[str(ear_path.relative_to(REPO))] = sha(ear_path)
    own_joints = [b for b in native["boxes"] if b[0].startswith("E28_J4")]
    assert own_joints
    own_joints += json.loads(
        (ROOT / "generated/receiver-ear/checks.scad").read_text().split("joints=", 1)[1].split(";", 1)[0]
    )
    boxes = [b for b in native["boxes"] if not b[0].startswith("E28_J4")]
    boxes += native["switch_diagnostic_boxes"] + base["current_E19_component_packet"]["bodies"]
    boxes += [b for b in other["envelopes"] if not b[0].startswith(("e19_", "disconnect_"))] + other[
        "port_envelopes"
    ]
    source_board = next(b for b in native["boards"] if b["id"] == "E28")
    assert source_board["datum"] == [8, 108.5, 5.0]
    assert source_board["thickness_range_allocation_mm"] == [1.5, 1.7]
    pcb = ROOT / "proposals/processor-awg18-ear-supported/processor_carrier.kicad_pcb"
    assert sha(pcb) == json.loads((SUPPORT / "analysis.json").read_text())["candidate_pcb_sha256"]
    receiver_outline = outline(read_sexpr(pcb.read_text()))
    hashes[str(pcb.relative_to(REPO))] = sha(pcb)
    rows = []
    for r in route["routes"]:
        pin = str(r["pin"])
        assert pin in ["1", "2"] and r["net"] == ("5V_DIG" if pin == "1" else "AGND")
        start, end = r["source_face_mm"], r["destination_stub"]["finish"]
        assert start == [161, 120.5 if pin == "1" else 126.5, 6.62]
        assert end == [188, 100 if pin == "1" else 104, 8.1]
        points = r["native_points_mm"]
        assert math.dist(points[0], start) < 1e-9 and math.dist(points[-1], end) < 1e-9
        assert r["whole_continuous_radius_lower_mm"] >= required
        assert r["destination_stub"]["length_mm"] == 7
        assert r["source_bare_cut_z_mm"] == 9.72 and r["destination_stub"]["bare_cut_z_mm"] == 11.2
        bend = [*start[:2], start[2] + r["source_prefix_profile"]["initial_straight_mm"]]
        index = min(range(len(points)), key=lambda i: math.dist(points[i], bend))
        assert math.dist(points[index], bend) < 1e-9, "Missing exact initial tangent boundary"
        stub_start = r["destination_stub"]["start"]
        last = min(range(index, len(points)), key=lambda i: math.dist(points[i], stub_start))
        assert math.dist(points[last], stub_start) < 1e-9
        assert all(math.dist(p[:2], start[:2]) < 1e-9 for p in points[: index + 1])
        assert all(math.dist(p[:2], end[:2]) < 1e-9 for p in points[last:])
        middle = points[index : last + 1]
        chord = r["sample_contract"]["native"]["whole_chord_error_bound_mm"]
        # Every interpolated curve point is within the declared chord bound.
        # Away from the two straight endpoint stubs, the entire tube is above
        # both own PCBs; only the bore checks may therefore replace those PCBs
        # in the general obstacle union.
        lowest = (
            min(p[2] for p in middle)
            - chord
            - (1.7526 / 2 + 0.65 + 0.25 + 0.005) / math.cos(math.pi / 64) ** 2
        )
        assert lowest > 8.46, "Own PCB omitted without full central height separation"
        assert r["wire_length_upper_mm_including_prefix_stub_boardtails"] < 200
        rows.append(
            dict(
                pin=pin,
                net=r["net"],
                start=start,
                end=end,
                bend=bend,
                source_cut=[*start[:2], 9.72],
                receiver_cut=[*end[:2], 11.2],
                middle=middle,
                stub_start=stub_start,
                source_tail=[*start[:2], 3.5],
                receiver_tail=[*end[:2], 5],
                central_external_tube_min_z_lower_mm=lowest,
                radius_lower_mm=r["whole_continuous_radius_lower_mm"],
                length_upper_mm=r["wire_length_upper_mm_including_prefix_stub_boardtails"],
            )
        )
    assert [r["pin"] for r in rows] == ["1", "2"]
    for p in [Path(__file__), SUPPORT / "checks.scad", ROOT / "generated/receiver-ear/checks.scad"]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    assert all(sha(REPO / n) == h for n, h in hashes.items()), "Stale source before full route checks"
    OUT.mkdir(parents=True, exist_ok=True)
    scad = "include <" + str(SUPPORT / "checks.scad") + ">\n"
    for key, value in dict(
        pf_rows=rows,
        pf_boxes=boxes,
        pf_cylinders=native["cylinders"],
        pf_joints=own_joints,
        pf_source_outline=source_board["outline_relative_mm"],
        pf_receiver_outline=receiver_outline,
    ).items():
        scad += key + "=" + json.dumps(value) + ";\n" if key != "pf_rows" else ""
    # OpenSCAD has no Python-style dictionary indexing.
    for key in [
        "start",
        "end",
        "bend",
        "source_cut",
        "receiver_cut",
        "middle",
        "stub_start",
        "source_tail",
        "receiver_tail",
    ]:
        scad += "pf_" + key + "=" + json.dumps([r[key] for r in rows]) + ";\n"
    scad += """
module pf_sweep(path,r){for(j=[0:len(path)-2])hull(){translate(path[j])sphere(r=r/pow(cos(180/64),2),$fn=64);translate(path[j+1])sphere(r=r/pow(cos(180/64),2),$fn=64);}}
module pf_above(z){translate([-500,-500,z])cube([1000,1000,1000]);}
module pf_bare(i,m=0){pf_sweep([pf_start[i],pf_source_cut[i]],.7+.65+.005+m);pf_sweep([pf_end[i],pf_receiver_cut[i]],.7+.65+.005+m);}
module pf_insulated(i,m=0){r=1.7526/2+.65+.005+m;intersection(){pf_sweep([pf_source_cut[i],pf_bend[i]],r);pf_above(9.72-.655-m);}pf_sweep(pf_middle[i],r);intersection(){pf_sweep([pf_stub_start[i],pf_receiver_cut[i]],r);pf_above(11.2-.655-m);}}
module pf_wire(i,m=0){pf_bare(i,m);pf_insulated(i,m);}
module pf_wires(m=0){pf_wire(0,m);pf_wire(1,m);}
module pf_joint(m=0){for(b=pf_joints)translate([b[1]-m,b[2]-m,b[3]-.2-m])cube([b[4]+2*m,b[5]+2*m,b[6]+.4+2*m]);}
module pf_electronics(){for(b=pf_boxes)translate([b[1],b[2],b[3]-.2])cube([b[4],b[5],b[6]+.4]);for(c=pf_cylinders)translate([c[1],c[2],c[3]-.2])cylinder(d=c[4]/cos(180/128),h=c[5]+.4,$fn=128);
"""
    for b in native["boards"]:
        if b["id"] == "E28":
            continue
        scad += (
            "translate("
            + json.dumps([*b["datum"][:2], b["datum"][2] - 0.2])
            + ")linear_extrude("
            + str(b["thickness_range_allocation_mm"][1] + 0.4)
            + ")polygon("
            + json.dumps(b["outline_relative_mm"])
            + ");\n"
        )
    for b in other["boards"]:
        if b[0] not in ["dsp_carrier", "disconnect_carrier"]:
            scad += "board_reserve(" + json.dumps(b) + ");\n"
    scad += """}
module pf_hardware(){hardware();ss_post();ss_head();ss_shaft();}
module pf_case(){case_parts();ss_post();}
module pf_source_PCB(){translate([8,108.5,4.8])difference(){linear_extrude(2.1)polygon(pf_source_outline);for(p=pf_start)translate([p[0]-8,p[1]-108.5,-.01])cylinder(d=2.1,h=2.12,$fn=128);}}
module pf_receiver_PCB(){translate([30,42,6.3])difference(){linear_extrude(2.16)polygon(pf_receiver_outline);for(p=pf_end)translate([p[0]-30,p[1]-42,-.01])cylinder(d=2.1,h=2.18,$fn=128);}}
module pf_relative_source(){for(i=[0:1]){pf_sweep([pf_source_tail[i],pf_source_cut[i]],1.005);intersection(){pf_sweep([pf_source_cut[i],pf_bend[i]],1.1813);pf_above(9.72-.305);}}}
module pf_relative_receiver(){for(i=[0:1]){pf_sweep([pf_receiver_tail[i],pf_receiver_cut[i]],1.005);intersection(){pf_sweep([pf_stub_start[i],pf_receiver_cut[i]],1.1813);pf_above(11.2-.305);}}}
if(trial=="full_geometry"){pf_wires();pf_joint();}
if(trial=="full_bare_geometry")for(i=[0:1])pf_bare(i);
if(trial=="full_insulated_geometry")for(i=[0:1])pf_insulated(i);
if(trial=="full_wire_electronics_collision")intersection(){pf_wires(.25);pf_electronics();}
if(trial=="full_joint_electronics_collision")intersection(){pf_joint(.25);pf_electronics();}
if(trial=="full_wire_case_collision")intersection(){pf_wires(.25);pf_case();}
if(trial=="full_joint_case_collision")intersection(){pf_joint(.25);pf_case();}
if(trial=="full_wire_hardware_collision")intersection(){pf_wires(.25);pf_hardware();}
if(trial=="full_joint_hardware_collision")intersection(){pf_joint(.25);pf_hardware();}
if(trial=="full_pair_collision")intersection(){pf_wire(0,.25);pf_wire(1);}
if(trial=="full_source_PCB_geometry")pf_source_PCB();
if(trial=="full_receiver_PCB_geometry")pf_receiver_PCB();
if(trial=="full_source_bore_collision")intersection(){pf_relative_source();pf_source_PCB();}
if(trial=="full_receiver_bore_collision")intersection(){pf_relative_receiver();pf_receiver_PCB();}
if(trial=="full_source_bare_positive_control")intersection(){pf_bare(0);translate([160.9,120.4,7.02])cube([.2,.2,.2]);}
if(trial=="full_receiver_bare_positive_control")intersection(){pf_bare(1);translate([187.9,103.9,8.5])cube([.2,.2,.2]);}
if(trial=="full_source_insulated_positive_control")intersection(){pf_insulated(0);translate([160.9,120.4,12])cube([.2,.2,.2]);}
if(trial=="full_receiver_insulated_positive_control")intersection(){pf_insulated(1);translate([187.9,103.9,13])cube([.2,.2,.2]);}
if(trial=="full_middle_positive_control")intersection(){pf_insulated(0);translate(pf_middle[0][floor(len(pf_middle[0])/2)]-[.1,.1,.1])cube([.2,.2,.2]);}
if(trial=="full_source_PCB_positive_control")intersection(){pf_source_PCB();translate([160,134,5.7])cube([.2,.2,.2]);}
if(trial=="full_receiver_PCB_positive_control")intersection(){pf_receiver_PCB();translate([190,105,7])cube([.2,.2,.2]);}
"""
    (OUT / "checks.scad").write_text(scad)
    report = dict(
        scope=__doc__,
        source_sha256=hashes,
        routes=[{k: v for k, v in r.items() if k not in ["middle"]} for r in rows],
        true_radius_requirement_mm=required,
        geometry_reserve_mm=0.005,
        maximum_chord_bound_mm=route["maximum_native_chord_error_bound_mm"],
        independent_position_each_wire_mm=0.65,
        separate_clearance_mm=0.25,
        maximum_pretinned_core_requirement_mm=1.4,
        minimum_finished_bores_requirement_mm=2.1,
        relative_bore_centering_requirement_mm=0.3,
        source_PCB_thickness_range_allocation_mm=[1.5, 1.7],
        receiver_PCB_thickness_range_allocation_mm=[1.44, 1.76],
        PCB_vertical_position_allocation_mm=0.2,
        tails_checked_in_correlated_joint_reserves_not_free_wire_endcaps=True,
        own_two_PCBs_excluded_only_with_endpoint_bores_and_central_height_separation=True,
        H9_vertical_tool_access_clear=False,
        strain_relief_implemented=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def verify(executable):
    report = json.loads((OUT / "analysis.json").read_text())
    inputs = {str(p.relative_to(REPO)): sha(p) for p in [OUT / "analysis.json", OUT / "checks.scad"]}
    cases = {}
    names = [
        "geometry",
        "bare_geometry",
        "insulated_geometry",
        "wire_electronics_collision",
        "joint_electronics_collision",
        "wire_case_collision",
        "joint_case_collision",
        "wire_hardware_collision",
        "joint_hardware_collision",
        "pair_collision",
        "source_PCB_geometry",
        "receiver_PCB_geometry",
        "source_bore_collision",
        "receiver_bore_collision",
        "source_bare_positive_control",
        "receiver_bare_positive_control",
        "source_insulated_positive_control",
        "receiver_insulated_positive_control",
        "middle_positive_control",
        "source_PCB_positive_control",
        "receiver_PCB_positive_control",
    ]
    (OUT / "verification.json").unlink(missing_ok=True)
    for short in names:
        name = "full_" + short
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", key + '="full_route_only"']
        cmd += ["-D", 'trial="' + name + '"', "-o", str(target), str(OUT / "checks.scad")]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        log = process.stdout + process.stderr
        (OUT / (name + ".log")).write_text(log)
        clean = not any(t in log for t in ["WARNING", "ERROR"])
        expect_empty = short.endswith("collision")
        empty = (
            process.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        )
        if expect_empty and empty and clean:
            row = dict(clear=True, empty=True)
        elif process.returncode == 0 and target.exists() and "NoError" in log and clean:
            stats = binary_stl(target)
            ok = not expect_empty and stats["volume_mm3"] > 0.001
            if short.endswith("positive_control"):
                ok &= math.isclose(stats["volume_mm3"], 0.008, abs_tol=1e-6)
            row = dict(clear=bool(ok), **stats)
        else:
            row = dict(clear=False, returncode=process.returncode)
        cases[name] = row
        print(name, row, flush=True)
    changed = [n for n, h in {**report["source_sha256"], **inputs}.items() if sha(REPO / n) != h]
    result = dict(
        scope=__doc__,
        cases=cases,
        changed_inputs=changed,
        whole_pair_native_geometry_clear=not changed and all(r["clear"] for r in cases.values()),
        source_sha256=report["source_sha256"],
        evidence_inputs_sha256=inputs,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in [".log", ".stl"]
        },
        H9_tool_access_clear=False,
        forming_strain_relief_solder_process_qualified=False,
        complete_electrical_harness_qualified=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", type=Path, required=True)
    args = parser.parse_args()
    generate()
    raise SystemExit(0 if verify(args.openscad)["whole_pair_native_geometry_clear"] else 1)
