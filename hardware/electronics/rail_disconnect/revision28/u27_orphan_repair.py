"""Remove four proved obsolete pad-free U27 escape islands in a NEW draft."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u27-band-reconnect1-work"
WORK = ROOT / "generated/u27-band-orphan-repair-work"
NETS = {"E28_NORMAL_PRE", "E28_NOT_FAULT", "E28_RUN_AND_SOURCE", "E28_SOURCE_READY_LOGIC"}


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    tree = read_sexpr(original.decode())
    inventory_path = SOURCE / "generated/residual-components.json"
    inventory = json.loads(inventory_path.read_text())
    assert [v for p, v in inventory["source_sha256"].items() if Path(p).resolve() == path] == [digest]
    locked = {
        row["uuid"]
        for row in json.loads((ROOT / "generated/leaf-prune-source-lock-contract.json").read_text())[
            "locked_copper"
        ]
    }
    net_ids = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    selected = set()
    groups = {}
    for net in sorted(NETS):
        # A signal zone could make a seemingly pad-free copper island operative.
        assert not any(
            children(z, "net") and net_ids[str(first(z, "net")[1])] == net for z in children(tree, "zone")
        )
        unused = [
            g for g in inventory["inventory"][net]["components"] if not any(o["kind"] == "PAD" for o in g)
        ]
        assert len(unused) == 1
        group = unused[0]
        assert all(o["kind"] in ("PCB_TRACK", "PCB_VIA") for o in group)
        ids = {o["uuid"] for o in group}
        assert not ids & locked
        selected.update(ids)
        groups[net] = group
    assert len(selected) == 62
    removed = [
        n for kind in ("segment", "via") for n in children(tree, kind) if str(first(n, "uuid")[1]) in selected
    ]
    assert len(removed) == len(selected)
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
    old_raw = json.loads(
        (ROOT / "generated/u14-residual-batch1-work/generated/drc-surface-batch1.json").read_text()
    )
    old_warning_ids = {i["uuid"] for row in old_raw["violations"] for i in row["items"]}
    report = dict(
        source_pcb_sha256=digest,
        inventory_sha256=hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        actual_pad_free_unlocked_zone_free_native_components=groups,
        removed_copper_objects=[sexpr(n) for n in removed],
        original_warning_objects_physically_removed=sorted(old_warning_ids & selected),
        all_actual_pad_terminal_components_retained=True,
        all_other_objects_exactly_preserved=True,
        native_and_PDN_checks_pending=True,
        physical_and_electrical_qualified=False,
    )
    (WORK / "generated/proposed-orphan-repair.json").write_text(json.dumps(report, indent=2) + "\n")
    assert path.read_bytes() == original


if __name__ == "__main__":
    main()
