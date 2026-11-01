"""Actual NEW 4-layer PCB from FPC01 placed parts. Run with KiCad Python3.9."""

import hashlib
import json
import os
import subprocess
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew

from hardware.electronics.common.sexpr import a, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def mm(x):
    return pcbnew.FromMM(float(x))


def xy(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def check(label="placement"):
    path = ROOT / "fan_power_health.kicad_pcb"
    board = pcbnew.LoadBoard(str(path))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(path), board)
    before = sha(path)
    report = ROOT / "generated" / (label + "-drc.json")
    cli = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/rmx-kicad-config",
        FONTCONFIG_FILE=str(REPO / "build-hardware/kicad-fonts.conf"),
    )
    command = [
        cli,
        "pcb",
        "drc",
        "--schematic-parity",
        "--format",
        "json",
        "--output",
        str(report),
        str(path),
    ]
    p = subprocess.run(command, env=env, capture_output=True, text=True)
    (ROOT / "generated" / (label + "-drc.log")).write_text(p.stdout + p.stderr)
    assert p.returncode in (0, 5), (p.returncode, p.stderr)
    data = json.loads(report.read_text())
    parts = json.loads((ROOT / "components.json").read_text())
    expected = {p["ref"]: {n["number"]: n["net"] for n in p["pins"]} for p in parts}
    actual = {
        fp.GetReference(): {
            p.GetNumber(): (
                None
                if p.GetNetname().lstrip("/").startswith("unconnected-")
                else p.GetNetname().lstrip("/") or None
            )
            for p in fp.Pads()
            if p.GetNumber()
        }
        for fp in board.GetFootprints()
    }
    assert actual == expected, set(actual) ^ set(expected)
    record = dict(
        label=label,
        parts=len(actual),
        native_pad_net_parity_differences=0,
        hard_errors=sum(v["severity"] == "error" for v in data["violations"]),
        warnings=sum(v["severity"] == "warning" for v in data["violations"]),
        unconnected=len(data.get("unconnected_items", [])),
        schematic_parity=len(data.get("schematic_parity", [])),
        pcb_sha256=before,
        source_unchanged_by_cli=sha(path) == before,
        raw_report_sha256=sha(report),
        command=command,
        returncode=p.returncode,
        tracks=len(list(board.GetTracks())),
        zones=board.GetAreaCount(),
        physical_qualified=False,
        fabrication_released=False,
    )
    (ROOT / "generated" / (label + "-native.json")).write_text(json.dumps(record, indent=2) + "\n")
    (ROOT / "generated/current-native.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))


def build():
    assert not (ROOT / "handoff.json").exists(), "Preserve sealed candidate"
    parts = json.loads((ROOT / "components.json").read_text())
    plan = json.loads((ROOT / "generated/placement.json").read_text())
    width, height, _ = plan["board_mm"]
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    board.GetDesignSettings().SetBoardThickness(mm(1.6))
    nets = {}
    for name in sorted({p["net"] for c in parts for p in c["pins"] if p["net"] is not None}):
        n = pcbnew.NETINFO_ITEM(board, "/" + name)
        board.Add(n)
        nets[name] = n
    nc = {}
    for net in ET.parse(ROOT / "generated/netlist.xml").findall("./nets/net"):
        if net.attrib["name"].startswith("unconnected-"):
            name = net.attrib["name"]
            n = pcbnew.NETINFO_ITEM(board, name)
            board.Add(n)
            for node in net.findall("node"):
                nc[(node.attrib["ref"], node.attrib["pin"])] = n
    root_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:FPC01:root"))
    for p in parts:
        alias = p["footprint"].split(":")[1]
        fp = pcbnew.FootprintLoad(str(ROOT / "FPC01.pretty"), alias)
        assert fp is not None, p["ref"]
        fp.SetReference(p["ref"])
        fp.SetValue(p["part"])
        fp.GetField(pcbnew.FIELD_T_DATASHEET).SetText(p["source"])
        fp.GetField(pcbnew.FIELD_T_DATASHEET).SetVisible(False)
        fp.SetFPID(pcbnew.LIB_ID("FPC01", alias))
        symbol_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:FPC01:" + p["ref"]))
        fp.SetPath(pcbnew.KIID_PATH("/" + root_uuid + "/" + symbol_uuid))
        fp.Reference().SetLayer(pcbnew.F_Fab)
        fp.Reference().SetVisible(False)
        fp.Value().SetLayer(pcbnew.F_Fab)
        fp.Value().SetVisible(False)
        pose = plan["placements"][p["ref"]]
        fp.SetPosition(xy(*pose["anchor_mm"]))
        fp.SetOrientationDegrees(pose["rotation_deg"])
        pins = {n["number"]: n["net"] for n in p["pins"]}
        for pad in fp.Pads():
            number = pad.GetNumber()
            if not number:
                continue
            assert number in pins, (p["ref"], number)
            if pins[number] is not None:
                pad.SetNet(nets[pins[number]])
            else:
                pad.SetNet(nc[(p["ref"], number)])
        board.Add(fp)
    for start, end in [
        ((0, 0), (width, 0)),
        ((width, 0), (width, height)),
        ((width, height), (0, height)),
        ((0, height), (0, 0)),
    ]:
        edge = pcbnew.PCB_SHAPE()
        edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
        edge.SetLayer(pcbnew.Edge_Cuts)
        edge.SetStart(xy(*start))
        edge.SetEnd(xy(*end))
        edge.SetWidth(mm(0.05))
        board.Add(edge)
    # Dedicated In1 return reference; do not quietly route signals through it.
    plane = pcbnew.ZONE(board)
    plane.SetLayer(pcbnew.In1_Cu)
    plane.SetNet(nets["GND"])
    plane.SetLocalClearance(mm(0.2))
    plane.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    plane.SetMinThickness(mm(0.2))
    plane.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    outline = plane.Outline()
    outline.NewOutline()
    for x, y in [(0.5, 0.5), (width - 0.5, 0.5), (width - 0.5, height - 0.5), (0.5, height - 0.5)]:
        outline.Append(mm(x), mm(y))
    board.Add(plane)
    rule = pcbnew.ZONE(board)
    rule.SetLayer(pcbnew.In1_Cu)
    rule.SetIsRuleArea(True)
    rule.SetDoNotAllowTracks(True)
    rule.SetDoNotAllowVias(False)
    rule.SetDoNotAllowZoneFills(False)
    rule.SetDoNotAllowPads(False)
    rule.SetDoNotAllowFootprints(False)
    outline = rule.Outline()
    outline.NewOutline()
    for x, y in [(0.5, 0.5), (width - 0.5, 0.5), (width - 0.5, height - 0.5), (0.5, height - 0.5)]:
        outline.Append(mm(x), mm(y))
    board.Add(rule)

    def keepout(name, box, tracks, vias, pours):
        z = pcbnew.ZONE(board)
        z.SetLayer(pcbnew.F_Cu)
        z.SetIsRuleArea(True)
        z.SetZoneName(name)
        z.SetDoNotAllowTracks(tracks)
        z.SetDoNotAllowVias(vias)
        z.SetDoNotAllowZoneFills(pours)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        o = z.Outline()
        o.NewOutline()
        x0, y0, x1, y1 = box
        for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            o.Append(mm(x), mm(y))
        board.Add(z)

    # Conventional tented .30mm through holes: NO unfilled via-in-SMD-pad.
    for fp in list(board.GetFootprints()):
        for pad in fp.Pads():
            if not pad.GetNumber() or not pad.GetLayerSet().Contains(pcbnew.F_Cu) or pad.GetDrillSize().x:
                continue
            b = pad.GetBoundingBox()
            box = [
                pcbnew.ToMM(b.GetX()) - 0.1,
                pcbnew.ToMM(b.GetY()) - 0.1,
                pcbnew.ToMM(b.GetRight()) + 0.1,
                pcbnew.ToMM(b.GetBottom()) + 0.1,
            ]
            keepout("NO_UNFILLED_VIP_" + fp.GetReference() + "_" + pad.GetNumber(), box, False, True, False)
    # ABLS metal case: only its manufacturer lands may contain F copper.
    # Two land windows remain open, all other body regions reject tracks/pours.
    keepout("XTAL_BODY_NO_VIA", [42.7, 3.075, 54.3, 7.925], False, True, False)
    for n, box in enumerate(
        [[42.7, 3.075, 54.3, 4.45], [42.7, 6.55, 54.3, 7.925], [46.55, 4.45, 50.45, 6.55]]
    ):
        keepout("XTAL_BODY_COPPER_EXCLUSION_" + str(n), box, True, True, True)
    pcbnew.SaveBoard(str(ROOT / "fan_power_health.kicad_pcb"), board)
    tree = read_sexpr((ROOT / "fan_power_health.kicad_pcb").read_text())
    setup = first(tree, "setup")
    layers = []
    for n, name in enumerate(["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]):
        layers.append([a("layer"), name, [a("type"), "copper"], [a("thickness"), 0.035]])
        if n < 3:
            layers.append(
                [
                    a("layer"),
                    "dielectric " + str(n + 1),
                    [a("type"), "core" if n == 1 else "prepreg"],
                    [a("thickness"), [0.2, 1.06, 0.2][n]],
                    [a("material"), "FR4_RECEIVING_UNACCEPTED"],
                    [a("epsilon_r"), 4.5],
                    [a("loss_tangent"), 0.02],
                ]
            )
    setup.append(
        [a("stackup"), *layers, [a("copper_finish"), "None"], [a("dielectric_constraints"), a("no")]]
    )
    (ROOT / "fan_power_health.kicad_pcb").write_text(sexpr(tree) + "\n")
    project = dict(
        meta=dict(filename="fan_power_health.kicad_pro", version=1),
        board=dict(
            design_settings=dict(
                rules=dict(
                    min_clearance=0.16,
                    min_track_width=0.16,
                    min_copper_edge_clearance=0.5,
                    min_hole_clearance=0.25,
                    min_through_hole_diameter=0.3,
                    min_via_annular_width=0.15,
                )
            )
        ),
        net_settings=dict(
            classes=[dict(name="Default", clearance=0.2, track_width=0.2, via_diameter=0.65, via_drill=0.3)]
        ),
    )
    (ROOT / "fan_power_health.kicad_pro").write_text(json.dumps(project, indent=2) + "\n")
    # KiCad stores copper/laminate dimensions, not through-hole wall bounds.
    construction = dict(
        board_nominal_thickness_mm=1.6,
        finished_Cu_minimum_required_um=[35, 35, 35, 35],
        proposed_dielectric_mm=[0.2, 1.06, 0.2],
        via_finished_bore_mm=0.3,
        via_land_mm=0.65,
        minimum_via_wall_receiving_um=25,
        via_wall_maximum_approved_um=None,
        material_and_microsection_qualified=False,
        fabricator_DFM_approved=False,
        native_stack_is_lower_bound_scenario_NOT_accepted_fabrication_template=True,
    )
    (ROOT / "construction.json").write_text(json.dumps(construction, indent=2) + "\n")
    board = pcbnew.LoadBoard(str(ROOT / "fan_power_health.kicad_pcb"))
    data = []
    for fp in board.GetFootprints():
        pads = []
        for p in fp.Pads():
            if not p.GetNumber():
                continue
            pads.append(
                dict(
                    number=p.GetNumber(),
                    net=p.GetNetname() or None,
                    centre_mm=[pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)],
                    size_mm=[pcbnew.ToMM(p.GetSize().x), pcbnew.ToMM(p.GetSize().y)],
                    orientation_degrees=p.GetOrientationDegrees(),
                    drill_mm=[pcbnew.ToMM(p.GetDrillSize().x), pcbnew.ToMM(p.GetDrillSize().y)],
                )
            )
        data.append(dict(ref=fp.GetReference(), value=fp.GetValue(), pads=pads))
    (ROOT / "generated/native-pad-geometry.json").write_text(json.dumps(data, indent=2) + "\n")
    check()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        check(sys.argv[1])
    else:
        build()
