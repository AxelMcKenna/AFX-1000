"""Synchronize reviewed value/datasheet changes without disturbing copper.

Footprint and pad-net changes require an explicit layout operation instead.
"""

import json

from ...common.netlists import netlist
from ...common.sexpr import children, first, read_sexpr, sexpr
from .route import coded, named
from .spec import ROOT


def sync():
    pcb = ROOT / "power_p03.kicad_pcb"
    tree = coded(read_sexpr(pcb.read_text()))
    parts = {c["ref"]: c for c in json.loads((ROOT / "components.json").read_text())}
    _, pins = netlist(ROOT / "generated/netlist.xml")
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref not in parts:
            continue
        c = parts[ref]
        assert fp[1] == c["footprint"], f"{ref}: footprint changed; actual layout repair required"
        for pad in children(fp, "pad"):
            if not children(pad, "net"):
                continue
            number = str(pad[1])
            net = str(first(pad, "net")[-1]).lstrip("/")
            assert net == pins[ref][number], (
                f"{ref}.{number}: pad net changed; actual circuit/layout repair required"
            )
        for p in children(fp, "property"):
            if p[1] in {"Value", "MPN"}:
                p[2] = c["part"]
            if p[1] == "Datasheet":
                p[2] = c.get("source", "")
    pcb.write_text(sexpr(named(tree)) + "\n")
    print("P03 value metadata synchronized; footprint and pad nets independently unchanged")


if __name__ == "__main__":
    sync()
