"""Explicit C83 supply-barrel replacement and real U40.6 receiving escape.

This replaces one dedicated AUX barrel rather than preserving a physically
closed planning cage. Force/reference/ground barrels and all other components
remain fixed. Actual supply connectivity and new PDN/MCAD checks are required.
"""

import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..revision26 import router as aid
from ..routing.check import point_segment
from .focused import legal_line
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/coherent-follow2-c84-corrected-work"
WORK = ROOT / "generated/c83-aux-branch-repair-work"
REMOVE = {"50408bcb-ef23-5e99-aef8-62483b522aab", "4016f7a6-b5d2-53c5-b7e9-9f1119e9b8b6"}
ROUTES = [
    ("V2V5_AUX", [(135.75, 45.5), (137, 45.5), (137, 46.25)]),
    ("AGND", [(138.6, 46.25), (138.1, 46.25)]),
    ("DIG_PG2", [(135.05, 46.5), (135.75, 46.5), (135.975, 46.475)]),
]
VIAS = [("V2V5_AUX", (137, 46.25)), ("DIG_PG2", (135.975, 46.475))]


def check_via(rt, net, point):
    margins = []
    for g in rt.geometry:
        if g["net"] == net:
            continue
        if g["kind"] == "line":
            gap = point_segment(point, g["start"], g["end"]) - g["width"] / 2
        elif g["kind"] == "via":
            gap = math.dist(point, g["xy"]) - g["radius"]
        else:
            gap = math.hypot(*(max(abs(point[i] - g["xy"][i]) - g["size"][i] / 2, 0) for i in (0, 1)))
        assert gap >= 0.500001, (net, point, g, gap)
        margins.append(gap - 0.5)
    return min(margins)


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    assert hashlib.sha256(original).hexdigest() == "fd4b1055fa75be07aead5be006062739e5b3a1d5cdc7cd6ac7b2dad9fb752efa"
    tree = read_sexpr(original.decode())
    codes = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    removed = []
    for node in list(tree):
        if not isinstance(node, list) or not node or node[0] not in ("segment", "via"):
            continue
        if str(first(node, "uuid")[1]) in REMOVE:
            assert codes[str(first(node, "net")[1])] == "V2V5_AUX"
            removed.append(sexpr(node))
            tree.remove(node)
    assert len(removed) == 2
    cap = next(f for f in children(tree, "footprint") if any(p[1] == "Reference" and p[2] == "C83" for p in children(f, "property")))
    before = sexpr(cap)
    assert [float(v) for v in first(cap, "at")[1:3]] == [237.3, 146.25]
    first(cap, "at")[1] = a("237.8")
    router = Router(tree)
    for net, points in ROUTES:
        assert all(legal_line(router, net, 0, p, q, 0.2) for p, q in zip(points, points[1:])), (net, points)
    via_margins = {net: check_via(router, net, point) for net, point in VIAS}
    old_ids = {id(n) for n in tree}
    aid.STEP = 0.025
    for net, points in ROUTES:
        router.path(net, 0, points, 0.2)
    for net, point in VIAS:
        router.via(net, point)
    additions = []
    digest = hashlib.sha256(original).hexdigest()
    for index, node in enumerate(tree):
        if id(node) not in old_ids and isinstance(node, list) and node and node[0] in ("segment", "via"):
            node.append([a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:C83aux:{digest}:{index}:{sexpr(node)}")))])
            additions.append(sexpr(node))
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for source in SOURCE.iterdir():
        if source.is_file() and (source.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym") or source.name in ("components.json", "fp-lib-table", "sym-lib-table")):
            shutil.copy2(source, WORK / source.name)
        elif source.suffix == ".pretty":
            shutil.copytree(source, WORK / source.name)
    (WORK / path.name).write_text(sexpr(tree) + "\n")
    report = dict(source_pcb_sha256=digest, recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), removed_exact_local_AUX_objects=removed, dedicated_AUX_barrel_is_a_deliberate_replacement_not_an_all_old_vias_fixed_claim=True, C83_before=before, C83_after=sexpr(cap), C83_pose_shift_mm=[0.5, 0], added_exact_objects=additions, input_receiving_via=[135.975, 46.475], new_cap_AUX_via=[137, 46.25], actual_analytical_via_clearance_margins_above_0p2_rule_mm=via_margins, all_other_existing_copper_vias_parts_ports_rules_and_force_reference_ground_primitives_fixed=True, actual_native_AUX_and_GND_component_continuity_required=True, new_current_noise_supply_PDN_and_MCAD_not_inherited=True, filled_capped_process_acceptance=False, physical_qualified=False)
    (WORK / "generated/local-branch-repair.json").write_text(json.dumps(report, indent=2) + "\n")
    assert path.read_bytes() == original


if __name__ == "__main__":
    main()
