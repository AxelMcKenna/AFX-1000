"""Try native-flagged signal stubs individually; preserve every pad connection.

Linux pcbnew only. Power, ground, AUX, wide tracks and the smaller READY via
are immutable. A fresh full native refill/DRC/ERC is required after this step.
"""

import argparse
import ast
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import pcbnew

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

WORK = Path(__file__).resolve().parents[4] / "hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work"
LAYOUT = Path(__file__).resolve().parents[4] / "hardware/electronics/rail_disconnect/revision26/layout.py"
# Read the authoritative constant without loading its host-only numpy router.
POWER_NETS = next(ast.literal_eval(n.value) for n in ast.parse(LAYOUT.read_text()).body
                 if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "POWER_NETS" for t in n.targets))
INTERNAL_FORCE = {p["net"] for c in json.loads((WORK / "components.json").read_text())
                  for p in c["pins"] if p["net"] and p["net"].endswith("_COMMON")}
assert len(INTERNAL_FORCE) == 4
PROTECTED = POWER_NETS | INTERNAL_FORCE | {"AGND", "V2V5_AUX"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def missing(board):
    board.BuildConnectivity()
    connectivity = board.GetConnectivity()
    connectivity.RecalculateRatsnest()
    return connectivity.GetUnconnectedCount(False)


def single_layer_signal_vias(board):
    connectivity = board.GetConnectivity()
    assert board.GetCopperLayerCount() == 8
    layers = [(name, board.GetLayerID(name)) for name in
              ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "In5.Cu", "In6.Cu", "B.Cu")]
    result = []
    for item in board.GetTracks():
        if item.GetClass() != "PCB_VIA" or item.GetNetname().lstrip("/") in PROTECTED or item.GetDrillValue() < 300000:
            continue
        contacts = [name for name, identifier in layers if connectivity.IsConnectedOnLayer(item, identifier)]
        if len(contacts) < 2:
            result.append((item, contacts))
    return result


def run():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--batch", action="store_true", help="Validate the entire removal set together; abort on any open")
    parser.add_argument("--cascade", action="store_true", help="Follow actual native dangling endpoints, at most 256 rounds")
    parser.add_argument("--restore-internal-force", action="store_true")
    parser.add_argument("--cascade-vias", action="store_true", help="Validate the layer test against source DRC, then follow unused signal vias")
    args = parser.parse_args()
    assert all(s and all(c.isalnum() or c in "-_" for c in s) for s in (args.source, args.output))
    source = WORK / "generated" / args.source
    output = WORK / "generated" / args.output
    pcb = source / "rail_disconnect.kicad_pcb"
    drc = source / "drc.json"
    original = {str(p): sha(p) for p in (pcb, drc, source / "rail_disconnect.kicad_pro")}
    findings = json.loads(drc.read_text())
    assert not findings["unconnected_items"] and not findings["schematic_parity"]
    assert not [v for v in findings["violations"] if v["severity"] == "error"]
    board = pcbnew.LoadBoard(str(pcb))
    assert missing(board) == 0
    restored = []
    if args.restore_internal_force:
        parent = WORK / "generated/native-closed-control-layout/rail_disconnect.kicad_pcb"
        original[str(parent)] = sha(parent)
        current_tree, parent_tree = [read_sexpr(p.read_text()) for p in (pcb, parent)]
        present = {str(first(n, "uuid")[1]) for kind in ("segment", "via") for n in children(current_tree, kind)}
        for kind in ("segment", "via"):
            for item in children(parent_tree, kind):
                identifier = str(first(item, "uuid")[1])
                if identifier not in present and str(first(item, "net")[1]).lstrip("/") in INTERNAL_FORCE:
                    current_tree.append(item)
                    restored.append(identifier)
        assert len(restored) == 16
        with tempfile.NamedTemporaryFile(mode="w", suffix=".kicad_pcb", dir=WORK / "generated") as temporary:
            temporary.write(sexpr(current_tree) + "\n")
            temporary.flush()
            board = pcbnew.LoadBoard(temporary.name)
        assert missing(board) == 0
    objects = {v.m_Uuid.AsString(): v for v in board.GetTracks()}
    if args.cascade_vias:
        assert args.cascade
        expected = {v["items"][0]["uuid"] for v in findings["violations"] if v["type"] == "via_dangling"
                    and objects[v["items"][0]["uuid"]].GetNetname().lstrip("/") not in PROTECTED
                    and objects[v["items"][0]["uuid"]].GetDrillValue() >= 300000}
        observed = {item.m_Uuid.AsString() for item, _ in single_layer_signal_vias(board)}
        assert observed == expected, ("Layer test differs from actual DRC", sorted(observed - expected), sorted(expected - observed))
    attempts = []
    removed_items = []
    for finding in findings["violations"]:
        if finding["type"] not in ("track_dangling", "via_dangling"):
            continue
        item = objects[finding["items"][0]["uuid"]]
        net = item.GetNetname().lstrip("/")
        via = item.GetClass() == "PCB_VIA"
        row = dict(uuid=item.m_Uuid.AsString(), net=net, kind=item.GetClass())
        protected = (net in PROTECTED or
                     (not via and item.GetWidth() > 400000) or
                     (via and item.GetDrillValue() < 300000))
        if protected:
            row.update(removed=False, reason="protected copper or process via")
        else:
            board.Remove(item)
            count = 0 if args.batch else missing(board)
            if count:
                board.Add(item)
                assert missing(board) == 0
                row.update(removed=False, reason="removal breaks connectivity", trial_opens=count)
            else:
                removed_items.append(item)
                row.update(removed=True, connectivity_check="whole removal set" if args.batch else "individual removal")
        attempts.append(row)
        if len(attempts) % 20 == 0:
            print("Reviewed", len(attempts), "removed", sum(r["removed"] for r in attempts), flush=True)
    assert len(attempts) <= 250 and missing(board) == 0
    cascade_rounds = []
    cascade_converged = None
    if args.cascade:
        cascade_converged = False
        for number in range(256):
            connectivity = board.GetConnectivity()
            tips = [item for item in board.GetTracks()
                    if item.GetClass() == "PCB_TRACK" and item.GetWidth() <= 400000
                    and item.GetNetname().lstrip("/") not in PROTECTED
                    and connectivity.TestTrackEndpointDangling(item, False)]
            via_contacts = {}
            if args.cascade_vias:
                for item, contacts in single_layer_signal_vias(board):
                    tips.append(item)
                    via_contacts[item.m_Uuid.AsString()] = contacts
            if not tips:
                cascade_converged = True
                break
            for item in tips:
                board.Remove(item)
                removed_items.append(item)
                attempts.append(dict(uuid=item.m_Uuid.AsString(), net=item.GetNetname().lstrip("/"),
                    kind=item.GetClass(), removed=True, connectivity_check="whole native dangling-tip set",
                    native_endpoint_test=item.GetClass() == "PCB_TRACK", cascade_round=number + 1,
                    connected_copper_layers=via_contacts.get(item.m_Uuid.AsString())))
            assert missing(board) == 0, "Dangling-tip removal unexpectedly broke a connection; do not save"
            cascade_rounds.append(dict(round=number + 1, removed=len(tips), uncapped_opens=0))
            print("Native dangling-tip cascade", number + 1, "removed", len(tips), flush=True)

    # Clip the connector's three lower outline strokes to 0.29 mm from the edge.
    # The connector body, pads, mounting metal, courtyard and pose stay fixed.
    silk_changes = []
    connector = next(f for f in board.GetFootprints() if f.GetReference() == "J12")
    for graphic in connector.GraphicalItems():
        if graphic.GetLayer() != pcbnew.F_SilkS or graphic.GetClass() != "PCB_SHAPE":
            continue
        start, end = graphic.GetStart(), graphic.GetEnd()
        if max(start.y, end.y) <= 154150000:
            continue
        before = [[start.x, start.y], [end.x, end.y]]
        assert max(start.y, end.y) <= 154860000
        graphic.SetStart(pcbnew.VECTOR2I(start.x, min(start.y, 154150000)))
        graphic.SetEnd(pcbnew.VECTOR2I(end.x, min(end.y, 154150000)))
        silk_changes.append(dict(uuid=graphic.m_Uuid.AsString(), before_nm=before,
                                 after_nm=[[graphic.GetStart().x, graphic.GetStart().y],
                                           [graphic.GetEnd().x, graphic.GetEnd().y]]))
    # Later passes see the already clipped outline and must not edit anything else.
    assert len(silk_changes) in (0, 3)
    output.mkdir(exist_ok=False)
    destination = output / pcb.name
    pcbnew.SaveBoard(str(destination), board)
    assert all(sha(Path(p)) == digest for p, digest in original.items())
    report = dict(source_sha256=original, output_pcb_sha256=sha(destination),
                  recipe_sha256=sha(Path(__file__)), attempts=attempts,
                  whole_removal_set_has_zero_uncapped_opens=True,
                  native_endpoint_cascade=cascade_rounds,
                  cascade_converged=cascade_converged, cascade_round_limit=256,
                  signal_via_layer_test_matches_source_DRC=args.cascade_vias,
                  removed_count=sum(r["removed"] for r in attempts),
                  restored_internal_force_uuids=restored, internal_force_nets=sorted(INTERNAL_FORCE),
                  silk_changes=silk_changes, uncapped_opens_before_save=0,
                  power_ground_aux_objects_protected=True,
                  source_unchanged=True, native_refill_DRC_ERC_pending=True,
                  physical_qualified=False, fabrication_released=False)
    (output / "cleanup.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Removed", report["removed_count"], "signal stubs; clipped", len(silk_changes), "silk strokes", flush=True)


if __name__ == "__main__":
    run()
