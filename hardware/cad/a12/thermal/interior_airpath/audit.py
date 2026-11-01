"""Independent saved-source/native/assembly contracts; no CAD tools executed."""

import json
import math
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base_pot.stage import closure

from .assembly import GROUPS, NS, digest, triangles
from .mating import CONTROLS, EMPTY
from .plan import plan
from .seated_stage import CONTROL_GUARD, EXTRA, GUARDED
from .stage import FI, MODEL, OUT, REPO, ROOT, sha
from .verify import row_errors, specs


def design_errors(data):
    bad = []
    expected = plan()
    for k, v in expected.items():
        if data.get(k) != v:
            bad.append("design-requirement-changed:" + k)
    if (
        data["inlet"]["nominal_total_net_mm2"] < 2500
        or data["exhaust"]["nominal_net_mm2"] < 2500
        or data["guard"]["nominal_net_each_mm2"] < 800
    ):
        bad.append("insufficient-declared-net-area")
    if data["fan"]["hole_min"] != 4.0:
        bad.append("Sunon-minimum-hole-fact-lost")
    if not math.isclose(
        data["fan"]["nominal_CAD_thickness"] + data["fan"]["nominal_CAD_matched_shim"], 12.5, abs_tol=1e-10
    ):
        bad.append("unmatched-fan-shim-stack")
    for k in [
        "actual_flow_split_verified",
        "fan_face_contact_and_rotor_dynamics_qualified",
        "physical_qualified",
        "thermal_qualified",
        "structural_qualified",
        "fabrication_released",
        "newer_board_wire_candidates_adopted",
    ]:
        if data[k] is not False:
            bad.append("unsupported-approval:" + k)
    return bad


def header_errors(proof, definitions, selector):
    bad = []
    if list(proof["cases"]) != list(definitions) or proof["required_cases"] != list(definitions):
        bad.append("missing/reordered-native-coverage")
    if not proof["all_requested_clear"] or proof["changed_inputs"]:
        bad.append("failed-or-stale-native-proof")
    for n, row in proof["cases"].items():
        if n not in definitions:
            bad.append("unknown-case:" + n)
            continue
        if row["role"] != definitions[n]["role"] or not row["clear"] or row["errors"]:
            bad.append("failed-role-or-result:" + n)
        if row["command"].count(selector + "=" + json.dumps(n)) != 1:
            bad.append("wrong-actual-native-selector:" + n)
    return bad


def history_errors():
    bad = []
    for p in (ROOT / "history").rglob("reconstruction-map.json"):
        d = json.loads(p.read_text())
        receipt = Path(d["original_receipt"])
        if sha(receipt) != d["original_receipt_sha256"]:
            bad.append("historical-receipt-changed:" + str(p))
        r = json.loads(receipt.read_text())
        if set(d["input_bytes"]) != set(r["input_sha256"]):
            bad.append("incomplete-historical-input-capture:" + str(p))
        for n, row in d["input_bytes"].items():
            if row["sha256"] != r["input_sha256"][n] or sha(ROOT / row["copy"]) != row["sha256"]:
                bad.append("historical-source-copy-changed:" + n)
        for n, h in r["artifact_sha256"].items():
            if sha(Path(n)) != h:
                bad.append("historical-native-artifact-changed:" + n)
    infra = json.loads((OUT / "repaired-preflight/verification.json").read_text())
    if len(infra["cases"]) != 6 or infra["all_requested_clear"]:
        bad.append("missing-or-falsely-passed-daemon-failure")
    for n, row in infra["cases"].items():
        lp = OUT / "repaired-preflight" / (n + ".log")
        if (
            "docker.sock" not in lp.read_text()
            or "no such file or directory" not in lp.read_text()
            or (lp.with_suffix(".stl")).exists()
            or row["returncode"] != 1
        ):
            bad.append("daemon-failure-not-actual-no-CAD:" + n)
    original = json.loads((OUT / "raw-port-boundary-audit.json").read_text())
    mapping = json.loads((ROOT / "history/root-approved-port-audit/source-reconstruction.json").read_text())
    if sha(OUT / "raw-port-boundary-audit.json") != mapping["report_sha256"]:
        bad.append("raw-port-audit-changed")
    for n, row in mapping["source_aliases"].items():
        if sha(ROOT / row["copy"]) != row["sha256"] or original["source_sha256"][n] != row["sha256"]:
            bad.append("raw-port-audit-source-not-reconstructible:" + n)
    return bad


def assembly_errors(manifest):
    bad = []
    path = OUT / "AP02-complete-modeled-component-review.3mf"
    if set(manifest["objects"]) != set(GROUPS):
        return ["missing-assembly-family"]
    with zipfile.ZipFile(path) as z:
        xml = ET.fromstring(z.read("3D/3dmodel.model"))
    objects = xml.findall(f"{{{NS}}}resources/{{{NS}}}object")
    items = xml.findall(f"{{{NS}}}build/{{{NS}}}item")
    if (
        len(objects) != 21
        or {o.attrib["name"] for o in objects} != set(GROUPS)
        or len(items) != 21
        or any("transform" in p.attrib for p in items)
    ):
        bad.append("incomplete-or-repositioned-3MF")
    for o in objects:
        n = o.attrib["name"]
        expected = manifest["objects"][n]
        m = o.find(f"{{{NS}}}mesh")
        vs = [tuple(float(v.attrib[k]) for k in ["x", "y", "z"]) for v in m.find(f"{{{NS}}}vertices")]
        ts = [tuple(vs[int(t.attrib[k])] for k in ["v1", "v2", "v3"]) for t in m.find(f"{{{NS}}}triangles")]
        source = ROOT / expected["source_path"]
        if (
            len(ts) != expected["triangles"]
            or digest(ts) != expected["triangle_coordinate_digest"]
            or sha(source) != expected["source_sha256"]
            or digest(triangles(source)) != expected["triangle_coordinate_digest"]
        ):
            bad.append("3MF-source-faces-altered:" + n)
    if (
        manifest["deleted_repaired_reoriented_or_decimated_faces"] != 0
        or manifest["whole_as_one_manufacturable_part"]
        or manifest["full_operating_wiring_or_physical_unit_complete"]
    ):
        bad.append("false-assembly-physical-promotion")
    return bad


def guard_errors(contract, guard_text, fixture_text):
    bad = []
    if contract["test_only_guard_mm"] != 0.00002 or not re.search(r"\bmg\s*=\s*\.00002\s*;", guard_text):
        bad.append("wrong-numeric-seat-guard")
    if (
        contract["guarded_empty_cases"] != GUARDED
        or contract["positive_controls_use_the_same_guard"] != CONTROL_GUARD
        or contract["additional_radial_and_axial_controls"] != EXTRA
    ):
        bad.append("missing-guarded-counterexample")
    raw = dict(re.findall(r'^if\(mate_case=="([^\"]+)"\)(.*)$', (ROOT / "mating.scad").read_text(), re.M))
    seated = dict(re.findall(r'^if\(mate_seated_case=="([^\"]+)"\)(.*)$', fixture_text, re.M))
    for n, branch in raw.items():
        g = n if n in GUARDED else CONTROL_GUARD.get(n)
        expected = ("difference(){" + branch + "mate_guard_for(" + json.dumps(g) + ");}") if g else branch
        if seated.get(n) != expected:
            bad.append("raw-branch-or-guard-control-changed:" + n)
    if contract["raw_source_or_actual_AP02_parts_modified"] or contract["deliberate_penetration_mm"] != 0.02:
        bad.append("part-edit-or-weakened-counterexample")
    return bad


def base_report_errors(data):
    expected = data["parent_volume_mm3"] - 108 * 42 - 6.2 * plan()["inlet"]["nominal_total_net_mm2"]
    if (
        not all(data[k] for k in ["new_valid", "roundtrip_valid"])
        or data["new_solids"] != 1
        or data["roundtrip_solids"] != 1
    ):
        return ["invalid-base-STEP"]
    if abs(data["exact_curve_new_volume_mm3"] - expected) > 0.001:
        return ["base-mass-balance-mismatch"]
    if abs(data["exact_curve_new_volume_mm3"] - data["native_faceted_volume_mm3"]) > 5:
        return ["base-CAD-native-mismatch"]
    return []


def errors():
    bad = []
    capture = json.loads((ROOT / "capture.json").read_text())
    for row in capture["parents"].values():
        folder = Path(row["folder"])
        if sha(folder / "handoff.json") != row["handoff_sha256"]:
            bad.append("parent-seal-changed:" + str(folder))
        h = json.loads((folder / "handoff.json").read_text())
        mapping = h.get("files_sha256", h.get("sha256"))
        for n, v in mapping.items():
            p = folder / n if (folder / n).exists() else REPO / n
            if sha(p) != v:
                bad.append("parent-source-changed:" + n)
    for n, h in capture["private_model_sha256"].items():
        if sha(ROOT / n) != h:
            bad.append("captured-model-changed:" + n)
    for p in closure(OUT / "checks.scad"):
        if not p.is_relative_to(ROOT):
            bad.append("uncaptured-literal-SCAD-dependency:" + str(p))
    design = json.loads((OUT / "analysis.json").read_text())
    bad += design_errors(design)
    for p, prefix in [
        (MODEL / "parts.scad", "eb_part_pins="),
        (MODEL / "context/hardware/cad/a12/thermal/generated/thermal-base.scad", "thermal_pins="),
    ]:
        values = json.loads(
            next(l for l in p.read_text().splitlines() if l.startswith(prefix)).split("=", 1)[1].rstrip(";")
        )
        if values != design["pins"]["kept_centres"] or len(values) != 918:
            bad.append("wrong-actual-pin-field:" + str(p))
    main = json.loads((OUT / "current-native/verification.json").read_text())
    definitions = specs()
    bad += header_errors(main, definitions, "ap_case")
    if not main["complete_set"]:
        bad.append("falsely-incomplete-main-proof")
    for n, row in main["cases"].items():
        bad += [n + ":" + e for e in row_errors(n, row, definitions[n], OUT / "current-native")]
    definitions = {
        n: dict(role="empty" if n in EMPTY else "control" if n in CONTROLS else "witness")
        for n in EMPTY + CONTROLS + EXTRA
    }
    for n in CONTROLS:
        definitions[n]["expected_volume"] = 0.0016
    seated = json.loads((OUT / "mating-seated/verification.json").read_text())
    bad += header_errors(seated, definitions, "mate_seated_case")
    for n, row in seated["cases"].items():
        bad += [n + ":" + e for e in row_errors(n, row, definitions[n], OUT / "mating-seated")]
    for proof in [main, seated]:
        for kind in ["input_sha256", "artifact_sha256"]:
            for n, h in proof[kind].items():
                if sha(Path(n)) != h:
                    bad.append("current-native-source/artifact-changed:" + n)
    contract = json.loads((OUT / "mating-seat-contract.json").read_text())
    bad += guard_errors(
        contract, (ROOT / "mating_guards.scad").read_text(), (OUT / "mating-seated.scad").read_text()
    )
    for n, h in contract["source_sha256"].items():
        if sha(ROOT / n) != h:
            bad.append("seat-contract-source-changed:" + n)
    if sha(OUT / "mating-seated.scad") != contract["fixture_sha256"]:
        bad.append("seat-fixture-changed")
    bad += history_errors()
    for filename in [
        "fan-geometry.json",
        "common-land.json",
        "base-BREP-verification.json",
        "drawing-provenance.json",
        "channel-geometry.json",
        "assembly-manifest.json",
    ]:
        d = json.loads((OUT / filename).read_text())
        aliases = {
            "parent_BASE_STEP": FI / "generated/AFX-FI01-BASE.step",
            "current_native_proof": OUT / "current-native/verification.json",
        }
        for n, h in d.get("source_sha256", {}).items():
            if sha(aliases.get(n, ROOT / n)) != h:
                bad.append(filename + ":source-changed:" + n)
        for n, h in d.get("artifact_sha256", {}).items():
            if sha(OUT / n) != h:
                bad.append(filename + ":artifact-changed:" + n)
    common = json.loads((OUT / "common-land.json").read_text())
    if (
        common["missing_bottom_volume_for1mm_profile_mm3"] > 1e-6
        or common["missing_top_volume_for1mm_profile_mm3"] > 1e-6
    ):
        bad.append("shim-lacks-actual-nominal-endface-support")
    brep = json.loads((OUT / "base-BREP-verification.json").read_text())
    bad += base_report_errors(brep)
    bad += assembly_errors(json.loads((OUT / "assembly-manifest.json").read_text()))
    from .pressure_rejection import report

    saved_pressure = json.loads((OUT / "pressure-rejection.json").read_text())
    if saved_pressure != report() or not saved_pressure["nominal125_base_target_rejected"]:
        bad.append("lost-or-changed-pressure-rejection")
    return bad


if __name__ == "__main__":
    result = errors()
    print(json.dumps(dict(errors=result)))
    raise SystemExit(bool(result))
