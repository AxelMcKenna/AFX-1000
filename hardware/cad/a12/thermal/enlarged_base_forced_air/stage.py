"""FI01 captured CP01+FA01 geometry, no native launch or live board adoption."""

import json
import re
import shutil
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base_pot.stage import audit_parent, guard_capture, sha, write

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
OUT = ROOT / "generated"
CP = ROOT.parent / "enlarged_base_pot"
FA = ROOT.parent / "forced_air_prototype"
EB = ROOT.parent / "enlarged_base"


def replace_module_body(source, name, transform):
    start = source.index("module " + name + "(")
    begin = source.index("{", start)
    depth = 1
    end = begin + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[: begin + 1] + transform(source[begin + 1 : end - 1]) + source[end - 1 :]


def capture():
    guard_capture(ROOT)
    parents = dict(CP01=audit_parent(CP), FA01=audit_parent(FA))
    audit = json.loads((ROOT / "initial-source-audit.json").read_text())
    assert audit["actual_kept_count"] == 960
    cp_cap = json.loads((CP / "capture.json").read_text())
    assert all(sha(CP / n) == h for n, h in cp_cap["derived_context_sha256"].items())
    OUT.mkdir(exist_ok=True)
    context = ROOT / "context"
    shutil.copytree(CP / "context", context)
    for p in context.rglob("*.scad"):
        p.write_text(p.read_text().replace(str(CP / "context"), str(context)))
    fa_analysis = json.loads((FA / "generated/analysis.json").read_text())
    part_source = (CP / "generated/parts.scad").read_text()
    pinline = next(l for l in part_source.splitlines() if l.startswith("eb_part_pins="))
    pins = json.loads(pinline.split("=", 1)[1].rstrip(";"))
    removed = set(map(tuple, fa_analysis["removed_pin_centres_mm"]))
    kept = [p for p in pins if tuple(p) not in removed]
    assert len(pins) == 1037 and len(removed) == 77 and len(kept) == 960
    thermal = context / "hardware/cad/a12/thermal/generated/thermal-base.scad"
    s = thermal.read_text()
    s, count = re.subn(r"^thermal_pins=.*?;", "thermal_pins=" + json.dumps(kept) + ";", s, flags=re.M)
    assert count == 1
    s = replace_module_body(s, "thermal_feet", lambda body: "translate([0,0,-8]){" + body + "}")
    thermal.write_text(s)
    part_source = part_source.replace(pinline, "eb_part_pins=" + json.dumps(kept) + ";")
    part_source = replace_module_body(
        part_source, "eb_part_feet", lambda body: "translate([0,0,-8]){" + body + "}"
    )
    (OUT / "parts.scad").write_text(
        "// FI01actual960-pin part; CP01/EB01originals unchanged.\n" + part_source
    )
    base = (CP / "generated/context-derived.scad").read_text().replace(str(CP / "context"), str(context))
    assert base.count("cylinder(d=3,h=10.35") == 1
    base = base.replace("cylinder(d=3,h=10.35", "cylinder(d=3,h=18.35")
    assert base.count("-12.00002])cylinder(d=3.02,h=5.80004") == 1
    base = base.replace("-12.00002])cylinder(d=3.02,h=5.80004", "-20.00002])cylinder(d=3.02,h=5.80004")
    ui = context / "hardware/cad/a12/enclosure_growth/integration_repaired/generated/checks.scad"
    s = ui.read_text()
    old = next(l for l in s.splitlines() if l.startswith("module ui_case_shell()"))
    s = s.replace(old, old[:-1] + "fi_tray();fi_guards();fi_spacers();fi_fans();fi_fan_fasteners();}")
    ui.write_text(s)
    prototype = (FA / "generated/checks.scad").read_text()
    assert prototype.count('fa_case="assembly";') == 1
    # Private module scope preserves FA's$fn96 without changing CP01tessellation.
    prototype = prototype.replace('fa_case="assembly";', "fa_case=fa_selector;")
    prototype += (
        '\nif(fa_case=="fan_stress_receiving")for(p=fa_fans)translate([p[0],p[1],0])fa_fan_receiving(.3);\n'
    )
    prototype += 'if(fa_case=="hardware_stress_receiving")for(p=fa_fans)for(x=[-16,16],y=[-16,16])translate([p[0]+x,p[1]+y,-30.70002])cylinder(r=(3.7+sqrt(2)*.275+.005)/cos(180/128),h=23.10004,$fn=128);\n'
    (OUT / "fa-scoped.scad").write_text(prototype)
    geometry = (ROOT / "geometry.scad").read_text()
    geometry = geometry.replace(
        "FI_REMOVED_WITNESS", json.dumps([sorted(removed)[0][0] - 0.1, sorted(removed)[0][1] - 0.1, -15.1])
    )
    geometry = geometry.replace(
        "FI_RETAINED_WITNESS", json.dumps([kept[0][0] - 0.1, kept[0][1] - 0.1, -15.1])
    )
    (OUT / "context-derived.scad").write_text(base + "\n" + geometry)
    shutil.copyfile(CP / "generated/config.json", OUT / "config.json")
    cases = json.loads((CP / "generated/cases.json").read_text())
    fa_proof = json.loads((FA / "generated/verification.json").read_text())
    for n, row in fa_proof["cases"].items():
        role = (
            "empty"
            if n.endswith("_collision")
            else "part"
            if n in ["tray_geometry", "guard_geometry", "spacer_geometry"]
            else "review"
            if n in ["assembly", "fan_gauge_geometry", "fastener_gauge_geometry"]
            else "control"
        )
        cases["fa_" + n] = dict(
            selector="fi_fa_case",
            value=n,
            role=role,
            expected_volume=0.008 if n.endswith("_positive_control") else None,
        )
    empty = [
        "actual_base_tray_collision",
        "actual_base_fan_stress_collision",
        "actual_base_hardware_sweep_collision",
        "foot_screws_tray_collision",
        "foot_screws_spacers_collision",
        "feet_spacers_contact_collision",
        "actual_feet_tray_collision",
        "added_case_controls_collision",
        "added_electronics_collision",
        "added_existing_power_collision",
        "added_existing_wires_collision",
        "nominal_fan_hardware_mates_collision",
        "removed_pin_void_collision",
        "engaged_thread_void_collision",
    ]
    for n in empty:
        cases["fi_" + n] = dict(selector="fi_case", value=n, role="empty", expected_volume=None)
    for n, volume in [
        ("retained_pin_positive_control", 0.008),
        ("long_foot_screw_positive_control", 0.008),
        ("below_thread_tip_positive_control", 0.002),
    ]:
        cases["fi_" + n] = dict(selector="fi_case", value=n, role="control", expected_volume=volume)
    write(OUT / "cases.json", cases)
    # Parents stay immutable. Only necessary raw/source identities are copied.
    for parent, files in [
        (
            CP,
            [
                "handoff.json",
                "capture.json",
                "generated/verification.json",
                "generated/identities.json",
                "README.md",
            ],
        ),
        (
            FA,
            [
                "handoff.json",
                "space-plan.json",
                "fan-source.json",
                "electrical-and-test-holds.json",
                "generated/analysis.json",
                "generated/verification.json",
                "generated/checks.scad",
                "build.py",
            ],
        ),
    ]:
        for n in files:
            t = ROOT / "parent_evidence" / parent.name / n
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(parent / n, t)
    write(
        OUT / "pin-datum.json",
        dict(
            original=pins,
            removed=list(map(list, sorted(removed))),
            kept=kept,
            whole_pin_volume_removed_mm3=8316,
            retained_witness=[*kept[0], -15],
            removed_witness=[*list(sorted(removed))[0], -15],
        ),
    )
    write(
        ROOT / "FI01-stack.json",
        dict(
            foot_screw="AccuSPK-M3-20-A2",
            screw_overall_including_countersunk_head_mm=20,
            plate=6.2,
            tray_flange=2,
            spacer=6,
            nominal_engagement=5.8,
            nominal_actual_thread_overlap=[-20, -14.2],
            receiving_thread_interval=[-20.00002, -14.19998],
            numerical_tip_mouth_guards_each=0.00002,
            foot_translation=-8,
            manufacturing_pilot_unchanged=True,
            nominal_bumper_bottom=-36.8,
            nominal_max_PS01_knob_top=67.2,
            nominal_overall_height=104.0,
            nominal_fan_pan_under_head_bolt_length=20,
            fan_hardware_gauges_selected_parts=False,
            actual_supplier_lot_dimensions_thread_length_preload_strength_accepted=False,
            fan_body_height_and_stack_minimum_bearing_not_qualified=True,
            original_plastic_case_has_no_conditional_metal_wall_lid_heat_credit=True,
            fan_current_ledger_or_full_wiring_implemented=False,
            physical_qualified=False,
            thermal_qualified=False,
        ),
    )
    copied = {str(p.relative_to(ROOT)): sha(p) for p in context.rglob("*") if p.is_file()}
    write(
        ROOT / "capture.json",
        dict(
            parents=parents,
            derived_context_sha256=copied,
            transformations=[
                "Actualwhole77pins removed in nativebase andstandaloneAPI; remaining960 list preserved",
                "Four original feet translated-8; manufacturingblindpilot unchanged",
                "AccuSPK-M3-20-A2countersunk length20; actualthreadreceiving[-20.00002,-14.19998]",
                "FA01allfunctions/$fn isolated insideprivate module; sourcefan/tray/guard/spacer geometry preserved",
                "AddedFAgeometry included in currentcaseenvironment; alloldbody/control/wire sources untouched",
            ],
            original_CP01_or_FA01_modified=False,
            new_board_or_wire_source_adopted=False,
            new_native_execution_performed=False,
        ),
    )
    print(
        json.dumps(
            dict(
                captured_context_files=len(copied),
                kept_pins=len(kept),
                cases=len(cases),
                native_not_launched=True,
            )
        )
    )


if __name__ == "__main__":
    capture()
