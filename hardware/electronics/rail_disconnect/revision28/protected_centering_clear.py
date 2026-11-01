"""Keep the original MCAP approach straight and centre only its short final stem."""

import copy
import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .focused import legal_line
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/strict-protected-centering-trial-work"
WORK = ROOT / "generated/strict-centering-clear-work"


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    rt = Router(t)
    n = next(
        n
        for n in children(t, "segment")
        if str(first(n, "uuid")[1]) == "1c3027c7-dca5-52f3-92a9-34ae2b5638ad"
    )
    before = sexpr(n)
    assert first(n, "layer")[1] == "F.Cu" and float(first(n, "width")[1]) == 0.25
    net = "P12_MCAP1_LIMIT"
    start = (53.5, 26.125)
    bend = (53.5, 27.5)
    end = (53.7, 27.8)
    assert tuple(map(float, first(n, "start")[1:3])) == (153.5, 126.125)
    assert tuple(map(float, first(n, "end")[1:3])) == (153.7, 127.8)
    assert math.dist(bend, end) > 0.3
    assert legal_line(rt, net, 0, start, bend, 0.25) and legal_line(rt, net, 0, bend, end, 0.25), (
        "New approach must meet every actual foreign pad/track/barrel clearance"
    )
    first(n, "end")[1:3] = [a("153.5"), a("127.5")]
    stem = copy.deepcopy(n)
    first(stem, "start")[1:3] = [a("153.5"), a("127.5")]
    first(stem, "end")[1:3] = [a("153.7"), a("127.8")]
    first(stem, "uuid")[1] = a(
        str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:E28:centredMCAPstem:" + hashlib.sha256(blob).hexdigest()))
    )
    t.append(stem)
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
    (WORK / "generated/centred-MCAP-stem.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                before=before,
                after=[sexpr(n), sexpr(stem)],
                final_stem_length_mm=math.dist(bend, end),
                original_pretrial_straight_approach_restored=True,
                trace_width_mm=0.25,
                all_vias_parts_ports_and_other_copper_unchanged=True,
                all_prior_force_noise_timing_resistance_proofs_still_require_source_specific_renewal=True,
                native_and_physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
