"""Private real B.Cu negative-source sense arm; no virtual circuit bridge.

The bounded polygon has lower priority than every existing backside supply
zone. Existing copper objects, lands, holes, board outline and rules remain
unchanged. Native connectivity/fill/subtraction decides whether it works.
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
from .repair import Router

ROOT = Path(__file__).resolve().parent


def main(workspace, width=1.2):
    source = ROOT / "generated/p9-analog-outlet-work"
    workspace = Path(workspace).resolve()
    assert workspace.is_relative_to(ROOT / "generated") and not workspace.exists()
    path = source / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    router = Router(tree)
    start = next(p["xy"] for p in router.by_ref["R53"] if p["pin"] == "1")
    assert next(p["net"] for p in router.by_ref["R53"] if p["pin"] == "1") == "N12_SRC"
    finish = (70, 14.3)
    assert any(
        g["kind"] == "via" and g["net"] == "N12_SRC" and math.dist(g["xy"], finish) < 1e-7
        for g in router.geometry
    )
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    templates = [
        z
        for z in children(tree, "zone")
        if children(z, "net")
        and names[str(first(z, "net")[1])] == "N12_SRC"
        and first(z, "layer")[1] == "B.Cu"
    ]
    assert templates
    assert not any(
        names[str(first(z, "net")[1])] == "AGND" and children(z, "layer") and first(z, "layer")[1] == "B.Cu"
        for z in children(tree, "zone")
        if children(z, "net")
    )
    priorities = [
        int(first(z, "priority")[1])
        for z in children(tree, "zone")
        if children(z, "net") and children(z, "layer") and first(z, "layer")[1] == "B.Cu"
    ]
    assert min(priorities) > 100
    dx, dy = finish[0] - start[0], finish[1] - start[1]
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    nx, ny = -uy * width / 2, ux * width / 2
    aa = (start[0] - ux * width, start[1] - uy * width)
    bb = (finish[0] + ux * width, finish[1] + uy * width)
    points = [
        (aa[0] + nx, aa[1] + ny),
        (bb[0] + nx, bb[1] + ny),
        (bb[0] - nx, bb[1] - ny),
        (aa[0] - nx, aa[1] - ny),
    ]
    zone = copy.deepcopy(templates[0])
    zone[:] = [
        n
        for n in zone
        if not (isinstance(n, list) and n and n[0] in ("polygon", "filled_polygon", "fill_segments", "uuid"))
    ]
    first(zone, "priority")[1] = a("100")
    # The inherited filled-zone minimum may be smaller than the declared
    # routing rule. This new arm explicitly uses the current 0.2 mm minimum.
    first(zone, "min_thickness")[1] = a("0.2")
    polygon = [
        a("polygon"),
        [a("pts"), *[[a("xy"), a(f"{x + 100:.6f}"), a(f"{y + 100:.6f}")] for x, y in points]],
    ]
    zone.append(polygon)
    zone.append(
        [
            a("uuid"),
            str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL, "rmx:E28:real-N12-sense-arm:" + hashlib.sha256(before).hexdigest()
                )
            ),
        ]
    )
    tree.append(zone)
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
        source_pcb_sha256=hashlib.sha256(before).hexdigest(),
        candidate_pcb_sha256=hashlib.sha256((workspace / path.name).read_bytes()).hexdigest(),
        added_actual_zone=sexpr(zone),
        arm_width_mm=width,
        source_pad_board_mm=start,
        actual_existing_target_barrel_mm=finish,
        priority=100,
        every_existing_backside_supply_zone_priority_higher=True,
        original_tracks_vias_components_holes_and_rules_unchanged=True,
        no_existing_B_ground_plane_removed=True,
        new_native_connectivity_and_all_filled_copper_comparison_required=True,
        sense_capacitive_coupling_and_transient_behavior_unqualified=True,
        physical_qualified=False,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (workspace / "generated/N12-sense-arm.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Added real bounded1.2mm backside copper arm; native proof still required")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    args = p.parse_args()
    main(args.workspace)
