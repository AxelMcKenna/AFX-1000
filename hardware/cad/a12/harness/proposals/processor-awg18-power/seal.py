"""Seal actual source/native/model evidence for the private E19 repair."""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy
import scipy
from verify import validate_report

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    candidates = [ROOT, ROOT / "stitch_trial"]
    reports = []
    for folder in candidates:
        for path in (folder / "generated").glob("*-grid*.json"):
            data = json.loads(path.read_text())
            if "local_simultaneous_sharing_corners" in data:
                validate_report(path, data)
                reports.append(path)
    assert len(reports) == 10
    commands = []
    for args in [
        [sys.executable, str(ROOT / "test_power.py")],
        [
            "/Users/axelmckrnna/.cache/uv/archive-v0/4FxQ2rYyAjvgsfLW/bin/ruff",
            "check",
            *[str(p) for p in ROOT.glob("*.py")],
        ],
    ]:
        p = subprocess.run(args, cwd=REPO, capture_output=True, text=True)
        commands.append(dict(args=args, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr))
        assert p.returncode == 0, commands[-1]
    checks = dict(
        verified_model_reports=len(reports),
        commands=commands,
        python=sys.version,
        numpy_version=numpy.__version__,
        scipy_version=scipy.__version__,
        physical_qualified=False,
    )
    (ROOT / "generated/checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    external = {}
    for p in [
        ROOT / "generated/native.json",
        ROOT / "generated/baseline/native.json",
        ROOT / "stitch_trial/generated/native.json",
    ]:
        native = json.loads(p.read_text())
        assert not any(native["counts"].values())
        for group in ["source_sha256", "artifact_sha256"]:
            for name, digest in native[group].items():
                source = (REPO / name).resolve()
                assert sha(source) == digest
                if not source.is_relative_to(ROOT):
                    external[name] = digest
    for name in [
        "hardware/wiring/generated/system-interconnect.json",
        "hardware/electronics/common/sexpr.py",
        "hardware/electronics/common/netlists.py",
    ]:
        external[name] = sha(REPO / name)
    snapshot = ROOT / "generated/inputs/external"
    for name, digest in external.items():
        source = REPO / name
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert sha(target) == digest, "Prior frozen dependency changed"
        else:
            shutil.copyfile(source, target)
        assert sha(source) == sha(target) == digest
    sourcehashes = {}
    artifacthashes = {}
    for p in ROOT.rglob("*"):
        if (
            not p.is_file()
            or "__pycache__" in p.parts
            or p.suffix in [".pyc", ".kicad_prl"]
            or p.name == "handoff.json"
        ):
            continue
        relative = p.relative_to(ROOT)
        group = artifacthashes if "generated" in relative.parts else sourcehashes
        group[str(relative)] = sha(p)
    report = dict(
        scope="Private four-layer finite E19 distribution repair/diagnostic; not adoption or qualification",
        preferred_private_candidate="stitch_trial/processor_carrier.kicad_pcb",
        preferred_candidate_sha256=sha(ROOT / "stitch_trial/processor_carrier.kicad_pcb"),
        actual_filled_candidate_sha256=sha(ROOT / "stitch_trial/generated/filled.kicad_pcb"),
        source_sha256=sourcehashes,
        artifact_sha256=artifacthashes,
        frozen_external_dependency_sha256=external,
        verified_source_bound_local_diagnostic_reports=10,
        local_cold_hot_cases=20,
        grid_refinement_comparisons=10,
        full_AGND_manifest_plus_Seed_ports=21,
        native_counts_each_candidate=dict(erc=0, hard_drc=0, warnings=0, parity=0, opens=0),
        S1_minimum_required_copper_um_all_four_layers=70,
        S1_minimum_required_wall_um=25,
        fabricator_stackup_material_contact_process_accepted=False,
        complete_external_network_and_endpoint_accepted=False,
        ampacity_noise_thermal_or_startup_qualified=False,
        P03_capacitance_stability_and_bipolar_startup_holds_cleared=False,
        physical_measurements_performed=0,
        physical_qualified=False,
        fabrication_released=False,
        canonical_or_52_receiver_source_modified=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "SEALED",
        report["preferred_candidate_sha256"],
        len(sourcehashes),
        "sources",
        len(artifacthashes),
        "artifacts",
        len(external),
        "external dependencies",
    )


if __name__ == "__main__":
    main()
