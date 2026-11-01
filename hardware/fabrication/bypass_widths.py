"""Restore the required 0.2 mm width on router fanout tracks; no rule relaxation."""

import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent


def run():
    source = ROOT/"staging/bypass-routed-native-01/sequenced_bypass.kicad_pcb"
    output = ROOT/"staging/bypass-width-repair-01"
    assert not output.exists()
    original = sha(source)
    tree = read_sexpr(source.read_text())
    edits = []
    for track in children(tree,"segment"):
        if float(first(track,"width")[1]) < .2:
            assert float(first(track,"width")[1]) == .15
            edits.append(dict(uuid=str(first(track,"uuid")[1]),old_width_mm=.15,new_width_mm=.2))
            first(track,"width")[1] = .2
    assert len(edits) == 23 and sha(source) == original
    output.mkdir()
    pcb = output/source.name
    pcb.write_text(sexpr(tree)+"\n")
    (output/"construction.json").write_text(json.dumps(dict(source_PCB_sha256=original,
        candidate_PCB_sha256=sha(pcb),recipe_sha256=sha(Path(__file__)),edits=edits,
        all_other_authored_objects_unchanged=True,native_checks_pending=True,fabrication_released=False),indent=2)+"\n")
    print("Raised23 fanout segments to0.2mm; all board rules retained")


if __name__ == "__main__":
    run()
