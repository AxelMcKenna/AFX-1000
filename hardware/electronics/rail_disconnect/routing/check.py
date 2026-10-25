"""Check original pin geometry, actual local copper and native E25 routing results."""

import argparse
import copy
import datetime
import heapq
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ...common.netlists import netlist
from ...common.placement import footprint_root
from ...common.reports import sha
from ...common.sexpr import children, first, read_sexpr
from ...output_stage.check_placement import transform
from ..placement.check import mechanical
from ..verify import contract

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
PLACEMENT = PARENT / "placement"
OUT = ROOT / "generated"
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")


def point_segment(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def segment_distance(a, b, c, d):
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    if (
        cross(a, b, c) * cross(a, b, d) <= 0
        and cross(c, d, a) * cross(c, d, b) <= 0
        and all(
            max(min(a[k], b[k]), min(c[k], d[k])) <= min(max(a[k], b[k]), max(c[k], d[k])) + 1e-7
            for k in (0, 1)
        )
    ):
        return 0
    return min(point_segment(a, c, d), point_segment(b, c, d), point_segment(c, a, b), point_segment(d, a, b))


def copper_path(tree, net, start, end, minimum_width=0.7):
    """Measure the actual F.Cu centre-line graph, including interior junctions."""
    fs = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }

    def pad(endpoint):
        ref, number, index = endpoint
        fp = fs[ref]
        pads = [p for p in children(fp, "pad") if str(p[1]) == str(number)]
        assert 0 <= index < len(pads), (ref, number, index)
        p = pads[index]
        assert str(first(p, "net")[-1]).lstrip("/") == net
        assert first(fp, "layer")[1] == "F.Cu"
        return tuple(transform(fp, first(p, "at")[1:3]))

    a, b = pad(start), pad(end)
    edges = []
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    for s in children(tree, "segment"):
        if names[str(first(s, "net")[1])] != net or first(s, "layer")[1] != "F.Cu":
            continue
        if float(first(s, "width")[1]) + 1e-9 < minimum_width:
            continue
        edges.append((tuple(map(float, first(s, "start")[1:3])), tuple(map(float, first(s, "end")[1:3]))))
    starts = [i for i, (c, d) in enumerate(edges) if point_segment(a, c, d) < 1e-5]
    goals = {i for i, (c, d) in enumerate(edges) if point_segment(b, c, d) < 1e-5}
    assert starts and goals, (net, start, end, "missing expected physical copper endpoint")
    graph = {i: [] for i in range(len(edges))}
    for i, (c, d) in enumerate(edges):
        for j, (e, f) in enumerate(edges[:i]):
            if segment_distance(c, d, e, f) < 1e-5:
                graph[i].append(j)
                graph[j].append(i)
    queue = [(0, i) for i in starts]
    visited = set()
    while queue:
        length, index = heapq.heappop(queue)
        if index in visited:
            continue
        visited.add(index)
        if index in goals:
            return round(length + math.dist(*edges[index]), 6)
        for other in graph[index]:
            heapq.heappush(queue, (length + math.dist(*edges[index]), other))
    raise AssertionError((net, start, end, "actual copper path disconnected"))


def local_contract(tree):
    result = {}
    for q in range(1, 15):
        fp = next(
            f
            for f in children(tree, "footprint")
            if any(p[1:3] == ["Reference", f"Q{q}"] for p in children(f, "property"))
        )
        net = str(first(next(p for p in children(fp, "pad") if p[1] == "1"), "net")[-1]).lstrip("/")
        for index in (1, 2):
            result[f"Q{q}_source_land_{index}"] = copper_path(tree, net, (f"Q{q}", 1, 0), (f"Q{q}", 1, index))
    for left, right in ((1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14)):
        fp = next(
            f
            for f in children(tree, "footprint")
            if any(p[1:3] == ["Reference", f"Q{left}"] for p in children(f, "property"))
        )
        net = str(first(next(p for p in children(fp, "pad") if p[1] == "1"), "net")[-1]).lstrip("/")
        result[f"common_bus_Q{left}_Q{right}"] = copper_path(
            tree, net, (f"Q{left}", 1, 1), (f"Q{right}", 1, 1)
        )
    result["digital_parallel_common"] = copper_path(tree, "5V_DIG_COMMON", ("Q11", 1, 1), ("Q13", 1, 1))
    result["digital_parallel_source"] = copper_path(tree, "5V_DIG_SRC", ("Q11", 3, 0), ("Q13", 3, 0), 2)
    result["digital_parallel_protected"] = copper_path(tree, "5V_DIG", ("Q12", 3, 0), ("Q14", 3, 0), 2)
    return result


def check(cli, local=False):
    global OUT
    OUT = ROOT / "generated/local-source-bars" if local else ROOT / "generated"
    OUT.mkdir(exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    pcb = (OUT if local else ROOT) / "rail_disconnect.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    baseline = read_sexpr((PLACEMENT / "rail_disconnect.kicad_pcb").read_text())
    stripped = [n for n in tree if not isinstance(n, list) or not n or n[0] not in ("segment", "via", "zone")]
    assert stripped == baseline, "Routing candidate changed placed geometry/net topology"
    with tempfile.TemporaryDirectory(prefix="rmx-e25-routing-check-") as folder:
        temp = Path(folder)
        for n in ("rail_disconnect.kicad_sch", "sym-lib-table", "RMX_E17.kicad_sym"):
            shutil.copy2(PARENT / n, temp / n)
        shutil.copy2(pcb, temp / "rail_disconnect.kicad_pcb")
        for n in ("rail_disconnect.kicad_pro", "fp-lib-table"):
            shutil.copy2(ROOT / n, temp / n)
        shutil.copytree(ROOT / "RMX_Disconnect.pretty", temp / "RMX_Disconnect.pretty")
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
            FONTCONFIG_FILE=str(ROOT.parents[3] / "build-hardware/kicad-fonts.conf"),
        )

        def run(*args):
            r = subprocess.run([str(cli), *map(str, args)], env=env, capture_output=True, text=True)
            assert r.returncode == 0, (args, r.stdout, r.stderr)
            return r.stdout.strip()

        version = run("--version")
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "netlist.xml",
            temp / "rail_disconnect.kicad_sch",
        )
        parts, pins = netlist(OUT / "netlist.xml")
        contract(parts, pins)
        mechanical(copy.deepcopy(stripped), parts, pins)
        paths = local_contract(tree)
        run(
            "pcb",
            "drc",
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--format",
            "json",
            "-o",
            OUT / "drc.json",
            temp / "rail_disconnect.kicad_pcb",
        )
        native = json.loads((OUT / "drc.json").read_text())
        assert not native["violations"] and not native["schematic_parity"], (
            len(native["violations"]),
            len(native["schematic_parity"]),
        )
        for name, layers in (("top", "F.Cu,F.Fab,Edge.Cuts"), ("bottom", "B.Cu,B.Fab,Edge.Cuts")):
            run(
                "pcb",
                "export",
                "svg",
                "--mode-single",
                "--page-size-mode",
                "2",
                "--exclude-drawing-sheet",
                "--layers",
                layers,
                "-o",
                OUT / (name + ".svg"),
                temp / "rail_disconnect.kicad_pcb",
            )
    files = [
        *ROOT.glob("*.py"),
        ROOT / "README.md",
        ROOT / "reviewed-copper.json",
        pcb,
        ROOT / "rail_disconnect.kicad_pro",
        ROOT / "fp-lib-table",
        *list((ROOT / "RMX_Disconnect.pretty").glob("*.kicad_mod")),
        OUT / "routing-inputs.json",
        OUT / "drc.json",
        OUT / "netlist.xml",
        PLACEMENT / "rail_disconnect.kicad_pcb",
        PLACEMENT / "generated/verification.json",
        PARENT / "rail_disconnect.kicad_sch",
        PARENT / "components.json",
        PARENT / "verify.py",
        PARENT.parent / "common/sexpr.py",
        PARENT.parent / "common/netlists.py",
        PARENT.parent / "output_stage/check_placement.py",
        PARENT / "placement/check.py",
    ]
    report = dict(
        revision="E25-routing",
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        kicad_version=version,
        circuit_components=164,
        physical_mosfet_lands_preserved=True,
        placed_geometry_preserved=True,
        routed_segments=len(children(tree, "segment")),
        through_vias=len(children(tree, "via")),
        native_drc_violations=0,
        schematic_parity_issues=0,
        native_open_connections=len(native["unconnected_items"]),
        independent_local_paths=paths,
        local_path_lengths_scope="Conservative sum of entire touched F.Cu segment centre lines; not an optimized resistance or current-sharing model",
        pcb_routed=not native["unconnected_items"],
        dc_loss_current_balance_or_thermal_qualified=False,
        protection_timing_verified=False,
        physical_fit_verified=False,
        hardware_verified=False,
        build_ready=False,
        source_sha256={os.path.relpath(p, ROOT): sha(p) for p in files},
    )
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"E25 routing: {report['routed_segments']} segments/{report['through_vias']} vias; zero native DRC/parity; {report['native_open_connections']} opens; {len(paths)} independent local paths; unqualified"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True)
    parser.add_argument(
        "--local", action="store_true", help="Check the independently saved source-bar milestone"
    )
    args = parser.parse_args()
    check(Path(args.kicad_cli).resolve(), args.local)


if __name__ == "__main__":
    main()
