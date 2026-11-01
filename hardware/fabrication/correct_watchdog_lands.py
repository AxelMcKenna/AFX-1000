"""Separate routed-board candidates with only declared watchdog-land changes."""

import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.package_lands import DRB, LIBRARY, footprint

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
CHANGES = {"negative_startup_protection": ("nf-watchdog-land-01", {"U3","U9"}),
           "fan_health_protection": ("fan-watchdog-land-01", {"U4"})}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(node):
    return next(str(p[2]) for p in children(node,"property") if p[1] == "Reference")


def replace_footprint(old):
    new = footprint(DRB)
    copied = {"at","uuid","path","sheetname","sheetfile"}
    new[:] = [n for n in new if not (isinstance(n,list) and n and n[0] == "property")]
    new.extend(n for n in old if isinstance(n,list) and n and (n[0] in copied or n[0] == "property"))
    nets = {str(p[1]):first(p,"net") for p in children(old,"pad") if str(p[1]) and children(p,"net")}
    assert set(nets) == {str(i) for i in range(1,10)}
    for pad in children(new,"pad"):
        if str(pad[1]):
            pad.append(nets[str(pad[1])])
    return new


def run():
    scope = json.loads((ROOT/"scope.json").read_text())
    for row in scope["roles"]:
        if row["role"] not in CHANGES:
            continue
        label, targets = CHANGES[row["role"]]
        project = REPO/row["source"]
        source, name = project.parent, project.stem
        output = ROOT/"staging"/label
        output.mkdir(exist_ok=False)
        inputs = [source/(name+suffix) for suffix in (".kicad_pro",".kicad_sch",".kicad_pcb")]
        inputs += [source/f for f in ("fp-lib-table","sym-lib-table","netlist.xml")]
        hashes = {str(p):sha(p) for p in inputs}
        for p in inputs:
            shutil.copyfile(p,output/p.name)
        for p in (source/"libraries").rglob("*"):
            if p.is_file():
                hashes[str(p)] = sha(p)
        shutil.copytree(source/"libraries",output/"libraries")
        local = output/(LIBRARY+".pretty")
        local.mkdir()
        (local/(DRB+".kicad_mod")).write_text(sexpr(footprint(DRB))+"\n")
        table = read_sexpr((output/"fp-lib-table").read_text())
        table.append([a("lib"),[a("name"),LIBRARY],[a("type"),"KiCad"],
                      [a("uri"),"${KIPRJMOD}/"+local.name],[a("options"),""],[a("descr"),"Own TI DRB0008A central-land transcription"]])
        (output/"fp-lib-table").write_text(sexpr(table)+"\n")
        pcb = output/(name+".kicad_pcb")
        tree = read_sexpr(pcb.read_text())
        changed = []
        for index,node in enumerate(tree):
            if isinstance(node,list) and node and node[0] == "footprint" and ref(node) in targets:
                assert "VSON-8-1EP_3x3mm_P0.65mm_EP1.65x2.4mm" in str(node[1])
                changed.append(dict(ref=ref(node),old_FPID=str(node[1]),new_FPID=LIBRARY+":"+DRB))
                tree[index] = replace_footprint(node)
        assert {r["ref"] for r in changed} == targets
        pcb.write_text(sexpr(tree)+"\n")
        schematic = output/(name+".kicad_sch")
        sch = read_sexpr(schematic.read_text())
        count = 0
        for symbol in children(sch,"symbol"):
            if ref(symbol) in targets:
                prop = next(p for p in children(symbol,"property") if p[1] == "Footprint")
                prop[2] = LIBRARY+":"+DRB
                count += 1
        assert count == len(targets)
        schematic.write_text(sexpr(sch)+"\n")
        xml = output/"netlist.xml"
        netlist = ET.parse(xml)
        for part in netlist.getroot().findall("./components/comp"):
            if part.attrib["ref"] in targets:
                part.find("footprint").text = LIBRARY+":"+DRB
        netlist.write(xml,encoding="utf-8",xml_declaration=True)
        assert all(sha(Path(p)) == digest for p,digest in hashes.items())
        (output/"construction.json").write_text(json.dumps(dict(source_sha256=hashes,
            recipe_sha256=sha(Path(__file__)),land_recipe_sha256=sha(ROOT/"package_lands.py"),changes=changed,
            pin_nets_values_and_component_poses_unchanged=True,old_tracks_vias_drills_and_zones_unchanged=True,
            native_checks_pending=True,assembly_process_accepted=False,physical_qualified=False,
            fabrication_released=False),indent=2)+"\n")
        print(label,"updated",sorted(targets),"only; native checks pending")


if __name__ == "__main__":
    run()
