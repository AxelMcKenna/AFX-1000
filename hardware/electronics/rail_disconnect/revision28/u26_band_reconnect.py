"""Bounded native-component joins for the nine relocated-U26 logic nets."""

import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .band_router import BandRouter
from .component_routes import connect_components

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u26-band-fanout-work"
WORK = ROOT / "generated/u26-band-reconnect1-work"


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    graph = SOURCE / "generated/residual-components.json"
    inventory = json.loads(graph.read_text())
    matching_inputs = [
        value for name, value in inventory["source_sha256"].items() if Path(name).resolve() == path.resolve()
    ]
    assert matching_inputs == [digest]
    filled_path = SOURCE / "generated/filled-local-u26-fanout1.kicad_pcb"
    pads_path = SOURCE / "generated/native-pads.json"
    pads = json.loads(pads_path.read_text())
    assert pads["source_pcb_sha256"] == hashlib.sha256(filled_path.read_bytes()).hexdigest()
    tree = read_sexpr(original.decode())
    router = BandRouter(tree, read_sexpr(filled_path.read_text()), pads, step=0.1)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    editable = {
        str(first(n, "uuid")[1]): names[str(first(n, "net")[1])]
        for kind in ("segment", "via")
        for n in children(tree, kind)
    }
    tasks = []
    for net, row in inventory["inventory"].items():
        if not any(any(p.get("ref") == "U26" for p in g) for g in row["components"]):
            continue
        groups = []
        for group in row["components"]:
            points = []
            for obj in group:
                if obj["kind"] != "PAD" and editable.get(obj["uuid"]) != net:
                    continue
                for xy in [obj["position_mm"]] + ([obj["end_mm"]] if obj["kind"] == "PCB_TRACK" else []):
                    points.append(
                        dict(
                            xy=xy,
                            layers=obj["layers"],
                            uuid=obj["uuid"],
                            kind=obj["kind"],
                            ref=obj.get("ref"),
                        )
                    )
            groups.append(points)
        index = next(i for i, g in enumerate(groups) if any(p.get("ref") == "U26" for p in g))
        others = [g for i, g in enumerate(groups) if i != index]
        others.sort(key=lambda g: min(math.dist(p["xy"], q["xy"]) for p in groups[index] for q in g))
        tasks.append((net, groups[index], others[0]))
    # Recover the six newly disconnected logic paths first, then the three
    # original fault joins. Every task is bounded and physically explicit.
    order = [
        "E28_OUT_UV_FAULT",
        "E28_TIMEOUT_FAULT",
        "E28_NOT_OUT_READY",
        "E28_OUT_ARMED",
        "E28_TIMEOUT",
        "DIG_PG3",
        "ANA_PG2",
        "E28_OUTPUT_PERMISSION",
        "E28_OUT_READY",
    ]
    tasks.sort(key=lambda task: order.index(task[0]))
    results = []
    for net, one, two in tasks:
        router.cached = {}
        result = connect_components(router, dict(net=net, components=[one, two]), width=0.2, budget=250000)
        results.append(dict(net=net, **result))
        print(net, result.get("connected"), result.get("visited"), result.get("reason"), flush=True)
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append(
                [
                    a("uuid"),
                    a(
                        str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL, f"rmx:E28:U26reconnect:{digest}:{index}:{sexpr(node)}"
                            )
                        )
                    ),
                ]
            )
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
    (WORK / path.name).write_text(sexpr(tree) + "\n")
    report = dict(
        source_pcb_sha256=digest,
        source_inventory_sha256=hashlib.sha256(graph.read_bytes()).hexdigest(),
        native_pad_geometry_sha256=hashlib.sha256(pads_path.read_bytes()).hexdigest(),
        filled_source_sha256=hashlib.sha256(filled_path.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        attempts=results,
        routes=router.routes,
        no_old_copper_removed_or_moved=True,
        actual_filled_force_protected_during_search=True,
        AGND_refill_requires_fresh_extraction=True,
        all_native_and_qualification_results_pending=True,
    )
    (WORK / "generated/reconnection-routes.json").write_text(json.dumps(report, indent=2) + "\n")
    assert path.read_bytes() == original


if __name__ == "__main__":
    main()
