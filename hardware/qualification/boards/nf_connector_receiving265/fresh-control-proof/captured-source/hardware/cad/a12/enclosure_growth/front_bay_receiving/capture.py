"""One-shot immutable source capture, without changing parent scenes or PCBs."""

import json
import shutil
from pathlib import Path

from hardware.cad.a12.enclosure_growth.unified_airpath.ground_route import sha

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
UA = ROOT.parent / "unified_airpath"
NF = REPO / "hardware/qualification/boards/startup_negative_circuit/placement"
FPC = REPO / "hardware/qualification/boards/fan_health/composite/generated/receiving-placement-66x38"


def capture():
    target = ROOT / "capture.json"
    if target.exists() or (ROOT / "handoff.json").exists():
        raise RuntimeError("Capture is one-shot; use a separate successor")
    parent = json.loads((UA / "handoff.json").read_text())
    assert all(sha(UA / n) == h for n, h in parent["files_sha256"].items())
    sources = {}
    copies = {}
    for name, folder in [("NF231", NF), ("FPC84", FPC)]:
        selected = [
            p
            for p in folder.rglob("*")
            if p.is_file()
            and not set(p.relative_to(folder).parts).intersection({"routing", "history", "__pycache__"})
            and p.suffix not in {".lck", ".kicad_prl"}
            and not p.name.startswith("~")
        ]
        if name == "FPC84":
            seal = json.loads((folder / "handoff.json").read_text())
            assert all(sha(folder / n) == h for n, h in seal["files_sha256"].items())
        for p in selected:
            before = sha(p)
            out = ROOT / "inputs" / name / p.relative_to(folder)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, out)
            assert sha(out) == before == sha(p), p
            sources[str(p)] = before
            copies[str(out.relative_to(ROOT))] = before
    parts = json.loads((ROOT / "inputs/NF231/sources/components.json").read_text())
    assert len(parts) == 231 and len(json.loads((ROOT / "inputs/FPC84/components.json").read_text())) == 84
    data = dict(
        parent_handoff_sha256=sha(UA / "handoff.json"),
        original_source_sha256=sources,
        copied_input_sha256=copies,
        NF_source_parts=231,
        FPC_source_parts=84,
        NF233_successor_incorporated=False,
        later_FPC_routing_incorporated=False,
        parent_snapshot_scope="UA01 sealed32/P03db83/R1dc559/R04/PB27/HT01/AP03",
        physical_qualified=False,
        fabrication_released=False,
    )
    target.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(dict(files=len(copies), NF231=True, FPC84=True)))


if __name__ == "__main__":
    capture()
