"""Explicit single-cell local force-antipad trial; no inherited copper acceptance."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, read_sexpr, sexpr
from .receiver_local_escape import escape
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-near-reconnect-work"
WORK = ROOT / "generated/schmitt-receiver-barrel-trial-work"


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    rt = Router(t)
    rows = []
    for num in ("2", "7", "8", "1", "3", "6"):
        p = next(p for p in rt.by_ref["U36"] if p["pin"] == num)
        got, reason = escape(rt, p, maxdistance=2.5, step=0.025)
        rows.append(dict(ref="U36", pin=num, net=p["net"], route=got, reason=reason))
        print("U36", num, bool(got), reason, flush=True)
    for i, n in enumerate(t):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(
                        str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL,
                                f"rmx:E28:receiver-local-barrels:{hashlib.sha256(blob).hexdigest()}:{i}:{sexpr(n)}",
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
    (WORK / "generated/local-barrel-trial.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                escape_recipe_sha256=hashlib.sha256(
                    (ROOT / "receiver_local_escape.py").read_bytes()
                ).hexdigest(),
                maximum_stem_and_drill_radius_from_each_selected_pad_mm=2.5,
                existing_pad_track_hole_constraints_retained=True,
                selected_filled_capped_via_drill_diameter_mm=0.3,
                selected_via_Cu_diameter_mm=0.6,
                original_Cu_preserved=True,
                routes=rows,
                force_fill_changes_not_guarded_or_accepted=True,
                all_native_force_positive_negative_return_extractions_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
