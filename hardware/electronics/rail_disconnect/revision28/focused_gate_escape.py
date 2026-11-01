"""Append a real P19 gate link between independently traced native barrels.

No existing gate/force/timing object, component, rule or hole is removed/moved.
The routing-only numeric-net view is never saved. In4 must contain no foreign
filled power-zone copper in both the frozen reference and current source fill;
all actual pads/tracks/vias remain obstacles. Native checks remain mandatory.
"""

import argparse
import copy
import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..revision26.layout import POWER_NETS as FORCE_NETS
from .ground_corridor import path_between
from .repair import Router

ROOT = Path(__file__).resolve().parent


def numeric_view(tree):
    view = copy.deepcopy(tree)
    assert not children(view, "net"), "This trial expects modern native named-net encoding"
    labels = set()

    def visit(node, operation):
        if not isinstance(node, list):
            return
        if node and node[0] == "net":
            operation(node)
        else:
            for member in node:
                visit(member, operation)

    visit(view, lambda node: labels.add(str(node[-1])))
    codes = {name: i for i, name in enumerate(sorted(labels), 1)}

    def number(node):
        label = str(node[-1])
        node[:] = [a("net"), a(codes[label]), label]

    visit(view, number)
    view.extend([[a("net"), a(code), name] for name, code in codes.items()])
    return view


def main(workspace):
    base = ROOT / "generated/discrete-signal-router"
    source = base / "candidate/rail_disconnect.kicad_pcb"
    filled = ROOT / "generated/filled-discrete-routed1.kicad_pcb"
    graph_path = base / "gate-native-components.json"
    graph = json.loads(graph_path.read_text())
    before = source.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    assert digest == graph["source_pcb_sha256"]
    assert hashlib.sha256(filled.read_bytes()).hexdigest() == graph["filled_pcb_sha256"]
    main_group = next(
        r for r in graph["groups"] if r["logical_pads"] == [["Q1", "2"], ["Q2", "2"], ["R1", "2"]]
    )
    leaf = next(r for r in graph["groups"] if r["logical_pads"] == [["R2", "1"]])
    start = next(r for r in leaf["native_objects"] if r["kind"] == "PCB_VIA")
    targets = sorted(
        (r for r in main_group["native_objects"] if r["kind"] == "PCB_VIA"),
        key=lambda r: math.dist(start["position_mm"], r["position_mm"]),
    )
    tree = read_sexpr(before.decode())
    layer = "In4.Cu"
    for board in (filled, base / "force-filled-reference.kicad_pcb"):
        # The export kept its original reference in the parent pilot workspace.
        if not board.exists():
            board = ROOT / "generated/original-force-reference-router/force-filled-reference.kicad_pcb"
        ft = read_sexpr(board.read_text())
        for zone in children(ft, "zone"):
            if not children(zone, "net"):
                continue
            net = str(first(zone, "net")[-1]).lstrip("/")
            if net in FORCE_NETS:
                assert not any(str(first(p, "layer")[1]) == layer for p in children(zone, "filled_polygon"))
    router = Router(numeric_view(tree))
    source_xy = tuple(v - 100 for v in start["position_mm"])
    selected, failures = None, []
    for target in targets[:2]:
        target_xy = tuple(v - 100 for v in target["position_mm"])
        for margin in (4, 10):
            try:
                points, visited = path_between(
                    router, source_xy, target_xy, 4, margin=margin, step=0.025, net="P19_GATE"
                )
                selected = (target, points, visited, margin)
                break
            except AssertionError as error:
                failures.append(dict(target=target, margin=margin, failure=str(error)))
        if selected:
            break
    workspace = Path(workspace).resolve()
    assert workspace.is_relative_to(ROOT / "generated") and not workspace.exists()
    workspace.mkdir()
    (workspace / "generated").mkdir()
    if selected is None:
        (workspace / "generated/failed-gate-escape.json").write_text(json.dumps(failures, indent=2) + "\n")
        raise AssertionError("Bounded existing-barrel corridors blocked; no copper emitted")
    for p in (base / "candidate").iterdir():
        if (
            p.is_file()
            and p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("sym-lib-table", "fp-lib-table", "components.json")
        ):
            shutil.copy2(p, workspace / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, workspace / p.name)
    target, points, visited, margin = selected
    added = []
    for index, (start_point, end_point) in enumerate(zip(points, points[1:])):
        if math.dist(start_point, end_point) < 1e-9:
            continue
        uid = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:focused-gate:{digest}:{index}:{start_point}:{end_point}")
        )
        node = read_sexpr(
            f"(segment (start {start_point[0] + 100:.6f} {start_point[1] + 100:.6f}) "
            f"(end {end_point[0] + 100:.6f} {end_point[1] + 100:.6f}) (width .2) "
            f'(layer "{layer}") (net "/P19_GATE") (uuid {uid}))'
        )
        tree.append(node)
        added.append(sexpr(node))
    (workspace / source.name).write_text(sexpr(tree) + "\n")
    report = dict(
        source_pcb_sha256=digest,
        source_native_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(),
        candidate_pcb_sha256=hashlib.sha256((workspace / source.name).read_bytes()).hexdigest(),
        added_actual_segments=added,
        actual_route_points_board_mm=points,
        layer=layer,
        width_mm=0.2,
        routing_grid_mm=0.025,
        margin_mm=margin,
        visited_cells=visited,
        source_barrel=start,
        target_barrel=target,
        all_existing_objects_and_operative_gate_links_retained=True,
        new_drills_or_placements=0,
        numeric_view_saved=False,
        chosen_layer_has_no_filled_power_pours_in_current_and_reference=True,
        analog_return_cut_and_gate_transients_need_independent_checks=True,
        source_recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        physical_qualified=False,
    )
    (workspace / "generated/focused-gate-escape.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Appended", len(added), "real0.2mm gate segments on", layer)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    args = p.parse_args()
    main(args.workspace)
