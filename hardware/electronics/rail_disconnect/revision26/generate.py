"""E26 escape-first variant; original E25/A11 files are never rewritten."""

import argparse
import copy
import json
import shutil
from pathlib import Path

from ...common.netlists import netlist
from ...common.placement import footprint_root
from ...common.reports import sha
from ...common.sexpr import children, first, read_sexpr, sexpr
from .layout import BULK, DRIVERS, MOVES, POWER_NETS, Layout

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
SOURCE = PARENT / "placement"
OUT = ROOT / "generated"


def generate(cli):
    OUT.mkdir(exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    baseline = read_sexpr((SOURCE / "rail_disconnect.kicad_pcb").read_text())
    parts = {c["ref"]: c for c in json.loads((PARENT / "components.json").read_text())}
    _, pins = netlist(SOURCE / "generated/netlist.xml")
    board = [
        copy.deepcopy(n)
        for n in baseline
        if not isinstance(n, list)
        or not n
        or n[0] != "footprint"
        or any(p[1] == "Reference" and str(p[2]).startswith("H") for p in children(n, "property"))
    ]
    lay = Layout(board, parts, pins, footprint_root(str(cli)))
    poses = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): (
            float(first(f, "at")[1]) - 100,
            float(first(f, "at")[2]) - 100,
            float(first(f, "at")[3]) if len(first(f, "at")) > 3 else 0,
            str(first(f, "layer")[1]).split(".")[0],
        )
        for f in children(baseline, "footprint")
    }
    poses.update(MOVES)
    originals = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(baseline, "footprint")
    }
    driver_caps = {c for cs in DRIVERS.values() for c in cs}
    for ref in parts:
        if ref.startswith("R") or ref.startswith("C") and ref not in BULK:
            continue
        fp = copy.deepcopy(originals[ref]) if ref in BULK else lay.footprint(ref, poses[ref])
        lay.add_body(ref, fp, poses[ref])
    for u, (aux, a, b) in DRIVERS.items():
        x, y, _, _ = poses[u]
        for ref, dx, dy in ((aux, -6.25, -2.5), (a, 6.25, -1.1), (b, 6.25, 1.6)):
            pose = (x + dx, y + dy, 180, "F")
            lay.add_body(ref, lay.footprint(ref, pose), pose)
    lay.refresh()
    # Local grouped source buses keep main current off thin signal routing.
    for i in range(1, 15):
        ps = [p for p in lay.router.by_ref["Q" + str(i)] if p["pin"] == "1"]
        ps.sort(key=lambda p: p["xy"][1])
        lay.local(ps[0]["net"], 0, [p["xy"] for p in ps], 0.7)
    for l, r in ((1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14)):
        left = lay.pad("Q" + str(l), 1)
        right = lay.pad("Q" + str(r), 1)
        y = poses["Q" + str(l)][1]
        lay.local(left["net"], 0, [(left["xy"][0], y), (right["xy"][0], y)], 1.2)
    lay.local("5V_DIG_COMMON", 0, [(131.5, 7), (131.5, 13)], 1.2)
    lay.local("5V_DIG_SRC", 0, [(126.67, 7), (126.67, 13)], 2.0)
    lay.local("5V_DIG", 0, [(136.33, 7), (136.33, 13)], 2.0)
    # Gate vias escape away from adjacent source bars, not through large drain pads.
    for i in range(1, 15):
        p = lay.pad("Q" + str(i), 2)
        x, y = p["xy"]
        lay.port(p, (x, y + (0.97 if i % 2 == 0 else -0.97)), width=0.25)
    # Driver multiplier capacitors have short direct F.Cu connections; do not add
    # parasitic through-vias to these two-terminal10pF oscillator nodes.
    skipped = set()
    for u, (aux, a, b) in DRIVERS.items():
        p = lay.pad(u, 1)
        cap = lay.pad(aux, 1)
        via = (round(p["xy"][0] - 1.625, 6), cap["xy"][1])
        lay.local(p["net"], 0, [p["xy"], (via[0], p["xy"][1]), via, cap["xy"]], 0.25)
        lay.port(cap, via, path=[cap["xy"], via], width=0.25)
        skipped.add((u, "1"))
        for number, ref in ((7, a), (6, b)):
            p = lay.pad(u, number)
            c = lay.pad(ref, 2)
            lay.local(p["net"], 0, [p["xy"], c["xy"]], 0.25)
            skipped.add((u, str(number)))
            q = lay.pad(ref, 1)
            lay.port(q, (q["xy"][0] + 1.2, q["xy"][1]), width=0.25)
        ground = lay.pad(aux, 2)
        lay.port(ground, (ground["xy"][0] - 1.2, ground["xy"][1]), width=0.25)
    # Every IC pad gets a reserved conventional-via escape before global traces.
    for i in range(1, 13):
        ref = "U" + str(i)
        cx, cy, angle, _ = poses[ref]
        ps = lay.router.by_ref[ref]
        for p in ps:
            if (ref, p["pin"]) in skipped or p["net"].startswith("unconnected-"):
                continue
            horizontal = round(angle) % 180 == 0
            axis = 0 if horizontal else 1
            sign = 1 if p["xy"][axis] > (cx, cy)[axis] else -1
            long_half = p["size"][axis] / 2
            offset = long_half + 0.575
            if i >= 7 or i <= 6 and p["xy"][0] < cx:
                offset += 1.0 * (int(p["pin"]) % 2)
            via = list(p["xy"])
            via[axis] += sign * offset
            via = tuple(round(v, 6) for v in via)
            lay.port(p, via, width=0.2 if i in (11, 12) else 0.25)
    # Source/drain power connections use parallel conventional vias where a wide
    # main-current plane must change layer. The eventual plane solver must include
    # these barrels, pad spreading and all necks.
    arrays = {3: (50.3, 0.635), 4: (67.05, 0), 7: (91.95, 0), 8: (110.05, 0), 9: (33.3, 0), 10: (49.7, 0)}
    for i, (x, dy) in arrays.items():
        ps = [p for p in lay.router.by_ref["Q" + str(i)] if p["pin"] == "3"]
        outer = [p for p in ps if p["size"][0] < 1]
        for p in outer:
            via = (x, round(p["xy"][1] + dy, 6))
            lay.port(p, via, width=0.5)
    # Provide slow sensing ports for F.Cu-only rail/common banks without forcing
    # their load currents through the small signal vias.
    for i in (1, 2, 5, 6, 11, 12):
        ps = [p for p in lay.router.by_ref["Q" + str(i)] if p["pin"] == "3"]
        p = next(p for p in ps if p["size"][0] < 1)
        sign = -1 if i % 2 else 1
        if i in (2, 6):
            p = max((p for p in ps if p["size"][0] < 1), key=lambda p: p["xy"][1])
            via = (p["xy"][0], p["xy"][1] + 1.25)
        else:
            via = (p["xy"][0] + sign * 1.25, p["xy"][1])
        lay.port(p, via, width=0.5)
    for i in (1, 3, 5, 7, 9, 11):
        p = lay.pad("Q" + str(i), 1)
        cx = (poses["Q" + str(i)][0] + poses["Q" + str(i + 1)][0]) / 2
        via = (cx, poses["Q" + str(i)][1] + 3.5)
        lay.port(p, via, path=[p["xy"], (cx, p["xy"][1]), via], width=0.25)
    # Remaining top bypass/filter capacitors get both their copper lands and via
    # corridors allocated as one unit. This prevents the old placement's escape trap.
    fixed_anchor = {
        "C25": "U7",
        "C26": "U7",
        "C29": "U8",
        "C34": "U9",
        "C35": "U10",
        "C36": "U11",
        "C37": "U12",
        "C38": "J5",
    }

    def anchor(ref):
        if ref in fixed_anchor:
            return poses[fixed_anchor[ref]][:2]
        special = set(pins[ref].values()) - {"AGND", "V2V5_AUX"}
        ranked = sorted((-len(special & set(pins[u].values())), u) for u in poses if u.startswith("U"))
        return poses[ranked[0][1]][:2]

    def auto(ref, side):
        ax, ay = anchor(ref)
        candidates = sorted(
            ((x - ax) ** 2 + (y - ay) ** 2, x, y)
            for x in range(7, 151, 5)
            for y in (4.5, 8, 11.5, 15, 18.5, 22, 25.5, 29, 32.5, 36, 39.5, 43)
        )
        for _, x, y in candidates:
            pose = (x, y, 0, side)
            fp = lay.footprint(ref, pose)
            if not lay.legal_body(ref, fp):
                continue
            trial = type(lay.router)([n for n in board if isinstance(n, list) and n and n[0] == "net"] + [fp])
            ps = trial.by_ref[ref]
            pairs = []
            for p in ps:
                sign = 1 if p["xy"][0] > x else -1
                via = (x + sign * 2, y + sign * 0.7)
                if not lay.free_via(p["net"], via) or not lay.free_line(
                    p["net"], p["layers"][0], p["xy"], via, 0.25
                ):
                    break
                pairs.append((p, via))
            else:
                lay.add_body(ref, fp, pose)
                lay.refresh()
                for p, via in pairs:
                    lay.port(lay.pad(ref, p["pin"]), via, width=0.25)
                return
        raise RuntimeError((ref, "no placement with reserved legal escapes"))

    for ref in parts:
        if ref.startswith("C") and ref not in BULK and ref not in driver_caps:
            auto(ref, "F")
    for ref in sorted((r for r in parts if r.startswith("R")), key=lambda r: int(r[1:])):
        auto(ref, "B")
    # Headers are already plated through all layers. Bulk/rail headers are joined
    # by the main-current planes, not by narrow global signal traces.
    for ref in ("J1", "J2", "J3", "J4", "J5", "J6"):
        for p in lay.router.by_ref[ref]:
            if p["net"] not in POWER_NETS and p["net"] != "AGND":
                lay.ports.append(p)
    for n in ("rail_disconnect.kicad_pro", "fp-lib-table"):
        shutil.copy2(SOURCE / n, ROOT / n)
    shutil.copytree(SOURCE / "RMX_Disconnect.pretty", ROOT / "RMX_Disconnect.pretty", dirs_exist_ok=True)
    for fp in children(board, "footprint"):
        for pad in children(fp, "pad"):
            if children(pad, "net") and str(first(pad, "net")[-1]).startswith("/unconnected-"):
                first(pad, "net")[-1] = str(first(pad, "net")[-1])[1:]
    (ROOT / "rail_disconnect.kicad_pcb").write_text(sexpr(board) + "\n")
    packet = dict(
        revision="E26",
        source_placement_sha256=sha(SOURCE / "rail_disconnect.kicad_pcb"),
        schematic_sha256=sha(PARENT / "rail_disconnect.kicad_sch"),
        components_sha256=sha(PARENT / "components.json"),
        placements={k: list(v) for k, v in lay.placements.items()},
        ports=lay.ports,
        local_paths=lay.local_paths,
        segments=len(children(board, "segment")),
        vias=len(children(board, "via")),
        required_minimum_finished_copper_um=70,
        required_copper_temperature_ceiling_c=85,
        board_size_mm=[156, 45.25, 1.6],
        proposed_copper_layers=6,
        pcb_routed=False,
        physical_fit_verified=False,
        copper_loss_or_current_balance_qualified=False,
        build_ready=False,
    )
    (OUT / "placement-inputs.json").write_text(json.dumps(packet, indent=2) + "\n")
    print(
        "E26escape-first candidate:",
        len(lay.placements),
        "parts,",
        len(lay.ports),
        "ports;",
        packet["segments"],
        "segments,",
        packet["vias"],
        "vias; native checks required",
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli", required=True)
    a = p.parse_args()
    generate(Path(a.kicad_cli).resolve())


if __name__ == "__main__":
    main()
