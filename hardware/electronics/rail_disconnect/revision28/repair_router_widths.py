"""Physically widen newly emitted fanout traces; no native rule exemptions."""

import hashlib
import json
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .repair import ROOT


def main(label, contract_path):
    pcb = ROOT / "rail_disconnect.kicad_pcb"
    before = pcb.read_bytes()
    receipt_path = ROOT / "generated" / ("native-" + label + ".json")
    receipt = json.loads(receipt_path.read_text())
    assert receipt["pcb_sha256"] == hashlib.sha256(before).hexdigest()
    drc = ROOT / "generated" / ("drc-" + label + ".json")
    assert receipt["drc_sha256"] == hashlib.sha256(drc.read_bytes()).hexdigest()
    raw = json.loads(drc.read_text())
    offenders = set()
    for finding in raw["violations"]:
        if finding["severity"] != "error":
            continue
        assert finding["type"] == "track_width", "Repair only exact native width findings in this pass"
        offenders.update(i["uuid"] for i in finding["items"])
    protected = {r["uuid"] for r in json.loads(Path(contract_path).read_text())["locked_copper"]}
    assert not protected & offenders, "A protected original width must never be changed"
    tree = read_sexpr(before.decode())
    changed = []
    for node in children(tree, "segment"):
        uid = str(first(node, "uuid")[1])
        if uid not in offenders:
            continue
        width = first(node, "width")
        old = float(width[1])
        assert 0 < old < 0.2
        changed.append(dict(uuid=uid, old_native_object=sexpr(node), old_width_mm=old, new_width_mm=0.2))
        width[1] = a(".2")
    assert len(changed) == len(offenders) and changed
    pcb.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/router-width-repair.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(before).hexdigest(),
                output_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
                native_receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                raw_drc_sha256=receipt["drc_sha256"],
                changed=changed,
                actual_new_clearance_and_all_track_checks_required=True,
                rules_relaxed=False,
                findings_exempted=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Physically widened", len(changed), "new fanout tracks to0.2mm")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("label")
    p.add_argument("contract_path")
    a = p.parse_args()
    main(a.label, a.contract_path)
