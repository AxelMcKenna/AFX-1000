"""Remove exact native-failed ordinary raw-OC leaf pieces at retargeted receivers."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .schmitt_cone_candidate import GROUPS, ROOT

SOURCE = ROOT / "generated/schmitt-all-oc-placement2-work"
WORK = ROOT / "generated/schmitt-all-oc-old-leaf-work"
REPORT = ROOT / "generated/schmitt-all-oc-placement-work/generated/drc-all-oc-placement.json"


def main():
    assert not WORK.exists()
    t = read_sexpr((SOURCE / "rail_disconnect.kicad_pcb").read_text())
    r = json.loads((SOURCE / "generated/receiving-change.json").read_text())
    raw = json.loads(REPORT.read_text())
    endpoints = {(v["ref"], v["pin"]) for v in r["endpoint_changes"]}
    checked = read_sexpr((REPORT.parent / "filled-all-oc-placement.kicad_pcb").read_text())
    receiver_ids = {
        str(first(p, "uuid")[1])
        for f in children(checked, "footprint")
        for p in children(f, "pad")
        if (next(q[2] for q in children(f, "property") if q[1] == "Reference"), str(p[1])) in endpoints
    }
    ids = set()
    for v in raw["violations"]:
        if v["severity"] == "error" and any(q["uuid"] in receiver_ids for q in v["items"]):
            ids.update(q["uuid"] for q in v["items"])
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(t, "net")}
    nets = {n for g in GROUPS for n in g if n}
    removed = []
    for n in list(t):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and str(first(n, "uuid")[1]) in ids:
            net = names[str(first(n, "net")[1])]
            if net in nets:
                removed.append(dict(net=net, literal=sexpr(n)))
                t.remove(n)
    assert removed
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
    report = dict(
        source_pcb_sha256=hashlib.sha256((SOURCE / "rail_disconnect.kicad_pcb").read_bytes()).hexdigest(),
        raw_native_report_sha256=hashlib.sha256(REPORT.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        removed_native_failed_ordinary_raw_OC_leaf_copper=removed,
        force_reference_and_other_old_Cu_preserved=True,
        no_qualification=True,
    )
    (WORK / "generated/obsolete-receiver-leaves.json").write_text(json.dumps(report, indent=2) + "\n")
    print(len(removed), "old raw receiver leaf pieces removed")


if __name__ == "__main__":
    main()
