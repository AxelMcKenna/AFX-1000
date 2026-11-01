"""Explicit local N12/N19 source B-fill retreat trial for three timing joins.

This changes a planning obstacle, never an accepted copper/voltage allocation.
All physical copper primitives remain hard and every resulting pour is refilled
and extracted afresh. The complete current-source diagnostics may reject it.
"""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

import numpy as np

from ...common.sexpr import a, children, read_sexpr, sexpr
from .band_router import BandRouter
from .component_routes import connect_components

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/residual-landing-pass-work"
WORK = ROOT / "generated/timing-negative-window-work"
NETS = ("E28_ANA_0_DVDT", "E28_ANA_0_DVDT_CAP", "P19_MCAP1_LIMIT")


def main():
    assert not WORK.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    blob = source.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    assert digest == "07d8a910f299216e5bd78a75e887139e16d7593cdb5338cb9541fe9d2f1b1506"
    tree = read_sexpr(blob.decode())
    graph_path = SOURCE / "generated/residual-components.json"
    graph = json.loads(graph_path.read_text())
    assert graph["source_sha256"][str(source.resolve())] == digest
    fill = SOURCE / "generated/filled-residual-landing-pass.kicad_pcb"
    pads_path = SOURCE / "generated/native-pads.json"
    pads = json.loads(pads_path.read_text())
    assert pads["source_pcb_sha256"] == hashlib.sha256(fill.read_bytes()).hexdigest()
    router = BandRouter(tree, read_sexpr(fill.read_text()), pads, step=0.05)
    window = (router.xx >= 20) & (router.xx <= 50) & (router.yy >= 2) & (router.yy <= 34)
    changed_guards = []
    for key, distance in router.force_guard.distances.items():
        if key in (("N19_SRC", 5), ("N12_SRC", 5)):
            distance[window] = np.inf
            changed_guards.append(key)
    assert changed_guards
    attempts = []
    for net in NETS:
        row = graph["inventory"][net]
        assert len(row["components"]) == 2
        groups = []
        for component in row["components"]:
            group = []
            for item in component:
                for xy in [item["position_mm"]] + ([item["end_mm"]] if item["kind"] == "PCB_TRACK" else []):
                    group.append(
                        dict(
                            xy=xy,
                            layers=item["layers"],
                            uuid=item["uuid"],
                            kind=item["kind"],
                            ref=item.get("ref"),
                            pin=item.get("pin"),
                        )
                    )
            groups.append(group)
        router.cached = {}
        result = connect_components(router, dict(net=net, components=groups), width=0.2, budget=1500000)
        attempts.append(dict(net=net, **result))
        print(net, result.get("connected"), result.get("visited"), result.get("reason"), flush=True)
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append(
                [
                    a("uuid"),
                    a(
                        str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL, f"rmx:E28:timingWindow:{digest}:{index}:{sexpr(node)}"
                            )
                        )
                    ),
                ]
            )
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for path in SOURCE.iterdir():
        if path.is_file() and (
            path.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or path.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(path, WORK / path.name)
        elif path.suffix == ".pretty":
            shutil.copytree(path, WORK / path.name)
    (WORK / source.name).write_text(sexpr(tree) + "\n")
    report = dict(
        source_pcb_sha256=digest,
        native_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(),
        filled_sha256=hashlib.sha256(fill.read_bytes()).hexdigest(),
        native_pads_sha256=hashlib.sha256(pads_path.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        exact_planning_exception=dict(nets_layers=changed_guards, local_mm_rectangle=[20, 2, 50, 34]),
        target_timing_nets=list(NETS),
        attempts=attempts,
        routes=router.routes,
        all_original_actual_copper_parts_rules_fixed=True,
        all_other_filled_force_planning_guards_retained=True,
        native_fill_positive_negative_return_PDN_validation_required=True,
        physical_qualified=False,
    )
    (WORK / "generated/timing-negative-window.json").write_text(json.dumps(report, indent=2) + "\n")
    assert source.read_bytes() == blob


if __name__ == "__main__":
    main()
