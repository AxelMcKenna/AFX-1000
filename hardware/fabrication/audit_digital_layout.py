"""Verify DC01 placement against native reports and the original circuit export."""

import argparse
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from shapely.geometry import LineString, Polygon, box
from shapely.ops import polygonize

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.audit_digital_core import verify_export

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "hardware/fabrication/staging/digital-core-placement-03"
PROFILE = [(0,0),(64,0),(64,3),(104,3),(104,9),(114,9),(114,60),(0,60)]


def check():
    construction = json.loads((OUT/"construction.json").read_text())
    native = json.loads((OUT/"placement-native-review.json").read_text())
    for record in (construction,native):
        assert all(sha(REPO/p)==h for p,h in record["source_sha256"].items()), "Changed placement inputs"
    assert all(sha(OUT/p)==h for p,h in native["raw_report_sha256"].items())
    drc,erc = [json.loads((OUT/p).read_text()) for p in ("drc.json","erc.json")]
    assert drc["violations"] == drc["schematic_parity"] == drc["ignored_checks"] == []
    assert erc["ignored_checks"] == [] and not any(s["violations"] for s in erc["sheets"])
    assert all(c["returncode"]==0 for c in native["complete_native_commands"])
    assert native["DRC_geometry_findings"] == native["schematic_parity_findings"] == native["ERC_findings"] == 0
    assert native["uncapped_open_connections"] == 466 and len(drc["unconnected_items"]) == 466
    parts,pins = netlist(OUT/"native-netlist.xml")
    verify_export(parts,pins)
    tree = read_sexpr((OUT/"digital_core.kicad_pcb").read_text())
    profiles = list(polygonize([LineString([tuple(map(float,first(n,k)[1:3])) for k in ("start","end")])
                               for n in children(tree,"gr_line") if first(n,"layer")[1]=="Edge.Cuts"]))
    assert len(profiles)==1 and profiles[0].equals(Polygon(PROFILE)) and profiles[0].area==6630
    assert float(first(first(tree,"general"),"thickness")[1])==1.6
    assert not children(tree,"segment") and not children(tree,"via"), "Placed-only checkpoint acquired unreviewed copper"
    raw = ET.parse(OUT/"native-netlist.xml")
    expected_pins = {(n.attrib["ref"],n.attrib["pin"]):net.attrib["name"]
                     for net in raw.findall("nets/net") for n in net.findall("node")}
    refmap = {next(p[2] for p in children(fp,"property") if p[1]=="Reference"):fp for fp in children(tree,"footprint")}
    mounts = {f"H{i}":p for i,p in enumerate([(4,4),(66,13),(110,25),(4,36),(110,44)],1)}
    assert set(refmap)==set(parts)|set(mounts)
    courts,sides,through = {},{},{}
    for ref,fp in refmap.items():
        side = str(first(fp,"layer")[1]).split(".")[0]
        bbox = courtyard(fp,side+".CrtYd")
        courts[ref],sides[ref] = box(*bbox),side
        assert profiles[0].covers(courts[ref]), ("Outside board profile",ref)
        if ref in parts:
            assert courts[ref].distance(profiles[0].boundary)>=.5-1e-8, ("Insufficient edge allocation",ref)
            assert fp[1]==parts[ref].findtext("footprint")
            assert next(p[2] for p in children(fp,"property") if p[1]=="Value")==parts[ref].findtext("value")
            actual = {str(p[1]):str(first(p,"net")[-1]) for p in children(fp,"pad") if str(p[1])}
            assert actual=={pin:net for (r,pin),net in expected_pins.items() if r==ref}, ("Board pin parity",ref)
        else:
            assert tuple(map(float,first(fp,"at")[1:3]))==tuple(mounts[ref])
            assert len(children(fp,"pad"))==1 and children(fp,"pad")[0][2]=="np_thru_hole"
        holes = []
        for p in children(fp,"pad"):
            if p[2]!="thru_hole":
                continue
            x,y = transform(fp,first(p,"at")[1:3])
            sx,sy = map(float,first(p,"size")[1:3])
            # All present THT lands are square/circular; rotation leaves this
            # conservative axis-aligned solder receiving box unchanged.
            assert abs(sx-sy)<1e-8
            holes.append(box(x-sx/2-.5,y-sy/2-.5,x+sx/2+.5,y+sy/2+.5))
        through[ref]=holes
    electrical = sorted(parts)
    for i,ref in enumerate(electrical):
        for other in electrical[i+1:]:
            if sides[ref]==sides[other]:
                assert courts[ref].distance(courts[other])>=.3-1e-8, ("Body clearance",ref,other)
            else:
                assert not any(courts[ref].intersection(p).area>1e-10 for p in through[other]), ("THT solder/body collision",other,ref)
                assert not any(courts[other].intersection(p).area>1e-10 for p in through[ref]), ("THT solder/body collision",ref,other)
        for mount in mounts.values():
            assert courts[ref].distance(box(mount[0]-3.6,mount[1]-3.6,mount[0]+3.6,mount[1]+3.6))>=.15-1e-8
    paths = [Path(__file__),OUT/"construction.json",OUT/"placement-native-review.json",OUT/"digital_core.kicad_pcb",OUT/"native-netlist.xml"]
    return dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},electrical_parts=138,
        exported_physical_terminals=sum(len(v) for v in pins.values()),mounting_holes=5,
        parts_by_side=dict(Counter(sides[r] for r in parts)),PCB_area_mm2=6630,
        native_geometry_findings=0,native_schematic_parity_findings=0,native_ERC_findings=0,
        all_native_categories_enabled=True,uncapped_open_connections=466,
        retained_component_values_lands_and_pin_nets_match_original_circuits=True,
        opposite_face_solder_and_body_screen_passes_with_declared_limits=True,
        PCB_routed=False,complete_mechanical_receiving_qualified=False,fabrication_released=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    result=check()
    path=OUT/"placement-handoff.json"
    if args.check:
        assert result==json.loads(path.read_text())
    else:
        with path.open("x") as stream:
            json.dump(result,stream,indent=2)
            stream.write("\n")
    print("Digital placement: 138 parts; five mounts; geometry/parity/ERC 0; 466 opens; all categories enabled")
