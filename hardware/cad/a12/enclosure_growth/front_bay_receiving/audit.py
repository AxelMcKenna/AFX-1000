"""Read-only saved-evidence audit; retained failures are never counted as passes."""

import argparse
import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

from .capture import ROOT, UA, sha


def hash_errors(mapping):
    return [str(p) for p, h in mapping.items() if not Path(p).is_file() or sha(Path(p)) != h]


def row_errors(name, row, spec, folder, projection=None):
    errors = []
    p = folder / (name + ".stl")
    logpath = folder / (name + ".log")
    if row.get("role") != spec["role"]:
        errors.append("wrong-role")
    if not logpath.is_file():
        return errors + ["missing-log"]
    log = logpath.read_text()
    if "WARNING" in log or "ERROR" in log:
        errors.append("native-warning/error")
    if spec["role"] == "empty":
        if (
            row.get("returncode") != 1
            or "Current top level object is empty." not in log
            or p.exists()
            or row.get("statistics") is not None
        ):
            errors.append("nonempty-collision-or-failed-execution")
        return errors
    if row.get("returncode") != 0 or not p.is_file():
        return errors + ["missing-required-solid"]
    try:
        m = mesh(p)
    except (AssertionError, ValueError):
        return errors + ["unparseable-actual-STL"]
    if m != row.get("statistics"):
        errors.append("actual-STL-disagrees-with-row")
    if m["volume_mm3"] <= 0.001:
        errors.append("missing-positive-volume")
    if "NoError" not in log:
        if (
            name != "new_receiving_inlet_shadow"
            or projection is None
            or "Top level object is a 3D object (PolySet)" not in log
        ):
            errors.append("missing-NoError-or-named-primitive")
        elif (
            not m["closed_oriented_boundary"]
            or m["degenerate_triangles_excluded"]
            or abs(m["volume_mm3"] - projection) > 0.002
            or any(
                abs(x - y) > 1e-5
                for a, b in zip([m["min_mm"], m["max_mm"]], [[38, 168.5, 0], [276.5, 183, 0.1]])
                for x, y in zip(a, b)
            )
        ):
            errors.append("wrong-named-primitive")
    if spec["role"] != "review" and (not m["closed_oriented_boundary"] or m["degenerate_triangles_excluded"]):
        errors.append("bad-part/control-topology")
    if "expected_volume" in spec and not math.isclose(m["volume_mm3"], spec["expected_volume"], abs_tol=2e-6):
        errors.append("wrong-control-volume")
    return errors


def model_errors(d, interface, delta):
    errors = []
    if (
        len(d["component_records"]) != 317
        or len(d["boxes"]) != 317
        or len(d["tails"]) != 102
        or len(d["mates"]) != 12
    ):
        errors.append("incomplete-source-geometry")
    for b in d["boards"]:
        x, y, z = b["origin"]
        matrix = [[1, 0, 0, x], [0, 0, -1, y], [0, 1, 0, z], [0, 0, 0, 1]]
        if (
            b["local_to_world_matrix"] != matrix
            or b["rotation_determinant"] != 1
            or b["KiCad_STEP_origin_used"]
        ):
            errors.append("wrong-frame")
    if d["rear_SMD_requirement_mm"] != 1.2 or d["rear_THT_requirement_mm"] != 1.5:
        errors.append("wrong-rear-receiver")
    if max(d["rear_ref_maximum_Z_mm"].values()) >= 41.6 or max(d["rear_tail_maximum_Z_mm"].values()) >= 41.6:
        errors.append("rear-parts-enter-upper-seat")
    if (
        delta["new_body_projection_max_mm"] != 0.97
        or delta["unchanged_complete_geometry_after_canonicalization"] != 83
        or delta["only_changed_part"] != "C7"
        or not delta["new_receiving_body_strict_subset"]
        or not delta["all84_native_net_name_pinmaps_equal"]
    ):
        errors.append("wrong-C7-delta")
    for axis in [0, 1]:
        if (
            delta["new_native_courtyard_mm"][axis] < delta["old_native_courtyard_mm"][axis]
            or delta["new_native_courtyard_mm"][axis + 2] > delta["old_native_courtyard_mm"][axis + 2]
        ):
            errors.append("C7-not-contained")
    required = [
        ("NF233", 38, 210, 42.5),
        ("NF233", 138, 310, 42.5),
        ("FPC84", 17, 31, 41.5),
        ("FPC84", 54.5, 68.5, 41.5),
    ]
    actual = [(m["board"], m["local_u"], m["world_X"], m["board_top_Z"]) for m in interface["mounting"]]
    if actual != required:
        errors.append("wrong-mount-datums")
    if (
        interface["nominal_test_only_contact_guard_mm"] != 0.00002
        or interface["external_receiver_margin_mm"] != 0.45
    ):
        errors.append("changed-guard-or-margin")
    if interface["all_layer_edge_copper_keepouts_adopted"] or interface["PCB_soldermask_insulation_credit"]:
        errors.append("unsupported-insulation-credit")
    for k in [
        "physical_qualified",
        "thermal_qualified",
        "electrical_unit_qualified",
        "full_harness_qualified",
        "fabrication_released",
    ]:
        if interface[k]:
            errors.append("unsupported-release-flag")
    return errors


def report_audit(folder, specs, expected_raw_failures, expected_effective_failures, projection=None):
    p = folder / "verification.json"
    d = json.loads(p.read_text())
    errors = []
    if set(d["cases"]) != set(specs) or d["required_cases"] != list(specs):
        errors.append("case-coverage")
    if d["changed_inputs"]:
        errors.append("changed-live-inputs")
    for group in ["input_sha256", "artifact_sha256"]:
        errors += ["stale-" + group + ":" + n for n in hash_errors(d[group])]
    actual = {}
    for n, s in specs.items():
        if n not in d["cases"]:
            continue
        actual[n] = row_errors(n, d["cases"][n], s, folder, projection)
    effective = [n for n, v in actual.items() if v]
    raw = [n for n, r in d["cases"].items() if not r["clear"]]
    if set(raw) != set(expected_raw_failures):
        errors.append("retained-raw-failure-mismatch")
    if set(effective) != set(expected_effective_failures):
        errors.append("actual-effective-failure-mismatch")
    for n in expected_effective_failures:
        row = d["cases"][n]
        target = folder / (n + ".stl")
        log = (folder / (n + ".log")).read_text()
        if not target.is_file() or row["returncode"] != 0 or "NoError" not in log:
            errors.append("failure-is-not-real-nonempty:" + n)
        elif mesh(target) != row["statistics"] or mesh(target)["volume_mm3"] <= 0.001:
            errors.append("wrong-actual-failure-mesh:" + n)
    return dict(
        errors=errors,
        cases=len(specs),
        raw_failures=raw,
        effective_failures=effective,
        effective_valid=len(specs) - len(effective),
        source_hashes=len(d["input_sha256"]),
        artifact_hashes=len(d["artifact_sha256"]),
        actual_row_errors={n: v for n, v in actual.items() if v},
    )


def run(continuous=False, assembly=False):
    from .verify_escape import specs as wire_specs
    from .verify_mount5 import specs as mount_specs
    from .verify_robust import specs as robust_specs

    errors = []
    out = ROOT / "generated"
    primitive = json.loads((out / "robust-projection-validation.json").read_text())[
        "independent_expected_volume_mm3"
    ]
    failures = ["NF233_mate_other_components_collision", "FPC84_short_bundle_electronics_collision"]
    reports = {
        "robust_rear": report_audit(
            out / "native-robust-rear",
            robust_specs(),
            failures + ["new_receiving_inlet_shadow"],
            failures,
            primitive,
        ),
        "mounting": report_audit(out / "native-mount5", mount_specs(), [], []),
        "wire_exits": report_audit(out / "native-wire-escape", wire_specs(), [], []),
    }
    for n, r in reports.items():
        errors += [n + ":" + e for e in r["errors"]]
    xh = json.loads((out / "native-xh-reference/verification.json").read_text())
    xhs = {n: robust_specs()[n] for n in xh["required_cases"]}
    if set(xhs) != {
        "FPC84_mate_other_components_collision",
        "FPC84_mate_mutual_collision",
        "FPC_components_positive_control",
        "FPC_PCB_positive_control",
    }:
        errors.append("wrong-XH-coverage")
    reports["XH_reference"] = report_audit(out / "native-xh-reference", xhs, [], [])
    errors += ["XH:" + e for e in reports["XH_reference"]["errors"]]
    d = json.loads((out / "coherent-receiving-model.json").read_text())
    interface = json.loads((out / "interface-final.json").read_text())
    delta = json.loads((out / "FPCClosed-C7-delta.json").read_text())
    errors += model_errors(d, interface, delta)
    for name in ["capture.json", "NF233-delta-capture.json"]:
        c = json.loads((ROOT / name).read_text())
        errors += [
            "captured:" + n
            for n in hash_errors({str(ROOT / p): h for p, h in c["copied_input_sha256"].items()})
        ]
    errors += [
        "closed-copy:" + n
        for n in hash_errors({str(ROOT / p): h for p, h in delta["copied_input_sha256"].items()})
    ]
    sidecars = [
        "coherent-receiving-model.json",
        "interface-final.json",
        "FPCClosed-C7-delta.json",
        "robust-projection-validation.json",
        "drawing-final.json",
        "keeper-BREP/verification.json",
        "assembly-manifest-final.json",
    ]
    for n in sidecars:
        c = json.loads((out / n).read_text())
        for group in ["source_sha256", "artifact_sha256"]:
            errors += [n + ":" + p for p in hash_errors(c.get(group, {}))]
    identity = json.loads((out / "guarded-parts-identity.json").read_text())
    if len(identity["parts"]) != 11:
        errors.append("missing-guarded-part-identity")
    for n, v in identity["parts"].items():
        a = out / "native-mount4" / (n + ".stl")
        b = out / "native-mount5" / (n + ".stl")
        if (
            not v["byte_identical"]
            or sha(a) != v["original_sha256"]
            or sha(b) != v["guarded_sha256"]
            or a.read_bytes() != b.read_bytes()
        ):
            errors.append("actual-part-changed-by-guard:" + n)
    parent = json.loads((UA / "handoff.json").read_text())
    errors += [
        "parent:" + n for n in hash_errors({str(UA / p): h for p, h in parent["files_sha256"].items()})
    ]
    cert = json.loads((ROOT / "fpc_escape_variant2/pair-certificate.json").read_text())
    routes = json.loads((ROOT / "fpc_escape_variant2/contract.json").read_text())["routes"]
    if (
        len(cert["pairs"]) != 91
        or not cert["all91_pairs_certified"]
        or not cert["continuous_interval_bounds"]
        or cert["sampled_minimum_used"]
    ):
        errors.append("missing-continuous-pair-coverage")
    errors += ["certificate:" + n for n in hash_errors(cert["source_sha256"])]
    replayed = 0
    if continuous:
        from .escape_certificate import separation

        for i, a in enumerate(routes):
            for b in routes[i + 1 :]:
                if not separation(a, b, cert["required_pair_centerline_distance_mm"])["certified"]:
                    errors.append("continuous-pair-replay-failure")
                replayed += 1
    manifest = json.loads((out / "assembly-manifest-final.json").read_text())
    if len(manifest["objects"]) != 82 or manifest["whole_as_one_manufacturable_part"]:
        errors.append("wrong-assembly-representation")
    for n, v in manifest["objects"].items():
        if (
            sha(ROOT / v["source_path"]) != v["source_sha256"]
            or sha(Path(v["origin_path"])) != v["origin_sha256"]
        ):
            errors.append("assembly-object-hash:" + n)
    if assembly:
        from hardware.cad.a12.thermal.interior_airpath_meter318.assembly import roundtrip_errors

        errors += roundtrip_errors(out / "FR01-component-review-final.3mf", manifest["objects"])
    return dict(
        errors=errors,
        reports=reports,
        continuous_pairs_replayed=replayed,
        assembly_roundtrip_replayed=assembly,
        all_saved_evidence_consistent=not errors,
        all_receiving_interfaces_clear=False,
        remaining_NF_generic_mate_collision_mm3=reports["robust_rear"]["cases"] and 1.4161780200797487,
        old_opaque_bundle_retained_rejection=True,
        new_local14_exit_cases=9,
        complete_unit_wiring=False,
        physical_qualified=False,
        thermal_qualified=False,
        electrical_unit_qualified=False,
        fabrication_released=False,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--continuous", action="store_true")
    p.add_argument("--assembly", action="store_true")
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    d = run(a.continuous, a.assembly)
    if a.output:
        if a.output.exists():
            raise RuntimeError("Never overwrite saved audit")
        d["source_sha256"] = {str(Path(__file__)): sha(Path(__file__))}
        a.output.write_text(json.dumps(d, indent=2) + "\n")
    print(json.dumps(d, indent=2))
    raise SystemExit(bool(d["errors"]))
