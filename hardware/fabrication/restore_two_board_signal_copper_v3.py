"""Translate existing source copper into the integrated signal board.

No layer-count or stack qualification is implied. Existing layer names are
retained; native refill/parity and an independent copper audit are mandatory.
"""
import copy
import json
import uuid
from collections import Counter
from pathlib import Path
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, SOURCES, prop, read_netlist, sha

PARENT = STAGING / "two-board-signal-native-03"
OUT = STAGING / "two-board-signal-copper-03"


def build():
    assert not OUT.exists()
    OUT.mkdir()
    paths = [Path(__file__), PARENT / "review.json", PARENT / "erc.json", PARENT / "netlist.xml",
             PARENT / "signal_main.kicad_pcb", STAGING / "two-board-placement-05/capture.json",
             STAGING / "two-board-placement-05/placement.json"]
    erc = json.loads((PARENT / "erc.json").read_text())
    assert not [v for s in erc["sheets"] for v in s.get("violations", [])]
    target = read_sexpr((PARENT / "signal_main.kicad_pcb").read_text())
    assert not any(children(target, tag) for tag in ["segment", "via", "arc", "zone"])
    _, actual = read_netlist(PARENT / "netlist.xml")
    target_nets = {str(n[2]).lstrip("/"): (int(n[1]), str(n[2])) for n in children(target, "net")}
    cap = json.loads((STAGING / "two-board-placement-05/capture.json").read_text())
    poses = json.loads((STAGING / "two-board-placement-05/placement.json").read_text())["poses"]
    ledger = []
    for role, caprole in [("A", "audio_main"), ("D", "digital_core")]:
        folder, name, nl = SOURCES[role]
        pcb = folder / (name + ".kicad_pcb")
        paths += [pcb, folder / nl]
        source = read_sexpr(pcb.read_text())
        _, pins = read_netlist(folder / nl)
        net_map = {}
        for (ref, pin), net in pins.items():
            new = target_nets[actual[(role + "_" + ref, pin)]]
            assert net not in net_map or net_map[net] == new
            net_map[net] = new
        source_nets = {int(n[1]): str(n[2]) for n in children(source, "net")}
        deltas = {tuple(round(poses[p["id"]]["xy"][i] - p["source_xy"][i], 6) for i in range(2))
                  for p in cap["parts"] if p["role"] == caprole}
        assert len(deltas) == 1
        delta = next(iter(deltas))
        objects = []

        def transform(node):
            if not isinstance(node, list) or not node:
                return
            tag = str(node[0])
            if tag in ["start", "end", "mid", "at", "xy"]:
                node[1:3] = [round(float(node[i+1]) + delta[i], 6) for i in range(2)]
            elif tag in ["uuid", "tstamp"]:
                node[1] = str(uuid.uuid5(uuid.NAMESPACE_URL, "AFX:TBC03:" + role + ":" + str(node[1])))
            elif tag == "net":
                old = source_nets[int(node[1])] if str(node[1]).isdigit() else str(node[1])
                code, new = net_map[old.lstrip("/")] if old else (0, "")
                node[1] = code
            elif tag == "net_name" and node[1]:
                node[1] = net_map[str(node[1]).lstrip("/")][1]
            for child in node:
                if isinstance(child, list):
                    transform(child)

        for tag in ["segment", "arc", "via", "zone"]:
            for original in children(source, tag):
                node = copy.deepcopy(original)
                if tag == "zone":
                    # Refill against the actual combined board, not cached old fills.
                    node[:] = [x for x in node if not (isinstance(x, list) and x and x[0] in ["filled_polygon", "fill_segments"])]
                transform(node)
                target.append(node)
                objects.append(dict(type=tag, source_uuid=(str(first(original, "uuid")[1]) if children(original, "uuid") else str(first(original, "tstamp")[1]) if children(original, "tstamp") else None), source_index=len(objects),
                                    transformed_sha256=__import__("hashlib").sha256(sexpr(node).encode()).hexdigest()))
        ledger.append(dict(source_role=caprole, translation_mm=delta, counts=dict(Counter(o["type"] for o in objects)), objects=objects))
    path = OUT / "signal_main.kicad_pcb"
    path.write_text(sexpr(target) + "\n")
    (OUT / "copper-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    record = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        artifact_sha256={path.name: sha(path), "copper-ledger.json": sha(OUT / "copper-ledger.json")},
        copper_counts={l["source_role"]: l["counts"] for l in ledger},
        layer_mapping="Source layer names retained; A In1 ground/In2 supply on provisional eight-layer template",
        native_refill_and_parity_pending=True, stack_approved=False, routing_complete=False, fabrication_released=False)
    (OUT / "construction.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record["copper_counts"]))


if __name__ == "__main__":
    build()
