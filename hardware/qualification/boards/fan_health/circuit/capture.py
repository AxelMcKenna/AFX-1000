"""Capture existing native/software/contracts without changing any parent seal."""

import json
import shutil

from hardware.qualification.boards.fan_health.circuit.design import FP, NF, REPO, ROOT, sha


def capture():
    fw = ROOT.parent
    verification = json.loads((fw / "generated/verification.json").read_text())
    paths = [fw / "generated/verification.json", fw / "README.md", fw / "temperature.py"]
    paths += [fw / k for section in ("inputs", "outputs") for k in verification[section]]
    paths += [
        FP / k for k in ("design.py", "components.json", "generated/analysis.json", "generated/netlist.xml")
    ]
    paths += [
        NF / k for k in ("handoff.json", "generated/analysis.json", "components.json", "integration.json")
    ]
    paths += [
        REPO / k
        for k in (
            "hardware/electronics/common/flat_schematic.py",
            "hardware/electronics/common/netlists.py",
            "hardware/electronics/common/symbols.py",
            "hardware/electronics/common/sexpr.py",
            "hardware/electronics/power_distribution/p03/candidates/aux-u10-combined/components.json",
            "hardware/electronics/power_distribution/p03/candidates/aux-u10-combined/generated/netlist.xml",
            "hardware/electronics/rail_disconnect/revision28/components.json",
            "hardware/electronics/rail_disconnect/revision28/rail_disconnect.kicad_sch",
        )
    ]
    paths = sorted(set(paths))
    before = {str(p.relative_to(REPO)): sha(p) for p in paths}
    for section in ("inputs", "outputs"):
        for rel, digest in verification[section].items():
            if sha(fw / rel) != digest:
                raise ValueError("Actual firmware receipt mismatch: " + rel)
    for p in paths:
        target = ROOT / "sources/repository" / p.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and sha(target) != sha(p):
            raise ValueError("Preserved capture changed: " + str(p))
        if not target.exists():
            shutil.copy2(p, target)
    if before != {str(p.relative_to(REPO)): sha(p) for p in paths}:
        raise ValueError("Sources changed during capture")
    result = dict(
        repository_inputs_sha256=before,
        actual_parent_firmware_claims_verified_against_named_source_and_artifact_bytes=True,
        firmware_host_result=verification["host_result"],
        firmware_text_bytes=verification["text_bytes"],
        firmware_bss_bytes=verification["bss_bytes"],
        captured_inputs_are_historical_and_NOT_automatic_currentness_claims=True,
    )
    (ROOT / "generated/captured-inputs.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Captured and bracket-checked", len(paths), "existing inputs;", verification["host_result"])


if __name__ == "__main__":
    capture()
