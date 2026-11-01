"""Validate rejected/accepted geometry faithfully; failures are never green passes."""

import hashlib
import json
import math

from hardware.cad.a12.enclosure_growth.integration.stage import E28, P03
from hardware.cad.a12.thermal.verify import binary_stl
from hardware.electronics.common.sexpr import children, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform

from .stage import OUT, REPO, ROOT, actual_bores
from .verify import COLLISIONS, CONTROLS, SOLIDS


def digest(data):
    return hashlib.sha256(data).hexdigest()


def errors(report=None, scene=None, overrides=None, check_live=True):
    r = report if report is not None else json.loads((OUT / "verification.json").read_text())
    s = scene if scene is not None else json.loads((OUT / "scene.json").read_text())
    replacements = overrides or {}
    result = []

    def read(p):
        name = str(p.relative_to(REPO))
        return replacements[name] if name in replacements else p.read_bytes() if p.is_file() else None

    expected = SOLIDS + COLLISIONS + CONTROLS
    if (
        r.get("requested_cases") != expected
        or set(r.get("cases", {})) != set(expected)
        or not r.get("complete_required_case_set")
    ):
        result.append("case coverage")
    if r.get("changed_inputs"):
        result.append("changed inputs during run")
    for group in ["source_sha256", "evidence_inputs_sha256", "artifact_sha256"]:
        for name, h in r.get(group, {}).items():
            path = REPO / name
            data = read(path)
            if group == "source_sha256":
                frozen = ROOT / "sources" / name
                if not frozen.is_file() or digest(frozen.read_bytes()) != h:
                    result.append("captured source " + name)
                if not check_live:
                    continue
            if data is None or digest(data) != h:
                result.append(group + " " + name)
    actual_failed = []
    for name, row in r.get("cases", {}).items():
        role = "empty" if name in COLLISIONS else "control" if name in CONTROLS else "solid"
        if row.get("role") != role:
            result.append("role " + name)
        mesh = read(OUT / (name + ".stl"))
        logdata = read(OUT / (name + ".log"))
        if logdata is None:
            result.append("missing log " + name)
            continue
        log = logdata.decode()
        clean = not any(t in log for t in ["WARNING", "ERROR"])
        if not clean:
            result.append("unclean log " + name)
        noerror = "NoError" in log
        if row.get("native_boolean_status_no_error") != noerror:
            result.append("status mismatch " + name)
        if mesh is None:
            success = (
                role == "empty"
                and row.get("returncode") == 1
                and row.get("empty") is True
                and "Current top level object is empty." in log
                and clean
            )
            if not success:
                result.append("missing required mesh " + name)
        else:
            # The saved actual file must agree with the declared row, including failed collisions.
            if not noerror:
                result.append("missing native NoError " + name)
            if row.get("returncode") != 0 or row.get("empty") is not False:
                result.append("nonempty evidence " + name)
            actual = binary_stl(OUT / (name + ".stl"))
            if actual != row.get("statistics"):
                result.append("mesh metadata " + name)
            if str((OUT / (name + ".stl")).relative_to(REPO)) not in r.get("artifact_sha256", {}):
                result.append("unbound mesh " + name)
            success = clean and noerror and role != "empty" and actual["volume_mm3"] > 0.001
            if role == "control":
                success &= math.isclose(actual["volume_mm3"], 0.008, abs_tol=1e-6)
        if row.get("clear") != success:
            result.append("false clear flag " + name)
        if not success:
            actual_failed.append(name)
    all_clear = not actual_failed and not r.get("changed_inputs")
    if r.get("all_requested_native_geometry_checks_clear") != all_clear:
        result.append("false overall pass")
    for key in [
        "physical_qualified",
        "thermal_qualified",
        "complete_wiring_qualified",
        "fabrication_released",
    ]:
        if r.get(key) is not False:
            result.append("false qualification " + key)
    for b, base, filename in [
        (s["native_boards"][0], P03, "power_p03"),
        (s["native_boards"][1], E28, "rail_disconnect"),
    ]:
        path = ROOT / "sources" / base.relative_to(REPO) / (filename + ".kicad_pcb")
        if actual_bores(read_sexpr(path.read_text())) != b.get("all_actual_drilled_pad_bores"):
            result.append("actual bores " + b["id"])
    meta = json.loads((OUT / "analysis.json").read_text())
    p = ROOT / "sources" / meta["receiver_source_folder"] / "processor_carrier.kicad_pcb"
    if actual_bores(read_sexpr(p.read_text())) != s.get("receiver_holes"):
        result.append("receiver bores")
    if not p.is_file() or digest(p.read_bytes()) != meta.get("receiver_source_pcb_sha256"):
        result.append("receiver source substitution")
    if meta.get("source_wire_points_mm") != [[161, 120.5, 6.62], [161, 126.5, 6.62]]:
        result.append("source port substitution")
    tree = read_sexpr(p.read_text())
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(a[1:3] == ["Reference", "J29"] for a in children(f, "property"))
    )
    x0, y0, x1, y1 = courtyard(fp, "F.CrtYd")
    expected = [
        "e19_J29",
        round(x0 - 70 - 0.5, 6),
        round(y0 - 58 - 0.5, 6),
        8.1,
        round(x1 - x0 + 1, 6),
        round(y1 - y0 + 1, 6),
        11.31,
    ]
    saved = next(a for a in s["inherited_envelopes"] if a[0] == "e19_J29")
    if saved != expected or meta.get("J29_actual_service_requirement") != expected:
        result.append("actual J29 body")
    for pad in children(fp, "pad"):
        x, y = transform(fp, next(a for a in children(pad, "at"))[1:3])
        tail = next(a for a in s["inherited_envelopes"] if a[0] == "e19_J29_lead_" + str(pad[1]))
        if not (math.isclose(tail[1], x - 71, abs_tol=1e-8) and math.isclose(tail[2], y - 59, abs_tol=1e-8)):
            result.append("actual J29 tails")
    rear = ROOT / "sources/hardware/cad/a12/enclosure_growth/rear-ports/analysis.json"
    rp = json.loads(rear.read_text())
    if (
        s.get("rear_ports") != rp["candidate_rear_ports"]
        or s.get("rear_port_reserves") != rp["candidate_port_envelopes"]
    ):
        result.append("rear interface substitution")
    for key, want in [
        ("native_external_clearance_mm", 0.25),
        ("native_extra_Z_uncertainty_each_mm", 0.2),
        ("native_thicknessrange_already_in_components", True),
        ("nominal_and_0p25_cases_separate", True),
        ("rear_mating_face_correlated_Y0", True),
    ]:
        if meta.get(key) != want:
            result.append("clearance contract " + key)
    required = [
        "native_component_case_0p25_collision",
        "native_component_other_0p25_collision",
        "native_boards_mutual_0p25_collision",
        "rear_body_case_0p25_collision",
        "native_nominal_strip_negative_control_collision",
        "native_cylinder_nominal_negative_control_collision",
    ]
    if any(name not in r["cases"] for name in required):
        result.append("missing clearance cases")
    # These controls must lie entirely outside nominal bodies, proving actual margin execution.
    box = next(b for b in s["native_boxes"] if b[0] == "E28_U18")
    ctl = r["cases"].get("native_component_clearance_positive_control", {}).get("statistics")
    if ctl and not ctl["max_mm"][0] < box[1]:
        result.append("box margin witness inside nominal")
    cyl = next(c for c in s["native_cylinders"] if c[0] == "E28_C8")
    ctl = r["cases"].get("native_cylinder_clearance_positive_control", {}).get("statistics")
    if ctl and not ctl["min_mm"][0] > cyl[1] + cyl[4] / math.cos(math.pi / 128) / 2:
        result.append("cylinder margin witness inside nominal")
    tc = ROOT / "sources/hardware/cad/a12/trill_front_bay/generated/verification.json"
    baseline = json.loads(tc.read_text())["cases"]["geometry"]["statistics"]
    current = r["cases"].get("trill_frontbay_geometry", {}).get("statistics")
    if current and any(
        not all(math.isclose(x, y, abs_tol=0.00003) for x, y in zip(current[k], baseline[k]))
        for k in ["min_mm", "max_mm"]
    ):
        result.append("Trill transform changed")
    return result


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--historical", action="store_true")
    a = p.parse_args()
    found = errors(check_live=not a.historical)
    print(
        json.dumps(
            dict(
                evidence_errors=found,
                valid_evidence=not found,
                whole_geometry_clear=bool(
                    json.loads((OUT / "verification.json").read_text())[
                        "all_requested_native_geometry_checks_clear"
                    ]
                ),
                physical_qualified=False,
            )
        )
    )
    raise SystemExit(bool(found))
