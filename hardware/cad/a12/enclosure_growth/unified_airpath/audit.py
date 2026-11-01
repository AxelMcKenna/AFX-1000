"""Read-only saved-evidence gate; a blocked guide is NEVER renamed a pass."""

import json
from pathlib import Path

from .ground_route import ROOT, sha
from .verify_review import specs as review_specs
from .verify_service import specs as service_specs
from .verify_v6 import row_errors
from .verify_v6 import specs as main_specs

BLOCKED = "H9_openlid_controls_collision"


def report_errors(data, definitions, folder, blocked=False):
    bad = []
    if set(data.get("cases", {})) != set(definitions) or data.get("required_cases") != list(definitions):
        bad.append("required-case-coverage")
    if not data.get("complete_set"):
        bad.append("incomplete-native-set")
    if data.get("changed_inputs"):
        bad.append("changed-native-inputs")
    for n, spec in definitions.items():
        row = data.get("cases", {}).get(n)
        if row is None:
            continue
        if row.get("role") != spec["role"]:
            bad.append("wrong-role:" + n)
        actual = row_errors(n, row, spec, folder)
        if blocked and n == BLOCKED:
            if (
                actual != ["actual-nonempty-or-failed-execution"]
                or row.get("clear")
                or row.get("errors") != actual
            ):
                bad.append("blocked-guide-state-not-preserved")
            witness = row_errors(n, row, dict(role="witness"), folder)
            if witness:
                bad.extend(n + ":" + e for e in witness)
        elif actual or row.get("errors") or not row.get("clear"):
            bad.extend([n + ":" + e for e in actual] or ["failed-or-forged-row:" + n])
    expected_clear = not blocked
    if data.get("all_requested_clear") is not expected_clear:
        bad.append("wrong-aggregate-status")
    for k in [
        "physical_qualified",
        "thermal_qualified",
        "electrical_qualified",
        "fabrication_released",
        "full_wiring_qualified",
        "actual_NF_FH_boards_adopted",
        "latest_E28_development_adopted",
    ]:
        if data.get(k) is not False:
            bad.append("unsupported-promotion:" + k)
    if data.get("E28_electrical_opens") != 32:
        bad.append("wrong-E28-source-scope")
    return bad


def contract_errors(g, ret, pb):
    bad = []
    required = {
        "source_face_mm": [161, 129.5, 6.62],
        "receiver_face_mm": [188, 104, 8.1],
        "wire_insulation_OD_max_mm": 1.7526,
        "core_receiving_OD_mm": 1.4,
        "independent_position_allowance_mm": 0.65,
        "separate_clearance_mm": 0.25,
        "separate_geometry_reserve_mm": 0.005,
        "minimum_prospective_native_bore_mm": 2.1,
        "relative_bore_centering_mm": 0.3,
        "destination_stub_length_mm": 7,
        "above_face_strip_length_mm": 3.1,
        "required_true_radius_mm": 9.6393,
    }
    for k, v in required.items():
        if g.get(k) != v:
            bad.append("changed-wire-contract:" + k)
    cert = g.get("continuous_radius_certificate", {})
    if (
        not cert.get("certified")
        or cert.get("radius_lower_mm", 0) <= 9.6393
        or g.get("whole_radius_lower_mm", 0) <= 9.6393
    ):
        bad.append("uncertified-continuous-radius")
    if (
        not g.get("all_unit_tangent_joins_C1")
        or g.get("length_upper_mm_including_max_boardtails", 1000) >= 200
    ):
        bad.append("wire-join-length-contract")
    for name, b in ret["bars"].items():
        if b["minimum_normal_section_mm2"] < 20:
            bad.append("return-area:" + name)
    if min(pb["analytical_minimum_area_mm2"].values()) < 6:
        bad.append("positive-area")
    return bad


def hashes_errors(mapping):
    return ["stale-or-missing:" + n for n, h in mapping.items() if not Path(n).is_file() or sha(Path(n)) != h]


def errors():
    bad = []
    out = ROOT / "generated"
    proofs = {}
    for name, defs, blocked in [
        ("current-native", main_specs(), True),
        ("service-state-native", service_specs(), False),
        ("review-native", review_specs(), False),
    ]:
        folder = out / name
        d = json.loads((folder / "verification.json").read_text())
        proofs[name] = d
        bad += report_errors(d, defs, folder, blocked)
        for group in ["input_sha256", "artifact_sha256"]:
            bad += hashes_errors(d[group])
    main = proofs["current-native"]["cases"][BLOCKED]["statistics"]
    owner = proofs["service-state-native"]["cases"]["H9_guide_owner_geometry"]["statistics"]
    if main != owner:
        bad.append("guide-owner-geometry-not-exact")
    for p in [out / "base-BREP-verification.json", out / "assembly-manifest-corrected.json"]:
        d = json.loads(p.read_text())
        for group in ["source_sha256", "artifact_sha256"]:
            bad += hashes_errors(d[group])
    g = json.loads((out / "ground-route.json").read_text())
    ret = json.loads((ROOT / "return_variant3/generated/geometry.json").read_text())
    pb = json.loads((ROOT / "positive_variant27/generated/geometry.json").read_text())
    bad += contract_errors(g, ret, pb)
    for n, h in g["source_sha256"].items():
        p = Path(n)
        if not p.is_absolute():
            p = Path.cwd() / p
        if not p.is_file() or sha(p) != h:
            bad.append("stale-route-source:" + n)
    audit = json.loads((out / "production-mesh-audit.json").read_text())
    if len(audit["parts"]) != 52 or not audit["all_actual_part_meshes_strict"]:
        bad.append("incomplete-part-mesh-gate")
    for n, v in audit["parts"].items():
        s = v["statistics"]
        if (
            sha(Path(v["source_path"])) != v["source_sha256"]
            or not s["closed_oriented_boundary"]
            or s["degenerate_triangles_excluded"]
            or s["volume_mm3"] <= 0.001
        ):
            bad.append("bad-actual-part:" + n)
    from hardware.cad.a12.thermal.interior_airpath_meter318.assembly import roundtrip_errors

    manifest = json.loads((out / "assembly-manifest-corrected.json").read_text())
    bad += roundtrip_errors(out / "UA01-component-review.3mf", manifest["objects"])
    if len(manifest["objects"]) != 70 or manifest["whole_as_one_manufacturable_part"]:
        bad.append("incomplete-or-fused-review")
    for v in manifest["objects"].values():
        if (
            sha(ROOT / v["source_path"]) != v["source_sha256"]
            or sha(Path(v["origin_path"])) != v["origin_sha256"]
        ):
            bad.append("stale-review-object")
    return bad


if __name__ == "__main__":
    result = errors()
    print(
        json.dumps(
            dict(
                errors=result,
                saved_scoped_evidence_valid=not result,
                main_42=dict(pass_count=41, blocked_guide_access=1),
                new_service_8_pass=True,
                review_exports=2,
                physical_qualified=False,
                thermal_qualified=False,
            )
        )
    )
    raise SystemExit(bool(result))
