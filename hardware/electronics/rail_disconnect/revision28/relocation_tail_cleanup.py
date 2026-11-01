"""Explicit follow-on relocation-tail repair, retaining every prior source.

Only native dangling objects newly exposed by the declared U23/U26 relocation
are proposed for deletion. The baseline warning objects, locked copper and two
pending fanout barrels are retained. Accept only after fresh all-net native
connectivity and hard-error comparisons; a removed tail can expose its upstream
tail on the next iteration, so every round remains separately reviewable.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent


def propose(source, work, drc):
    assert source.parent == work.parent == ROOT / "generated"
    assert not work.exists()
    path = source / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    tree = read_sexpr(original.decode())
    raw = json.loads(drc.read_text())
    baseline = json.loads(
        (ROOT / "generated/u14-residual-batch1-work/generated/drc-surface-batch1.json").read_text()
    )
    old = {item["uuid"] for row in baseline["violations"] for item in row["items"]}
    locked = {
        row["uuid"]
        for row in json.loads((ROOT / "generated/leaf-prune-source-lock-contract.json").read_text())[
            "locked_copper"
        ]
    }
    pending = {"8dd37fe1-7896-507f-8f46-8293f5612559", "d17c5ccb-1b0f-59c1-a29f-5e2b9f814637"}
    warned = {
        item["uuid"]
        for row in raw["violations"]
        if row["type"] in ("track_dangling", "via_dangling")
        for item in row["items"]
    }
    selected = warned - old - locked - pending
    removed = [
        n for kind in ("segment", "via") for n in children(tree, kind) if str(first(n, "uuid")[1]) in selected
    ]
    assert len(removed) == len(selected) > 0
    tree[:] = [n for n in tree if n not in removed]
    work.mkdir()
    (work / "generated").mkdir()
    for p in source.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, work / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, work / p.name)
    (work / path.name).write_text(sexpr(tree) + "\n")
    result = dict(
        source_project=str(source),
        source_pcb_sha256=hashlib.sha256(original).hexdigest(),
        source_drc_sha256=hashlib.sha256(drc.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        removed_objects=[sexpr(n) for n in removed],
        removed_uuids=sorted(selected),
        original_warning_objects_and_locked_copper_preserved=True,
        all_other_copper_footprints_zones_edges_rules_unchanged=True,
        native_connectivity_and_warning_results_pending=True,
        physical_and_electrical_qualified=False,
    )
    (work / "generated/proposed-leaf-repair.json").write_text(json.dumps(result, indent=2) + "\n")
    assert path.read_bytes() == original
    return len(removed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "work", "drc"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print("Proposed removed tails:", propose(args.source, args.work, args.drc))
