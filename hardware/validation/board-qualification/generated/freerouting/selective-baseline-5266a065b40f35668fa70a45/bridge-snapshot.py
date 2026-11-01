"""Isolated DSN/SES bridge; native KiCad checks and copper extraction stay mandatory.

Run with KiCad's bundled Python, which supplies pcbnew. Export locks every
existing track/via unless a source-bound lock contract is supplied. Import
refuses lost protected copper or changed component identities/poses.
Neither command writes to the source project.
"""

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def session_design(text):
    """Read only the SES base-design atom; reject absent/ambiguous namespaces."""
    matches = re.findall(r'\(base_design\s+(?:"([^"\r\n]+)"|([^\s()"]+))\s*\)', text)
    if len(matches) != 1:
        raise ValueError("Session must identify exactly one base design")
    return matches[0][0] or matches[0][1]


def parts(board):
    return sorted(
        (
            p.GetReference(),
            p.GetValue(),
            int(p.GetLayer()),
            p.GetPosition().x,
            p.GetPosition().y,
            p.GetOrientationDegrees(),
        )
        for p in board.GetFootprints()
    )


def copper(board, pcbnew, uuids=None):
    layers = (
        [pcbnew.F_Cu]
        + [getattr(pcbnew, "In%d_Cu" % n) for n in range(1, board.GetCopperLayerCount() - 1)]
        + [pcbnew.B_Cu]
    )
    rows = []
    for item in board.GetTracks():
        if uuids is not None and item.m_Uuid.AsString() not in uuids:
            continue
        row = (
            type(item).__name__,
            item.GetNetname(),
            int(item.GetLayer()),
            item.GetStart().x,
            item.GetStart().y,
            item.GetEnd().x,
            item.GetEnd().y,
        )
        if isinstance(item, pcbnew.PCB_VIA):
            row += (tuple(item.GetWidth(layer) for layer in layers), item.GetDrillValue())
        else:
            row += (item.GetWidth(),)
        rows.append(row)
    return Counter(rows)


def export(source, workspace, clearance_mm, lock_contract=None):
    import pcbnew

    source, workspace = source.resolve(), workspace.resolve()
    assert source.is_file() and source.suffix == ".kicad_pcb"
    assert not workspace.exists() or not any(workspace.iterdir()), "Use a fresh isolated workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    snapshot = workspace / "source"
    snapshot.mkdir()
    paths = []
    for path in source.parent.iterdir():
        if path.suffix in (
            ".kicad_pcb",
            ".kicad_sch",
            ".kicad_pro",
            ".kicad_sym",
            ".kicad_dru",
        ) or path.name in ("sym-lib-table", "fp-lib-table"):
            if path.is_file():
                paths.append(path)
        elif path.is_dir() and path.suffix == ".pretty":
            paths.extend(p for p in path.rglob("*") if p.is_file())
    original_hashes = {str(p.relative_to(source.parent)): sha(p) for p in paths}
    for path in paths:
        target = snapshot / path.relative_to(source.parent)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    assert all(
        sha(source.parent / name) == value == sha(snapshot / name) for name, value in original_hashes.items()
    ), "Project changed during capture"
    board = pcbnew.LoadBoard(str(snapshot / source.name))
    locks = {t.m_Uuid.AsString(): t.IsLocked() for t in board.GetTracks()}
    contract_sha = None
    protected = set(locks)
    if lock_contract is not None:
        contract = json.loads(lock_contract.read_text())
        assert contract["source_pcb_sha256"] == sha(snapshot / source.name), "Lock contract source mismatch"
        protected = {r["uuid"] for r in contract["locked_copper"]}
        movable = {r["uuid"] for r in contract["unlocked_nonforce_copper"]}
        assert protected and not protected & movable and protected | movable == set(locks), (
            "Lock contract must partition every original copper UUID"
        )
        assert len(protected) == len(contract["locked_copper"])
        assert len(movable) == len(contract["unlocked_nonforce_copper"])
        shutil.copyfile(lock_contract, workspace / "lock-contract.json")
        contract_sha = sha(workspace / "lock-contract.json")
    for item in board.GetTracks():
        item.SetLocked(item.m_Uuid.AsString() in protected)
    pcbnew.SaveBoard(str(workspace / "locked-input.kicad_pcb"), board)
    assert pcbnew.ExportSpecctraDSN(board, str(workspace / "exporter-original.dsn"))
    text = (workspace / "exporter-original.dsn").read_text()
    changes = []

    def clearance(match):
        before = float(match[1])
        after = max(before, clearance_mm * 1000)
        changes.append([before, after])
        return "(clearance %g (type smd_smd))" % after

    assert clearance_mm > 0
    text = re.sub(r"\(clearance ([\d.]+) \(type smd_smd\)\)", clearance, text)
    assert changes, "Expected exporter SMD-clearance rule is absent; inspect the new format"
    # Freerouting names SES base_design after the DSN filename, not its PCB
    # header. Bind that namespace to both the captured project and constraints.
    design_name = (
        "afx-"
        + hashlib.sha256(
            json.dumps([original_hashes, clearance_mm, contract_sha], sort_keys=True).encode()
        ).hexdigest()[:24]
    )
    dsn = workspace / (design_name + ".dsn")
    dsn.write_text(text)
    report = dict(
        scope="Source project untouched; protected copper locked; routing export only",
        source_path=str(source),
        source_filename=source.name,
        source_pcb_sha256=sha(source),
        source_project_sha256=original_hashes,
        pcbnew_version=pcbnew.Version(),
        original_lock_states=locks,
        protected_copper_uuids=sorted(protected),
        lock_contract_sha256=contract_sha,
        smd_clearance_um_before_after=changes,
        design_name=design_name,
        dsn_filename=dsn.name,
        dsn_sha256=sha(dsn),
        locked_input_sha256=sha(workspace / "locked-input.kicad_pcb"),
        bridge_sha256=sha(Path(__file__)),
        native_checks_performed=False,
        copper_losses_qualified=False,
        fabrication_released=False,
    )
    shutil.copyfile(__file__, workspace / "bridge-snapshot.py")
    (workspace / "export.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Exported isolated locked-copper DSN:", workspace)
    return report


def import_session(workspace, session, unchanged=False):
    import pcbnew

    workspace, session = workspace.resolve(), session.resolve()
    report = json.loads((workspace / "export.json").read_text())
    snapshot = workspace / "source"
    assert all(sha(snapshot / name) == value for name, value in report["source_project_sha256"].items()), (
        "Frozen project changed"
    )
    assert sha(workspace / "locked-input.kicad_pcb") == report["locked_input_sha256"]
    assert sha(workspace / report["dsn_filename"]) == report["dsn_sha256"]
    if report.get("lock_contract_sha256"):
        assert sha(workspace / "lock-contract.json") == report["lock_contract_sha256"]
    if session_design(session.read_text()) != report["design_name"]:
        raise ValueError("Session base design does not match this captured project/constraints")
    original = pcbnew.LoadBoard(str(snapshot / report["source_filename"]))
    board = pcbnew.LoadBoard(str(workspace / "locked-input.kicad_pcb"))
    before = copper(original, pcbnew)
    protected = copper(original, pcbnew, set(report["protected_copper_uuids"]))
    assert pcbnew.ImportSpecctraSES(board, str(session)), "Native SES import failed"
    after = copper(board, pcbnew)
    assert parts(original) == parts(board), "Router changed component identities/poses"
    assert not protected - after, "Router removed/changed protected original copper"
    if unchanged:
        assert before == after, "Baseline roundtrip added copper"
    for item in board.GetTracks():
        item.SetLocked(report["original_lock_states"].get(item.m_Uuid.AsString(), False))
    candidate = workspace / "candidate"
    shutil.copytree(snapshot, candidate, dirs_exist_ok=True)
    pcbnew.SaveBoard(str(candidate / report["source_filename"]), board)
    receipt = dict(
        scope="Native SES import and original-copper/part preservation only",
        source_pcb_sha256=report["source_pcb_sha256"],
        export_receipt_sha256=sha(workspace / "export.json"),
        session_sha256=sha(session),
        session_base_design=report["design_name"],
        imported_candidate_sha256=sha(candidate / report["source_filename"]),
        original_track_via_count=sum(before.values()),
        imported_track_via_count=sum(after.values()),
        protected_track_via_count=sum(protected.values()),
        protected_original_copper_preserved=True,
        all_original_copper_preserved=not bool(before - after),
        explicit_lock_contract_sha256=report.get("lock_contract_sha256"),
        all_via_copper_layer_widths_and_drills_compared=True,
        component_identities_and_poses_preserved=True,
        unchanged_baseline_required=unchanged,
        bridge_sha256=sha(Path(__file__)),
        native_drc_erc_parity_and_connectivity_checked=False,
        actual_filled_copper_and_return_network_qualified=False,
        fabrication_released=False,
        build_ready=False,
    )
    (workspace / "import.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("Imported isolated candidate; native/filled-copper checks still required:", candidate)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    exp = sub.add_parser("export")
    exp.add_argument("source", type=Path)
    exp.add_argument("workspace", type=Path)
    exp.add_argument("--clearance-mm", type=float, default=0.2)
    exp.add_argument("--lock-contract", type=Path)
    imp = sub.add_parser("import")
    imp.add_argument("workspace", type=Path)
    imp.add_argument("session", type=Path)
    imp.add_argument("--require-unchanged", action="store_true")
    args = parser.parse_args()
    if args.operation == "export":
        export(args.source, args.workspace, args.clearance_mm, args.lock_contract)
    else:
        import_session(args.workspace, args.session, args.require_unchanged)
