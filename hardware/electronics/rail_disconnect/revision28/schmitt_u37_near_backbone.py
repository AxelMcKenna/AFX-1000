"""One explicit U37/C80 move and three physically separated backbone partitions."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.placement import placed_footprint
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .schmitt_backbone_cut_plan import partition
from .schmitt_cone_candidate import GROUPS, ROOT

SOURCE = ROOT / "generated/schmitt-receiver-debt-reconnect-work"
ORIGINAL = ROOT / "generated/coherent-ground-repair-work"
WORK = ROOT / "generated/schmitt-u37-near-backbone-work"


def ident(n):
    return str(first(n, "uuid")[1])


def edges(points):
    return [
        (tuple(round(float(v), 6) for v in x), tuple(round(float(v), 6) for v in y))
        for x, y in zip(points, points[1:])
        if x != y
    ]


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    old = read_sexpr((ORIGINAL / "rail_disconnect.kicad_pcb").read_text())
    original_nodes = {ident(n): n for k in ("segment", "via") for n in children(old, k)}
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(t, "net")}
    nets = {v: k for k, v in names.items()}
    parts = json.loads((SOURCE / "components.json").read_text())
    by = {p["ref"]: p for p in parts}
    affected = set(GROUPS[1])
    removed = []
    # Remove only newly introduced signal routing for this moved single cell.
    fan = json.loads((ROOT / "generated/schmitt-all-oc-fanout-work/generated/escapes.json").read_text())[
        "routes"
    ]
    power_vias = []
    power_segments = []
    for row in fan:
        if row["ref"] not in ("U37", "C80") or row["net"] not in ("AGND", "V2V5_AUX") or not row["route"]:
            continue
        route = row["route"]
        power_vias.append((row["net"], tuple(round(float(v), 6) for v in route["via"])))
        for path in (route["path"], route.get("pad_stem", [])):
            power_segments.extend((row["net"], x, y) for x, y in edges(path))
    for n in list(t):
        if not isinstance(n, list) or not n or n[0] not in ("segment", "via") or ident(n) in original_nodes:
            continue
        net = names[str(first(n, "net")[1])]
        delete = net in affected | {n + "_SCHMITT" for n in affected}
        if net in ("AGND", "V2V5_AUX"):
            if n[0] == "via":
                delete = (net, tuple(round(float(v) - 100, 6) for v in first(n, "at")[1:])) in power_vias
            else:
                x, y = [tuple(round(float(v) - 100, 6) for v in first(n, k)[1:]) for k in ("start", "end")]
                delete = (net, x, y) in power_segments or (net, y, x) in power_segments
        if delete:
            removed.append(
                dict(reason="new cell-specific signal/power escape replaced", net=net, literal=sexpr(n))
            )
            t.remove(n)
    # Keep physical component identity; only U37/C80 faces/poses change.
    placement = json.loads((ROOT / "generated/schmitt-cone-proposal/near-receiver-search.json").read_text())[
        "rows"
    ][1]
    moves = []
    for ref, xy in [("U37", placement["local_mm"]), ("C80", placement["cap_local_mm"])]:
        before = next(
            f
            for f in children(t, "footprint")
            if any(p[1] == "Reference" and p[2] == ref for p in children(f, "property"))
        )
        c = by[ref]
        comp = dict(c, value=c["part"], mpn=c["part"], nets={p["number"]: p["net"] for p in c["pins"]})
        lib = SOURCE / "RMX_E28.pretty" / (c["footprint"].split(":")[1] + ".kicad_mod")
        fp = placed_footprint(
            comp, (*xy, 0, "B"), lib, {n: int(code) for n, code in nets.items()}, namespace="rmx:E28:allOC:"
        )
        assert ident(before) == ident(fp)
        moves.append(dict(ref=ref, before=sexpr(before), after=sexpr(fp)))
        t[t.index(before)] = fp
    graph_path = ROOT / "generated/schmitt-cone-proposal/native-backbone-direct-graph.json"
    graph = json.loads(graph_path.read_text())
    plans_path = ROOT / "generated/schmitt-cone-proposal/backbone-cut-plan.json"
    plans = json.loads(plans_path.read_text())
    assert plans["source_graph_sha256"] == hashlib.sha256(graph_path.read_bytes()).hexdigest()
    retagged = []
    cuts = []
    for net in sorted(affected):
        row = graph["rows"][net]
        assert row["direct_shape_components_equal_native_transitive_clusters"]
        plan = plans["rows"][net]
        down, roots, receivers = partition(row, set(plan["cut_track_uuids"]))
        assert down == set(plan["buffered_item_uuids"])
        for uid in plan["cut_track_uuids"]:
            n = next((n for k in ("segment", "via") for n in children(t, k) if ident(n) == uid), None)
            if n is not None:
                cuts.append(dict(net=net, literal=sexpr(n)))
                t.remove(n)
        for uid in down:
            if row["nodes"][uid]["kind"] == "PAD":
                continue
            oldnode = original_nodes[uid]
            n = next((n for k in ("segment", "via") for n in children(t, k) if ident(n) == uid), None)
            if n is None:
                n = read_sexpr(sexpr(oldnode))
                t.append(n)
            first(n, "net")[1] = a(nets[net + "_SCHMITT"])
            retagged.append(dict(old_net=net, new_net=net + "_SCHMITT", literal=sexpr(n)))
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for p in SOURCE.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, WORK / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, WORK / p.name)
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(t) + "\n")
    report = dict(
        source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
        original_pcb_sha256=hashlib.sha256((ORIGINAL / "rail_disconnect.kicad_pcb").read_bytes()).hexdigest(),
        graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(),
        plan_sha256=hashlib.sha256(plans_path.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        component_moves=moves,
        removed_cell_specific_new_Cu=removed,
        cut_original_ordinary_tracks=cuts,
        original_backbone_geometry_net_only_retargeted=retagged,
        all_actual_force_studs_bulk_axes_and_original_reference_Cu_unchanged=True,
        native_boundary_clearance_MCAD_and_PDN_pending=True,
        physical_qualified=False,
    )
    (WORK / "generated/change.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        len(retagged),
        "backbone pieces retained/retagged;",
        len(cuts),
        "ordinary cut segments;",
        len(removed),
        "new cell pieces replaced",
    )


if __name__ == "__main__":
    main()
