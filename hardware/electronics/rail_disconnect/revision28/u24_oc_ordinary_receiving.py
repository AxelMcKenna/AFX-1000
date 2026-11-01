"""Explicit actual U24 receiver-pad escapes from the immutable thirty-open source."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..routing.check import point_segment, segment_distance
from .ordinary_joint_ripup7 import ORDINARY
from .receiving_escape_centered import escape
from .repair import Router
from .schmitt_cone_candidate import GROUPS
from .schmitt_receiver_joint_surface import geometry, key

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/v5-nearest-components-work"
WORK = ROOT / "generated/u24-oc-ordinary-receiving-work"


def separation(a, b):
    if not set(a["layers"]) & set(b["layers"]):
        return float("inf")
    if a["kind"] == "line" and b["kind"] == "line":
        return segment_distance(a["start"], a["end"], b["start"], b["end"]) - a["width"] / 2 - b["width"] / 2
    if a["kind"] == "via" and b["kind"] == "via":
        return __import__("math").dist(a["xy"], b["xy"]) - a["radius"] - b["radius"]
    if a["kind"] == "via":
        a, b = b, a
    return point_segment(b["xy"], a["start"], a["end"]) - a["width"] / 2 - b["radius"]


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(t, "net")}
    ordinary = (set(ORDINARY) | {n for g in GROUPS for n in g if n} | {n+"_SCHMITT" for g in GROUPS for n in g if n} | {"NF_VALID_LOGIC", "POS_OUTPUT_READY"}) - {"E28_FAULT", "E28_NOT_FAULT", "E28_ARMED", "E28_NOT_ARMED", "E28_OUT_ARMED", "E28_OUT_ARM_BAR", "E28_RESET", "E28_RESET_OUT"}
    candidates = {
        str(first(n, "uuid")[1]): (n, geometry(n, names))
        for k in ("segment",)
        for n in children(t, k)
        if names[str(first(n, "net")[1])] in ordinary
    }
    keys = {key(g) for n, g in candidates.values()}
    rows = []
    removed = []
    for ref, num in [("U24", n) for n in ("2", "5", "1", "4")]:
        rt = Router(t)
        p = next(p for p in rt.by_ref[ref] if p["pin"] == num)
        rt.geometry = [g for g in rt.geometry if not (key(g) in keys and g["net"] != p["net"])]
        before = {id(n) for n in t}
        got, reason = escape(rt, p, maxdistance=6, step=0.025)
        new = [
            geometry(n, names)
            for n in t
            if id(n) not in before and isinstance(n, list) and n and n[0] in ("segment", "via")
        ]
        ripped = []
        if got:
            for uid, (n, g) in candidates.items():
                if n not in t or g["net"] == p["net"]:
                    continue
                if any(separation(ng, g) < 0.200001 for ng in new):
                    t.remove(n)
                    row = dict(uuid=uid, net=g["net"], literal=sexpr(n))
                    removed.append(row)
                    ripped.append(row)
        rows.append(
            dict(ref=ref, pin=num, net=p["net"], route=got, reason=reason, ripped_ordinary_objects=ripped)
        )
        print(ref, num, bool(got), "removed", len(ripped), reason, flush=True)
    for i, n in enumerate(t):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(
                        str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL,
                                f"rmx:E28:U24OCjoint:{hashlib.sha256(blob).hexdigest()}:{i}:{sexpr(n)}",
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
    (WORK / "generated/joint-escape.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                escape_recipe_sha256=hashlib.sha256(
                    (ROOT / "receiving_escape_centered.py").read_bytes()
                ).hexdigest(),
                attempts=rows,
                removed_ordinary_objects=removed,
                affected_ordinary_nets=sorted({v["net"] for v in removed}),
                every_existing_force_quiet_ground_track_and_via_and_all_existing_vias_and_pads_fixed=True,
                ordinary_track_whitelist=sorted(ordinary),
                all_crosscoupled_state_feedback_nets_force_reference_ground_and_existing_vias_hard=True,
                actual_filled_force_changes_require_new_PDN=True,
                native_and_physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
