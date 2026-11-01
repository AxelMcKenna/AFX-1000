"""Explicit three-site receiving escape experiment, real drills and original-rule stems."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, read_sexpr, sexpr
from ..routing.check import point_segment
from .focused import legal_line
from .receiver_local_escape import escape
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-c79-input-first-work"
WORK = ROOT / "generated/schmitt-receiver-three-drill-work"


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    rt = Router(t)
    rows = []
    # A moved real barrel reconnects the retained F/B stems of the former P12
    # receiver barrel. Its prior location was removed for an actual N19 conflict.
    net = "P12_OV_OK_SCHMITT"
    old = (7.325, 14.0)
    new = (7.325, 14.6)
    for layer in (0, 5):
        assert any(
            g["kind"] == "line"
            and g["net"] == net
            and layer in g["layers"]
            and point_segment(old, g["start"], g["end"]) < 1e-6
            for g in rt.geometry
        )
    if all(legal_line(rt, net, z, old, new, 0.2) for z in (0, 5)):
        got, reason = escape(rt, dict(net=net, xy=new, layers=(0,)), maxdistance=0.025, step=0.025)
        if got:
            assert all(legal_line(rt, net, z, old, got["via"], 0.2) for z in (0, 5))
            for z in (0, 5):
                rt.path(net, z, [old, got["via"]], 0.2)
    else:
        got, reason = None, "physical F/B stems to proposed moved barrel violate clearance"
    rows.append(
        dict(
            net=net,
            operation="moved P12 receiving barrel",
            old_connection=old,
            proposed_new_barrel=new,
            route=got,
            reason=reason,
        )
    )
    print("P12 moved barrel", bool(got), reason, flush=True)
    for num in ("1", "7"):
        p = next(p for p in rt.by_ref["U36"] if p["pin"] == num)
        got, reason = escape(rt, p, maxdistance=6, step=0.025)
        rows.append(
            dict(ref="U36", pin=num, net=p["net"], maximum_search_radius_mm=6, route=got, reason=reason)
        )
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
                                f"rmx:E28:receiving-three-drills:{hashlib.sha256(blob).hexdigest()}:{i}:{sexpr(n)}",
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
    (WORK / "generated/three-drill-trial.json").write_text(
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
