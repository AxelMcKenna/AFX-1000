"""Seal the rejected current-hardware J8 gauge and exact captured replay."""

import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

from .direct_j8_gauge import OUT, PDF, PDF_SHA, REPO, ROOT, sha


def checked(hashes):
    return [name for name, value in hashes.items() if sha(REPO / name) != value]


def main():
    first = json.loads((OUT / "verification.json").read_text())
    detail = json.loads((OUT / "clock-detail-review.json").read_text())
    south = json.loads((OUT / "south-complete-review.json").read_text())
    assert first["collision_failures"] == ["positive_hardware_collision", "other_returns_collision"]
    assert south["collision_failures"] == ["south_complete_inflated_positive"]
    assert south["full_declared_gauge_screen_passed"] is False
    assert all(not r[k] for r in (first, south) for k in ("stale_sources", "changed_inputs"))
    assert not detail["changed_inputs"]
    assert not checked(first["capture"]["source_sha256"])
    assert not checked(first["input_sha256"])
    assert not checked(south["input_sha256"])
    assert not checked(detail["input_sha256"])
    assert not checked(first["native_evidence_sha256"])
    assert not checked(south["native_evidence_sha256"])
    assert not checked(detail["native_evidence_sha256"])
    external_replay = Path("/private/tmp/afx-e28-direct-j8-captured-replay2")
    replay = json.loads((external_replay / "verification.json").read_text())
    assert replay["all_recorded_failures_and_controls_reproduced"]
    assert all(sha(external_replay / p) == value for p, value in replay["output_sha256"].items())
    assert replay["captured_input_index_sha256"] == sha(OUT / "captured-replay-inputs.json")
    saved_replay = OUT / "captured-replay"
    saved_replay.mkdir(exist_ok=True)
    for path in external_replay.iterdir():
        if path.is_file():
            shutil.copyfile(path, saved_replay / path.name)
    assert all(sha(saved_replay / p) == value for p, value in replay["output_sha256"].items())
    version = subprocess.run(
        ["/private/tmp/rmx-openscad-mounted/OpenSCAD.app/Contents/MacOS/OpenSCAD", "--version"],
        capture_output=True, text=True, check=True, timeout=30,
    )
    (OUT / "native-tool-version.log").write_text(version.stdout + version.stderr)
    sources = dict(first["capture"]["source_sha256"])
    interface_path = ROOT / "generated/direct-j8-ground-study/interface.json"
    interface = json.loads(interface_path.read_text())
    assert not checked(interface["source_sha256"])
    sources.update(interface["source_sha256"])
    extras = [ROOT / name for name in (
        "direct_j8_ground.py", "direct_j8_gauge.py", "direct_j8_gauge_details.py",
        "direct_j8_south_gauge.py", "seal_direct_j8.py",
        "generated/p9-u14-input-escape-work/generated/return-diagnostic.json",
    )] + [REPO / name for name in (
        "hardware/cad/a12/thermal/verify.py", "hardware/cad/a12/thermal/analyze.py",
        "hardware/cad/a12/thermal/generate.py", "tests/tooling/test_disconnect_revision28.py",
    )]
    sources.update({str(path.relative_to(REPO)): sha(path) for path in extras})
    artifact_paths = [p for p in OUT.rglob("*") if p.is_file()
                      and p.name not in ("current-study.json", "receipt-input-index.json",
                                         "direct-j8-source-and-native-inputs.tar.gz")]
    artifact_paths += [interface_path, interface_path.with_name("COHERENT-SOURCE-PLAN.md")]
    artifacts = {str(path.relative_to(REPO)): sha(path) for path in artifact_paths}
    payload = dict(sources)
    payload.update(artifacts)
    index_path = OUT / "native-inputs/receipt-input-index.json"
    index_path.write_text(json.dumps(dict(
        repo_relative_member_sha256=payload,
        external_original_PDF_not_redistributed=dict(path=str(PDF), sha256=PDF_SHA),
        physical_or_manufacturing_qualification=False,
    ), indent=2) + "\n")
    payload[str(index_path.relative_to(REPO))] = sha(index_path)
    archive = OUT / "direct-j8-source-and-native-inputs.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for name in sorted(payload):
            tar.add(REPO / name, arcname=name, recursive=False)
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        assert len(members) == len(payload)
        for member in members:
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == payload[member.name]
    assert not checked(sources) and not checked(artifacts) and not checked(payload)
    assert sha(PDF) == PDF_SHA
    canonical_sha = sha(ROOT / "rail_disconnect.kicad_pcb")
    assert canonical_sha == "2830c8874d73ae9e9a460e360979b741d2c53eaf8fece934bd65020bd4d5cf68"
    receipt = dict(
        scope="PRIVATE rejected complete-attachment screen on source-frozen U14; no adopted ground strategy",
        source_sha256=sources, artifact_sha256=artifacts,
        archive=dict(path=str(archive.relative_to(REPO)), sha256=sha(archive),
                     bytes=archive.stat().st_size, members=len(payload),
                     every_decompressed_member_byte_verified=True,
                     index_path=str(index_path.relative_to(REPO)), index_sha256=sha(index_path)),
        source_native_pcb_sha256=first["capture"]["native_pcb_sha256"],
        source_native_counts_from_immutable_U14_receipt=first["capture"]["native_pcb_counts"],
        saved_canonical_pcb_sha256_unchanged=canonical_sha,
        complete_south_attachment_current_positive_hardware_collision_mm3=
            south["native_results"]["south_complete_inflated_positive"]["volume_mm3"],
        current_hardware_complete_attachment_screen_passed=False,
        receiving_bounds_are_project_requirements_not_manufacturer_guarantees=True,
        nominal_clearance_not_substituted_for_declared_inflated_failure=True,
        captured_native_cases_replayed=len(replay["results"]),
        captured_failures_and_controls_reproduced=True,
        old_fed_EI02_wire_ground=[161,126.5], U14_P9_test_ground=[161,129.5],
        proposed_J8_force_return=[132,129.5], unchanged_J4_positive=[161,120.5],
        digital_C24_charging_and_parallel_return_graph_still_required=True,
        root_owned_corner_repair_and_whole_wire_case_support_checks_pending=True,
        no_PCB_BOM_or_other_agent_CAD_changes=True,
        external_manufacturer_PDF_sha256=PDF_SHA,
        physical_electrical_contact_thermal_startup_SOA_PDN_fabrication_qualified=False,
    )
    target = OUT / "current-study.json"
    target.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(dict(path=str(target.relative_to(REPO)), sha256=sha(target),
                          source_files=len(sources), artifact_files=len(artifacts), archive=receipt["archive"]), indent=2))


if __name__ == "__main__":
    main()
