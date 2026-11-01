"""Remove only unlocked, PAD-only physical dangling signal holes in a copy.

Actual native attachment proof is required: no tracks/zones, one SMD pad, one
connected copper layer. Critical force/gate/timing/repair locks stay intact.
The unchanged native open counts and fresh filled geometry remain mandatory.
Run with KiCad Python; source projects and shared source are never saved.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pcbnew

from ...common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent


def main(workspace):
    source = ROOT / "generated/p9-six-load-n12-work"
    path = source / "rail_disconnect.kicad_pcb"
    filled = source / "generated/filled-six-load-n12-1.kicad_pcb"
    raw_path = source / "generated/drc-six-load-n12-1.json"
    contract_path = ROOT / "generated/leaf-prune-source-lock-contract.json"
    before = path.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    contract = json.loads(contract_path.read_text())
    assert contract["source_pcb_sha256"] == digest
    locked = {r["uuid"] for r in contract["locked_copper"]}
    raw = json.loads(raw_path.read_text())
    warned = {i["uuid"] for row in raw["violations"] if row["type"] == "via_dangling" for i in row["items"]}
    board = pcbnew.LoadBoard(str(filled))
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    eligible, protected = [], []
    for via in board.GetTracks():
        uid = via.m_Uuid.AsString()
        if via.GetClass() != "PCB_VIA" or uid not in warned:
            continue
        pads = list(connection.GetConnectedPads(via))
        tracks = list(connection.GetConnectedTracks(via))
        neighbors = [i for i in connection.GetConnectedItems(via) if i.m_Uuid.AsString() != uid]
        layers = [z for z in range(32) if board.IsLayerEnabled(z) and connection.IsConnectedOnLayer(via, z)]
        if (
            len(pads) != 1
            or tracks
            or len(neighbors) != 1
            or neighbors[0].GetClass() != "PAD"
            or len(layers) != 1
        ):
            continue
        pad = pads[0]
        if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD or not pad.IsOnLayer(layers[0]):
            continue
        assert via.GetNetname() == pad.GetNetname()
        row = dict(
            uuid=uid,
            net=via.GetNetname(),
            actual_connected_pad=[pad.GetParentFootprint().GetReference(), pad.GetNumber()],
            actual_connected_layer=board.GetLayerName(layers[0]),
            connected_tracks=0,
            connected_zones=0,
            directly_connected_native_items=1,
            actual_position_mm=[via.GetPosition().x / 1e6, via.GetPosition().y / 1e6],
            native_drill_mm=via.GetDrillValue() / 1e6,
            native_land_mm=via.GetWidth() / 1e6,
            protected_by_source_lock_contract=uid in locked,
        )
        (protected if uid in locked else eligible).append(row)
    tree = read_sexpr(before.decode())
    ids = {r["uuid"] for r in eligible}
    removed = [n for n in children(tree, "via") if str(first(n, "uuid")[1]) in ids]
    assert len(removed) == len(eligible) and not ids & locked
    report = dict(
        source_pcb_sha256=digest,
        filled_pcb_sha256=hashlib.sha256(filled.read_bytes()).hexdigest(),
        native_drc_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        source_lock_contract_sha256=hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        reviewer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        actual_unlocked_leaf_vias=eligible,
        protected_leaf_vias_retained=protected,
        removed_actual_objects=[sexpr(n) for n in removed],
        all_critical_locked_objects_retained=True,
        every_original_package_pad_and_port_retained=True,
        new_native_and_filled_conductor_checks_required=True,
        physical_qualified=False,
    )
    (ROOT / "generated/leaf-prune-native-inventory.json").write_text(json.dumps(report, indent=2) + "\n")
    assert eligible, "No unlocked pad-only via; inventory retained, no board emitted"
    workspace = Path(workspace).resolve()
    assert workspace.is_relative_to(ROOT / "generated") and not workspace.exists()
    workspace.mkdir()
    (workspace / "generated").mkdir()
    for p in source.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, workspace / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, workspace / p.name)
    tree[:] = [n for n in tree if n not in removed]
    candidate = workspace / path.name
    candidate.write_text(sexpr(tree) + "\n")
    report["candidate_pcb_sha256"] = hashlib.sha256(candidate.read_bytes()).hexdigest()
    (workspace / "generated/pruned-pad-only-vias.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "Removed",
        len(eligible),
        "unlocked pad-only signal holes; retained",
        len(protected),
        "protected leaves",
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    main(p.parse_args().workspace)
