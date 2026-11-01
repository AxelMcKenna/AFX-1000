"""EB01: new enlarged base, retaining EI02 as an immutable source scene."""

import hashlib
import importlib.util
import json
import math
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
OUT = ROOT / "generated"
EI = REPO / "hardware/cad/a12/enclosure_growth/integration_repaired"
THERMAL = ROOT.parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")


def stage():
    OUT.mkdir(exist_ok=True)
    report = json.loads((EI / "generated/analysis.json").read_text())
    assert all(sha(REPO / n) == h for n, h in report["source_sha256"].items())
    dims = json.loads((THERMAL / "coupled_housing20/sources/dimensions.json").read_text())
    design = json.loads((THERMAL / "design.json").read_text())
    design["revision"] = "EB01 enlarged machined base and retained plastic carrier"
    design["housing"] = dims["candidate_outer_shell"]
    design["feet"]["centres"] = dims["new_feet_candidate_xy"]
    design["shell_fasteners"] = dims["candidate_shell_fasteners_xy"]
    spec = importlib.util.spec_from_file_location("captured_geometry", THERMAL / "coupled_housing20/base_geometry.py")
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    pins = g.pin_centres(design)
    assert len(pins) == 1037
    write(ROOT / "design.json", design)
    paths = {REPO / n for n in report["source_sha256"]}
    paths.update([
        EI / "generated/checks.scad", EI / "generated/scene.json", EI / "generated/analysis.json",
        EI / "generated/verification.json", EI / "handoff.json", THERMAL / "design.json",
        THERMAL / "source-facts.json", THERMAL / "generate.py",
        THERMAL / "coupled_housing20/base_geometry.py",
        THERMAL / "coupled_housing20/sources/dimensions.json",
    ])
    # Resolve actual SCAD dependencies, including imports, rather than assume a
    # parent's provenance list is also an executable include/import closure.
    pending = [EI / "generated/checks.scad"]
    seen = set()
    while pending:
        p = pending.pop().resolve()
        if p in seen:
            continue
        seen.add(p)
        paths.add(p)
        if p.suffix != ".scad":
            continue
        s = p.read_text()
        refs = re.findall(r"(?:include|use)\s*<([^>]+)>|import\(\s*\"([^\"]+)\"", s)
        for a, b in refs:
            q = Path(a or b)
            q = q if q.is_absolute() else p.parent / q
            q = q.resolve()
            assert q.exists(), str(q)
            assert q.is_relative_to(REPO), str(q)
            pending.append(q)
    originals = {}
    derived = {}
    context = ROOT / "context"
    for p in sorted(paths):
        n = p.relative_to(REPO)
        originals[str(n)] = sha(p)
        saved = ROOT / "sources" / n
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, saved)
        target = context / n
        target.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == ".scad":
            s = p.read_text().replace(str(REPO), str(context))
            if p.name == "thermal-base.scad":
                replacements = {
                    "thermal_pins": pins,
                    "thermal_feet_xy": design["feet"]["centres"],
                    "thermal_shell_bolts": design["shell_fasteners"],
                }
                for name, value in replacements.items():
                    s, count = re.subn(r"^" + name + r"=.*?;", name + "=" + json.dumps(value) + ";", s, flags=re.M)
                    assert count == 1
                assert s.count("thermal_round_rect(334,157,7)") == 1
                s = s.replace("thermal_round_rect(334,157,7)", "thermal_round_rect(334,188.4,7)")
                # Only our derived copy gains the actual blind pilot in each
                # machined foot. Threads are separately abstracted for assembly.
                old = "translate([p[0],p[1],-25.2])cylinder(d=18,h=19,$fn=64);"
                new = "translate([p[0],p[1],-25.2])difference(){cylinder(d=18,h=19,$fn=64);translate([0,0,6])cylinder(d=2.5,h=13.01,$fn=64);}"
                assert old in s
                s = s.replace(old, new)
            target.write_text(s)
        else:
            shutil.copyfile(p, target)
        derived[str(target.relative_to(ROOT))] = sha(target)
    write(ROOT / "capture.json", dict(original_sha256=originals, derived_context_sha256=derived,
        transformations=["Absolute repo paths rebound to immutable private context", "thermal-base.scad only: extent188.4,1037 pins,nine shell axes,four relocated foot axes,blind foot tap pilots"],
        original_sources_modified=False))
    meta = dict(
        scope=__doc__, units="mm", base_extent_mm=[334,188.4,6.2], radius_mm=7,
        pins=dict(count=len(pins), width_mm=3, height_mm=12, pitch_mm=7, border_mm=12,
            centres=pins, H20_numeric_pin_count=1037, count_delta=0),
        retained_thermal_lands=g.lands(design), retained_supports=g.mounts(design),
        shell_fasteners=design["shell_fasteners"], foot_axes=design["feet"]["centres"],
        new_shell_axes=[p for p in design["shell_fasteners"] if p[1]>157],
        old_base_extent_mm=[334,157,6.2], new_plate_area_mm2=334*188.4-(4-math.pi)*7**2,
        retained_carrier_upper_surface_mm=2.8,
        countersinks=dict(shell_under_and_foot_upper=dict(through=3.4,OD=6.6,depth=1.6),return_under=dict(through=2.4,OD=4.8,depth=1.2)),
        hardware=dict(lower_screw="Accu SPK-M3-16-A2", lower_nut="Wurth03223 DIN934 M3",foot_screw="Accu SPK-M3-12-A2", bumper="3M SJ5312 7000001166"),
        stacks=dict(lower_tip_z_nominal=9.8, nut_z=[5,7.4], lower_above_nut_nominal=2.4,
            foot_screw_engagement_nominal=5.8,foot_available_thread_minimum_requirement=10,
            foot_tap_drill_depth=13,foot_blind_remaining_mm=6,
            board_screw_engagement_nominal_without_washer=2.2,board_screw_engagement_min_allocation_without_washer=1.84,
            screw_length_tolerances_and_actual_thread_runout_approved=False),
        intended_contacts=dict(plate_floor_Z0_guard_mm=0.00002,nut_pocket_floor_Z5_guard_mm=0.00002,
            foot_plate_contact_Z=-6.2,thread_abstraction="Only foot M3 engaged interval: nominal major diameter3.02 removed for assembly check; manufacturing foot retains2.5tap pilot; neither is resolved helical thread proof",
            P03_seats="Ten6mm supports to original matched shims/NPTH; no soldermask isolation credit",
            no_metal_wall_or_lid_adopted=True),
        geometric_delta_from_H20=dict(pin_count=0,foot_positions_unchanged=True,
            holes_countersinks_threads_lands_and_local_supports_now_explicit=True,
            H20_ideal_plate_area_ignores_holes_and_countersinks=True,
            thermal_replay_inherited=False),
        physical_qualified=False, thermal_qualified=False, fabrication_released=False,
        structural_qualified=False, whole_wiring_qualified=False,
    )
    write(OUT / "analysis.json", meta)
    scene = json.loads((EI / "generated/scene.json").read_text())
    write(OUT / "scene.json", dict(mounts=scene["mounts"], rear_ports=report["rear_ports"], fasteners=design["shell_fasteners"]))
    own = (ROOT / "geometry.scad").read_text().replace("EB_POSITIVE_STL", str(context / "hardware/cad/a12/positive_links/generated/positive-links.stl"))
    (OUT / "checks.scad").write_text("include <" + str(context / (EI / "generated/checks.scad").relative_to(REPO)) + ">\n" + own)
    print(json.dumps(dict(captured=len(paths),derived=len(derived),pins=len(pins))))


if __name__ == "__main__":
    stage()
