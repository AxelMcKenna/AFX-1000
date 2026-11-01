"""Add only seven new actual parts to the sealed84part PCB. KiCad Python."""

import hashlib
import json
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
POSES = {
    "U401": (12.5, 18.0, 270, "F"),
    "R401": (12.5, 21.1, 0, "F"),
    "C401": (11.6, 15.0, 90, "B"),
    "C402": (13.4, 15.0, 90, "B"),
    "C403": (11.6, 18.4, 90, "B"),
    "C404": (13.4, 18.4, 90, "B"),
    "J401": (5.0, 24.2, 0, "F"),
}


def main():
    assert not (ROOT / "handoff.json").exists()
    target = ROOT / "fan_power_health.kicad_pcb"
    assert not target.exists(), "Preserve prior candidate"
    b = pcbnew.LoadBoard(str(ROOT / "sources/M1/fan_power_health.kicad_pcb"))
    nets = {n.GetNetname(): n for n in b.GetNetsByNetcode().values()}
    for name in ["/NF_RAW5", "/NF_RAW5_ILIM"]:
        assert name not in nets
        n = pcbnew.NETINFO_ITEM(b, name)
        b.Add(n)
        nets[name] = n
    nc = {}
    for n in ET.parse(ROOT / "generated/netlist.xml").findall("./nets/net"):
        if not n.get("name").startswith("unconnected-"):
            continue
        for p in n.findall("node"):
            if p.get("ref") != "U401":
                continue
            item = pcbnew.NETINFO_ITEM(b, n.get("name"))
            b.Add(item)
            nc[(p.get("ref"), p.get("pin"))] = item
    parts = json.loads((ROOT / "components.json").read_text())
    for c in parts:
        if c["ref"] not in POSES:
            continue
        alias = c["footprint"].split(":")[1]
        f = pcbnew.FootprintLoad(str(ROOT / "FPC01.pretty"), alias)
        assert f, c["ref"]
        f.SetReference(c["ref"])
        f.SetValue(c["part"])
        f.SetFPID(pcbnew.LIB_ID("FPC01", alias))
        f.SetPath(
            pcbnew.KIID_PATH(
                "/"
                + str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:FPC01:root"))
                + "/"
                + str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:FPC01:" + c["ref"]))
            )
        )
        f.GetField(pcbnew.FIELD_T_DATASHEET).SetText(c["source"])
        f.GetField(pcbnew.FIELD_T_DATASHEET).SetVisible(False)
        for field in [f.Reference(), f.Value()]:
            field.SetLayer(pcbnew.F_Fab)
            field.SetVisible(False)
        x, y, angle, face = POSES[c["ref"]]
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        # KiCad10 Flip dereferences the BOARD for layer mapping. Assign the
        # actual parent first; a detached footprint must never be flipped.
        b.Add(f)
        assert f.GetBoard() == b
        if face == "B":
            f.Flip(f.GetPosition(), False)
        f.SetOrientationDegrees(angle)
        for pad in f.Pads():
            if not pad.GetNumber():
                continue
            p = next(p for p in c["pins"] if p["number"] == pad.GetNumber())
            pad.SetNet(nets["/" + p["net"]] if p["net"] else nc[(c["ref"], pad.GetNumber())])
    # CLI --refill-zones applies the actual project rules. GUI settings-manager
    # initialization is not required for adding literal objects in headless
    # pcbnew; its wxApp failure is preserved in generated/failed-wx-init.log.
    pcbnew.SaveBoard(str(target), b)
    (ROOT / "generated/initial-poses.json").write_text(
        json.dumps(
            dict(
                new_part_poses=POSES,
                parent_all84_poses_required_unchanged=True,
                PCB_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                local_loops_routed=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("91 actual footprints; retained parent copper/poses; native DRC/routing required")


if __name__ == "__main__":
    main()
