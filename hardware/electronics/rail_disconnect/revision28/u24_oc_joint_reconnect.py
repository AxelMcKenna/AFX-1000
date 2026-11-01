"""Restore every declared U24 cage net and four actual buffered receivers."""

import hashlib
import itertools
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .band_router import BandRouter
from .component_routes import connect_components

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u24-oc-ordinary-receiving-work"
WORK = ROOT / "generated/u24-oc-joint-reconnect-work"
RECEIVERS = {"ANA_SOURCE_OK_SCHMITT", "DIG_SOURCE_OK_SCHMITT", "ANA_OUTPUT_OK_SCHMITT", "DIG_OUTPUT_OK_SCHMITT"}


def main():
    assert not WORK.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    tree = read_sexpr(original.decode())
    graph_path = SOURCE / "generated/residual-components.json"
    graph = json.loads(graph_path.read_text())
    assert next(v for p, v in graph["source_sha256"].items() if Path(p).resolve() == source.resolve()) == digest
    escape_path = SOURCE / "generated/joint-escape.json"
    escapes = json.loads(escape_path.read_text())
    selected = RECEIVERS | set(escapes["affected_ordinary_nets"])
    filled = SOURCE / "generated/filled-u24-oc-ordinary-receiving.kicad_pcb"
    pads_path = SOURCE / "generated/native-pads.json"
    pads = json.loads(pads_path.read_text())
    assert pads["source_pcb_sha256"] == hashlib.sha256(filled.read_bytes()).hexdigest()
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    objects = {str(first(n, "uuid")[1]): n for k in ("segment", "via") for n in children(tree, k)}
    tasks = []
    removed = []
    for net in sorted(selected):
        row = graph["inventory"].get(net)
        if not row:
            continue
        groups = []
        for component in row["components"]:
            # Only declared ordinary signal islands with no actual package
            # terminal are obsolete. Keep V5's deliberately rebuilt barrel
            # components for their separately reviewed receiving repair.
            if net != "V5_REG_OV_OK" and not any(p["kind"] == "PAD" for p in component):
                for item in component:
                    node = objects[item["uuid"]]
                    assert names[str(first(node, "net")[1])] == net
                    removed.append(dict(net=net, uuid=item["uuid"], literal=sexpr(node), actual_native_component_pad_count=0))
                    tree.remove(node)
                continue
            anchors = []
            for item in component:
                assert item["kind"] == "PAD" or names[str(first(objects[item["uuid"]], "net")[1])] == net
                for xy in [item["position_mm"]] + ([item["end_mm"]] if item["kind"] == "PCB_TRACK" else []):
                    anchors.append(dict(xy=xy, layers=item["layers"], uuid=item["uuid"], kind=item["kind"], ref=item.get("ref"), pin=item.get("pin")))
            groups.append(anchors)
        if len(groups) > 1:
            tasks.append((net, groups))
    router = BandRouter(tree, read_sexpr(filled.read_text()), pads, step=0.1)
    attempts = []
    # First use the newly created four receiving barrels. Every affected
    # ordinary control net is included; no arbitrary net-count waiver applies.
    for net, groups in sorted(tasks, key=lambda x: (x[0] not in RECEIVERS, x[0])):
        generation = 0
        failed = set()
        while len(groups) > 1:
            pairs = [p for p in itertools.combinations(range(len(groups)), 2) if (id(groups[p[0]]), id(groups[p[1]]), generation) not in failed]
            if not pairs:
                break
            i, j = min(pairs, key=lambda p: min(math.dist(x["xy"], y["xy"]) for x in groups[p[0]] for y in groups[p[1]]))
            one, two = groups[i], groups[j]
            if len(one) > len(two):
                one, two = two, one
            router.cached = {}
            before = len(router.routes)
            result = connect_components(router, dict(net=net, components=[one, two]), width=0.2, budget=600000)
            attempts.append(dict(net=net, actual_connectivity_generation=generation, **result))
            print(net, result.get("connected"), result.get("visited"), result.get("reason"), flush=True)
            if not result.get("connected"):
                failed.add((id(groups[i]), id(groups[j]), generation))
                continue
            merged = one + two
            for route in router.routes[before:]:
                layer = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu").index(route["layer"])
                merged.extend(dict(xy=xy, layers=[layer], kind="NEW_ACTUAL_ROUTE") for xy in route["points_relative_mm"])
            groups = [g for k, g in enumerate(groups) if k not in (i, j)] + [merged]
            generation += 1
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append([a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:U24OCjoint:{digest}:{index}:{sexpr(node)}")))])
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for path in SOURCE.iterdir():
        if path.is_file() and (path.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym") or path.name in ("components.json", "fp-lib-table", "sym-lib-table")):
            shutil.copy2(path, WORK / path.name)
        elif path.suffix == ".pretty":
            shutil.copytree(path, WORK / path.name)
    (WORK / source.name).write_text(sexpr(tree) + "\n")
    report = dict(source_pcb_sha256=digest, source_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(), source_escape_ledger_sha256=hashlib.sha256(escape_path.read_bytes()).hexdigest(), source_filled_sha256=hashlib.sha256(filled.read_bytes()).hexdigest(), native_pad_geometry_sha256=hashlib.sha256(pads_path.read_bytes()).hexdigest(), recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), selected_ordinary_nets=sorted(selected), attempts=attempts, routes=router.routes, removed_PADfree_ordinary_islands=removed, ordinary_floating_barrels_are_deliberate_removals_not_an_inherited_all_vias_fixed_claim=True, all_remaining_tracks_vias_and_all_force_ground_reference_parts_values_ports_zones_and_rules_fixed=True, actual_saved_fill_and_current_source_PDN_noise_validation_required=True, no_partial_net_or_warning_exemption=True, physical_qualified=False)
    (WORK / "generated/joint-reconnection.json").write_text(json.dumps(report, indent=2) + "\n")
    assert source.read_bytes() == original


if __name__ == "__main__":
    main()
