"""Construct a new paired six-layer NF06P placement; native DRC is separate.

Run with KiCad's Python. Never call Flip on an unparented footprint, and never
attach a null/dangling PROJECT. This builder does not initialize a GUI/project.
"""

import hashlib
import json
import math
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def mm(value):
    return pcbnew.FromMM(value)


def xy(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rule_area(board, name, points, layer):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(True)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowFootprints(False)
    outline = z.Outline()
    outline.NewOutline()
    for p in points:
        outline.Append(mm(p[0]), mm(p[1]))
    board.Add(z)
    return z


def main():
    assert not (ROOT / "handoff.json").exists()
    output = ROOT / "negative_startup_physical.kicad_pcb"
    assert not output.exists(), "Preserve earlier native candidates"
    parts = json.loads((ROOT / "components.json").read_text())
    plan = json.loads((ROOT / "placement.json").read_text())
    inventory = json.loads((ROOT / "land-inventory.json").read_text())["rows"]
    by = {r["ref"]: r for r in inventory}
    ports = json.loads((ROOT / "connector-placement.json").read_text())
    # A real mechanical overlay must select the larger finished-bore contract;
    # the rejected2.4mm first proposal is not silently reused.
    holes = ports["force_shared_strain_candidate"]["PCB_mount_holes"]
    assert len(holes) == 2 and all(h["drill_mm"] >= 2.6 for h in holes)
    assert len(parts) == len(plan["placements"]) == 265
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(6)
    board.GetDesignSettings().SetBoardThickness(mm(1.6))
    net_by_pin = {}
    nets = {}
    for node in ET.parse(ROOT / "generated/netlist.xml").findall("./nets/net"):
        name = node.attrib["name"]
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net
        for pin in node.findall("node"):
            if not pin.attrib["ref"].startswith("#"):
                net_by_pin[(pin.attrib["ref"], pin.attrib["pin"])] = name
    root_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:NF06P:root"))
    for c in parts:
        ref = c["ref"]
        alias = c["footprint"].split(":")[1]
        source = ROOT / "NF06P.pretty" / (alias + ".kicad_mod")
        assert sha(source) == by[ref]["library_sha256"], ref
        fp = pcbnew.FootprintLoad(str(source.parent), alias)
        assert fp is not None, ref
        fp.SetReference(ref)
        fp.SetValue(c["part"])
        fp.GetField(pcbnew.FIELD_T_DATASHEET).SetText(c["source"])
        fp.GetField(pcbnew.FIELD_T_DATASHEET).SetVisible(False)
        fp.SetFPID(pcbnew.LIB_ID("NF06P", alias))
        fp.SetPath(pcbnew.KIID_PATH("/" + root_uuid + "/" + str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:NF06P:" + ref))))
        board.Add(fp)
        assert fp.GetBoard() is not None, "Flip requires a live parent BOARD"
        pose = plan["placements"][ref]
        fp.SetPosition(xy(*pose["anchor_mm"]))
        if pose["side"] == "B":
            fp.Flip(fp.GetPosition(), False)
        fp.SetOrientationDegrees(pose["rotation_deg"])
        fp.Reference().SetLayer(pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)
        fp.Reference().SetVisible(False)
        fp.Value().SetLayer(pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)
        fp.Value().SetVisible(False)
        numbers = set()
        for pad in fp.Pads():
            number = pad.GetNumber()
            if not number:
                continue
            numbers.add(number)
            pad.SetNet(nets[net_by_pin[(ref, number)]])
        assert numbers == {p["number"] for p in c["pins"]}, ref
    layers = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu,
              pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]
    for x in [38., 138.]:
        for edge, y0, y1 in [("BOTTOM", 0., 1.65), ("TOP", 37.35, 39.)]:
            points = [(x - 3.6, y0), (x + 3.6, y0), (x + 3.6, y1), (x - 3.6, y1)]
            for layer in layers:
                rule_area(board, "MOUNT_CLIP_" + str(x) + "_" + edge + "_" + board.GetLayerName(layer), points, layer)
    mechanical = []
    for hole in holes:
        # Mechanical-only footprints are explicitly excluded from schematic
        # parity and BOM. Their courtyards are distinct from the larger Cu KO.
        fp = pcbnew.FOOTPRINT(board)
        board.Add(fp)
        fp.SetReference(hole["ref"])
        fp.SetValue("STRAIN_POST_2p6_NPTH_RECEIVING")
        fp.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM)
        fp.SetPosition(xy(*hole["uv_mm"]))
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        pad = pcbnew.PAD(fp)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetDrillSize(xy(hole["drill_mm"], hole["drill_mm"]))
        pad.SetSize(xy(hole["drill_mm"], hole["drill_mm"]))
        pad.SetPosition(xy(*hole["uv_mm"]))
        pad.SetLayerSet(pcbnew.LSET.AllCuMask())
        fp.Add(pad)
        for layer in [pcbnew.F_CrtYd, pcbnew.B_CrtYd]:
            circle = pcbnew.PCB_SHAPE(fp)
            circle.SetShape(pcbnew.SHAPE_T_CIRCLE)
            circle.SetLayer(layer)
            circle.SetCenter(xy(*hole["uv_mm"]))
            circle.SetEnd(xy(hole["uv_mm"][0] + 3.5, hole["uv_mm"][1]))
            circle.SetWidth(mm(.05))
            fp.Add(circle)
        radius = 3.7 / math.cos(math.pi / 64)
        points = [(hole["uv_mm"][0] + radius * math.cos(2 * math.pi * i / 64),
                   hole["uv_mm"][1] + radius * math.sin(2 * math.pi * i / 64)) for i in range(64)]
        for layer in layers:
            z = rule_area(board, hole["ref"] + "_ALL_CU_R3p7_" + board.GetLayerName(layer), points, layer)
            # Exclude only the nonconductive physical NPTH core from the pad
            # prohibition. Native min_hole_clearance0.25mm remains strict and
            # must reject a deliberate copper intrusion inside this void.
            inner_radius = (hole["drill_mm"] / 2 + .01) / math.cos(math.pi / 64)
            polygon = z.Outline()
            h = polygon.NewHole(0)
            for i in reversed(range(64)):
                px = hole["uv_mm"][0] + inner_radius * math.cos(2 * math.pi * i / 64)
                py = hole["uv_mm"][1] + inner_radius * math.sin(2 * math.pi * i / 64)
                polygon.Append(mm(px), mm(py), 0, h)
        mechanical.append(hole)
    points = [(0, 0), (149, 0), (149, 39), (0, 39)]
    for start, end in zip(points, points[1:] + points[:1]):
        edge = pcbnew.PCB_SHAPE()
        edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
        edge.SetLayer(pcbnew.Edge_Cuts)
        edge.SetWidth(mm(.05))
        edge.SetStart(xy(*start))
        edge.SetEnd(xy(*end))
        board.Add(edge)
    # Only receiving planes, not a PDN proof. Native refill and connectivity
    # must decide actual connections after routing and literal ground stitches.
    for name, layer in [("/AGND", pcbnew.In1_Cu), ("/AUX2V6", pcbnew.In4_Cu)]:
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(nets[name])
        zone.SetLocalClearance(mm(.2))
        zone.SetThermalReliefGap(mm(.2))
        zone.SetThermalReliefSpokeWidth(mm(.3))
        outline = zone.Outline()
        outline.NewOutline()
        for p in [(.5, .5), (148.5, .5), (148.5, 38.5), (.5, 38.5)]:
            outline.Append(mm(p[0]), mm(p[1]))
        board.Add(zone)
    pcbnew.SaveBoard(str(output), board)
    reloaded = pcbnew.LoadBoard(str(output))
    actual = {}
    for fp in reloaded.GetFootprints():
        if fp.GetReference() in by:
            actual[fp.GetReference()] = {p.GetNumber(): p.GetNetname() for p in fp.Pads() if p.GetNumber()}
    assert actual == {c["ref"]: {p["number"]: net_by_pin[(c["ref"], p["number"])] for p in c["pins"]} for c in parts}
    report = dict(parts=265, board_only_mechanical_footprints=mechanical,
                  all267_native_footprints=len(list(reloaded.GetFootprints())), copper_layers=6,
                  physical_pad_net_differences=0, native_full_schematic_parity_required=True,
                  clip_keepout_records=24, strain_copper_keepout_records=12,
                  strain_annulus_omits_only_nonconductive_NPTH_core=True,
                  native_hole_clearance_intrusion_control_required=True,
                  receiving_plane_fills_qualified=False, tracks=0, native_DRC_required=True,
                  source_sha256={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ROOT / "components.json",
                                 ROOT / "placement.json", ROOT / "land-inventory.json", ROOT / "connector-placement.json",
                                 ROOT / "generated/netlist.xml", ROOT / "negative_startup_physical.kicad_sch"]},
                  PCB_sha256=sha(output), physical_qualified=False, fabrication_released=False)
    (ROOT / "generated/native-construction.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Native NF06P265 parts+two mechanical holes; exact actual pad nets;6layers/24clip+12strain KOs; UNROUTED")


if __name__ == "__main__":
    main()
