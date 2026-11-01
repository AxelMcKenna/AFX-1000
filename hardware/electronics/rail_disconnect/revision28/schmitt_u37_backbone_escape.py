"""Explicit three-site receiving escape experiment, real drills and original-rule stems."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, read_sexpr, sexpr
from .receiver_local_escape import escape
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-u37-backbone-surface-work"
WORK = ROOT / "generated/schmitt-u37-backbone-escape-work"


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    rt = Router(t)
    rows = []
    from .receiver_surface_path import connect

    p = next(p for p in rt.by_ref["U37"] if p["pin"] == "8")
    q = next(p for p in rt.by_ref["C80"] if p["pin"] == "1")
    got, reason = connect(
        rt, p, [dict(xy=q["xy"], ref="C80", pin="1", kind="PAD")], radius=8, step=0.025, budget=500000
    )
    rows.append(dict(ref="U37", pin="8", net=p["net"], route=got, reason=reason))
    print("U37power8", bool(got), reason, flush=True)
    for ref, num in [("U37", n) for n in ("1", "2", "3", "5", "7")] + [("C80", "2")]:
        p = next(p for p in rt.by_ref[ref] if p["pin"] == num)
        got, reason = escape(rt, p, maxdistance=6, step=0.025)
        rows.append(
            dict(ref=ref, pin=num, net=p["net"], maximum_search_radius_mm=6, route=got, reason=reason)
        )
        print(ref, num, bool(got), reason, flush=True)
    for i, n in enumerate(t):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(
                        str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL,
                                f"rmx:E28:U37-actual-leaf-escapes:{hashlib.sha256(blob).hexdigest()}:{i}:{sexpr(n)}",
                            )
                        )
                    ),
                ]
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
    (WORK / "generated/leaf-escape-trial.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                escape_recipe_sha256=hashlib.sha256(
                    (ROOT / "receiver_local_escape.py").read_bytes()
                ).hexdigest(),
                operations=rows,
                all_original_Cu_preserved=True,
                real_capped_filled_vias_diameter_mm=0.6,
                real_drill_diameter_mm=0.3,
                actual_pad_track_drill_and_board_rules_retained=True,
                force_fill_loss_not_guarded_or_accepted=True,
                fresh_all_force_and_positive_negative_return_resistance_required=True,
                native_and_physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
