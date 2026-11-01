"""Actual eight-layer native pad polygons and UUID connectivity components."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pcbnew

from hardware.electronics.rail_disconnect.revision28 import native_pad_geometry

WORK=Path(__file__).resolve().parents[4]/"hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work"
LAYERS=("F.Cu","In1.Cu","In2.Cu","In3.Cu","In4.Cu","In5.Cu","In6.Cu","B.Cu")


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-folder",default="eight-layer-routes")
    parser.add_argument("--native-folder",default="native-eight-routes")
    parser.add_argument("--output-folder",default="eight-routing-inputs")
    args=parser.parse_args()
    assert all(s and all(c.isalnum() or c in "-_" for c in s) for s in vars(args).values())
    source=WORK/"generated"/args.source_folder/"rail_disconnect.kicad_pcb"
    native=WORK/"generated"/args.native_folder
    filled=native/source.name
    out=WORK/"generated"/args.output_folder
    out.mkdir(exist_ok=False)
    native_pad_geometry.LAYERS=LAYERS
    pads=native_pad_geometry.export(filled)
    (out/"pads.json").write_text(json.dumps(pads,indent=2)+"\n")
    board=pcbnew.LoadBoard(str(filled))
    board.BuildConnectivity()
    conn=board.GetConnectivity()
    drc=json.loads((native/"drc.json").read_text())
    names={re.search(r"\[/([^]]+)\]",r["items"][0]["description"]).group(1) for r in drc["unconnected_items"]}
    objects=[p for fp in board.GetFootprints() for p in fp.Pads() if p.GetNetname().lstrip("/") in names]
    objects += [p for p in board.GetTracks() if p.GetNetname().lstrip("/") in names]
    byid={p.m_Uuid.AsString():p for p in objects}
    assert len(byid)==len(objects)
    parent={uid:uid for uid in byid}

    def root(uid):
        while uid!=parent[uid]:
            parent[uid]=parent[parent[uid]]
            uid=parent[uid]
        return uid

    for uid,obj in byid.items():
        for neighbor in conn.GetConnectedItems(obj):
            other=neighbor.m_Uuid.AsString()
            assert obj.GetNetname()==neighbor.GetNetname()
            if other in byid:
                parent[root(other)]=root(uid)
    groups={}
    for uid,obj in byid.items():
        net=obj.GetNetname().lstrip("/")
        xy=obj.GetPosition()
        row=dict(uuid=uid,kind=obj.GetClass(),net=net,position_mm=[xy.x/1e6-100,xy.y/1e6-100],
                 layers=[i for i,name in enumerate(LAYERS) if obj.IsOnLayer(board.GetLayerID(name))])
        if row["kind"]=="PAD":
            row.update(ref=obj.GetParentFootprint().GetReference(),pin=obj.GetNumber())
        elif row["kind"]=="PCB_TRACK":
            xy=obj.GetEnd()
            row["end_mm"]=[xy.x/1e6-100,xy.y/1e6-100]
        groups.setdefault((net,root(uid)),[]).append(row)
    inventory={}
    for net in sorted(names):
        components=[g for (n,_),g in groups.items() if n==net]
        inventory[net]=dict(components=components,component_logical_pads=[
            sorted({p["ref"]+"."+p["pin"] for p in group if p["kind"]=="PAD"}) for group in components],
            component_kind_counts=[dict(Counter(p["kind"] for p in group)) for group in components])
    import hashlib

    inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,filled,native/"drc.json",Path(__file__))}
    (out/"components.json").write_text(json.dumps(dict(source_sha256=inputs,native_version=pcbnew.GetBuildVersion(),
        copper_layers=LAYERS,inventory=inventory,all_native_layer_identities_retained=True,
        native_uncapped_missing=conn.GetUnconnectedCount(False),physical_qualified=False),indent=2)+"\n")
    print("Exported complete eight-layer native routing inputs")


if __name__=="__main__":
    run()
