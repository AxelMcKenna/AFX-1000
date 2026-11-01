"""Seal actual closed private candidate and all retained local evidence."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
assert not (ROOT / "handoff.json").exists(), "Preserve sealed source; use successor"
report = json.loads((ROOT / "generated/final-review.json").read_text())
for name, digest in report["sources_sha256"].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
assert all(
    report[n] == 0 for n in ["schematic_ERC_errors", "PCB_hard_DRC", "warnings", "opens", "schematic_parity"]
)
assert (
    "Ran 9 tests" in (ROOT / "generated/tests.log").read_text()
    and "\nOK\n" in (ROOT / "generated/tests.log").read_text()
)
manifest = {
    str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(ROOT.rglob("*"))
    if p.is_file()
    and "__pycache__" not in p.parts
    and p.suffix not in [".pyc", ".kicad_prl"]
    and p.name != "handoff.json"
}
record = dict(
    revision="FPC01-private-routed-composite",
    pcb_sha256=manifest["fan_power_health.kicad_pcb"],
    parts=84,
    ERC=0,
    hard_DRC=0,
    warnings=0,
    parity=0,
    opens=0,
    portable_tests=9,
    native_geometry_checks=True,
    actual_pose_mm=[14, 180.5, 3.5],
    receiving_outline_mm=[66, 38],
    files_sha256=manifest,
    parents_unchanged=True,
    physical_qualified=False,
    PDN_qualified=False,
    noise_qualified=False,
    installed_cooling_qualified=False,
    fabrication_released=False,
    production_released=False,
)
(ROOT / "handoff.json").write_text(json.dumps(record, indent=2) + "\n")
print(
    len(manifest),
    "files; PCB",
    record["pcb_sha256"],
    "handoff",
    hashlib.sha256((ROOT / "handoff.json").read_bytes()).hexdigest(),
)
