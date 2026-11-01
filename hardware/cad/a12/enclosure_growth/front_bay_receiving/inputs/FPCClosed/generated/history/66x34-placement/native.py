"""Actual NEW 4-layer PCB from FPC01 placed parts. Run with KiCad Python3.9."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid
import xml.etree.ElementTree as ET

import pcbnew

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mm(x):return pcbnew.FromMM(float(x))
def xy(x,y):return pcbnew.VECTOR2I(mm(x),mm(y))


def check(label="placement"):
    path=ROOT/"fan_power_health.kicad_pcb"
    board=pcbnew.LoadBoard(str(path))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(path),board)
    before=sha(path)
    report=ROOT/"generated"/(label+"-drc.json")
    cli="/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    env=dict(os.environ,KICAD_CONFIG_HOME="/private/tmp/rmx-kicad-config",FONTCONFIG_FILE=str(REPO/"build-hardware/kicad-fonts.conf"))
    command=[cli,"pcb","drc","--schematic-parity","--format","json","--output",str(report),str(path)]
    p=subprocess.run(command,env=env,capture_output=True,text=True)
    (ROOT/"generated"/(label+"-drc.log")).write_text(p.stdout+p.stderr)
    assert p.returncode in (0,5),(p.returncode,p.stderr)
    data=json.loads(report.read_text())
    parts=json.loads((ROOT/"components.json").read_text())
    expected={p["ref"]:{n["number"]:n["net"] for n in p["pins"]} for p in parts}
    actual={fp.GetReference():{p.GetNumber():(None if p.GetNetname().lstrip("/").startswith("unconnected-") else p.GetNetname().lstrip("/") or None) for p in fp.Pads() if p.GetNumber()} for fp in board.GetFootprints()}
    assert actual==expected,(set(actual)^set(expected))
    record=dict(label=label,parts=len(actual),native_pad_net_parity_differences=0,
        hard_errors=sum(v["severity"]=="error" for v in data["violations"]),
        warnings=sum(v["severity"]=="warning" for v in data["violations"]),
        unconnected=len(data.get("unconnected_items",[])),schematic_parity=len(data.get("schematic_parity",[])),
        pcb_sha256=before,source_unchanged_by_cli=sha(path)==before,raw_report_sha256=sha(report),
        command=command,returncode=p.returncode,tracks=len(list(board.GetTracks())),zones=board.GetAreaCount(),
        physical_qualified=False,fabrication_released=False)
    (ROOT/"generated"/(label+"-native.json")).write_text(json.dumps(record,indent=2)+"\n")
    (ROOT/"generated/current-native.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps(record))


def build():
    assert not (ROOT/"handoff.json").exists(),"Preserve sealed candidate"
    parts=json.loads((ROOT/"components.json").read_text())
    plan=json.loads((ROOT/"generated/placement.json").read_text())
    board=pcbnew.BOARD();board.SetCopperLayerCount(4)
    board.GetDesignSettings().SetBoardThickness(mm(1.6))
    nets={}
    for name in sorted({p["net"] for c in parts for p in c["pins"] if p["net"] is not None}):
        n=pcbnew.NETINFO_ITEM(board,"/"+name);board.Add(n);nets[name]=n
    nc={}
    for net in ET.parse(ROOT/"generated/netlist.xml").findall("./nets/net"):
        if net.attrib["name"].startswith("unconnected-"):
            name=net.attrib["name"];n=pcbnew.NETINFO_ITEM(board,name);board.Add(n)
            for node in net.findall("node"):nc[(node.attrib["ref"],node.attrib["pin"])]=n
    root_uuid=str(uuid.uuid5(uuid.NAMESPACE_URL,"rmx:FPC01:root"))
    for p in parts:
        alias=p["footprint"].split(":")[1]
        fp=pcbnew.FootprintLoad(str(ROOT/"FPC01.pretty"),alias)
        assert fp is not None,p["ref"]
        fp.SetReference(p["ref"]);fp.SetValue(p["part"])
        fp.GetField(pcbnew.FIELD_T_DATASHEET).SetText(p["source"])
        fp.GetField(pcbnew.FIELD_T_DATASHEET).SetVisible(False)
        fp.SetFPID(pcbnew.LIB_ID("FPC01",alias))
        symbol_uuid=str(uuid.uuid5(uuid.NAMESPACE_URL,"rmx:FPC01:"+p["ref"]))
        fp.SetPath(pcbnew.KIID_PATH("/"+root_uuid+"/"+symbol_uuid))
        fp.Reference().SetLayer(pcbnew.F_Fab);fp.Reference().SetVisible(False)
        fp.Value().SetLayer(pcbnew.F_Fab);fp.Value().SetVisible(False)
        pose=plan["placements"][p["ref"]]
        fp.SetPosition(xy(*pose["anchor_mm"]));fp.SetOrientationDegrees(pose["rotation_deg"])
        pins={n["number"]:n["net"] for n in p["pins"]}
        for pad in fp.Pads():
            number=pad.GetNumber()
            if not number:continue
            assert number in pins,(p["ref"],number)
            if pins[number] is not None:pad.SetNet(nets[pins[number]])
            else:pad.SetNet(nc[(p["ref"],number)])
        board.Add(fp)
    for a,b in [((0,0),(66,0)),((66,0),(66,34)),((66,34),(0,34)),((0,34),(0,0))]:
        edge=pcbnew.PCB_SHAPE();edge.SetShape(pcbnew.SHAPE_T_SEGMENT);edge.SetLayer(pcbnew.Edge_Cuts)
        edge.SetStart(xy(*a));edge.SetEnd(xy(*b));edge.SetWidth(mm(.05));board.Add(edge)
    # Dedicated In1 return reference; do not quietly route signals through it.
    plane=pcbnew.ZONE(board);plane.SetLayer(pcbnew.In1_Cu);plane.SetNet(nets["GND"])
    plane.SetLocalClearance(mm(.2));plane.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    plane.SetMinThickness(mm(.2));plane.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    outline=plane.Outline();outline.NewOutline()
    for x,y in [(.5,.5),(65.5,.5),(65.5,33.5),(.5,33.5)]:outline.Append(mm(x),mm(y))
    board.Add(plane)
    rule=pcbnew.ZONE(board);rule.SetLayer(pcbnew.In1_Cu);rule.SetIsRuleArea(True)
    rule.SetDoNotAllowTracks(True);rule.SetDoNotAllowVias(False);rule.SetDoNotAllowZoneFills(False)
    rule.SetDoNotAllowPads(False);rule.SetDoNotAllowFootprints(False)
    outline=rule.Outline();outline.NewOutline()
    for x,y in [(.5,.5),(65.5,.5),(65.5,33.5),(.5,33.5)]:outline.Append(mm(x),mm(y))
    board.Add(rule)
    pcbnew.SaveBoard(str(ROOT/"fan_power_health.kicad_pcb"),board)
    project=dict(meta=dict(filename="fan_power_health.kicad_pro",version=1),
        board=dict(design_settings=dict(rules=dict(min_clearance=.16,min_track_width=.16,
            min_copper_edge_clearance=.5,min_hole_clearance=.25,min_through_hole_diameter=.3,
            min_via_annular_width=.15))),
        net_settings=dict(classes=[dict(name="Default",clearance=.2,track_width=.2,via_diameter=.65,via_drill=.3)]))
    (ROOT/"fan_power_health.kicad_pro").write_text(json.dumps(project,indent=2)+"\n")
    # KiCad stores copper/laminate dimensions, not through-hole wall bounds.
    construction=dict(board_nominal_thickness_mm=1.6,finished_Cu_minimum_required_um=[35,35,35,35],
        proposed_dielectric_mm=[.2,1.06,.2],via_finished_bore_mm=.3,via_land_mm=.65,
        minimum_via_wall_receiving_um=25,via_wall_maximum_approved_um=None,
        material_and_microsection_qualified=False,fabricator_DFM_approved=False,
        native_stack_is_lower_bound_scenario_NOT_accepted_fabrication_template=True)
    (ROOT/"construction.json").write_text(json.dumps(construction,indent=2)+"\n")
    board=pcbnew.LoadBoard(str(ROOT/"fan_power_health.kicad_pcb"))
    data=[]
    for fp in board.GetFootprints():
        pads=[]
        for p in fp.Pads():
            if not p.GetNumber():continue
            pads.append(dict(number=p.GetNumber(),net=p.GetNetname() or None,
                centre_mm=[pcbnew.ToMM(p.GetPosition().x),pcbnew.ToMM(p.GetPosition().y)],
                size_mm=[pcbnew.ToMM(p.GetSize().x),pcbnew.ToMM(p.GetSize().y)],
                orientation_degrees=p.GetOrientationDegrees(),
                drill_mm=[pcbnew.ToMM(p.GetDrillSize().x),pcbnew.ToMM(p.GetDrillSize().y)]))
        data.append(dict(ref=fp.GetReference(),value=fp.GetValue(),pads=pads))
    (ROOT/"generated/native-pad-geometry.json").write_text(json.dumps(data,indent=2)+"\n")
    check()


if __name__=="__main__":
    import sys
    if len(sys.argv)>1:check(sys.argv[1])
    else:build()
