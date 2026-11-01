"""Native-airwire driven P03 routing aid; actual KiCad checks decide closure.

The helper never promotes a source or physical release gate. Wide current paths
and local loops require independent extraction after all native gaps are closed.
"""

import argparse
import datetime as dt
import hashlib
import inspect
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import types
from pathlib import Path

import numpy as np

from ...adc_driver.pcb.router import e12_masks
from ...common.placement import footprint_root
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ...input_range.pcb.router import InputRouter
from ...output_stage.check_placement import transform
from ...rail_disconnect.routing.router import LAYERS, Router
from .spec import MOUNTS, ROOT, SIZE, THERMAL_REGIONS, U13_QUIET_FIELD_NETS

OUT = ROOT / "generated"
STEP = 0.125
mask_source = (
    inspect.getsource(e12_masks)
    .replace(
        'if same and (destination is blocks or shape["kind"] == "line" or shape.get("through")):',
        'if same and (destination is blocks or shape["kind"] in {"line","rect"} or shape.get("through")):',
    )
    .replace("< 1e-7:", "< .18:")
    .replace("0.25 + width / 2 + 0.03", "0.16 + width / 2 + 0.03")
    .replace("(0.58, via_block)", "(0.49, via_block)")
)
mask_globals = dict(e12_masks.__globals__, SIZE=SIZE, MOUNTS=MOUNTS, STEP=STEP)
exec(compile(mask_source, "p03_explicit_clearance_masks", "exec"), mask_globals)
MASKS = mask_globals["e12_masks"]
CONNECT = types.FunctionType(Router.connect.__code__, dict(Router.connect.__globals__, STEP=STEP))


def coded(tree):
    """Adapt KiCad10 named-net serialization to the existing routing API."""
    names = set()

    def collect(node):
        if not isinstance(node, list):
            return
        if node and node[0] == "net" and len(node) == 2 and not str(node[1]).isdigit():
            names.add(str(node[1]))
        for child in node:
            collect(child)

    collect(tree)
    codes = {name: i + 1 for i, name in enumerate(sorted(names))}
    if not codes:
        return tree

    def change(node, parent=None):
        if not isinstance(node, list):
            return
        if node and node[0] == "net" and len(node) == 2 and str(node[1]) in codes:
            name = str(node[1])
            node[:] = [a("net"), a(codes[name]), name] if parent == "pad" else [a("net"), a(codes[name])]
            return
        for child in node:
            change(child, node[0] if node else None)

    change(tree)
    tree.extend([[a("net"), a(0), ""], *[[a("net"), a(code), name] for name, code in codes.items()]])
    return tree


def named(tree):
    names = {str(n[1]): str(n[2]) for n in children(tree, "net")}
    tree[:] = [v for v in tree if not (isinstance(v, list) and v and v[0] == "net")]

    def change(node):
        if not isinstance(node, list):
            return
        if node and node[0] == "net" and str(node[1]) in names:
            node[:] = [a("net"), names[str(node[1])]]
            return
        for child in node:
            change(child)

    change(tree)
    return tree


def electrical_identity(tree):
    """Require native serialization to preserve every connected pad and track."""
    tree = coded(tree)
    nets = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    pads = set()
    tracks = []
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        for pad in children(fp, "pad"):
            if not children(pad, "net"):
                continue
            name = nets[str(first(pad, "net")[1])]
            if name and not name.startswith("unconnected-"):
                pads.add((ref, str(pad[1]), name))
    for tag in ("segment", "via"):
        for obj in children(tree, tag):
            if not children(obj, "net"):
                raise ValueError("Routed copper has lost its electrical net")
            tracks.append((tag, nets[str(first(obj, "net")[1])]))
    if len(pads) < 500:
        raise ValueError("P03 connected-pad inventory is incomplete")
    return pads, sorted(tracks)


def copper_geometry(obj):
    if obj[0] == "segment":
        endpoints = sorted(tuple(map(float, first(obj, t)[1:3])) for t in ("start", "end"))
        return ("segment", *endpoints, str(first(obj, "layer")[1]), float(first(obj, "width")[1]))
    return (
        "via",
        *map(float, first(obj, "at")[1:3]),
        float(first(obj, "size")[1]),
        float(first(obj, "drill")[1]),
    )


def copper_nets(tree):
    tree = coded(tree)
    nets = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    return {
        copper_geometry(obj): nets[str(first(obj, "net")[1])]
        for tag in ("segment", "via")
        for obj in children(tree, tag)
    }


def dangling_chains(tree, seeds):
    """Prune whole unbranched dangling chains, stopping at physical anchors.

    A native warning can otherwise expose one 0.125mm fragment per refill.
    This only extends native dangling seeds, never a clearance-based rip-up.
    """
    segments = {str(first(s, "uuid")[1]): s for s in children(tree, "segment") if children(s, "uuid")}
    adjacency = {}
    bins = {}
    anchors = {}

    def pointkey(net, layer, xy):
        return net, layer, *[round(float(v), 6) for v in xy]

    def addanchor(net, layer, box):
        anchors.setdefault((net, layer), []).append(box)

    for uid, s in segments.items():
        net = str(first(s, "net")[1])
        layer = str(first(s, "layer")[1])
        w = float(first(s, "width")[1]) / 2
        points = [tuple(map(float, first(s, k)[1:3])) for k in ("start", "end")]
        for xy in points:
            adjacency.setdefault(pointkey(net, layer, xy), set()).add(uid)
        for ix in range(
            math.floor((min(p[0] for p in points) - w) / 5),
            math.floor((max(p[0] for p in points) + w) / 5) + 1,
        ):
            for iy in range(
                math.floor((min(p[1] for p in points) - w) / 5),
                math.floor((max(p[1] for p in points) + w) / 5) + 1,
            ):
                bins.setdefault((net, layer, ix, iy), set()).add(uid)
    for fp in children(tree, "footprint"):
        angle = float(first(fp, "at")[3]) if len(first(fp, "at")) > 3 else 0
        for pad in children(fp, "pad"):
            if not children(pad, "net") or not children(pad, "size"):
                continue
            layers = first(pad, "layers")[1:]
            layers = LAYERS if "*.Cu" in layers else [l for l in layers if l in LAYERS]
            x, y = transform(fp, first(pad, "at")[1:3])
            sx, sy = map(float, first(pad, "size")[1:3])
            if int(angle) % 180:
                sx, sy = sy, sx
            for layer in layers:
                addanchor(
                    str(first(pad, "net")[1]),
                    str(layer),
                    (x - sx / 2 - 0.15, y - sy / 2 - 0.15, x + sx / 2 + 0.15, y + sy / 2 + 0.15),
                )
    for via in children(tree, "via"):
        x, y = map(float, first(via, "at")[1:3])
        radius = float(first(via, "size")[1]) / 2 + 0.15
        for layer in LAYERS:
            addanchor(str(first(via, "net")[1]), layer, (x - radius, y - radius, x + radius, y + radius))
    removed = set(seeds) & segments.keys()
    queue = list(removed)
    while queue:
        uid = queue.pop()
        s = segments[uid]
        net = str(first(s, "net")[1])
        layer = str(first(s, "layer")[1])
        for tag in ("start", "end"):
            x, y = map(float, first(s, tag)[1:3])
            neighbors = adjacency[pointkey(net, layer, (x, y))]
            if len(neighbors) != 2 or any(
                b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in anchors.get((net, layer), [])
            ):
                continue
            # Adjacent short orthogonal grid steps overlap physically because
            # their length can be smaller than half the trace width. A second
            # graph hop along this same chain is not a separate copper branch.
            chain_hops = set(neighbors)
            local_queue = list(neighbors)
            while local_queue:
                neighbor = local_queue.pop()
                local_radius = (
                    max(float(first(segments[neighbor], "width")[1]), float(first(s, "width")[1])) / 2 + 0.015
                )
                for endpoint_tag in ("start", "end"):
                    other_xy = first(segments[neighbor], endpoint_tag)[1:3]
                    if math.dist(tuple(map(float, other_xy)), (x, y)) > local_radius:
                        continue
                    additions = adjacency.get(pointkey(net, layer, other_xy), set()) - chain_hops
                    chain_hops.update(additions)
                    local_queue.extend(additions)
            junction = False
            for other in bins.get((net, layer, math.floor(x / 5), math.floor(y / 5)), set()) - chain_hops:
                q = segments[other]
                ax, ay = map(float, first(q, "start")[1:3])
                bx, by = map(float, first(q, "end")[1:3])
                dx, dy = bx - ax, by - ay
                t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy))) if dx or dy else 0
                if math.hypot(x - ax - t * dx, y - ay - t * dy) <= float(first(q, "width")[1]) / 2 + 0.01:
                    junction = True
                    break
            if junction:
                continue
            for other in neighbors - removed:
                removed.add(other)
                queue.append(other)
    return removed


class PowerRouter(InputRouter):
    connect = CONNECT

    def __init__(self, board):
        super().__init__(board)
        self.nx, self.ny = round(SIZE[0] / STEP) + 1, round(SIZE[1] / STEP) + 1
        self.xx = np.arange(self.nx)[:, None] * STEP
        self.yy = np.arange(self.ny)[None, :] * STEP
        self.pads = [p for p in self.pads if p["layers"]]
        self.geometry = [
            g for g in self.geometry if g["layers"]
        ]  # mask/paste-only pads are not copper obstacles
        # Custom copper primitives can extend beyond the anchor rectangle.
        # Omitting these produced a real LFPAK drain-tab clearance finding.
        for fp in children(board, "footprint"):
            for pad in children(fp, "pad"):
                if not children(pad, "primitives") or not children(pad, "net"):
                    continue
                layers = first(pad, "layers")[1:]
                copper = tuple(i for i, l in enumerate(LAYERS) if l in layers)
                if not copper:
                    continue
                at = first(pad, "at")
                px, py = map(float, at[1:3])
                pts = []
                for poly in children(first(pad, "primitives"), "gr_poly"):
                    for xy in children(first(poly, "pts"), "xy"):
                        pts.append(transform(fp, (px + float(xy[1]), py + float(xy[2]))))
                if pts:
                    x0, x1 = min(x for x, y in pts) - 100, max(x for x, y in pts) - 100
                    y0, y1 = min(y for x, y in pts) - 100, max(y for x, y in pts) - 100
                    self.geometry.append(
                        dict(
                            kind="rect",
                            xy=((x0 + x1) / 2, (y0 + y1) / 2),
                            size=(x1 - x0, y1 - y0),
                            net=str(first(pad, "net")[-1]).lstrip("/"),
                            layers=copper,
                            through=False,
                        )
                    )
                for circle in children(first(pad, "primitives"), "gr_circle"):
                    center = tuple(map(float, first(circle, "center")[1:3]))
                    end = tuple(map(float, first(circle, "end")[1:3]))
                    radius = math.dist(center, end) + float(first(circle, "width")[1]) / 2
                    cx, cy = transform(fp, (px + center[0], py + center[1]))
                    # Conservative full outer bounding box; the actual NPTH
                    # still blocks the central hole. Do not mistake the tiny
                    # custom-pad anchor for the electrical terminal land.
                    self.geometry.append(
                        dict(
                            kind="rect",
                            xy=(cx - 100, cy - 100),
                            size=(2 * radius, 2 * radius),
                            net=str(first(pad, "net")[-1]).lstrip("/"),
                            layers=copper,
                            through=False,
                        )
                    )
        self.load_existing_copper()
        self.max_search_nodes = 400000
        self.search_bias = 1.2

    def masks(self, net, width):
        b, v = MASKS(self, net, width)
        notch = (self.yy > 34.5 - width / 2) & ((self.xx < 6.5 + width / 2) | (self.xx > 151.5 - width / 2))
        b |= notch
        if net != "AGND":
            x0, y0, x1, y1 = THERMAL_REGIONS["U13"]
            field = (self.xx > x0 - 0.2) & (self.xx < x1 + 0.2) & (self.yy > y0 - 0.2) & (self.yy < y1 + 0.2)
            if net in U13_QUIET_FIELD_NETS:
                for layer in (1, 3, 4, 5):
                    b[layer] |= field
            else:
                b[1:] |= field
                v |= field
        v |= (self.yy > 34.2) & ((self.xx < 6.8) | (self.xx > 151.2))
        return b, v

    def via(self, net, point, diameter=0.6):
        # .60/.25mm plated through via, .175mm nominal annulus. Via-in-pad
        # locations require filled/capped construction, never an open solder wick.
        if any(
            g["kind"] == "via" and g["net"] == net and math.dist(g["xy"], point) < 0.18 for g in self.geometry
        ):
            return
        self.board.append(
            read_sexpr(
                f'(via (at {point[0] + 100} {point[1] + 100}) (size {diameter}) (drill .25) (layers "F.Cu" "B.Cu") (free yes) (net {self.nets[net]}))'
            )
        )
        self.geometry.append(dict(kind="via", xy=point, radius=diameter / 2, net=net, layers=tuple(range(6))))

    def safe_via(self, net, xy, diameter=0.6, clearance=0.19):
        radius = diameter / 2
        if net != "AGND" and net not in U13_QUIET_FIELD_NETS:
            x0, y0, x1, y1 = THERMAL_REGIONS["U13"]
            if x0 - 0.5 <= xy[0] <= x1 + 0.5 and y0 - 0.5 <= xy[1] <= y1 + 0.5:
                return False
        if any(math.dist(xy, mount) < 3.73 + radius for mount in MOUNTS):
            return False
        for hole, diameter in self.holes:
            if math.dist(hole, xy) < diameter / 2 + 0.125 + 0.26:
                return False
        for g in self.geometry:
            if g["kind"] == "via" and math.dist(g["xy"], xy) < 0.5 - 1e-7:
                return False
            if g["net"] == net:
                continue
            if g["kind"] == "line":
                x, y = g["start"]
                dx, dy = g["end"][0] - x, g["end"][1] - y
                t = (
                    max(0, min(1, ((xy[0] - x) * dx + (xy[1] - y) * dy) / (dx * dx + dy * dy)))
                    if dx or dy
                    else 0
                )
                if math.dist(xy, (x + t * dx, y + t * dy)) < g["width"] / 2 + radius + clearance:
                    return False
            elif g["kind"] == "via":
                if math.dist(g["xy"], xy) < g["radius"] + radius + clearance:
                    return False
            else:
                dx = max(0, abs(xy[0] - g["xy"][0]) - g["size"][0] / 2)
                dy = max(0, abs(xy[1] - g["xy"][1]) - g["size"][1] / 2)
                if math.hypot(dx, dy) < radius + clearance:
                    return False
        return True

    def ground_vias(self):
        added = 0
        # Via-in-pad requires filled/capped plating, explicitly a new fabrication
        # requirement. It removes long shared return detours at local capacitors.
        for p in self.pads:
            if p["net"] != "AGND" or p.get("through") or len(p["layers"]) != 1:
                continue
            if any(
                g["kind"] == "via" and g["net"] == "AGND" and math.dist(g["xy"], p["xy"]) < 0.3
                for g in self.geometry
            ):
                continue
            if self.safe_via("AGND", p["xy"]):
                self.via("AGND", p["xy"])
                added += 1
        print(
            f"P03 explicit local ground/thermal vias added:{added}; filled/capped process required",
            flush=True,
        )
        return added


def drc(cli):
    with tempfile.TemporaryDirectory(prefix="afx-p03-route-") as name:
        temp = Path(name)
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
        )
        board = ROOT / "power_p03.kicad_pcb"
        before = electrical_identity(read_sexpr(board.read_text()))
        # Refill in a scratch copy. A file-format/net round-trip error must not
        # destroy the only editable routed source before parity is inspected.
        for suffix in (".kicad_pcb", ".kicad_pro", ".kicad_dru"):
            shutil.copy2(ROOT / ("power_p03" + suffix), temp / ("power_p03" + suffix))
        shutil.copy2(ROOT / "fp-lib-table", temp / "fp-lib-table")
        shutil.copytree(ROOT / "RMX_P03.pretty", temp / "RMX_P03.pretty")
        candidate = temp / board.name
        args = [
            str(cli),
            "pcb",
            "drc",
            "--severity-all",
            "--refill-zones",
            "--save-board",
            "--format",
            "json",
            "-o",
            str(OUT / "route-drc.json"),
            str(candidate),
        ]
        p = subprocess.run(args, env=env, capture_output=True, text=True)
        assert p.returncode == 0, p.stdout + p.stderr
        aftertree = read_sexpr(candidate.read_text())
        after = electrical_identity(aftertree)
        if before != after:
            if before[0] != after[0]:
                raise ValueError("Native refill changed P03 connected-pad identity")
            # KiCad may auto-assign a track touching a newly moved pad. That is
            # not an approved netlist edit: rip up the conflicting original
            # copper and rerun from an unchanged-pad circuit, rather than accept
            # an apparently cleaner but electrically changed file.
            original = read_sexpr(board.read_text())
            oldnets = copper_nets(original)
            newnets = copper_nets(aftertree)
            changed = {key for key, name in oldnets.items() if key in newnets and newnets[key] != name}
            if not changed:
                raise ValueError(
                    "Native refill changed P03 copper identity without an identifiable net conflict"
                )
            original[:] = [
                obj
                for obj in original
                if not (
                    isinstance(obj, list)
                    and obj
                    and obj[0] in {"segment", "via"}
                    and copper_geometry(obj) in changed
                )
            ]
            (OUT / "native-net-conflicts.json").write_text(
                json.dumps(
                    [
                        dict(
                            geometry=key,
                            before=oldnets[key],
                            native_conflicting_assignment=newnets[key],
                            action="removed original copper; reroute required",
                        )
                        for key in sorted(changed)
                    ],
                    indent=2,
                )
                + "\n"
            )
            board.write_text(sexpr(named(original)) + "\n")
            print(
                f"P03 removed {len(changed)} copper objects with native net-assignment conflicts; no pad/net changes accepted",
                flush=True,
            )
            return drc(cli)
        shutil.copy2(candidate, board)
    from .construction import write_contract

    write_contract()
    result = json.loads((OUT / "route-drc.json").read_text())
    # This is a working diagnostic, not a replacement for fresh ERC/parity.
    (OUT / "current-native.json").write_text(
        json.dumps(
            dict(
                generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                scope="Native PCB-only all-severity DRC after scratch refill; ERC and schematic parity were not run",
                pcb_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
                schematic_sha256=hashlib.sha256((ROOT / "power_p03.kicad_sch").read_bytes()).hexdigest(),
                diagnostic="route-drc.json",
                diagnostic_sha256=hashlib.sha256((OUT / "route-drc.json").read_bytes()).hexdigest(),
                native_drc_violations=len(result["violations"]),
                native_open_connections=len(result["unconnected_items"]),
                erc_fresh_for_this_diagnostic=False,
                schematic_parity_checked=False,
                full_verification_receipt="verification.json",
                physical_tests_performed=0,
                fabrication_released=False,
                build_ready=False,
            ),
            indent=2,
        )
        + "\n"
    )
    return result


def clean(cli):
    """Reach a native cleanup fixed point BEFORE reading new airwire endpoints.

    Removing a dangling track invalidates its old native airwire position. A
    routing request against that deleted endpoint can create another dangling
    branch, so a fresh native result is mandatory after every cleanup mutation.
    """
    removed = 0
    for attempt in range(200):
        result = drc(cli)
        tree = coded(read_sexpr((ROOT / "power_p03.kicad_pcb").read_text()))
        uuids = set()
        dangling = set()
        for finding in result["violations"]:
            candidates = [i for i in finding["items"] if i["description"].startswith(("Track ", "Via "))]
            if not candidates or finding["type"] not in {
                "track_dangling",
                "via_dangling",
                "clearance",
                "hole_to_hole",
                "holes_co_located",
                "hole_clearance",
                "shorting_items",
                "solder_mask_bridge",
            }:
                raise RuntimeError(f"Physical geometry must be repaired before routing: {finding}")
            uuids.update(
                i["uuid"]
                for i in (
                    candidates if finding["type"] in {"track_dangling", "via_dangling"} else candidates[-1:]
                )
            )
            if finding["type"] == "track_dangling":
                dangling.update(i["uuid"] for i in candidates)
        uuids.update(dangling_chains(tree, dangling))
        if not uuids:
            if removed:
                print(
                    f"P03 fresh native cleanup reached fixed point after removing {removed} copper objects",
                    flush=True,
                )
            return result
        before = len(tree)
        tree[:] = [
            obj
            for obj in tree
            if not (
                isinstance(obj, list)
                and obj
                and obj[0] in {"segment", "via"}
                and children(obj, "uuid")
                and str(first(obj, "uuid")[1]) in uuids
            )
        ]
        if len(tree) == before:
            raise RuntimeError("Native cleanup did not change the implicated copper")
        removed += before - len(tree)
        (ROOT / "power_p03.kicad_pcb").write_text(sexpr(named(tree)) + "\n")
    raise RuntimeError("Native cleanup failed to reach a fixed point")


def run(cli, rounds=3):
    reports = []
    for stage in range(rounds):
        native = clean(cli)
        tree = coded(read_sexpr((ROOT / "power_p03.kicad_pcb").read_text()))
        remove = {
            i["uuid"]
            for v in native["violations"]
            if v["type"] in {"track_dangling", "via_dangling"}
            for i in v["items"]
        }
        tree[:] = [
            obj
            for obj in tree
            if not (
                isinstance(obj, list)
                and obj
                and obj[0] in {"segment", "via"}
                and children(obj, "uuid")
                and str(first(obj, "uuid")[1]) in remove
            )
        ]
        # A non-dangling violation must be repaired geometrically, never ignored.
        hard = [v for v in native["violations"] if v["type"] not in {"track_dangling", "via_dangling"}]
        repairs = []
        if hard:
            (OUT / "routing-hard-findings.json").write_text(json.dumps(hard, indent=2) + "\n")
            for finding in hard:
                candidates = [i for i in finding["items"] if i["description"].startswith(("Track ", "Via "))]
                if not candidates or finding["type"] not in {
                    "clearance",
                    "hole_to_hole",
                    "holes_co_located",
                    "hole_clearance",
                    "shorting_items",
                    "solder_mask_bridge",
                }:
                    raise RuntimeError(f"Nonrepairable native geometry finding:{finding}")
                repairs.append(candidates[-1]["uuid"])
            tree[:] = [
                obj
                for obj in tree
                if not (
                    isinstance(obj, list)
                    and obj
                    and obj[0] in {"segment", "via"}
                    and children(obj, "uuid")
                    and str(first(obj, "uuid")[1]) in repairs
                )
            ]
            print(
                f"P03 removed{len(set(repairs))}offending copper objects using fresh native geometry findings; rerouting remains required",
                flush=True,
            )
        router = PowerRouter(tree)
        router.ground_vias()
        positions = {}
        for fp in children(tree, "footprint"):
            for pad in children(fp, "pad"):
                if children(pad, "uuid"):
                    positions[str(first(pad, "uuid")[1])] = pad

        copper_by_uuid = {
            str(first(obj, "uuid")[1]): obj
            for tag in ("segment", "via")
            for obj in children(tree, tag)
            if children(obj, "uuid")
        }
        resolved_anchors = []

        def endpoint(item, net):
            point = (item["pos"]["x"] - 100, item["pos"]["y"] - 100)
            description = item["description"]
            # An existing native track may already terminate on a through-via,
            # including a retained track on a normally reserved ground layer.
            # Use that actual connected barrel electrode, not an invented new
            # layer transition at the rounded airwire coordinate.
            obj = copper_by_uuid.get(item["uuid"])
            if obj is not None and obj[0] == "segment":
                ax, ay = [float(v) - 100 for v in first(obj, "start")[1:3]]
                bx, by = [float(v) - 100 for v in first(obj, "end")[1:3]]
                dx, dy = bx - ax, by - ay
                candidates = []
                for via in router.geometry:
                    if via["kind"] != "via" or via["net"] != net:
                        continue
                    x, y = via["xy"]
                    t = (
                        max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
                        if dx or dy
                        else 0
                    )
                    if (
                        math.hypot(x - ax - t * dx, y - ay - t * dy)
                        < via["radius"] + float(first(obj, "width")[1]) / 2 - 0.01
                    ):
                        candidates.append(via)
                if candidates:
                    via = min(candidates, key=lambda v: math.dist(v["xy"], point))
                    resolved_anchors.append(
                        dict(track_uuid=item["uuid"], net=net, actual_connected_via_mm=via["xy"])
                    )
                    return dict(net=net, xy=via["xy"], layers=tuple(range(6)))
            if description.startswith("Via ") or "PTH pad" in description:
                layers = tuple(range(6))
            elif "on F.Cu" in description:
                layers = (0,)
            elif "on B.Cu" in description:
                layers = (5,)
            elif " on In" in description:
                layers = (LAYERS.index(re.search(r"on (In[1-4].Cu)", description)[1]),)
            else:
                layers = tuple(range(6))
            return dict(net=net, xy=point, layers=layers)

        success, failed = 0, []

        # Analog/SET/reference first; ground planes already join most AGND pads.
        def priority(row):
            text = row["items"][0]["description"]
            return ("AGND" in text, "VIN_PROTECTED" in text, "5V_DIG_SRC" in text, text)

        for index, row in enumerate(sorted(native["unconnected_items"], key=priority)):
            if len(row["items"]) != 2:
                raise ValueError("Expected two native airwire terminals")
            match = re.search(r"\[/([^\]]+)\]", row["items"][0]["description"])
            if not match:
                raise ValueError(row)
            net = match[1]
            source, target = (endpoint(i, net) for i in row["items"])
            widths = (0.16,) if any(n in net for n in ("FB", "SET", "FSEL", "MODE", "BOOT")) else (0.25, 0.16)
            if any(router.connect(source, target, width) for width in widths):
                success += 1
            else:
                failed.append(row)
            if index % 40 == 0:
                print(
                    f"P03 routing round{stage + 1}: {index + 1}/{len(native['unconnected_items'])}, {success}joined,{len(failed)}search holds",
                    flush=True,
                )
        (ROOT / "power_p03.kicad_pcb").write_text(sexpr(named(tree)) + "\n")
        reports.append(
            dict(
                round=stage + 1,
                native_initial_opens=len(native["unconnected_items"]),
                removed_dangling_objects=len(remove),
                new_connections=success,
                failed_searches=failed,
                routes=router.routes,
                native_existing_barrel_anchors=resolved_anchors,
            )
        )
        (OUT / "routing-progress.json").write_text(json.dumps(reports, indent=2) + "\n")
        if not native["unconnected_items"] and not remove:
            break
    result = clean(cli)
    print(
        f"P03 routing aid: {len(result['violations'])}native violations,{len(result['unconnected_items'])}opens; no physical qualification",
        flush=True,
    )


def main():
    global STEP, MASKS, CONNECT
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli", type=Path, required=True)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--grid-mm", type=float, choices=(0.05, 0.1, 0.125), default=0.125)
    a = p.parse_args()
    STEP = a.grid_mm
    # Keep inherited obstacle and path-search coordinates on the same grid.
    # A finer trial does not relax any native copper clearance or via size.
    mask_globals["STEP"] = STEP
    CONNECT = types.FunctionType(Router.connect.__code__, dict(Router.connect.__globals__, STEP=STEP))
    PowerRouter.connect = CONNECT
    run(a.kicad_cli, a.rounds)


if __name__ == "__main__":
    main()
