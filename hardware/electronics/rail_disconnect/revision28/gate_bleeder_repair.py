"""Move the actual P19 gate bleeder to Q1; no broad routing rip-up."""

import hashlib
import json
import math
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..revision26.layout import Layout
from .integrate_positive import LIB, footprint, native_parts
from .repair import ROOT, Router
from .terminals import ALL_TERMINALS


def main():
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    binding_path = ROOT / "generated/native-open-components-binding.json"
    binding = json.loads(binding_path.read_text())
    assert binding["source_pcb_sha256"] == hashlib.sha256(before).hexdigest()
    graph_path = ROOT / "generated/open-components.json"
    assert binding["graph_sha256"] == hashlib.sha256(graph_path.read_bytes()).hexdigest()
    tree = read_sexpr(before.decode())
    old = Router(tree)
    old_gate = next(p for p in old.by_ref["R2"] if p["pin"] == "1")
    assert old_gate["net"] == "P19_GATE"
    branch = None
    for row in json.loads(graph_path.read_text()):
        if row["net"] != old_gate["net"]:
            continue
        for group in row["components"]:
            pads = [p for p in group if p["kind"] == "PAD"]
            if len(pads) == 1 and math.dist(pads[0]["xy"], old_gate["xy"]) < 1e-7:
                branch = group
    assert branch is not None, "Require actual native isolated bleeder branch evidence"
    removable = {p["uuid"] for p in branch if p["kind"] != "PAD"}
    removed = []
    kept = []
    old_pose = None
    for node in tree:
        drop = False
        if isinstance(node, list) and node:
            if node[0] == "footprint":
                ref = next(p[2] for p in children(node, "property") if p[1] == "Reference")
                if ref == "R2":
                    old_pose = list(first(node, "at")[1:]) + [str(first(node, "layer")[1])]
                    drop = True
            elif node[0] in ("segment", "via") and children(node, "uuid"):
                drop = str(first(node, "uuid")[1]) in removable
                if drop:
                    assert old.nets[old_gate["net"]] == int(first(node, "net")[1])
        if drop:
            removed.append(sexpr(node))
        else:
            kept.append(node)
    tree = kept
    parts = {p["ref"]: p for p in native_parts()}
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    pose = (23.7125, 4.125, 0, "B")
    placed = footprint(parts["R2"], pose, nets)
    bare = [n for n in tree if not (isinstance(n, list) and n and n[0] in ("segment", "via"))]
    judge = Layout(bare, parts, {}, LIB)
    judge.router = Router(bare)
    for fp in children(bare, "footprint"):
        name = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        side, box = judge.body(fp)
        judge.bodies.append((name, side, box))
    for name, (x, y, net) in ALL_TERMINALS.items():
        judge.bodies.append((name + "_access", "B", (x + 95, y + 95, x + 105, y + 105)))
    assert judge.legal_body("R2", placed), "Exact declared bleeder placement blocked by actual bodies/pads"
    tree.append(placed)
    rt = Router(tree)
    gate = next(p for p in rt.by_ref["R2"] if p["pin"] == "1")
    common = next(p for p in rt.by_ref["R2"] if p["pin"] == "2")
    assert gate["net"] == "P19_GATE" and common["net"] == "P19_COMMON"
    assert math.dist(gate["xy"], (22.8, 4.125)) < 1e-7
    existing_gate = rt.existing_via(gate["net"], gate["xy"])
    assert existing_gate is not None
    source = min(
        (p for p in rt.by_ref["Q1"] if p["pin"] == "1"), key=lambda p: math.dist(p["xy"], common["xy"])
    )
    assert source["net"] == common["net"]
    # The gate pad directly contacts an existing real gate barrel. A new
    # source barrel and short F.Cu path reach the actual Q1 source land without
    # crossing the retained N19 source track on the back face.
    judge.router = rt
    barrel = (25.0, 4.8)
    points = [barrel, (barrel[0], source["xy"][1]), source["xy"]]
    assert all(judge.free_line(common["net"], 0, s, t, 0.5) for s, t in zip(points, points[1:]))
    rt.via(common["net"], barrel)
    rt.path(common["net"], 5, [common["xy"], barrel], 0.5)
    rt.path(common["net"], 0, points, 0.5)
    ids = []
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:gate-bleeder:{index}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/p19-gate-bleeder-placement.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                native_graph_binding_sha256=hashlib.sha256(binding_path.read_bytes()).hexdigest(),
                old_footprint_pose_file_units=old_pose,
                new_pose_board_mm=pose,
                reused_gate_barrel_mm=existing_gate,
                new_source_barrel_mm=barrel,
                actual_q1_source_land_mm=source["xy"],
                source_link_points_mm=points,
                removed_old_isolated_native_branch_objects=removed,
                protected_ids=ids,
                mechanical_integration_refresh_required=True,
                gate_bias_and_miller_soa_qualified=False,
                native_all_severity_verification_required=True,
                filled_capped_assembly_accepted=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("R2 moved to", pose, "; actual gate/common links", gate["xy"], common["xy"])


if __name__ == "__main__":
    main()
