"""Move one newly introduced GND barrel inward to restore the unchanged0.5mm edge rule."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .focused import legal_line
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u31-front-reconnect-work"
WORK = ROOT / "generated/u31-front-edge-repair-work"


def main():
    assert not WORK.exists()
    data = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(data.decode())
    changes = []
    via = next(
        v for v in children(t, "via") if str(first(v, "uuid")[1]) == "945a4750-1088-5275-a82e-d7555d1c0a31"
    )
    assert first(via, "net")[1] == "15" and tuple(round(float(v), 6) for v in first(via, "at")[1:]) == (
        190.85,
        153.75,
    )
    changes.append(dict(before=sexpr(via)))
    first(via, "at")[2] = a("153.65")
    changes[-1]["after"] = sexpr(via)
    for n in list(children(t, "segment")):
        before = sexpr(n)
        updated = False
        for key in ("start", "end"):
            p = first(n, key)
            if tuple(round(float(v), 6) for v in p[1:]) == (190.85, 153.75):
                assert first(n, "net")[1] == "15"
                p[2] = a("153.65")
                updated = True
        if updated:
            changes.append(dict(before=before, after=sexpr(n)))
            if first(n, "start")[1:] == first(n, "end")[1:]:
                t.remove(n)
    r = Router(t)
    for c in changes[1:]:
        n = read_sexpr(c["after"])
        aa, bb = [tuple(float(v) - 100 for v in first(n, k)[1:]) for k in ("start", "end")]
        if aa != bb:
            assert legal_line(
                r,
                "AGND",
                ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu").index(first(n, "layer")[1]),
                aa,
                bb,
                0.2,
            )
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
    (WORK / "generated/edge-repair.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(data).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                changes=changes,
                edge_rule_mm=0.5,
                nominal_barrel_edge_gap_mm=0.55,
                no_original15_checkpoint_copper_changed=True,
                native_and_PDN_pending=True,
                qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
