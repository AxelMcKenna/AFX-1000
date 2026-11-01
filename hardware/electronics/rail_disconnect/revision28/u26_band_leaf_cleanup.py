"""Remove only newly exposed, unlocked relocation tails in a separate draft.

This is a proposed physical repair, not a warning exemption. A fresh native
check and per-net connectivity comparison must accept or reject the result.
The original 66 warning objects and protected copper remain untouched.
"""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u26-band-reconnect1-work"
BASE = ROOT / "generated/u14-residual-batch1-work"
WORK = ROOT / "generated/u26-band-leaf-cleanup1-work"


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    tree = read_sexpr(original.decode())
    report_path = SOURCE / "generated/drc-u26-reconnect1.json"
    raw = json.loads(report_path.read_text())
    baseline = json.loads((BASE / "generated/drc-surface-batch1.json").read_text())
    old = {item["uuid"] for row in baseline["violations"] for item in row["items"]}
    locked = {
        row["uuid"]
        for row in json.loads((ROOT / "generated/leaf-prune-source-lock-contract.json").read_text())[
            "locked_copper"
        ]
    }
    # Keep the two unresolved fanout barrel/stem candidates for later routing.
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
    assert len(removed) == len(selected) == 19
    tree[:] = [n for n in tree if n not in removed]
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
    result = dict(
        source_pcb_sha256=hashlib.sha256(original).hexdigest(),
        source_drc_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        removed_objects=[sexpr(n) for n in removed],
        removed_uuids=sorted(selected),
        original_warning_objects_and_locked_copper_preserved=True,
        all_other_copper_footprints_zones_edges_rules_unchanged=True,
        native_connectivity_and_warning_results_pending=True,
        physical_and_electrical_qualified=False,
    )
    (WORK / "generated/proposed-leaf-repair.json").write_text(json.dumps(result, indent=2) + "\n")
    assert path.read_bytes() == original


if __name__ == "__main__":
    main()
