"""Private real row-spacing repair; unchanged pads, envelopes and rules."""

import hashlib
import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-ear-fanout"
EXPECTED = "b743a4493ca38b7aa381f75febca9c2d215aa64f3ece09fcb91a6d86e33f4abc"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    assert sha(SOURCE / "processor_carrier.kicad_pcb") == EXPECTED
    assert not (ROOT / "processor_carrier.kicad_pcb").exists()
    for p in SOURCE.iterdir():
        if p.is_dir() and p.suffix == ".pretty":
            shutil.copytree(p, ROOT / p.name)
        elif p.is_file() and (
            p.suffix in [".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_sym"]
            or p.name in ["components.json", "bom.csv", "fp-lib-table", "sym-lib-table"]
        ):
            shutil.copy2(p, ROOT / p.name)
    out = ROOT / "generated"
    out.mkdir()
    t = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    changes = []
    for q in children(t, "gr_line"):
        if first(q, "layer")[1] != "Edge.Cuts":
            continue
        old = sexpr(q)
        for tag in ["start", "end"]:
            p = first(q, tag)
            if float(p[2]) == 143:
                p[2] = a(140)
        if sexpr(q) != old:
            changes.append(dict(uuid=str(first(q, "uuid")[1]), before=old, after=sexpr(q)))
    assert len(changes) == 3
    for q in children(t, "zone"):
        if (
            children(q, "net")
            and first(q, "net")[1] == "/AGND"
            and children(q, "priority")
            and str(first(q, "priority")[1]) == "1"
            and children(q, "layer")
            and first(q, "layer")[1] == "In1.Cu"
        ):
            old = sexpr(q)
            pts = first(first(q, "polygon"), "pts")
            assert float(pts[1][2]) == float(pts[2][2]) == 143
            pts[1][2] = a(140)
            pts[2][2] = a(140)
            changes.append(dict(uuid=str(first(q, "uuid")[1]), before=old, after=sexpr(q)))
    assert len(changes) == 4
    j14 = next(
        f
        for f in children(t, "footprint")
        if any(p[1:3] == ["Reference", "J14"] for p in children(f, "property"))
    )
    old = sexpr(j14)
    assert list(map(float, first(j14, "at")[1:])) == [258, 145.5, 90]
    first(j14, "at")[2] = a(142.5)
    changes.append(dict(uuid=str(first(j14, "uuid")[1]), before=old, after=sexpr(j14)))
    (ROOT / "processor_carrier.kicad_pcb").write_text(sexpr(t) + "\n")
    shutil.copyfile(
        SOURCE / "generated/parent-fanout-requirements.json", out / "parent-fanout-requirements.json"
    )
    (out / "design-change.json").write_text(
        json.dumps(
            dict(
                parent_pcb_sha256=EXPECTED,
                candidate_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
                changes=changes,
                J14_world_pad_centres_mm={"1": [188, 84.5], "2": [192, 84.5]},
                J15_world_pad_centres_mm={"1": [188, 92.5], "2": [192, 92.5]},
                world_outline_mm=[[30, 42], [180, 42], [180, 82], [194.5, 82], [194.5, 107], [30, 107]],
                added_area_mm2=43.5,
                nominal_service_gap_mm=3.1,
                unchanged_clearance_rules=True,
                unchanged_service_envelopes=True,
                all_other87_complete_FP_exact_required=True,
                all79parts_pinmaps_routing_stackup_exact_required=True,
                physical_qualified=False,
                fabrication_released=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(sha(ROOT / "processor_carrier.kicad_pcb"))


if __name__ == "__main__":
    run()
