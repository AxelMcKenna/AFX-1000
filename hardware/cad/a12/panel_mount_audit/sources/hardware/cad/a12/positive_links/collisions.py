"""Fresh native both-face board bodies and all inherited A12 obstacles."""

import json
import math
import re

from hardware.cad.a11.integration import assignments
from hardware.cad.a12.generate import build
from hardware.cad.a12.repaired import packet
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

from .bounds import rows as support_bounds
from .generate import OUT, REPO, ROOT, load, sha
from .selected_parts import requirement


def snapshot():
    native = packet()
    selected = []
    for row in native["component_records"]:
        chosen = requirement(row["actual_footprint"], row["part"])
        if chosen is not None:
            assert (
                abs(row["maximum_projection_allocation_mm"] - chosen["assembled_projection_requirement_mm"])
                < 1e-12
            ), "Shared selected height mismatch"
            selected.append(dict(board=row["board"], ref=row["ref"], **chosen))
    native["shared_selected_height_resolutions"] = selected
    contract, data, inherited = build()
    hashes = dict(native["source_sha256"])
    hashes.update(inherited["source_sha256"])
    selection = REPO / "hardware/electronics/power_distribution/p03/component-selections.json"
    hashes[str(selection.relative_to(REPO))] = sha(selection)
    # Repaired.packet() lists board fixing bores. The positive screw tips also
    # need the actual terminal locating NPTH bores, not an inferred empty PCB.
    for board in native["boards"]:
        relative = (
            "power_distribution/p03/power_p03.kicad_pcb"
            if board["id"] == "P03"
            else "rail_disconnect/revision28/rail_disconnect.kicad_pcb"
        )
        tree = read_sexpr((REPO / "hardware/electronics" / relative).read_text())
        for fp in children(tree, "footprint"):
            for pad in children(fp, "pad"):
                if str(pad[2]) != "np_thru_hole":
                    continue
                xy = transform(fp, first(pad, "at")[1:3])
                drill = float(first(pad, "drill")[1])
                hole = [xy[0] - 100, xy[1] - 100, drill]
                if not any(
                    all(abs(a - b) < 1e-6 for a, b in zip(hole, h))
                    for h in board["mounting_holes_relative_mm"]
                ):
                    board["mounting_holes_relative_mm"].append(hole)
    # Refresh all four routed inherited boards directly from the PCB-bound
    # body packets; cached A11 SCAD is not allowed to hide a later PCB change.
    prefixes = []
    new_bodies = []
    for folder, basename in [
        ("output_stage", "output_stage"),
        ("control_inputs", "control_inputs"),
        ("processor_carrier", "processor_carrier"),
        ("led_driver", "led_driver"),
    ]:
        base = REPO / "hardware/electronics" / folder
        placement = base / "generated/placement.json"
        actual = json.loads(placement.read_text())
        assert actual["pcb_sha256"] == sha(base / (basename + ".kicad_pcb")), (
            "Stale inherited native body packet"
        )
        prefixes.append(actual["bodies"][0][0].split("_")[0] + "_")
        new_bodies += actual["bodies"]
        for q in [placement, base / (basename + ".kicad_pcb"), base / "components.json"]:
            hashes[str(q.relative_to(REPO))] = sha(q)
    data["envelopes"] = [r for r in data["envelopes"] if not r[0].startswith(tuple(prefixes))] + new_bodies
    # Actual A11 button centres, Omron lead pattern and retained conservative
    # 4.5mm solder/lead projection below the switch base. These are assembly
    # requirements, not a measured lead or solder-wire guarantee.
    buttons = assignments(REPO / "hardware/cad/a11/generated/controls.scad")["buttons"]
    fixture = assignments(REPO / "hardware/cad/a11/generated/button-fixture.scad")
    switch_base = 36 - fixture["board_drop"]
    controlled = contract["switch_assembly"]
    assert controlled["local_body_terminal_reserve_xy_mm"] == [10, 10]
    native["switch_diagnostic_boxes"] = []
    for b in buttons:
        # Local10x10 is a project reserve around manufacturer terminal span
        # max8.2mm. Rotate with the actual switch; use its circumscribing AABB.
        angle = math.radians(b[7])
        half = 5 * (abs(math.cos(angle)) + abs(math.sin(angle)))
        native["switch_diagnostic_boxes"] += [
            [
                b[0] + "_switch_body",
                b[5] - half,
                b[6] - half,
                switch_base,
                2 * half,
                2 * half,
                controlled["body_projection_maximum_mm"],
                "DiagnosticAABB only; actual native case uses rotated a12_switch_electronics()",
            ],
            [
                b[0] + "_switch_leads",
                b[5] - half,
                b[6] - half,
                switch_base - controlled["lead_solder_projection_requirement_mm"],
                2 * half,
                2 * half,
                controlled["lead_solder_projection_requirement_mm"],
                "DiagnosticAABB only; controlled project requirement, not supplier guarantee",
            ],
        ]
    # Bind every included SCAD and imported frozen STL, not just the entrypoint.
    pending = [REPO / "hardware/cad/a12/thermal-integration.scad"]
    seen = set()
    while pending:
        q = pending.pop().resolve()
        if q in seen:
            continue
        seen.add(q)
        hashes[str(q.relative_to(REPO))] = sha(q)
        if q.suffix == ".scad":
            source = q.read_text()
            pending += [
                (q.parent / name).resolve() for name in re.findall(r"(?:include|use)\s*<([^>]+)>", source)
            ]
            pending += [(q.parent / name).resolve() for name in re.findall(r'import\("([^"\n]+)"\)', source)]
    for p in [
        ROOT / "design.json",
        ROOT / "generate.py",
        ROOT / "collisions.py",
        ROOT / "caps.py",
        ROOT / "support.py",
        ROOT / "verify.py",
        ROOT / "bounds.py",
        ROOT / "selected_parts.py",
        OUT / "support-bounds.json",
        REPO / "hardware/cad/a12/thermal/verify.py",
    ]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    return native, data, hashes


def main():
    d = load()
    bounded = json.loads((OUT / "support-bounds.json").read_text())
    assert all(sha(ROOT / path) == value for path, value in bounded["source_sha256"].items()), (
        "Stale support containment proof"
    )
    assert bounded["nominal_and_generated_extrema_contained"]
    assert bounded["contained_actual_step_sha256"] == sha(OUT / "SUPPORT-ENVELOPE.step"), (
        "Support containment geometry changed"
    )
    native, data, hashes = snapshot()
    ends = {r for p in d["paths"].values() for r in p["end_refs"]}
    for name, row in d["paths"].items():
        for q, ref in zip((row["points"][0], row["points"][-1]), row["end_refs"]):
            body = next(b for b in native["boxes"] if b[0] == ref)
            assert abs(body[1] + body[4] / 2 - q[0]) < 1e-6 and abs(body[2] + body[5] / 2 - q[1]) < 1e-6, (
                ref,
                q,
                body,
            )
    boxes = [r for r in native["boxes"] if r[0] not in ends]
    for r in boxes:
        r[3] -= 0.2
        r[6] += 0.4
    cylinders = native["cylinders"]
    for r in cylinders:
        r[3] -= 0.2
        r[5] += 0.4
    other_boards = [r for r in data["boards"] if r[0] != "disconnect_carrier"]
    other_boxes = [r for r in data["envelopes"] if not r[0].startswith("disconnect_")] + data[
        "port_envelopes"
    ]
    source = """include <../../thermal-integration.scad>
positive_part="review";
"""
    for key, value in dict(
        positive_boxes=boxes,
        positive_cylinders=cylinders,
        positive_boards=native["boards"],
        positive_other_boards=other_boards,
        positive_other_boxes=other_boxes,
        positive_support_boxes=support_bounds(d)[0],
        positive_support_cylinders=support_bounds(d)[1],
    ).items():
        source += key + "=" + json.dumps(value) + ";\n"
    source += """
module positive_copper(name){import(str(name,"-CU.stl"));}
module positive_cover(name){import(str(name,"-COVERED-ENVELOPE.stl"));}
module positive_support(){import("SUPPORT-ENVELOPE.stl");}
module support_convex_bounds(margin=.35){for(b=positive_support_boxes)translate([b[0]-margin,b[1]-margin,b[2]-margin])cube([b[3]+2*margin,b[4]+2*margin,b[5]+2*margin]);for(c=positive_support_cylinders)hull(){for(dx=[-margin,margin],dy=[-margin,margin])translate([c[0]+dx,c[1]+dy,c[2]-margin])cylinder(d=c[3]/cos(180/128),h=c[4]+2*margin,$fn=128);}}
module support_screen(margin=.35){intersection(){support_convex_bounds(margin);translate([0,0,4])cube([334,157,40]);}}
module positive_hardware(){import("positive-links.stl");}
module positive_envelope(name,margin=0){minkowski(){positive_cover(name);cube([2*margin,2*margin,2*margin],center=true);}}
module positive_envelopes(margin=0){for(name=["ANA","DIG"])positive_envelope(name,margin);}
module positive_native_boards(){for(b=positive_boards)translate([b["datum"][0],b["datum"][1],b["datum"][2]-.2])difference(){linear_extrude(b["thickness_range_allocation_mm"][1]+.4)polygon(b["outline_relative_mm"]);for(h=b["mounting_holes_relative_mm"])translate([h[0],h[1],-.01])cylinder(d=h[2],h=3,$fn=64);}}
module positive_electronics(){positive_native_boards();for(b=positive_boxes)translate([b[1],b[2],b[3]])cube([b[4],b[5],b[6]]);for(c=positive_cylinders)translate([c[1],c[2],c[3]])cylinder(d=c[4],h=c[5],$fn=128);for(b=positive_other_boards)board_reserve(b);for(e=positive_other_boxes)translate([e[1],e[2],e[3]])cube([e[4],e[5],e[6]]);}
module positive_case(){retained_thermal_shell();thermal_metal_base();thermal_controls();lower_shell_fasteners();}
module positive_return_obstacles(){return_retention();return_fasteners();minkowski(){return_bars();cube([1.3,1.3,.2],center=true);}}
if(positive_part=="copper") {positive_copper("ANA");positive_copper("DIG");}
if(positive_part=="case_collision")intersection(){positive_envelopes(.35);positive_case();}
if(positive_part=="electronics_collision")intersection(){positive_envelopes(.35);positive_electronics();}
if(positive_part=="returns_collision")intersection(){positive_envelopes(.35);positive_return_obstacles();}
if(positive_part=="pair_collision")intersection(){positive_envelope("ANA",.225);positive_envelope("DIG",.225);}
if(positive_part=="support_case_collision")intersection(){support_screen();positive_case();}
if(positive_part=="support_electronics_collision")intersection(){support_convex_bounds(.35);positive_electronics();}
if(positive_part=="support_returns_collision")intersection(){support_screen();positive_return_obstacles();}
if(positive_part=="support_positive_control")intersection(){positive_support();translate([166,123.5,10])cube([.2,.2,.2]);}
if(positive_part=="positive_control")intersection(){positive_copper("ANA");translate([210,139,13.3])cube([.2,.2,.2]);}
if(positive_part=="review"){color([.8,.4,.12])positive_hardware();color([.1,.4,.3,.15])positive_electronics();color([.2,.3,.4,.1])positive_case();return_assembly();}
"""
    # OpenSCAD has no dictionary indexing. Native board records are lowered to
    # compact positional tuples before writing the final source.
    boards = [
        [
            b["datum"],
            b["thickness_range_allocation_mm"],
            b["outline_relative_mm"],
            b["mounting_holes_relative_mm"],
        ]
        for b in native["boards"]
    ]
    source = source.replace(
        "positive_boards=" + json.dumps(native["boards"]), "positive_boards=" + json.dumps(boards)
    )
    for key, value in [
        ('b["datum"]', "b[0]"),
        ('b["thickness_range_allocation_mm"]', "b[1]"),
        ('b["outline_relative_mm"]', "b[2]"),
        ('b["mounting_holes_relative_mm"]', "b[3]"),
    ]:
        source = source.replace(key, value)
    (OUT / "collisions.scad").write_text(source)
    report = dict(
        source_sha256=hashes,
        intentional_connected_studs_excluded=sorted(ends),
        native_component_records=native["component_records"],
        shared_selected_height_resolutions=native["shared_selected_height_resolutions"],
        boxes=boxes,
        cylinders=cylinders,
        other_boxes=other_boxes,
        switch_diagnostic_boxes=native["switch_diagnostic_boxes"],
        switch_native_geometry="Rootthermal_controls()->a12_switch_electronics(),actual rotated local reserve; no duplicated custom switch obstacles",
        all_component_mate_heights_approved=False,
        physical_fit_verified=False,
    )
    (OUT / "obstacles.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
