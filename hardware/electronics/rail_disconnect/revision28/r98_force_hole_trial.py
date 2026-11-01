"""Focused actual-pad escape additions preserving all existing copper and filled force."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, read_sexpr, sexpr
from .r98_local_escape_trial import escape
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/coherent-ground-repair-work"
WORK = ROOT / "generated/r98-force-hole-trial-work"
PADS = [("R98", "1"), ("R98", "2")]


def main():
    assert not WORK.exists()
    src = SOURCE / "rail_disconnect.kicad_pcb"
    blob = src.read_bytes()
    tree = read_sexpr(blob.decode())
    digest = hashlib.sha256(blob).hexdigest()
    filled = SOURCE / "generated/filled-coherent-ground-repair.kicad_pcb"
    ft = read_sexpr(filled.read_text())
    rt = Router(tree)
    rows = []
    for ref, num in PADS:
        p = next(p for p in rt.by_ref[ref] if p["pin"] == num)
        result, reason = escape(rt, p, ft, maxdistance=1, step=0.025)
        row = dict(ref=ref, pin=num, net=p["net"], connected_escape=result, reason=reason)
        rows.append(row)
        print(ref, num, bool(result), reason, flush=True)
    added = []
    for i, n in enumerate(tree):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:remainingfine:{digest}:{i}:{sexpr(n)}"))),
                ]
            )
            added.append(sexpr(n))
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
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(tree) + "\n")
    (WORK / "generated/focused-escapes.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=digest,
                filled_pcb_sha256=hashlib.sha256(filled.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                escape_helper_sha256=hashlib.sha256((ROOT / "r98_local_escape_trial.py").read_bytes()).hexdigest(),
                actual_added_copper=added,
                attempts=rows,
                all_existing_copper_and_parts_retained=True,
                actual_filled_force_guard=True, explicit_V5_REG_SRC_In2_hole_trial_not_no_loss=True, allocation_and_all_physics_pending=True,
                native_and_PDN_pending=True,
                qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
