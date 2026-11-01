"""Private C82+0.1mm X move and exact U39.7 surface escape.

All electrical clearances and the0.5mm native edge rule are retained. The
surface path uses the actual edge instead of the router's conservative0.75mm
planning border. Its nominal25um margins are not fabrication acceptance.
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
SOURCE = ROOT / "generated/middle-input-ground-bridge-work"
WORK = ROOT / "generated/c82-output-edge-escape-work"
NET = "DIG_SOURCE_OK_SCHMITT"
POINTS = [(112.8, 52), (113.2, 52), (113.55, 52.125), (113.55, 53.875), (116.85, 53.875), (116.85, 53.3)]


def main():
    assert not WORK.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    assert digest == "8e53139def64e8e36a127a4610b3cf7c1d504913836bb0b64c045094d9b996b9"
    tree = read_sexpr(original.decode())
    fp = next(f for f in children(tree, "footprint") if any(p[1] == "Reference" and p[2] == "C82" for p in children(f, "property")))
    before = sexpr(fp)
    assert [float(v) for v in first(fp, "at")[1:3]] == [215.05, 152.25]
    first(fp, "at")[1:3] = [a("215.15"), a("152.25")]
    router = Router(tree)
    pad = next(p for p in router.by_ref["U39"] if p["pin"] == "7")
    assert pad["net"] == NET and math.dist(pad["xy"], POINTS[0]) < 1e-10
    assert all(legal_line(router, NET, 0, p, q, 0.2) for p, q in zip(POINTS, POINTS[1:]))
    via = POINTS[-1]
    via_checks = []
    for g in router.geometry:
        if g["kind"] == "line":
            if g["net"] == NET:
                continue
            gap = point_segment(via, g["start"], g["end"]) - g["width"] / 2
            need = 0.500001
        elif g["kind"] == "via":
            gap = math.dist(via, g["xy"]) - g["radius"]
            need = 0.250001 if g["net"] == NET else 0.500001
        else:
            if g["net"] == NET:
                continue
            gap = math.hypot(*(max(abs(via[i] - g["xy"][i]) - g["size"][i] / 2, 0) for i in (0, 1)))
            need = 0.500001
        assert gap >= need, (g, gap, need)
        via_checks.append(gap - need)
    assert via[0] - 0.3 >= 0.5 and 156 - via[0] - 0.3 >= 0.5
    assert via[1] - 0.3 >= 0.5 and 54.5 - via[1] - 0.3 >= 0.5
    assert 54.5 - max(p[1] for p in POINTS) - 0.1 >= 0.5
    ids = {id(n) for n in tree}
    aid.STEP = 0.025
    router.path(NET, 0, POINTS, 0.2)
    router.via(NET, via)
    additions = []
    for index, node in enumerate(tree):
        if id(node) not in ids and isinstance(node, list) and node and node[0] in ("segment", "via"):
            node.append([a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:C82edge:{digest}:{index}:{sexpr(node)}")))])
            additions.append(sexpr(node))
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for path in SOURCE.iterdir():
        if path.is_file() and (path.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym") or path.name in ("components.json", "fp-lib-table", "sym-lib-table")):
            shutil.copy2(path, WORK / path.name)
        elif path.suffix == ".pretty":
            shutil.copytree(path, WORK / path.name)
    (WORK / source.name).write_text(sexpr(tree) + "\n")
    report = dict(source_pcb_sha256=digest, recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), footprint_before=before, footprint_after=sexpr(fp), cap_pose_change_mm=[0.1, 0], both_existing_supply_annuli_still_within_actual_cap_lands_requires_native_confirmation=True, new_copper=additions, new_trace_width_mm=0.2, new_via_diameter_drill_mm=[0.6, 0.3], minimum_analytical_via_margin_above_unreduced_rules_mm=min(via_checks), nominal_trace_to_bottom_edge_mm=54.5-max(p[1] for p in POINTS)-0.1, physical_edge_rule_mm=0.5, planner_border_is_not_a_manufacturing_rule=True, no_existing_copper_drill_zone_outline_rule_or_other_part_changed=True, deliberate_C82_pose_requires_new_MCAD_and_supply_PDN_review=True, narrow_nominal_margins_and_filled_capped_process_not_accepted=True, actual_source_and_target_component_closure_still_required=True, physical_qualified=False)
    (WORK / "generated/edge-escape.json").write_text(json.dumps(report, indent=2) + "\n")
    assert source.read_bytes() == original


if __name__ == "__main__":
    main()
