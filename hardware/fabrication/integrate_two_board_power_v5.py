"""TBP05: sense negative source rails upstream of their NF startup switches.

E28's original input became the NF output when the series stage was inserted.
Leaving its UV/OV source-sense dividers there makes NF permission depend on
its own disabled output rising. Move only the two high-impedance sense feeds.
Protected-output, drain, force and clamp connections are retained.
"""
import copy
import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha, read_netlist
from hardware.fabrication.integrate_two_board_power_v3 import pin_label, promote

SOURCE = STAGING / "two-board-power-integration-04"
BASELINE = STAGING / "two-board-power-native-04"
OUT = STAGING / "two-board-power-integration-05"


def build():
    assert not OUT.exists()
    parts, pins = read_netlist(BASELINE / "netlist.xml")
    expected = json.loads((SOURCE / "expected-circuit.json").read_text())
    before = copy.deepcopy(expected)
    changes = [("E_R49", "1", "PWR_N19_POST_NF", "PWR_N19_SOURCE", "N_J2", "150k 0.01% 5ppm"),
               ("E_R53", "1", "PWR_N12_POST_NF", "PWR_N12_SOURCE", "N_J4", "100k 0.01% 5ppm")]
    for ref, pin, old, new, force, value in changes:
        assert pins[(ref, pin)] == pins[(force, "2")] == old
        assert pins[(force, "1")] == new
        assert parts[ref].findtext("value") == value
        assert expected[ref]["pins"][pin] == old
        expected[ref]["pins"][pin] = new
    shutil.copytree(SOURCE, OUT)
    path = next(OUT.glob("E_*.kicad_sch"))
    sheet = read_sexpr(path.read_text())
    for ref, pin, old, new, force, value in changes:
        label = pin_label(sheet, ref, pin)
        assert label[1] == old
        promote(label, new)
    path.write_text(sexpr(sheet) + "\n")
    rootpath = OUT / "power_protection.kicad_sch"
    root = read_sexpr(rootpath.read_text())
    first(first(root, "title_block"), "rev")[1] = "TBP05"
    notes = children(root, "text")
    notes[0][1] = "30 base + 15 NF interface pairs; reset-masked fault SET. Negative source senses moved upstream of NF."
    notes[2][1] = "E_R49.1 and E_R53.1 sense P03 sources before NF; force, drain and protected-output feedback remain distinct."
    rootpath.write_text(sexpr(root) + "\n")
    (OUT / "expected-circuit.json").write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n")
    delta = [dict(ref=r, pin=p, before=n, after=expected[r]["pins"][p])
             for r, c in before.items() for p, n in c["pins"].items() if n != expected[r]["pins"][p]]
    assert len(delta) == 2
    paths = [Path(__file__), REPO / "hardware/fabrication/integrate_two_board_power_v3.py",
             BASELINE / "netlist.xml", BASELINE / "review.json", BASELINE / "fault-mask-audit.json",
             *[p for p in SOURCE.rglob("*") if p.is_file()]]
    record = json.loads((SOURCE / "construction.json").read_text())
    record["source_sha256"] = {str(p.relative_to(REPO)): sha(p) for p in paths}
    record["negative_source_sense_pin_delta"] = delta
    record["negative_source_sense_reason"] = "NF permit requires source UV-good; a disabled NF output cannot supply its own pre-start source qualification."
    record["force_and_protected_monitor_connections_changed"] = False
    record["full_startup_and_fault_recovery_qualified"] = False
    (OUT / "construction.json").write_text(json.dumps(record, indent=2) + "\n")
    print("Two negative-source sense feeds moved upstream; no force paths, component values or placements changed")


if __name__ == "__main__":
    build()
