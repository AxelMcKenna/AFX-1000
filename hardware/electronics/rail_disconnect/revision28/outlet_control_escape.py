"""Separate U13 output barrel with real local control-trace detours.

No package land, terminal, hole or rule is moved. Two identified control
connections are rerouted on their original layers around the new real hole.
Via-in-pad assembly, mask/paste, current and transient limits remain open.
"""

import argparse
import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .ground_corridor import path_between
from .repair import Router

ROOT = Path(__file__).resolve().parent
REMOVE_ALLOW = {
    "1dbb5f1b-3259-5484-ab47-bacf6d1da193",
    "530b883b-486f-563b-b29a-9594a50c5302",
    "77c62a52-c164-5fc6-b84c-b372316e2c1d",
    "0bd61fff-4a6a-53e6-bb43-021978501519",
    "b3aed3cf-9347-51ef-9f77-f1d9d5dccbea",
    "32e308b2-7385-5601-8532-d3c779bc8e68",
    "34c08ed1-145e-5ff9-b989-2de4dcec72ef",
}
REMOVE_REF = {"90f7dcca-643c-509a-99df-b1761885f548"}


def main(workspace):
    source = ROOT / "generated/p9-analog-outlet-work"
    path = source / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    tree = read_sexpr(before.decode())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    codes = {name: code for code, name in names.items()}
    selected = REMOVE_ALLOW | REMOVE_REF
    removed = [s for s in children(tree, "segment") if str(first(s, "uuid")[1]) in selected]
    assert len(removed) == len(selected)
    for s in removed:
        identity = str(first(s, "uuid")[1])
        assert names[str(first(s, "net")[1])] == ("P12_ALLOW" if identity in REMOVE_ALLOW else "P12_OV_REF")
        assert float(first(s, "width")[1]) == 0.2
    tree[:] = [s for s in tree if s not in removed]
    added = []
    point = (41.876, 5.95)
    via = read_sexpr(
        f"(via (at {point[0] + 100} {point[1] + 100}) (size .6) (drill .3) "
        f'(layers "F.Cu" "B.Cu") (net {codes["V5_REG"]}) '
        f"(uuid {uuid.uuid5(uuid.NAMESPACE_URL, 'rmx:E28:U13OUT6:' + digest)}))"
    )
    tree.append(via)
    added.append(sexpr(via))
    attempts = []
    routes = []
    for net, start, finish, layer in (
        ("P12_ALLOW", (41.1, 6.2), (42.6, 6.6), 1),
        ("P12_OV_REF", (42.9, 4.1), (40.6, 6.4), 4),
    ):
        rt = Router(tree)
        try:
            points, visited = path_between(rt, start, finish, layer, margin=3, step=0.025, net=net)
        except AssertionError as e:
            attempts.append(dict(net=net, failure=str(e)))
            raise AssertionError((net, "No actual detour; no candidate source written", attempts)) from e
        layername = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")[layer]
        for index, (aa, bb) in enumerate(zip(points, points[1:])):
            if math.dist(aa, bb) < 1e-8:
                continue
            segment = read_sexpr(
                f"(segment (start {aa[0] + 100:.6f} {aa[1] + 100:.6f}) "
                f"(end {bb[0] + 100:.6f} {bb[1] + 100:.6f}) (width .2) "
                f'(layer "{layername}") (net {codes[net]}) '
                f"(uuid {uuid.uuid5(uuid.NAMESPACE_URL, f'rmx:E28:U13OUT6:{digest}:{net}:{index}')}))"
            )
            tree.append(segment)
            added.append(sexpr(segment))
        routes.append(dict(net=net, layer=layername, points=points, visited=visited))
    workspace = Path(workspace).resolve()
    assert workspace.is_relative_to(ROOT / "generated") and not workspace.exists()
    workspace.mkdir()
    (workspace / "generated").mkdir()
    for p in source.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, workspace / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, workspace / p.name)
    (workspace / path.name).write_text(sexpr(tree) + "\n")
    report = dict(
        source_pcb_sha256=digest,
        candidate_pcb_sha256=hashlib.sha256((workspace / path.name).read_bytes()).hexdigest(),
        removed_actual_control_objects=[sexpr(s) for s in removed],
        added_actual_objects=added,
        routes=routes,
        existing_package_pads_and_component_poses_unchanged=True,
        physical_mask_paste_and_via_process_qualified=False,
        resistance_and_native_acceptance_pending=True,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (workspace / "generated/U13-output-control-escape.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Actual U13 barrel and two local control detours emitted; native checks required")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    main(p.parse_args().workspace)
