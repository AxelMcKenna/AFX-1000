"""Validate rejected/accepted geometry faithfully; failures are never green passes."""

import hashlib
import json
import math

from hardware.cad.a12.thermal.verify import binary_stl
from hardware.electronics.common.sexpr import read_sexpr

from .stage import E28, OUT, P03, REPO, ROOT, actual_bores
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
    if (
        meta.get("receiver_source_pcb_sha256")
        != "e415660388344af08fb372d11ed011381e951cd021a1aa45b913900f0b9784c2"
    ):
        result.append("receiver source substitution")
    if meta.get("source_wire_points_mm") != [[161, 120.5, 6.62], [161, 126.5, 6.62]]:
        result.append("source port substitution")

    def volume(name):
        stats = r.get("cases", {}).get(name, {}).get("statistics")
        return stats.get("volume_mm3", float("nan")) if isinstance(stats, dict) else float("nan")

    for whole, part in [
        ("power_electronics_collision", "isolate_power_J29"),
        ("trill_other_electronics_collision", "isolate_Trill_C8"),
    ]:
        if not math.isclose(volume(whole), volume(part), abs_tol=1e-6):
            result.append("owner split " + whole)
    if not math.isclose(volume("isolate_rear_ports"), volume("isolate_rear_TS"), abs_tol=1e-6):
        result.append("rear split")
    # Four19mm requirements meet an opening lower edge at3.8mm, before/after explicit.2Z sweep.
    for case, height in [("isolate_rear_TS", 0.3), ("isolate_rear_TS_nominal", 0.1)]:
        want = 4 * 19 * (2.8 - 0.00002) * height
        if not math.isclose(volume(case), want, abs_tol=0.0002):
            result.append("rear arithmetic " + case)
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
                whole_geometry_clear=False,
                physical_qualified=False,
            )
        )
    )
    raise SystemExit(bool(found))
