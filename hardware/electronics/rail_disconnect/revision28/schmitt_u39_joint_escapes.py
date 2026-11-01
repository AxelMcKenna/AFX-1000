"""Prune obsolete U39 ordinary islands and reconnect actual receiving lands."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .receiver_local_escape import escape
from .receiver_surface_path import connect
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-u39-joint-placement-work"
WORK = ROOT / "generated/schmitt-u39-joint-escapes-work"
NETS = {"DIG_SOURCE_OK", "ANA_OUTPUT_OK", "DIG_OUTPUT_OK", "DIG_SOURCE_OK_SCHMITT", "ANA_OUTPUT_OK_SCHMITT", "DIG_OUTPUT_OK_SCHMITT"}


def main():
    assert not WORK.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    tree = read_sexpr(original.decode())
    graph_path = SOURCE / "generated/residual-components.json"
    graph = json.loads(graph_path.read_text())
    assert next(v for p, v in graph["source_sha256"].items() if Path(p).resolve() == source.resolve()) == hashlib.sha256(original).hexdigest()
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    objects = {str(first(n, "uuid")[1]): n for k in ("segment", "via") for n in children(tree, k)}
    removed = []
    for net in NETS:
        if net not in graph["inventory"]:
            continue
        for component in graph["inventory"][net]["components"]:
            if any(x["kind"] == "PAD" for x in component):
                continue
            for item in component:
                node = objects[item["uuid"]]
                assert names[str(first(node, "net")[1])] == net
                removed.append(dict(net=net, uuid=item["uuid"], literal=sexpr(node), native_component_actual_pad_count=0))
                tree.remove(node)
    rows = []
    # Outputs first: their existing receiver backbones are closest to this bay.
    for ref, pin in [("U39", n) for n in ("7", "5", "2", "1", "3", "6", "4", "8")] + [("C82", "1"), ("C82", "2")]:
        router = Router(tree)
        pad = next(p for p in router.by_ref[ref] if p["pin"] == pin)
        targets = []
        for g in router.geometry:
            if g["net"] != pad["net"] or not set(g["layers"]) & set(pad["layers"]) or g.get("ref") in ("U39", "C82"):
                continue
            for xy in ([g["start"], g["end"]] if g["kind"] == "line" else [g["xy"]]):
                targets.append(dict(xy=xy, layers=g["layers"], kind=g["kind"], net=g["net"]))
        route, reason = connect(router, pad, targets, radius=7, step=0.025, budget=250000)
        method = "surface_to_actual_same_net_copper"
        if route is None:
            route, reason = escape(router, pad, maxdistance=4, step=0.025)
            method = "explicit_new_filled_capped_barrel_requirement"
        rows.append(dict(ref=ref, pin=pin, net=pad["net"], method=method, route=route, reason=reason))
        print(ref, pin, pad["net"], bool(route), method, reason, flush=True)
    digest = hashlib.sha256(original).hexdigest()
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append([a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:U39joint:{digest}:{index}:{sexpr(node)}")))])
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for path in SOURCE.iterdir():
        if path.is_file() and (path.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym") or path.name in ("components.json", "fp-lib-table", "sym-lib-table")):
            shutil.copy2(path, WORK / path.name)
        elif path.suffix == ".pretty":
            shutil.copytree(path, WORK / path.name)
    (WORK / source.name).write_text(sexpr(tree) + "\n")
    report = dict(source_pcb_sha256=digest, source_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(), recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), attempts=rows, removed_obsolete_ordinary_PADfree_components=removed, no_other_existing_tracks_vias_parts_rules_or_ports_changed=True, actual_fill_and_finite_copper_and_noise_checks_required=True, receiving_cell_continuity_not_inferred_from_escape_alone=True, filled_capped_process_required_not_approved=True, native_manufacturing_via_filling_property_not_proven=True, physical_qualified=False)
    (WORK / "generated/joint-escapes.json").write_text(json.dumps(report, indent=2) + "\n")
    assert source.read_bytes() == original


if __name__ == "__main__":
    main()
