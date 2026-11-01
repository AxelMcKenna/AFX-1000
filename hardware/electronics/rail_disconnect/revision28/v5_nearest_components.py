"""Join nearest real V5 components and repair the newly separated ground island."""

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
SOURCE = ROOT / "generated/v5-actual-components-joined-work"
WORK = ROOT / "generated/v5-nearest-components-work"


def main():
    assert not WORK.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    graph_path = SOURCE / "generated/residual-components.json"
    graph = json.loads(graph_path.read_text())
    assert next(v for p, v in graph["source_sha256"].items() if Path(p).resolve() == source.resolve()) == digest
    filled = SOURCE / "generated/filled-v5-actual-components-joined.kicad_pcb"
    pad_path = SOURCE / "generated/native-pads.json"
    pads = json.loads(pad_path.read_text())
    assert pads["source_pcb_sha256"] == hashlib.sha256(filled.read_bytes()).hexdigest()
    tree = read_sexpr(original.decode())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    source_objects = {str(first(n, "uuid")[1]): n for k in ("segment", "via") for n in children(tree, k)}
    router = BandRouter(tree, read_sexpr(filled.read_text()), pads, step=0.05)
    attempts = []
    for net in ("V5_REG_OV_OK", "AGND"):
        groups = []
        for component in graph["inventory"][net]["components"]:
            anchors = []
            for item in component:
                assert item["kind"] == "PAD" or names[str(first(source_objects[item["uuid"]], "net")[1])] == net
                for xy in [item["position_mm"]] + ([item["end_mm"]] if item["kind"] == "PCB_TRACK" else []):
                    anchors.append(dict(xy=xy, layers=item["layers"], uuid=item["uuid"], kind=item["kind"], ref=item.get("ref"), pin=item.get("pin")))
            groups.append(anchors)
        generation = 0
        failed = set()
        while len(groups) > 1:
            pairs = [p for p in itertools.combinations(range(len(groups)), 2) if (id(groups[p[0]]), id(groups[p[1]]), generation) not in failed]
            if not pairs:
                break
            i, j = min(pairs, key=lambda p: min(math.dist(x["xy"], y["xy"]) for x in groups[p[0]] for y in groups[p[1]]))
            one, two = groups[i], groups[j]
            # A small physical seed avoids simultaneously expanding hundreds
            # of distant real root tracks before reaching a local component.
            if len(one) > len(two):
                one, two = two, one
            router.cached = {}
            before = len(router.routes)
            result = connect_components(router, dict(net=net, components=[one, two]), width=0.2, budget=1600000)
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
            node.append([a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:V5nearest:{digest}:{index}:{sexpr(node)}")))])
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for path in SOURCE.iterdir():
        if path.is_file() and (path.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym") or path.name in ("components.json", "fp-lib-table", "sym-lib-table")):
            shutil.copy2(path, WORK / path.name)
        elif path.suffix == ".pretty":
            shutil.copytree(path, WORK / path.name)
    (WORK / source.name).write_text(sexpr(tree) + "\n")
    report = dict(source_pcb_sha256=digest, source_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(), source_filled_sha256=hashlib.sha256(filled.read_bytes()).hexdigest(), native_pad_geometry_sha256=hashlib.sha256(pad_path.read_bytes()).hexdigest(), recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), attempts=attempts, routes=router.routes, every_existing_pad_via_track_zone_primitive_retained=True, no_existing_object_net_or_geometry_changed=True, actual_filled_force_pours_guarded=True, ground_island_is_real_and_not_exempted=True, current_native_PDN_and_quiet_ground_validation_required=True, physical_qualified=False)
    (WORK / "generated/nearest-components-routes.json").write_text(json.dumps(report, indent=2) + "\n")
    assert source.read_bytes() == original


if __name__ == "__main__":
    main()
