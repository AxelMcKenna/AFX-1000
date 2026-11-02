"""Place DC01 in the right-side enclosure allocation, without inventing copper.

Uses captured source lands, a bounded deterministic placement search and
explicit through-hole solder keepouts on the opposite assembly face.
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.placement import placed_footprint
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.audit_digital_core import check as check_source
from hardware.fabrication.bypass_layout import mount

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "hardware/fabrication/staging/digital-core-integration-01"
OUT = SOURCE.parent / "digital-core-placement-03"
OUTLINE = [(0, 0), (64, 0), (64, 3), (104, 3), (104, 9), (114, 9), (114, 60), (0, 60)]
MOUNTS = [(4, 4), (66, 13), (110, 25), (4, 36), (110, 44)]
DATUM = [184, 44, 7]
FIXED = {
    "U1001": (10, 42, 90, "F"),
    "U2001": (21, 34.2, 90, "B"), "U2002": (43, 34.2, 90, "B"), "U2003": (72, 34.2, 90, "B"),
    "U3001": (13, 17, 0, "F"), "U3002": (39, 17, 0, "F"),
    "U3003": (79, 23, 0, "F"), "U3004": (100, 33, 0, "F"), "U3005": (66, 21.5, 0, "F"),
    "J3002": (6, 54, 90, "F"), "J3003": (43, 54, 90, "F"),
    "J3004": (80, 54, 90, "F"), "J3005": (78, 14, 90, "F"),
    "J2001": (12, 7, 90, "F"), "J2002": (37, 7, 90, "F"), "J2003": (60, 7, 90, "F"),
    **{f"J{1020+i}": (4+10*i, 46, 90, "F") for i in range(10)},
}


def overlaps(x, y, gap=0):
    return x[0] < y[2]+gap-1e-8 and x[2] > y[0]-gap+1e-8 and x[1] < y[3]+gap-1e-8 and x[3] > y[1]-gap+1e-8


def pad_box(fp, pad, extra):
    p = first(pad, "at")
    angle = math.radians(float(p[3]) if len(p) > 3 else 0)
    sx, sy = [float(v)/2 for v in first(pad, "size")[1:3]]
    corners = [transform(fp, (float(p[1])+dx*math.cos(angle)+dy*math.sin(angle),
                              float(p[2])-dx*math.sin(angle)+dy*math.cos(angle)))
               for dx in (-sx, sx) for dy in (-sy, sy)]
    return [min(v[0] for v in corners)-extra, min(v[1] for v in corners)-extra,
            max(v[0] for v in corners)+extra, max(v[1] for v in corners)+extra]


def build():
    assert check_source() == json.loads((SOURCE / "integration-handoff.json").read_text())
    assert not OUT.exists()
    OUT.mkdir()
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_sym") or p.name in ("sym-lib-table", "fp-lib-table", "netlist.xml"):
            shutil.copyfile(p, OUT / p.name)
    shutil.copytree(SOURCE / "libraries", OUT / "libraries")
    # The symbol table has root-level symbols, while captured lands live below libraries/.
    own = OUT / "libraries/AFX_Digital.pretty"
    own.mkdir()
    (own / "M2_Clearance.kicad_mod").write_text(sexpr(mount()) + "\n")
    table = read_sexpr((OUT / "fp-lib-table").read_text())
    table.append(read_sexpr('(lib (name "AFX_Digital") (type "KiCad") (uri "${KIPRJMOD}/libraries/AFX_Digital.pretty") (options "") (descr "Proposed mounting clearance"))'))
    (OUT / "fp-lib-table").write_text(sexpr(table) + "\n")
    parts, pin_nets = netlist(SOURCE / "netlist.xml")
    components = {ref: dict(ref=ref, value=part.findtext("value"), footprint=part.findtext("footprint"),
                            nets=pin_nets[ref], source=part.findtext("datasheet") or "", mpn=part.findtext("value"))
                  for ref, part in parts.items()}
    nets = {net: i+1 for i, net in enumerate(sorted({n for pins in pin_nets.values() for n in pins.values()}))}
    prototypes = {}
    for ref, part in components.items():
        lib, name = part["footprint"].split(":")
        prototypes[ref] = OUT / "libraries" / (lib + ".pretty") / (name + ".kicad_mod")
    poses, shapes, bounds, tht = {}, {}, {}, {}
    mount_boxes = [[x-3.6, y-3.6, x+3.6, y+3.6] for x, y in MOUNTS]

    def shape(ref, pose):
        return placed_footprint(components[ref], pose, prototypes[ref], nets, origin=(0, 0), namespace="AFX:DC01:placement:")

    def legal(fp, bbox, side):
        # Minimum courtyard-to-profile allocation .5 mm, including inlet notch.
        if bbox[0] < .5 or bbox[1] < .5 or bbox[2] > 113.5 or bbox[3] > 59.5:
            return False
        if bbox[2] > 63.5 and bbox[1] < 3.5:
            return False
        if bbox[2] > 103.5 and bbox[1] < 9.5:
            return False
        if any(overlaps(bbox, m, .15) for m in mount_boxes):
            return False
        new_tht = [pad_box(fp, p, .5) for p in children(fp, "pad") if p[2] == "thru_hole"]
        for other, b in bounds.items():
            if poses[other][3] == side:
                if overlaps(bbox, b, .3):
                    return False
            else:
                if any(overlaps(bbox, p) for p in tht[other]) or any(overlaps(b, p) for p in new_tht):
                    return False
        return True

    def install(ref, pose):
        fp = shape(ref, pose)
        bbox = courtyard(fp, pose[3]+".CrtYd")
        assert legal(fp, bbox, pose[3]), ("Illegal proposed placement", ref, pose, bbox)
        poses[ref], shapes[ref], bounds[ref] = pose, fp, bbox
        tht[ref] = [pad_box(fp, p, .5) for p in children(fp, "pad") if p[2] == "thru_hole"]

    # Install all top-side receiving constraints before the underside ICs.
    for ref, pose in sorted(FIXED.items(), key=lambda item: item[1][3] == "B"):
        install(ref, pose)

    remaining = set(parts) - poses.keys()
    sizes = {}
    for ref in remaining:
        b = courtyard(shape(ref, (0, 0, 0, "F")), "F.CrtYd")
        sizes[ref] = (b[2]-b[0])*(b[3]-b[1])
    # Larger remaining headers first. SMDs follow connected placement anchors.
    ordered = sorted(remaining, key=lambda r: (not r.startswith("J"), -sizes[r], r))
    candidates_tried = 0
    for ref in ordered:
        weights = []
        for other, pose in poses.items():
            common_nets = set(pin_nets[ref].values()) & set(pin_nets[other].values())
            common_nets -= {"AGND", "5V_DIG", "V3V3_IO", "PROCESSOR/V3V3_ANALOG"}
            if common_nets:
                b = bounds[other]
                weights.append(((b[0]+b[2])/2, (b[1]+b[3])/2, len(common_nets)))
        if weights:
            total = sum(w[2] for w in weights)
            target = [sum(w[i]*w[2] for w in weights)/total for i in (0, 1)]
        else:
            target = [55, 24]
        # Header placement remains on top. Small SMDs can use either face.
        sides = ("F",) if ref.startswith("J") else ("F", "B")
        choices = []
        for side in sides:
            for angle in (0, 90, 180, 270):
                proto = shape(ref, (0, 0, angle, side))
                b = courtyard(proto, side+".CrtYd")
                for ix in range(2, 226, 2):
                    x = ix/2
                    for iy in range(2, 118, 2):
                        y = iy/2
                        centre = (x+(b[0]+b[2])/2, y+(b[1]+b[3])/2)
                        score = math.dist(centre, target) + (2.5 if side == "B" else 0)
                        choices.append((score, x, y, angle, side, b))
        choices.sort(key=lambda v: v[:5])
        for _, x, y, angle, side, local in choices:
            b = [local[0]+x, local[1]+y, local[2]+x, local[3]+y]
            # Cheap rejection before constructing the full footprint tree.
            if b[0] < .5 or b[1] < .5 or b[2] > 113.5 or b[3] > 59.5 or (b[2] > 63.5 and b[1] < 3.5):
                continue
            if b[2] > 103.5 and b[1] < 9.5:
                continue
            if any(overlaps(b, m, .15) for m in mount_boxes):
                continue
            if any(poses[o][3] == side and overlaps(b, ob, .3) for o, ob in bounds.items()):
                continue
            candidates_tried += 1
            fp = shape(ref, (x, y, angle, side))
            if legal(fp, b, side):
                install(ref, (x, y, angle, side))
                break
        else:
            raise AssertionError(("No placement in this allocation", ref))
    board = read_sexpr('''(kicad_pcb (version 20240108) (generator pcbnew)
      (general (thickness 1.6)) (paper "A4")
      (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" power) (31 "B.Cu" signal)
        (35 "F.Paste" user) (34 "B.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user)
        (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user)
        (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))
      (setup (pad_to_mask_clearance 0)) (net 0 ""))''')
    board.extend([a("net"), code, "/"+net] for net, code in nets.items())
    board.extend(shapes[ref] for ref in sorted(shapes))
    for i, (x, y) in enumerate(MOUNTS, 1):
        part = dict(ref="H"+str(i), value="M2_CLEARANCE", nets={}, footprint="AFX_Digital:M2_Clearance", source="", mpn="")
        board.append(placed_footprint(part, (x, y, 0, "F"), own/"M2_Clearance.kicad_mod", nets, origin=(0, 0), namespace="AFX:DC01:placement:"))
    for start, end in zip(OUTLINE, OUTLINE[1:]+OUTLINE[:1]):
        board.append(read_sexpr(f'(gr_line (start {start[0]} {start[1]}) (end {end[0]} {end[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'))
    # Global labels have no leading slash; hierarchical local labels do.
    # The common flat-board helper adds a slash, so restore exact native names.
    raw_names = {n.attrib["name"].lstrip("/"): n.attrib["name"]
                 for n in ET.parse(SOURCE/"netlist.xml").findall("nets/net")}
    assert len(raw_names) == len(nets), "Ambiguous global/local net spelling"
    for node in children(board,"net"):
        if str(node[1]) != "0":
            node[2] = raw_names[str(node[2]).lstrip("/")]
    for fp in children(board,"footprint"):
        for pad in children(fp,"pad"):
            for net in children(pad,"net"):
                net[2] = raw_names[str(net[2]).lstrip("/")]
    (OUT/"digital_core.kicad_pcb").write_text(sexpr(board)+"\n")
    profile = json.loads((SOURCE/"digital_core.kicad_pro").read_text())
    profile.update(board=dict(design_settings=dict(rules=dict(min_clearance=.2, min_track_width=.2,
        min_copper_edge_clearance=.5, min_hole_clearance=.25, min_through_hole_diameter=.3, min_via_annular_width=.15))),
        net_settings=dict(classes=[dict(name="Default", clearance=.2, track_width=.2, via_diameter=.65, via_drill=.3)]))
    profile["board"]["design_settings"]["rule_severities"] = {key:"error" for key in (
        "missing_courtyard", "track_not_centered_on_via", "tuning_profile_track_geometries",
        "footprint_filters_mismatch", "footprint_type_mismatch")}
    (OUT/"digital_core.kicad_pro").write_text(json.dumps(profile, indent=2)+"\n")
    record = dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),SOURCE/"integration-handoff.json",SOURCE/"native-review.json"]},
        electrical_parts=138, outlines_local_mm=OUTLINE, enclosure_datum_mm=DATUM, mount_centres_mm=MOUNTS,
        poses=poses, courtyard_bounds=bounds, opposite_face_through_hole_solder_expansion_mm=.5,
        minimum_same_face_courtyard_gap_mm=.3, minimum_courtyard_to_outline_allocation_mm=.5,
        minimum_mount_courtyard_gap_mm=.15, mount_hardware_diameter_allocation_mm=7.2,
        placement_candidates_fully_checked=candidates_tried, native_checks_pending=True,
        routed=False, receiving_and_process_approved=False, fabrication_released=False)
    (OUT/"construction.json").write_text(json.dumps(record, indent=2)+"\n")
    (OUT/"source-recipes").mkdir()
    shutil.copyfile(Path(__file__),OUT/"source-recipes/digital_core_layout.py.txt")
    print("DC01 placed: 138 electrical parts in notched 114x60; native review pending; no routing")


def review():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    assert not (OUT/"placement-native-review.json").exists()
    paths = [p for p in OUT.iterdir() if p.suffix in (".kicad_pro", ".kicad_pcb", ".kicad_sch", ".kicad_sym") or p.name in ("construction.json", "sym-lib-table", "fp-lib-table")]
    inputs = {str(p.relative_to(REPO)):sha(p) for p in paths}
    commands = []
    for label, args in (
        ("netlist",["sch","export","netlist","--format","kicadxml","-o",str(OUT/"native-netlist.xml"),str(OUT/"digital_core.kicad_sch")]),
        ("erc",["sch","erc","--severity-all","--format","json","-o",str(OUT/"erc.json"),str(OUT/"digital_core.kicad_sch")]),
        ("drc",["pcb","drc","--all-track-errors","--schematic-parity","--severity-all","--format","json","-o",str(OUT/"drc.json"),str(OUT/"digital_core.kicad_pcb")]),
    ):
        command = ["kicad-cli",*args]
        result = subprocess.run(command,capture_output=True,text=True,timeout=120)
        (OUT/(label+".log")).write_text(result.stdout+result.stderr)
        commands.append(dict(command=command,returncode=result.returncode))
        assert result.returncode == 0,(label,result.stdout,result.stderr)
    import pcbnew

    board = pcbnew.LoadBoard(str(OUT/"digital_core.kicad_pcb"))
    board.BuildConnectivity()
    board.GetConnectivity().RecalculateRatsnest()
    drc,erc = [json.loads((OUT/p).read_text()) for p in ("drc.json","erc.json")]
    assert all(sha(REPO/p)==h for p,h in inputs.items())
    record = dict(source_sha256=inputs,native_version=pcbnew.GetBuildVersion(),complete_native_commands=commands,
        DRC_geometry_findings=len(drc["violations"]),schematic_parity_findings=len(drc["schematic_parity"]),
        uncapped_open_connections=board.GetConnectivity().GetUnconnectedCount(False),
        ERC_findings=sum(len(s["violations"]) for s in erc["sheets"]),
        DRC_ignored_checks=drc["ignored_checks"],ERC_ignored_checks=erc["ignored_checks"],
        raw_report_sha256={p:sha(OUT/p) for p in ("drc.json","erc.json","native-netlist.xml")},
        routed=False,physical_fit_qualified=False,fabrication_released=False)
    (OUT/"placement-native-review.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({k:v for k,v in record.items() if k not in ("source_sha256","raw_report_sha256","complete_native_commands")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("build","review"))
    args = parser.parse_args()
    (build if args.action=="build" else review)()
