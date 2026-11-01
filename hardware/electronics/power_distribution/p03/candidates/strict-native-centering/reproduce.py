"""Apply only the explicit source-bound PCB segment delta; never edit parent."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[5]))
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr  # noqa: E402


def check():
    d = json.loads((ROOT / "generated/source-delta.json").read_text())
    source = ROOT / "sources/db83/power_p03.kicad_pcb"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == d["source_parent_pcb_sha256"]
    t = read_sexpr(source.read_text())
    by = {str(first(n, "uuid")[1]): n for n in children(t, "segment")}
    for row in d["removed"] + d["changed"]:
        assert sexpr(by[row["uuid"]]) == row["old"]
    for row in d["removed"]:
        t.remove(by[row["uuid"]])
    for row in d["changed"]:
        t[t.index(by[row["uuid"]])] = read_sexpr(row["new"])
    for row in d["added"]:
        t.append(read_sexpr(row["new"]))
    actual = read_sexpr((ROOT / "power_p03.kicad_pcb").read_text())

    def objects(tree, kind):
        return {str(first(n, "uuid")[1]): sexpr(n) for n in children(tree, kind)}

    assert objects(t, "segment") == objects(actual, "segment")
    assert objects(t, "via") == objects(actual, "via")
    assert objects(t, "footprint") == objects(actual, "footprint")
    return t


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    tree = check()
    if a.output:
        assert not a.output.exists()
        assert a.output.resolve().is_relative_to(Path("/private/tmp"))
        a.output.write_text(sexpr(tree) + "\n")
    print("exact declared segment/via/FP geometry reproduced; no parent modified")
