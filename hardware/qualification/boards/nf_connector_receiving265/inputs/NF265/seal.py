"""Freeze a review checkpoint only after actual native evidence and tests exist."""

import json
import os
import subprocess
import sys

from .analyze import ROOT, sha
from .review import review


def seal():
    assert not (ROOT / "handoff.json").exists(), "Sealed packet: create a successor"
    native = json.loads((ROOT / "generated/native-review.json").read_text())
    assert native["parts"] == 265
    assert native["ERC"] == dict(error=0, warning=2)
    assert native["pin_parity_differences"] == 0
    review()
    for report in [
        "native-review",
        "analysis",
        "equivalence",
        "LED-DC-network",
        "package-fixture/verification",
    ]:
        r = json.loads((ROOT / "generated" / f"{report}.json").read_text())
        for key in ["source_sha256", "artifact_sha256"]:
            for name, digest in r.get(key, {}).items():
                assert sha(ROOT / name) == digest, (report, name)
    for name, digest in json.loads((ROOT / "sources/manifest.json").read_text()).items():
        assert sha(ROOT / "sources" / name) == digest, name
    # Copies preserve exact helper bytes; current-live equality is checked only
    # at capture. Later repository changes do not rewrite this frozen packet.
    deps = json.loads((ROOT / "sources/build-dependencies.json").read_text())
    repo = ROOT.parents[4]
    for name, digest in deps.items():
        assert sha(repo / name) == digest, name
        assert sha(ROOT / "sources/build-dependencies" / name) == digest, name
    cmd = [
        sys.executable,
        "-m",
        "unittest",
        "hardware.qualification.boards.startup_negative_circuit.uv_recovery.test_recovery",
        "-v",
    ]
    proc = subprocess.run(
        cmd,
        cwd=repo,
        capture_output=True,
        text=True,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH="."),
        timeout=120,
    )
    (ROOT / "generated/seal-test-command.json").write_text(
        json.dumps(
            dict(command=cmd, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr), indent=2
        )
        + "\n"
    )
    assert proc.returncode == 0, proc.stderr
    assert "Ran 13 tests" in proc.stderr
    lint = (ROOT / "generated/ruff.log").read_text()
    assert "All checks passed!" in lint, lint
    files = {
        str(p.relative_to(ROOT)): sha(p)
        for p in sorted(ROOT.rglob("*"))
        if p.is_file() and p.name not in ["handoff.json", ".DS_Store"] and "__pycache__" not in p.parts
    }
    handoff = dict(
        revision="NF05R265-schematic-design-review-checkpoint",
        files_sha256=files,
        file_count=len(files),
        actual_native_parts=265,
        ERC_errors=0,
        inherited_identified_ERC_warnings=2,
        native_declared_pin_value_differences=0,
        independent_TPS3890_physical_role_differences=0,
        exported_native_fault_cone_truth_cases=16,
        portable_tests_passed=13,
        three_package_fixture_DRC_violations=0,
        actual_full_NF_PCB_created=False,
        parent261_seal_sha256=sha(ROOT / "sources/parent261/handoff.json"),
        captured_build_dependency_sha256=deps,
        actual_source_fault_path_to_existing_E28_shared_latch_implemented=False,
        complete_loaded_cutoff_upper_s=None,
        partial_power_qualified=False,
        startup_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
        release_approved=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(handoff, indent=2) + "\n")
    print(len(files), "files sealed; handoff", sha(ROOT / "handoff.json"))


if __name__ == "__main__":
    seal()
