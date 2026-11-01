"""Retarget exact former receiving leaf geometry to buffered signals, no new drills."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-all-oc-fanout-work"
WORK = ROOT / "generated/schmitt-all-oc-receiver-anchors-work"
LEAVES = ROOT / "generated/schmitt-all-oc-old-leaf-work/generated/obsolete-receiver-leaves.json"


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    nets = {str(n[2]).lstrip("/"): str(n[1]) for n in children(t, "net")}
    rows = []
    existing = {str(first(n, "uuid")[1]) for k in ("segment", "via") for n in children(t, k)}
    for r in json.loads(LEAVES.read_text())["removed_native_failed_ordinary_raw_OC_leaf_copper"]:
        n = read_sexpr(r["literal"])
        assert str(first(n, "uuid")[1]) not in existing
        net = r["net"] + "_SCHMITT"
        assert net in nets
        first(n, "net")[1] = a(nets[net])
        t.append(n)
        rows.append(dict(previous_raw_net=r["net"], new_buffered_net=net, literal=sexpr(n)))
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
    (WORK / "generated/retargeted-receiver-anchors.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                old_leaf_ledger_sha256=hashlib.sha256(LEAVES.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                restored_geometry_net_only_retargeted=rows,
                native_checks_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(len(rows), "exact old receiver leaf shapes restored to buffered signals")


if __name__ == "__main__":
    main()
