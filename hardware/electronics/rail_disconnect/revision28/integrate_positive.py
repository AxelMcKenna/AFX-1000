"""Integrate the explicit E28 staged eFuse circuit on the native foundation."""

import copy
import hashlib
import json
import math
import uuid

from ...common.placement import placed_footprint
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .. import generate as sch
from ..revision26 import router as aid
from ..revision26.layout import Layout
from ..revision26.planes import ribbon
from ..routing.check import segment_distance
from .capacitor_patterns import main as cap_patterns
from .manufacturer import SOURCES
from .positive import REMOVED, components, retired
from .positive_footprints import main as patterns
from .repair import ROOT, Router
from .terminals import ALL_TERMINALS, PORTS, POWER_PORTS
from .wire_outputs import main as output_pattern

LIB = __import__("pathlib").Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints")
FIXED = {
    "U13": (41.5, 5.5, 0, "F"),
    "U14": (41.5, 10.5, 0, "F"),
    "U15": (131, 5.5, 0, "F"),
    "U16": (131, 10.5, 0, "F"),
    "U17": (131, 15.5, 0, "F"),
    "U32": (41.5, 15.5, 0, "F"),
    "U33": (135, 20.5, 0, "F"),
    "J6": (28, 36.3, 90, "F"),
    "J8": (124, 21, 0, "F"),
    "J9": (27, 40.05, 90, "F"),
    "C21": (116.75, 16.5, 180, "F"),
    "J10": (49.5, 17.5, 0, "F"),
    "J11": (115, 6, 0, "F"),
    "J2": (110.5, 20, 90, "F"),
    "J4": (153, 12, 0, "F"),
}
PREFER = {
    "U18": (32, 13.5, 90, "B"),
    "U19": (55, 16, 0, "B"),
    "U20": (56, 22, 0, "B"),
    "U21": (22, 9, 0, "B"),
    "U22": (44, 25, 0, "B"),
    "U23": (58, 13, 0, "B"),
    "U24": (23, 15, 0, "B"),
    "U25": (80, 12, 0, "B"),
    "U26": (96, 14.5, 0, "B"),
    "U27": (137, 8, 0, "B"),
    "U28": (40, 6, 0, "B"),
    "U29": (129, 18.5, 0, "B"),
    "U30": (135, 18.5, 0, "B"),
    "U31": (45, 16, 0, "B"),
    "U34": (138, 23, 0, "B"),
    "R14": (27, 35, 0, "B"),
    "R15": (32, 35, 0, "B"),
    "C34": (37, 36, 0, "B"),
    "R64": (139, 20, 0, "B"),
    "C36": (55, 10, 0, "F"),
    "R7": (43, 19, 0, "B"),
    "R9": (43, 22, 0, "B"),
    "R11": (56, 26, 0, "B"),
    "R88": (110.5, 13, 0, "F"),
    "R89": (117, 13, 0, "B"),
    "R90": (110, 8, 0, "B"),
    "R77": (115.5, 19.5, 0, "B"),
}


def native_parts():
    parts = components()
    old = json.loads((ROOT / "components.json").read_text())
    for ref in ("J7", "J8"):
        part = copy.deepcopy(next(c for c in old if c["ref"] == ref))
        part["x"], part["y"] = 1270, 2395.22 if ref == "J7" else 2476.5
        parts.append(part)
    for index, (ref, (_, _, net)) in enumerate(POWER_PORTS.items()):
        part = copy.deepcopy(next(c for c in old if c["ref"] == "J7"))
        part.update(
            ref=ref,
            x=1104.9,
            y=2395.22 + index * 38.1,
            note="Operating source-positive force terminal; whole AWG10/12 lead including all contacts <=2mohm measured acceptance.",
        )
        part["pins"][0]["net"] = net
        parts.append(part)
    j4 = next(c for c in parts if c["ref"] == "J4")
    j4.update(
        part="Alpha3079_AWG14_DIG_FORCE",
        footprint="RMX_E28:AWG14_Force_2x1_P6mm",
        source="https://www.alphawire.com/disteAPI/SpecPDF/DownloadProductSpecPdf?productPartNumber=3079",
        note="Direct-solder3079OR005/BK005 leads; source solder joint<=.5mohm measured; strain relief/current/bend/fill/receiving termination remain unqualified.",
    )
    for part in parts:
        if part["part"] in SOURCES:
            part["footprint"] = f"RMX_E28:{part['part']}_TI_Q5B"
    return parts


def footprint(part, pose, nets):
    lib, name = part["footprint"].split(":")
    base = ROOT if lib == "RMX_E28" else LIB
    return placed_footprint(
        dict(
            part,
            value=part["part"],
            mpn=part.get("manufacturer_part", part["part"]),
            nets={p["number"]: board_net(part, p) for p in part["pins"]},
        ),
        pose,
        base / (lib + ".pretty") / (name + ".kicad_mod"),
        nets,
        namespace="rmx:E28:positive:",
    )


def board_net(part, pin):
    return pin["net"] or f"unconnected-({part['ref']}-{pin['name']}-Pad{pin['number']})"


def write_schematic(parts):
    settings = (ROOT / "rail_disconnect.kicad_pro").read_bytes()
    sch.ROOT = ROOT
    sch.COMPONENTS = parts
    sch.CHANNELS = [
        dict(name="bipolar", implementation="retained Si8751 + source-verified TI Q5B"),
        dict(name="analog5", implementation="3 parallel TPS259482L, staged after digital"),
        dict(name="digital5", implementation="4 parallel TPS259482L, staged SPLYGD"),
    ]
    sch.NOTES = [
        (
            20.32,
            20.32,
            "E28 engineering candidate: exact Q5B lands, staged parallel TPS259482L positive rails, native fault latch and actual return studs.",
        ),
        (
            20.32,
            2514.6,
            "RCBCTRL=LOW permits steady reverse current. Source/AUX fault interlocks force all EN OFF; reverse-transient/thermal/startup/physical qualifications remain false.",
        ),
        (
            20.32,
            2527.3,
            "Output-ready is a coarse startup prerequisite; calibrated rail-monitor voltage windows and bias/audio checks must pass before unmute.",
        ),
    ]
    sch.main()
    schema = (ROOT / "rail_disconnect.kicad_sch").read_text()
    schema = schema.replace('(paper "User" 1250 1230)', '(paper "User" 1500 2600)')
    schema = schema.replace("1210.31", "2501.9").replace('(rev "E17/E21")', '(rev "E28")')
    (ROOT / "rail_disconnect.kicad_sch").write_text(schema)
    (ROOT / "rail_disconnect.kicad_pro").write_bytes(settings)
    table = read_sexpr((ROOT / "fp-lib-table").read_text())
    for entry in children(table, "lib"):
        if first(entry, "name")[1] == "RMX_E28":
            first(entry, "uri")[1] = "${KIPRJMOD}/RMX_E28.pretty"
    table = [
        n
        for n in table
        if not (isinstance(n, list) and n and n[0] == "lib" and first(n, "name")[1] == "RMX_Disconnect")
    ]
    table.append(
        read_sexpr(
            '(lib (name "RMX_Disconnect") (type "KiCad") (uri "${KIPRJMOD}/RMX_Disconnect.pretty") (options "") (descr "mounts"))'
        )
    )
    (ROOT / "fp-lib-table").write_text(sexpr(table) + "\n")


def main():
    patterns()
    cap_patterns()
    output_pattern()
    parts = native_parts()
    write_schematic(parts)
    source = ROOT / "generated/foundation.kicad_pcb"
    tree = read_sexpr(source.read_text())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    nets = {name: int(number) for number, name in names.items()}
    for name in sorted({board_net(c, p) for c in parts for p in c["pins"]}):
        if name not in nets:
            number = max(nets.values()) + 1
            nets[name] = number
            names[str(number)] = name
            tree.append([a("net"), number, "/" + name])
    byref = {c["ref"]: c for c in parts}
    kept = []
    removed = []
    relocated_legacy = set()
    for node in tree:
        if not isinstance(node, list) or not node:
            kept.append(node)
            continue
        tag = node[0]
        if tag == "footprint":
            ref = next(p[2] for p in children(node, "property") if p[1] == "Reference")
            bottom_passive = first(node, "layer")[1] == "B.Cu" and ref.startswith(("R", "C"))
            sensitive = any(
                any(v in p["net"] for v in ("_MCAP", "_TT", "_DRIVE", "_GATE"))
                for p in byref.get(ref, {}).get("pins", [])
                if p["net"]
            )
            if bottom_passive and not sensitive:
                relocated_legacy.add(ref)
            if (
                ref in relocated_legacy
                or ref in REMOVED
                or ref
                in set(FIXED)
                | {"R64", "R14", "R15", "C34", "C36", "R7", "R9", "R11", "R88", "R89", "R90", "R77"}
            ):
                removed.append(sexpr(node))
                continue
            if ref in byref:
                pins = {p["number"]: p["net"] for p in byref[ref]["pins"] if p["net"]}
                for pad in children(node, "pad"):
                    if str(pad[1]) in pins:
                        n = pins[str(pad[1])]
                        first(pad, "net")[1:] = [nets[n], "/" + n]
            kept.append(node)
            continue
        if tag in ("segment", "via", "zone") and children(node, "net"):
            name = names.get(str(first(node, "net")[1]), "")
            if retired(name):
                removed.append(sexpr(node))
                continue
            if name == "ALL_RAILS_ALLOW":
                first(node, "net")[1] = nets["E28_MASTER_ENABLE"]
                if children(node, "net_name"):
                    first(node, "net_name")[1] = "/E28_MASTER_ENABLE"
            if (
                tag == "zone"
                and name == "V5_REG"
                and children(node, "layer")
                and first(node, "layer")[1] == "In3.Cu"
            ):
                pts = first(first(node, "polygon"), "pts")[1:]
                if max(float(p[1]) for p in pts) > 200:
                    removed.append(sexpr(node))
                    continue
            if tag in ("segment", "via"):
                keys = ("at",) if tag == "via" else ("start", "end")
                coordinates = [tuple(float(v) - 100 for v in first(node, k)[1:3]) for k in keys]
                on_front = tag == "via" or first(node, "layer")[1] == "F.Cu"
                if on_front and any(
                    (36 <= x <= 47 and 2 <= y <= 16) or (124 <= x <= 139 and 2 <= y <= 20)
                    for x, y in coordinates
                ):
                    removed.append(sexpr(node))
                    continue
        kept.append(node)
    tree = kept
    # Rebuild global signal routes rather than trapping new IC escapes between
    # historical .125mm router fragments. Preserve power, return, floating-gate
    # and multiplier geometry; preserve only actual short signal pad escapes.
    probe = aid.Router(tree)
    padpoints = {}
    for pad in probe.pads:
        padpoints.setdefault(pad["net"], []).append(pad["xy"])
    result = []
    for node in tree:
        if not isinstance(node, list) or not node or node[0] not in ("segment", "via"):
            result.append(node)
            continue
        net = names[str(first(node, "net")[1])]
        preserve = net in {
            "P19_SRC",
            "P19",
            "N19_SRC",
            "N19",
            "P12_SRC",
            "P12",
            "N12_SRC",
            "N12",
            "V5_REG_SRC",
            "V5_REG",
            "5V_DIG_SRC",
            "5V_DIG",
        } or any(suffix in net for suffix in ("_COMMON", "_GATE", "_DRIVE", "_MCAP", "_TT"))
        if not preserve:
            keys = ("at",) if node[0] == "via" else ("start", "end")
            points = [tuple(float(v) - 100 for v in first(node, k)[1:3]) for k in keys]
            nearby = min((math.dist(p, q) for p in points for q in padpoints.get(net, [])), default=1000)
            # Existing surviving SMD ground/power returns retain short escapes;
            # relocated control passives have no stale footprint anchors.
            preserve = nearby < (1.5 if node[0] == "via" else 1.2)
        if preserve:
            result.append(node)
        else:
            removed.append(sexpr(node))
    tree = result
    setup = first(tree, "setup")
    for name in ("filling", "capping"):
        if children(setup, name):
            first(setup, name)[1] = a("yes")
        else:
            setup.append([a(name), a("yes")])
    placed = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference")
        for f in children(tree, "footprint")
    }
    layout = Layout(
        tree, byref, {c["ref"]: {p["number"]: p["net"] for p in c["pins"] if p["net"]} for c in parts}, LIB
    )

    spatial = {}

    def refresh():
        layout.router = Router(tree)
        spatial.clear()
        for g in layout.router.geometry:
            if g["kind"] == "line":
                xs = [g["start"][0], g["end"][0]]
                ys = [g["start"][1], g["end"][1]]
                m = g["width"] / 2
            else:
                xs, ys = [g["xy"][0]], [g["xy"][1]]
                m = max(g.get("size", (0, 0))) / 2 if g["kind"] == "rect" else g["radius"]
            for ix in range(math.floor((min(xs) - m) / 5), math.floor((max(xs) + m) / 5) + 1):
                for iy in range(math.floor((min(ys) - m) / 5), math.floor((max(ys) + m) / 5) + 1):
                    spatial.setdefault((ix, iy), []).append(g)
        layout.bodies = []
        for fp in children(tree, "footprint"):
            ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
            side, box = layout.body(fp)
            layout.bodies.append((ref, side, box))
        for fp in children(tree, "footprint"):
            ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
            if ref == "J4":
                layout.bodies.append(("J4_wire_tail_clearance", "B", layout.body(fp)[1]))
        for ref, (x, y, _) in ALL_TERMINALS.items():
            layout.bodies.append((ref + "_access_B", "B", (x + 95, y + 95, x + 105, y + 105)))

    refresh()
    poses = {}
    ports = []
    missing = [c for c in parts if c["ref"] not in placed]

    def clear_fixed_copper(fp):
        trial = aid.Router([n for n in tree if isinstance(n, list) and n and n[0] == "net"] + [fp])
        boxes = [g for g in trial.geometry if g["kind"] == "rect"]
        if "7466003R" in str(fp[1]):
            boxes[0] = dict(
                boxes[0],
                xy=(float(first(fp, "at")[1]) - 100, float(first(fp, "at")[2]) - 100),
                size=(8.5, 8.5),
            )
        killed = []
        for node in tree:
            if not isinstance(node, list) or not node or node[0] not in ("segment", "via"):
                continue
            net = names[str(first(node, "net")[1])]
            for pad in boxes:
                xy = pad["xy"]
                w, h = pad["size"]
                if node[0] == "via":
                    point = tuple(float(v) - 100 for v in first(node, "at")[1:3])
                    distance = math.hypot(
                        max(abs(point[0] - xy[0]) - w / 2, 0), max(abs(point[1] - xy[1]) - h / 2, 0)
                    )
                    if distance < 0.56:
                        killed.append(node)
                        break
                elif net != pad["net"] and aid.LAYERS.index(str(first(node, "layer")[1])) in pad["layers"]:
                    start, end = [
                        tuple(float(v) - 100 for v in first(node, k)[1:3]) for k in ("start", "end")
                    ]
                    corners = [
                        (xy[0] - w / 2, xy[1] - h / 2),
                        (xy[0] + w / 2, xy[1] - h / 2),
                        (xy[0] + w / 2, xy[1] + h / 2),
                        (xy[0] - w / 2, xy[1] + h / 2),
                    ]
                    d = min(
                        segment_distance(start, end, a, b) for a, b in zip(corners, corners[1:] + corners[:1])
                    )
                    if (
                        any(abs(p[0] - xy[0]) <= w / 2 and abs(p[1] - xy[1]) <= h / 2 for p in (start, end))
                        or d < float(first(node, "width")[1]) / 2 + 0.24
                    ):
                        killed.append(node)
                        break
        if killed:
            ids = {id(n) for n in killed}
            tree[:] = [n for n in tree if id(n) not in ids]
            removed.extend(sexpr(n) for n in killed)
            refresh()

    def geometry_near(pose, distance=10):
        x, y = pose[:2]
        found = {}
        for ix in range(math.floor((x - distance) / 5), math.floor((x + distance) / 5) + 1):
            for iy in range(math.floor((y - distance) / 5), math.floor((y + distance) / 5) + 1):
                for g in spatial.get((ix, iy), []):
                    found[id(g)] = g
        return list(found.values())

    def add(part, pose, required=False):
        fp = footprint(part, pose, nets)
        if required:
            clear_fixed_copper(fp)
        near = geometry_near(pose)
        all_geometry = layout.router.geometry
        layout.router.geometry = near
        legal = layout.legal_body(part["ref"], fp)
        layout.router.geometry = all_geometry
        if not legal:
            if required:
                side, box = layout.body(fp)
                overlaps = [
                    ref
                    for ref, face, b in layout.bodies
                    if face == side
                    and min(box[2], b[2]) - max(box[0], b[0]) > -0.1
                    and min(box[3], b[3]) - max(box[1], b[1]) > -0.1
                ]
                print(
                    "Fixed rejection", part["ref"], pose, "body", side, box, "overlap", overlaps, flush=True
                )
                (ROOT / "generated/rejected-fixed.kicad_pcb").write_text(sexpr(tree + [fp]) + "\n")
                raise AssertionError((part["ref"], pose, "fixed body/pads collide"))
            return False
        if required:
            tree.append(fp)
            poses[part["ref"]] = pose
            refresh()
            return True
        trial = aid.Router([n for n in tree if isinstance(n, list) and n and n[0] == "net"] + [fp])
        rt = copy.copy(layout.router)
        rt.geometry = list(near) + list(trial.geometry)
        rt.board = list(tree) + [fp]
        rt.by_ref = dict(layout.router.by_ref, **trial.by_ref)
        local = copy.copy(layout)
        local.router = rt
        local.ports = []
        axis = 0 if round(pose[2]) % 180 == 0 else 1
        cx, cy = pose[:2]
        active = [p for p in trial.pads if not p["net"].startswith("unconnected-")]
        if part["ref"].startswith(("R", "C")):
            # Real0.3mm filled/capped through barrels inside0805 copper lands.
            # This explicit IPC4761TypeVII fabrication candidate avoids long
            # external fanouts; process acceptance is never inferred from DRC.
            for p in active:
                geometry = rt.geometry
                rt.geometry = [g for g in geometry if g is not p and g["net"] != "BULK_BODY_NOVIA"]
                if not local.free_via(p["net"], p["xy"]):
                    return False
                rt.geometry = geometry
                rt.via(p["net"], p["xy"])
                ports.append(
                    dict(
                        ref=part["ref"],
                        pin=p["pin"],
                        net=p["net"],
                        xy=p["xy"],
                        layers=tuple(range(6)),
                        purpose="filled/capped via in0805 land",
                    )
                )
            tree.extend(rt.board[len(tree) :])
            poses[part["ref"]] = pose
            refresh()
            return True
        try:
            for p in active:
                sign = 1 if p["xy"][axis] > (cx, cy)[axis] else -1
                if part["ref"].startswith("U") and ("AUP2G08" in part["part"] or "TPS3890" in part["part"]):
                    # Three/four lead rows need a real fanout, not staggered
                    # horizontal vias that short the neighbouring .5mm row.
                    side = sorted(
                        [q for q in active if (q["xy"][axis] > (cx, cy)[axis]) == (sign > 0)],
                        key=lambda q: q["xy"][1 - axis],
                    )
                    rank = side.index(p)
                    n = len(side)
                    direction = 1 if rank >= n / 2 else -1
                    if rank in (0, n - 1):
                        via = list(p["xy"])
                        via[axis] += sign * (p["size"][axis] / 2 + 1.0)
                        via[1 - axis] += direction * 0.9
                        corner = list(p["xy"])
                        corner[axis] += sign * (p["size"][axis] / 2 + 0.2)
                        pathpoints = [p["xy"], tuple(corner), tuple(via)]
                    else:
                        via = list(p["xy"])
                        via[axis] += sign * (p["size"][axis] / 2 + 2.0)
                        if n == 4:
                            via[1 - axis] += direction * 0.30
                        corner = list(p["xy"])
                        corner[axis] = via[axis] - sign * 0.30
                        pathpoints = [p["xy"], tuple(corner), tuple(via)]
                elif part["ref"].startswith("U"):
                    via = list(p["xy"])
                    via[axis] += sign * (p["size"][axis] / 2 + 0.575 + int(p["pin"]) % 2)
                    pathpoints = [p["xy"], tuple(via)]
                else:
                    via = [cx, cy]
                    via[axis] += sign * 2
                    via[1 - axis] += sign * 0.7
                    pathpoints = [p["xy"], tuple(via)]
                via = tuple(round(v, 6) for v in via)
                local.port(p, via, path=pathpoints, width=0.2 if part["ref"].startswith("U") else 0.25)
        except AssertionError:
            return False
        tree.extend(rt.board[len(tree) :])
        poses[part["ref"]] = pose
        ports.extend(local.ports)
        refresh()
        return True

    for part in missing:
        ref = part["ref"]
        if ref in FIXED:
            add(part, FIXED[ref], True)
    # Explicit PWCSP lead fanouts and parallel finite-barrel power attachments.
    r = Router(tree)
    for ref in ("U13", "U14", "U15", "U16", "U17", "U32", "U33"):
        x, y, _, _ = poses[ref]
        for number in (5, 6):
            p = next(p for p in r.by_ref[ref] if p["pin"] == str(number))
            xx = p["xy"][0]
            r.path(p["net"], 0, [(xx, y - 1.4), (xx, y + 1.4)], 0.5)
            for yy in (y - 1.4, y + 1.4):
                r.via(p["net"], (xx, yy))
        for number, sign, dy in (
            (1, -1, -0.675),
            (2, -1, -0.225),
            (3, -1, 0.225),
            (4, -1, 0.675),
            (7, 1, 0.675),
            (8, 1, 0.225),
            (9, 1, -0.225),
        ):
            p = next(p for p in r.by_ref[ref] if p["pin"] == str(number))
            if abs(dy) > 0.5:
                direction = 1 if dy > 0 else -1
                end = (x + sign * 2.15, y + direction * 1.5)
                points = [p["xy"], (x + sign * 1.6, y + dy), (x + sign * 2.15, y + direction * 1.225), end]
            else:
                direction = 1 if dy > 0 else -1
                end = (x + sign * 3.15, y + direction * 0.5)
                points = [p["xy"], (x + sign * 2.875, y + dy), end]
            r.path(p["net"], 0, points, 0.2)
            r.via(p["net"], end)
            ports.append(dict(ref=ref, pin=str(number), net=p["net"], xy=end, layers=tuple(range(6))))
    for _, (x, y, net) in ALL_TERMINALS.items():
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            endpoint = (x + 4.8 * dx, y + 4.8 * dy)
            r.path(net, 0, [(x + 3.3 * dx, y + 3.3 * dy), endpoint], 0.8)
            r.via(net, endpoint)
    refresh()
    missing = [c for c in missing if c["ref"] not in poses]
    # Place large ICs first, preferring specified integration sites but checking
    # real courtyard/pad/via geometry at every candidate.
    missing.sort(key=lambda c: (not c["ref"].startswith("U"), c["ref"]))
    seed_path = ROOT / "generated/placement-seed.json"
    seeds = json.loads(seed_path.read_text()) if seed_path.exists() else {}
    for part in missing:
        ref = part["ref"]
        print("Placing", ref, flush=True)
        owner = part.get("owner_ref")
        anchor = poses.get(owner, (70, 10, 0, "B"))
        preferred = PREFER.get(ref, (anchor[0] - 5, anchor[1] + 4, 0, "B"))
        if ref in seeds and ref != "U26":
            preferred = seeds[ref]
        px, py, angle, side = preferred
        candidates = [preferred]
        for radius in range(1, 145):
            for dx, dy in (
                (radius, 0),
                (-radius, 0),
                (0, radius),
                (0, -radius),
                (radius, radius),
                (-radius, radius),
                (radius, -radius),
                (-radius, -radius),
            ):
                for turn in (angle, (angle + 90) % 180):
                    candidates.append((px + dx * 0.5, py + dy * 0.5, turn, side))
        candidates.extend(
            (x, y, turn, side)
            for _, x, y in sorted(
                (math.dist((x, y), (px, py)), x, y)
                for x in range(7, 151, 2)
                for y in [i * 0.5 for i in range(5, 88, 2)]
            )
            for turn in (0, 90)
        )
        if not ref.startswith("U"):
            candidates += [(x, y, turn, "F" if face == "B" else "B") for x, y, turn, face in candidates]
        for pose in candidates:
            if add(part, pose):
                break
        else:
            (ROOT / "generated/positive-placement-partial.kicad_pcb").write_text(sexpr(tree) + "\n")
            raise AssertionError((ref, "No legal placement in candidate search"))
        print(ref, poses[ref], flush=True)
        (ROOT / "generated/positive-placement-partial.kicad_pcb").write_text(sexpr(tree) + "\n")
        (ROOT / "generated/placement-accepted.json").write_text(json.dumps(poses, indent=2) + "\n")
    # Actual wide analog-cap arm moves to In2, avoiding the digital In3 bus.
    tree.extend(ribbon("V5_REG", "In2.Cu", [(62.7, 37.5), (142.5, 15.25)], 12, 35, nets))
    for y in (5.5, 10.5, 15.5):
        tree.extend(ribbon("V5_REG_SRC", "In2.Cu", [(49.5, 17.5), (41.024, y)], 8, 36, nets))
        tree.extend(ribbon("V5_REG", "In3.Cu", [(41.976, y), (49.7, 7)], 8, 36, nets))
    for y in (5.5, 10.5, 15.5):
        tree.extend(ribbon("5V_DIG", "In3.Cu", [(131.476, y), (146, 2.5), (142.75, 37)], 8, 36, nets))
    tree.extend(ribbon("5V_DIG_SRC", "In1.Cu", [(115, 6), (130.524, 5.5), (134.524, 20.5)], 8, 36, nets))
    tree.extend(ribbon("5V_DIG", "In3.Cu", [(135.476, 20.5), (142.75, 37)], 8, 36, nets))
    for index, node in enumerate(tree):
        if (
            isinstance(node, list)
            and node
            and node[0] in ("segment", "via", "zone")
            and not children(node, "uuid")
        ):
            node.append(
                [a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:positive:{index}:{sexpr(node)}")))]
            )
    # KiCad's NC nets have no hierarchy slash; match exported schematic exactly.
    for node in children(tree, "net"):
        if str(node[2]).lstrip("/").startswith("unconnected-"):
            node[2] = str(node[2]).lstrip("/")
    for fp in children(tree, "footprint"):
        for pad in children(fp, "pad"):
            if children(pad, "net"):
                node = first(pad, "net")
                if str(node[-1]).lstrip("/").startswith("unconnected-"):
                    node[-1] = str(node[-1]).lstrip("/")
    (ROOT / "rail_disconnect.kicad_pcb").write_text(sexpr(tree) + "\n")
    receipt = dict(
        parent_foundation_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        removed_items=removed,
        new_placements=poses,
        relocated_legacy_passives=sorted(relocated_legacy),
        parts=len(parts),
        return_ports=PORTS,
        source_positive_ports=POWER_PORTS,
        signal_ports=ports,
        routing_closed=False,
        passive_via_process="IPC4761TypeVII filled/capped0.3mm through vias in0805 SMD lands; fabricator/assembler acceptance pending",
        physical_qualified=False,
    )
    (ROOT / "generated/positive-integration.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("E28 positive stage placed; native escapes/routing/qualification still required")


if __name__ == "__main__":
    main()
