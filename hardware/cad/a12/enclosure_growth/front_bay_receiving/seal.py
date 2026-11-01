"""Seal this scoped receiving candidate after saved actual-artifact validation."""

import json

from . import audit
from .capture import ROOT, sha


def seal():
    target = ROOT / "handoff.json"
    if target.exists():
        raise RuntimeError("FR01 is immutable; create a separate successor")
    evidence = audit.run()
    if evidence["errors"]:
        raise RuntimeError(evidence["errors"])
    replay = json.loads((ROOT / "generated/final-evidence-audit.json").read_text())
    if (
        replay["errors"]
        or replay["continuous_pairs_replayed"] != 91
        or not replay["assembly_roundtrip_replayed"]
    ):
        raise RuntimeError("Full91pair and82object artifact replay required")
    if audit.hash_errors(replay["source_sha256"]):
        raise RuntimeError("Saved final audit is stale")
    tests = json.loads((ROOT / "generated/portable-tests.json").read_text())
    if (
        tests["returncode"]
        or tests["tests"] != 21
        or audit.hash_errors(tests["source_sha256"])
        or audit.hash_errors(tests["artifact_sha256"])
    ):
        raise RuntimeError("Current full21-test terminal receipt required")
    files = {
        str(p.relative_to(ROOT)): sha(p)
        for p in sorted(ROOT.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.name != ".DS_Store"
    }
    d = dict(
        revision="FR01-front-bay-robust-rear-edge-mount-local-exits",
        files=len(files),
        files_sha256=files,
        parent="UA01-R04-PB27-sealed32/db83/dc559/HT01/AP03",
        source_is_captured_snapshot_not_latest_whole_unit=True,
        NF233_source="copied9fe0966b priorUUIDsnapshot;499nativeopens; no electrical acceptance",
        FPC84_closed_source="86e07ac4 linked by83canonicalFPidentity+exactpinmaps+C7strictsubset; nativefitused9a4parentenvelopes",
        robust34=dict(
            valid_or_independently_validated=32,
            retained_rejections=["NF_generic_mate_neighbor", "FPC_opaque_bundle_electronics"],
        ),
        raw34_projection_validator_issue_preserved=True,
        projection_validation_is_not_native_rerun=True,
        exact_XH_reference_native=4,
        mounting_native=30,
        all_mounting_requested_clear=True,
        local14_wire_exit_native=9,
        all_local_exit_requested_clear=True,
        continuous_pair_replay=91,
        portable_mutation_tests=21,
        assembly_objects=82,
        assembly_triangles=1132332,
        exact_triangle_roundtrip_replayed=True,
        four_keeper_STEP_parts_valid_and_roundtrip_verified=True,
        whole_as_one_manufacturable_part=False,
        raw_mount4_contact_facets=726,
        test_only_nominal_guard_mm=0.00002,
        all11_actual_part_meshes_byte_identical_after_guard=True,
        all_receiver_interfaces_clear=False,
        all_layer_PCB_mount_keepout_adopted=False,
        physical_qualified=False,
        electrical_unit_qualified=False,
        thermal_qualified=False,
        installed_airflow_qualified=False,
        full_wiring_qualified=False,
        fabrication_released=False,
        production_adopted=False,
    )
    target.write_text(json.dumps(d, indent=2) + "\n")
    assert all(sha(ROOT / n) == h for n, h in files.items())
    print(
        json.dumps(
            dict(files=len(files), handoff_sha256=sha(target), receiving_all_clear=False, release=False)
        )
    )


if __name__ == "__main__":
    seal()
