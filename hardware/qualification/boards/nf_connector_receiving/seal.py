"""Freeze the bounded NC01 preselection, not production connector adoption."""

import json
import subprocess
from pathlib import Path

from . import audit
from .study import ROOT, sha


def seal():
    target = ROOT / "handoff.json"
    if target.exists():
        raise RuntimeError("Use a separate successor; NC01 is immutable")
    d = audit.run()
    if d["errors"]:
        raise RuntimeError(d["errors"])
    command = [
        "python3",
        "-S",
        "-m",
        "unittest",
        "hardware.qualification.boards.nf_connector_receiving.test_study",
    ]
    p = subprocess.run(command, capture_output=True, text=True)
    log = ROOT / "generated/portable-tests.log"
    if log.exists():
        raise RuntimeError("New test receipt required")
    log.write_text(p.stdout + p.stderr)
    if p.returncode or "Ran 12 tests" not in log.read_text() or not log.read_text().rstrip().endswith("OK"):
        raise RuntimeError("Complete12-test terminal pass required")
    d["tests"] = dict(command=command, returncode=p.returncode, count=12, raw_log_sha256=sha(log))
    d["source_sha256"] = {str(p): sha(p) for p in [Path(__file__), ROOT / "audit.py", ROOT / "test_study.py"]}
    (ROOT / "generated/evidence-audit.json").write_text(json.dumps(d, indent=2) + "\n")
    files = {
        str(p.relative_to(ROOT)): sha(p)
        for p in sorted(ROOT.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.name != ".DS_Store"
    }
    handoff = dict(
        revision="NC01-249-parent-control-connector-local-exit-and-force-options",
        files=len(files),
        files_sha256=files,
        scope="Preselection/source/library/native-parser/localfanout only; not a PCB or fullunit harness",
        parent_NF05S_parts=249,
        later_261_split_J6_adopted=False,
        local_control_wire_exits=30,
        continuous_pair_certificates_replayed=435,
        native_parser_footprints=2,
        native_parser_pads=32,
        portable_tests=12,
        PHD_PH_series_force_contacts_rejected=True,
        actual_force_strain_geometry_complete=False,
        source_pin_contract_is_historical_pending_final_electrical_owner=True,
        canonical_or_sealed_sources_edited=False,
        physical_qualified=False,
        electrical_qualified=False,
        installed_full_harness_qualified=False,
        PCB_fabrication_released=False,
        production_connector_adopted=False,
    )
    target.write_text(json.dumps(handoff, indent=2) + "\n")
    assert all(sha(ROOT / n) == h for n, h in files.items())
    print(json.dumps(dict(files=len(files), handoff_sha256=sha(target), production_adopted=False)))


if __name__ == "__main__":
    seal()
