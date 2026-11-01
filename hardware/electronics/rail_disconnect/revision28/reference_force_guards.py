"""Routing-only guards from a declared frozen, natively filled force reference.

Deleting legacy signal vias then refilling expands power copper into their old
antipads. This policy protects ORIGINAL actual force copper, rather than turning
those newly reclaimed voids into permanent routing obstacles. It changes no PCB,
clearance, package or native DRC rule. Actual final force/return extraction stays
mandatory and no material/process/voltage goal is waived.
"""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

import pcbnew

from hardware.qualification.boards.freerouting_bridge import copper
from hardware.qualification.boards.freerouting_force import guards

from .native_contract_compare import compare
from .native_force_compare import FORCE_NETS


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(workspace, reference_source, reference_filled):
    workspace = Path(workspace).resolve()
    reference_source = Path(reference_source)
    reference_filled = Path(reference_filled)
    meta_path = workspace / "export.json"
    meta = json.loads(meta_path.read_text())
    assert not meta.get("force_guard_receipt_sha256"), "Use a fresh export without another guard policy"
    source = workspace / "source" / meta["source_filename"]
    assert sha(source) == meta["source_pcb_sha256"]
    original = pcbnew.LoadBoard(str(reference_source))
    candidate = pcbnew.LoadBoard(str(source))
    semantic = compare(reference_source, source)
    assert semantic["contracts_equal"], (
        "All native package/pad/zone/outline/setup contracts must match the declared reference"
    )
    original_ids = {
        t.m_Uuid.AsString() for t in original.GetTracks() if t.GetNetname().lstrip("/") in FORCE_NETS
    }
    assert not (copper(original, pcbnew, original_ids) - copper(candidate, pcbnew)), (
        "Original actual force conductor changed"
    )
    protected = set(meta["protected_copper_uuids"])
    assert original_ids <= protected
    assert all(
        t.m_Uuid.AsString() in protected
        for t in candidate.GetTracks()
        if t.GetNetname().lstrip("/") in FORCE_NETS
    )
    text, report = guards(reference_source, reference_filled, protected, pcbnew)
    report.update(
        policy="Protect frozen original actual force copper; reset/refill additions are not immutable",
        current_candidate_source_sha256=sha(source),
        frozen_reference_source_sha256=sha(reference_source),
        frozen_reference_filled_sha256=sha(reference_filled),
        current_vs_reference_complete_native_contract=semantic,
        original_actual_force_objects_preserved=True,
        current_actual_force_objects_locked=True,
        final_native_and_contact_correct_positive_return_checks_required=True,
        guard_adapter_sha256=sha(Path(__file__)),
        physical_qualified=False,
    )
    guard_path = workspace / "force-guards.json"
    guard_path.write_text(json.dumps(report, indent=2) + "\n")
    shutil.copy2(reference_source, workspace / "force-source-reference.kicad_pcb")
    shutil.copy2(reference_filled, workspace / "force-filled-reference.kicad_pcb")
    dsn = workspace / meta["dsn_filename"]
    before = dsn.read_text()
    assert sha(dsn) == meta["dsn_sha256"]
    boundary = re.search(r"(?m)^    \(boundary\b", before)
    assert boundary
    revised = before[: boundary.start()] + text + "\n" + before[boundary.start() :]
    (workspace / "export-before-reference-guards.json").write_text(json.dumps(meta, indent=2) + "\n")
    name = "afx-" + hashlib.sha256((meta["design_name"] + sha(guard_path)).encode()).hexdigest()[:24]
    target = workspace / (name + ".dsn")
    assert not target.exists()
    target.write_text(revised)
    meta.update(
        design_name=name,
        dsn_filename=target.name,
        dsn_sha256=sha(target),
        force_guard_receipt_sha256=sha(guard_path),
        force_guard_reference_policy=report["policy"],
        force_reference_source_sha256=sha(reference_source),
        force_reference_filled_sha256=sha(reference_filled),
    )
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print("Original actual force guarded;", report["keepout_count"], "keepouts; current source not changed")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    p.add_argument("reference_source")
    p.add_argument("reference_filled")
    a = p.parse_args()
    main(a.workspace, a.reference_source, a.reference_filled)
