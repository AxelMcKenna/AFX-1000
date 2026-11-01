"""Integrate the eight AX03 source parts into a separate P03 prototype.

Preserve the complete combined thermal-repair source. Placement and subsequent
native routing are separate gates; this module never releases fabrication.
"""

import argparse
import copy
import hashlib
import json
import math
import shutil
from pathlib import Path

from shapely.affinity import translate
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from shapely.prepared import prep

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.placement import placed_footprint
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.electronics.power_distribution.p03.route import PowerRouter, coded, named
from hardware.electronics.power_distribution.p03.spec import MOUNTS, THERMAL_REGIONS

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(__file__).resolve().parent
P03 = REPO / "hardware/electronics/power_distribution/p03"
SOURCE = P03 / "candidates/aux-u10-combined"
WORK = P03 / "candidates/ax03-run-transmitter"
REFS = {"U1": "U201", "U2": "U202", "R1": "R401", "R2": "R402", "R4": "R403",
        "C1": "C401", "C2": "C402", "C3": "C403"}
NETS = {"AUX": "V2V5_AUX", "POWER_RUN_INTERNAL": "POWER_RUN",
        "RUN_GATE_COMMAND": "AX03_SOURCE_RESET", "RUN_BUFFERED_SOURCE": "AX03_RUN_DRIVE",
        "RUN_CT": "AX03_SOURCE_CT", "POWER_RUN_E28_LEAF": "POWER_RUN_E28_LEAF", "AGND": "AGND"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(fp):
    return next(p[2] for p in children(fp, "property") if p[1] == "Reference")


def land(path, name):
    tree = read_sexpr(path.read_text())
    tree[1] = name
    for text in children(tree, "fp_text"):
        if text[1] in ("reference", "value"):
            text[0] = a("property")
            text[1] = "Reference" if text[1] == "reference" else "Value"
    return tree


def geometries(router, layer, net):
    result = []
    for g in router.geometry:
        if layer not in g["layers"] or g["net"] == net:
            continue
        if g["kind"] == "line":
            result.append(LineString([g["start"], g["end"]]).buffer(g["width"] / 2))
        elif g["kind"] == "via":
            result.append(Point(g["xy"]).buffer(g["radius"]))
        elif g["kind"] == "rect":
            x, y = g["xy"]
            w, h = g["size"]
            result.append(box(x-w/2, y-h/2, x+w/2, y+h/2))
    return result


def stage():
    assert not WORK.exists()
    inputs = [SOURCE / n for n in ("power_p03.kicad_pcb", "power_p03.kicad_sch", "power_p03.kicad_pro",
              "power_p03.kicad_dru", "components.json", "generated/current-native.json")]
    hashes = {str(p): sha(p) for p in inputs}
    receipt = json.loads(inputs[-1].read_text())
    assert receipt["pcb_sha256"] == hashes[str(inputs[0])]
    assert receipt["native_counts"] == dict(ERC=0, DRC=0, parity=0, opens=0)
    parts = json.loads((SOURCE / "components.json").read_text())
    original_parts = copy.deepcopy(parts)
    assert len(parts) == 256 and not set(REFS.values()) & {c["ref"] for c in parts}
    extras = []
    for index, original in enumerate(json.loads((ROOT / "components.json").read_text())):
        if original["ref"] not in REFS:
            continue
        c = copy.deepcopy(original)
        c.update(ref=REFS[c["ref"]], x=152.4*(index % 8)+76.2, y=3340.1)
        for p in c["pins"]:
            if p["net"] is not None:
                p["net"] = NETS[p["net"]]
        c["footprint"] = "RMX_AX03_P03:" + ("TI_DSE0006A" if c["ref"] == "U201" else
            "TI_DCK0005A" if c["ref"] == "U202" else "R0805" if c["ref"] in ("R401", "R402") else
            "R1206" if c["ref"] == "R403" else "C0603")
        if c["ref"] == "R402":
            c.update(part="10M 1% CRCW080510M0FKEA", source="https://www.vishay.com/docs/20035/dcrcwe3.pdf")
        if c["ref"] == "R403":
            c["source"] = "https://www.vishay.com/docs/20035/dcrcwe3.pdf"
        if c["ref"] in ("C401", "C402"):
            c["source"] = "https://search.kemet.com/component-documentation/download/specsheet/C0603C104K5RACTU"
        extras.append(c)
    assert len(extras) == 8
    next(p for c in parts if c["ref"] == "J106" for p in c["pins"] if p["number"] == "3")["net"] = "POWER_RUN_E28_LEAF"
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for p in SOURCE.glob("*.pretty"):
        shutil.copytree(p, WORK / p.name)
    for name in ("power_p03.kicad_pro", "power_p03.kicad_dru", "construction.json", "component-selections.json"):
        shutil.copyfile(SOURCE / name, WORK / name)
    lands = {
        "TI_DSE0006A": REPO / "hardware/electronics/rail_disconnect/revision28/RMX_E28.pretty/TPS389001_DSE0006A.kicad_mod",
        "TI_DCK0005A": ROOT / "RMX_AX03.pretty/TI_DCK0005A.kicad_mod",
        "C0603": ROOT.parent / "fan_health/composite_nf_branch/FPC01.pretty/Capacitor_SMD__C_0603_1608Metric.kicad_mod",
        "R0805": ROOT.parent / "fan_health/composite_nf_branch/FPC01.pretty/Resistor_SMD__R_0805_2012Metric.kicad_mod",
        "R1206": ROOT.parent / "nf_connector_receiving265/inputs/NF261/sources/footprints/Resistor_SMD.pretty/R_1206_3216Metric.kicad_mod",
    }
    library = WORK / "RMX_AX03_P03.pretty"
    library.mkdir()
    for name, path in lands.items():
        hashes[str(path)] = sha(path)
        (library / (name + ".kicad_mod")).write_text(sexpr(land(path, name)) + "\n")
    # Reuse the original schematic's supply flags and annotations; add the new
    # source cell below the existing last row without moving original symbols.
    schematic = read_sexpr((SOURCE / "power_p03.kicad_sch").read_text())
    flags = []
    for symbol in children(schematic, "symbol"):
        if str(first(symbol, "lib_id")[1]).endswith(":SUPPLY_FLAG"):
            x, y = map(float, first(symbol, "at")[1:3])
            label = next(n for n in children(schematic, "label") if tuple(map(float, first(n, "at")[1:3])) == (x, y))
            flags.append((str(label[1]), x, y))
    generate(WORK, "P03", "power_p03", parts + extras,
        [(30, 3500, "AX03 prototype: only J106.3 buffered; internal POWER_RUN, R113 and PG topology retained. No physical/fabrication release.")],
        (1300, 3550), flags)
    # Keep J103's original non-BOM semantics exactly.
    tree = read_sexpr((WORK / "power_p03.kicad_sch").read_text())
    for symbol in children(tree, "symbol"):
        if any(p[1:3] == ["Reference", "J103"] for p in children(symbol, "property")):
            first(symbol, "in_bom")[1] = a("no")
    for symbol in children(first(tree, "lib_symbols"), "symbol"):
        if str(symbol[1]).endswith("_J103"):
            first(symbol, "in_bom")[1] = a("no")
    (WORK / "power_p03.kicad_sch").write_text(sexpr(tree) + "\n")
    symbols = WORK / "RMX_P03.kicad_sym"
    tree = read_sexpr(symbols.read_text())
    for symbol in children(tree, "symbol"):
        if str(symbol[1]).endswith("_J103"):
            first(symbol, "in_bom")[1] = a("no")
    symbols.write_text(sexpr(tree) + "\n")
    bom = WORK / "bom.csv"
    bom.write_text("\n".join(line for line in bom.read_text().splitlines() if not line.startswith("J103,")) + "\n")
    board = coded(read_sexpr(inputs[0].read_text()))
    codes = {str(n[2]).lstrip("/"): int(n[1]) for n in children(board, "net")}
    for name in NETS.values():
        if name not in codes:
            codes[name] = max(codes.values()) + 1
            board.append([a("net"), a(codes[name]), "/" + name])
    codes["NC"] = 0
    j106 = next(f for f in children(board, "footprint") if ref(f) == "J106")
    pad = next(p for p in children(j106, "pad") if p[1] == "3")
    first(pad, "net")[1:] = [a(codes["POWER_RUN_E28_LEAF"]), "/POWER_RUN_E28_LEAF"]
    # Isolate only original RUN copper inside the new output-pad clearance box.
    # Any internal trunk break is left explicit for subsequent native routing.
    cut = box(17.7, 17.7, 20.3, 20.3)
    removed = []
    for n in list(children(board, "segment")):
        if str(first(n, "net")[1]) == str(codes["POWER_RUN"]):
            line = LineString([tuple(float(v)-100 for v in first(n, key)[1:3]) for key in ("start", "end")])
            if line.buffer(float(first(n, "width")[1])/2).intersects(cut):
                removed.append(sexpr(n))
                board.remove(n)
    (WORK / "power_p03.kicad_pcb").write_text(sexpr(named(board)) + "\n")
    assert all(sha(Path(p)) == digest for p, digest in hashes.items())
    (WORK / "generated/integration.json").write_text(json.dumps(dict(source_sha256=hashes,
        original_parts=original_parts, added_refs=sorted(REFS.values()), net_mapping=NETS,
        removed_internal_RUN_segments=removed, original_part_delta="Only J106.3 net changes",
        all_original_footprint_poses_and_force_copper_preserved=True,
        new_parts_not_yet_placed=True, PCB_routing_complete=False,
        physical_qualified=False, fabrication_released=False), indent=2)+"\n")
    print("Staged264-part paired P03 schematic; eight source parts await physical placement/routing")


def place():
    output = WORK / "generated/placement"
    assert not output.exists()
    board = coded(read_sexpr((WORK / "power_p03.kicad_pcb").read_text()))
    source_digest = sha(WORK / "power_p03.kicad_pcb")
    r = PowerRouter(board)
    parts = {c["ref"]: c for c in json.loads((WORK / "components.json").read_text())}
    codes = {str(n[2]).lstrip("/"): int(n[1]) for n in children(board, "net")}
    for name in {p["net"] for c in parts.values() for p in c["pins"] if p["net"] is not None}:
        if name not in codes:
            codes[name] = max(codes.values()) + 1
            board.append([a("net"), a(codes[name]), "/" + name])
    codes["NC"] = 0
    net_nodes = children(board, "net")
    occupied = []
    for f in children(board, "footprint"):
        if first(f, "layer")[1] == "F.Cu":
            occupied.append(box(*[v-100 for v in courtyard(f, "F.CrtYd")]).buffer(.2))
    occupied += [Point(p).buffer(3.7) for p in MOUNTS]
    occupied += [box(*p).buffer(.25) for p in THERMAL_REGIONS.values()]
    # Leave the guard/LDO contact field, including its named adjacent barrels,
    # available for receiving TIM and refreshed thermal extraction.
    occupied.append(box(20, 15, 33.5, 27.5))
    body_block = prep(unary_union(occupied))
    baseline = {}
    for net in {p["net"] or "NC" for name in REFS.values() for p in parts[name]["pins"]}:
        baseline[net] = prep(unary_union(geometries(r, 0, net)).buffer(.170001))
    templates = {}
    for name in REFS.values():
        c = parts[name]
        path = WORK / (c["footprint"].split(":")[0] + ".pretty") / (c["footprint"].split(":")[1] + ".kicad_mod")
        for angle in (0, 90, 180, 270):
            f = placed_footprint(dict(c, value=c["part"], mpn=c["part"],
                    nets={p["number"]: p["net"] or "NC" for p in c["pins"]}),
                    (0, 0, angle, "F"), path, codes, namespace="rmx:P03:AX03:")
            for pad in children(f, "pad"):
                if any(p["number"] == pad[1] and p["net"] is None for p in c["pins"]):
                    pad[:] = [n for n in pad if not (isinstance(n, list) and n and n[0] == "net")]
            small = PowerRouter([a("kicad_pcb"), *copy.deepcopy(net_nodes), f])
            templates[name, angle] = (f, box(*[v-100 for v in courtyard(f, "F.CrtYd")]),
                [(g["net"], box(g["xy"][0]-g["size"][0]/2, g["xy"][1]-g["size"][1]/2,
                                g["xy"][0]+g["size"][0]/2, g["xy"][1]+g["size"][1]/2))
                 for g in small.geometry if g["kind"] == "rect"])
    added = []
    poses = {}

    def trial(name, x, y, angle, temporary=()):
        f, body, pads = templates[name, angle]
        body = translate(body, x, y)
        bounds = body.bounds
        if not (.65 < bounds[0] and bounds[2] < 159.35 and .65 < bounds[1] and bounds[3] < 44.35):
            return None
        if bounds[3] > 34.5 and (bounds[0] < 6.5 or bounds[2] > 151.5):
            return None
        if body_block.intersects(body) or any(body.distance(old[1]) < .2 for old in (*added, *temporary)):
            return None
        pads = [(net, translate(p, x, y)) for net, p in pads]
        if any(baseline.get(net, baseline["NC"]).intersects(p) for net, p in pads):
            return None
        if any(net != other_net and p.distance(other) < .17 for net, p in pads
               for old in (*added, *temporary) for other_net, other in old[2]):
            return None
        fp = copy.deepcopy(f)
        first(fp, "at")[1:3] = [100+x, 100+y]
        return (fp, body, pads)

    def centres(target):
        return sorted(((x/2, y/2) for x in range(3, 317) for y in range(3, 88)),
                      key=lambda p: math.dist(p, target))

    for controller, cap, target in (("U201", "C402", (15, 19)), ("U202", "C401", (15, 23))):
        selected = None
        for x, y in centres(target):
            for angle in (0, 90, 180, 270):
                candidate = trial(controller, x, y, angle)
                if candidate is None:
                    continue
                for dx, dy in ((2.75, 0), (-2.75, 0), (0, 2.5), (0, -2.5), (2, 2), (-2, 2), (2, -2), (-2, -2)):
                    for cap_angle in (0, 90, 180, 270):
                        bypass = trial(cap, x+dx, y+dy, cap_angle, (candidate,))
                        if bypass is not None:
                            selected = (candidate, bypass)
                            poses[controller], poses[cap] = [x, y, angle, "F"], [x+dx, y+dy, cap_angle, "F"]
                            break
                    if selected:
                        break
                if selected:
                    break
            if selected:
                break
        assert selected is not None, (controller, "No clear same-face controller/bypass pair")
        added.extend(selected)
    for name in ("C403", "R401", "R402", "R403"):
        target = poses["U201"][:2] if name != "R403" else (19, 19)
        selected = None
        for x, y in centres(target):
            for angle in (0, 90, 180, 270):
                selected = trial(name, x, y, angle)
                if selected:
                    poses[name] = [x, y, angle, "F"]
                    break
            if selected:
                break
        assert selected is not None, (name, "No copper-clear position")
        added.append(selected)
    board.extend(p[0] for p in added)
    output.mkdir()
    pcb = output / "power_p03.kicad_pcb"
    pcb.write_text(sexpr(named(board))+"\n")
    assert sha(WORK / "power_p03.kicad_pcb") == source_digest
    (output / "placement.json").write_text(json.dumps(dict(source_pcb_sha256=source_digest,
        output_pcb_sha256=sha(pcb), poses_local_mm=poses, all_eight_new_parts_on_front=True,
        no_existing_copper_or_pose_changed=True, outline_and_mounts_unchanged=True,
        selected_courtyard_gap_mm=.2, selected_existing_copper_gap_mm=.17,
        U102_contact_field_avoided=True, native_DRC_and_routing_pending=True,
        whole_unit_mechanical_qualified=False, physical_qualified=False, fabrication_released=False), indent=2)+"\n")
    print("Placed eight AX03 parts inside the original160x45 outline:", poses)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--place", action="store_true")
    args = parser.parse_args()
    place() if args.place else stage()
