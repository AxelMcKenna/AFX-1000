"""Capture actual six-layer native components on the remaining open nets."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import pcbnew

WORK = Path(__file__).resolve().parents[4] / "hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter"
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    assert args.source and all(c.isalnum() or c in "-_" for c in args.source)
    folder = WORK / "generated" / args.source
    destination = folder / "components.json"
    assert not destination.exists()
    pcb, drc = folder / "power_p03.kicad_pcb", folder / "drc.json"
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (pcb, drc)}
    raw = json.loads(drc.read_text())
    nets = {re.search(r"\[/([^]]+)\]", v["items"][0]["description"]).group(1) for v in raw["unconnected_items"]}
    assert nets <= {"POWER_RUN", "AX03_SOURCE_CT", "V2V5_AUX"}, nets
    board = pcbnew.LoadBoard(str(pcb))
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    items = [p for f in board.GetFootprints() for p in f.Pads() if p.GetNetname().lstrip("/") in nets]
    items += [t for t in board.GetTracks() if t.GetNetname().lstrip("/") in nets]
    objects = {p.m_Uuid.AsString(): p for p in items}
    parent = {key: key for key in objects}

    def root(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for key, item in objects.items():
        for neighbor in connection.GetConnectedItems(item):
            other = neighbor.m_Uuid.AsString()
            if other in objects:
                parent[root(other)] = root(key)
    groups = {}
    for key, item in objects.items():
        point = item.GetPosition()
        net = item.GetNetname().lstrip("/")
        row = dict(uuid=key, net=net, kind=item.GetClass(), xy=[point.x/1e6-100, point.y/1e6-100],
                   layers=[index for index, layer in enumerate(LAYERS) if item.IsOnLayer(board.GetLayerID(layer))])
        if row["kind"] == "PAD":
            row.update(ref=item.GetParentFootprint().GetReference(), pin=item.GetNumber())
        if row["kind"] == "PCB_TRACK":
            point = item.GetEnd()
            row["end"] = [point.x/1e6-100, point.y/1e6-100]
        groups.setdefault((net, root(key)), []).append(row)
    inventory = {net: [g for (name, _), g in groups.items() if name == net] for net in nets}
    destination.write_text(json.dumps(dict(source_sha256=hashes, copper_layers=LAYERS, inventory=inventory), indent=2)+"\n")
    print({net: [[p.get("ref", "")+"."+p.get("pin", "") for p in group if p["kind"] == "PAD"] for group in gs] for net, gs in inventory.items()})


if __name__ == "__main__":
    run()
