"""Correct the absolute pad angles of the intentionally rotated C1 footprint."""

import json
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent


def correct(cap):
    assert float(first(cap,"at")[3]) == 180
    assert {str(p[1]) for p in children(cap,"pad")} == {"1","2"}
    for pad in children(cap,"pad"):
        at = first(pad,"at")
        assert len(at) == 3 or (len(at) == 4 and float(at[3]) == 0)
        if len(at) == 3:
            at.append(a(180))
        else:
            at[3] = a(180)


def run():
    source = ROOT/"staging/bypass-closed-native-01/sequenced_bypass.kicad_pcb"
    output = ROOT/"staging/bypass-pad-orientation-01"
    assert not output.exists()
    tree = read_sexpr(source.read_text())
    cap = next(f for f in children(tree,"footprint") if any(p[1:3] == ["Reference","C1"] for p in children(f,"property")))
    correct(cap)
    output.mkdir()
    pcb = output/source.name
    pcb.write_text(sexpr(tree)+"\n")
    (output/"construction.json").write_text(json.dumps(dict(source_PCB_sha256=sha(source),
        candidate_PCB_sha256=sha(pcb),recipe_sha256=sha(Path(__file__)),
        change="C1 absolute pad orientation 0 to180 degrees; symmetric pad copper and other authored objects unchanged",
        native_checks_pending=True,fabrication_released=False),indent=2)+"\n")


if __name__ == "__main__":
    run()
