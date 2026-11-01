"""One real U14 input barrel, with a bounded unlocked ANA_PG1 detour.

The rejected two-barrel probe's output hole is not retained: it collided with
locked digital force copper. Only the input hole and three unlocked PG1 trace
objects are changed here. Actual factory, mask/fill and electrical release are
still unqualified and require fresh native/conductor/return evidence.
"""

import argparse
import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .ground_corridor import path_between
from .repair import Router

ROOT = Path(__file__).resolve().parent
REPLACED = {
    "394a85ef-4ec2-52e7-b197-b735fe397f3f",
    "ae9bc2a7-a35f-5c8e-b3be-7ecba6295c00",
    "5d0fe3eb-6572-57c2-a682-a042d33f590b",
}


def main(workspace):
    source = ROOT / "generated/p9-targeted-timing-leaf-work"
    path = source / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    assert digest == "bdac7c169ad48284d7f9eb267a66c7081a43ac2724d890058f0594ecc244d3ac"
    probe_path = ROOT / "generated/p9-u14-barrel-probe-work/generated/barrel-probe.json"
    probe = json.loads(probe_path.read_text())
    assert probe["source_pcb_sha256"] == digest
    via = next(p["actual_object"] for p in probe["added_real_barrels"] if p["pin"] == "5")
    contract_path = ROOT / "generated/leaf-prune-source-lock-contract.json"
    locked = {r["uuid"] for r in json.loads(contract_path.read_text())["locked_copper"]}
    assert not REPLACED & locked, "No global force/gate/timing/repair lock may be relaxed"
    tree = read_sexpr(before.decode())
    net = next(str(n[1]) for n in children(tree, "net") if str(n[2]).lstrip("/") == "ANA_PG1")
    old = [n for n in children(tree, "segment") if str(first(n, "uuid")[1]) in REPLACED]
    assert len(old) == 3
    assert all(
        str(first(n, "net")[1]) == net
        and first(n, "layer")[1] == "In1.Cu"
        and float(first(n, "width")[1]) == 0.2
        for n in old
    )
    tree[:] = [n for n in tree if n not in old]
    tree.append(read_sexpr(via))
    router = Router(tree)
    points, visited = path_between(router, (38.5, 10.8), (43.9, 10.9), 1, margin=3, step=0.025, net="ANA_PG1")
    added = [via]
    for index, (aa, bb) in enumerate(zip(points, points[1:])):
        if math.dist(aa, bb) < 1e-8:
            continue
        uid = uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:U14input-PG1:{digest}:{index}")
        node = read_sexpr(
            f'(segment (start {100 + aa[0]:.6f} {100 + aa[1]:.6f}) (end {100 + bb[0]:.6f} {100 + bb[1]:.6f}) (width .2) (layer "In1.Cu") (net {net}) (uuid {uid}))'
        )
        tree.append(node)
        added.append(sexpr(node))
    workspace = Path(workspace).resolve()
    assert workspace.is_relative_to(ROOT / "generated") and not workspace.exists()
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
        source_pcb_sha256=digest,
        source_probe_sha256=hashlib.sha256(probe_path.read_bytes()).hexdigest(),
        original_lock_contract_sha256=hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        source_recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        removed_unlocked_PG1_objects=[sexpr(n) for n in old],
        added_actual_objects=added,
        actual_control_route_points_mm=points,
        visited_cells=visited,
        original_PG1_endpoints_retained=True,
        new_force_barrels=1,
        rejected_output_barrel_and_digital_force_conflict_not_retained=True,
        factory_lands_and_all_critical_force_gate_timing_objects_retained=True,
        candidate_pcb_sha256=hashlib.sha256((workspace / path.name).read_bytes()).hexdigest(),
        physical_and_process_qualified=False,
    )
    (workspace / "generated/U14-input-escape.json").write_text(json.dumps(report, indent=2) + "\n")
    print("One real input barrel with actual unlocked PG1 detour; all checks pending")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    main(p.parse_args().workspace)
