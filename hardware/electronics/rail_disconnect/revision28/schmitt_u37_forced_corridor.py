"""Declare U37 ordinary-cage removal, preserving physical force/quiet/ground Cu."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..routing.check import point_segment, segment_distance
from .ordinary_joint_ripup7 import ORDINARY
from .receiver_local_escape import escape
from .receiver_surface_path import connect
from .repair import Router
from .schmitt_cone_candidate import GROUPS
from .schmitt_receiver_joint_surface import geometry, key

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-c80-corridor-work"
WORK = ROOT / "generated/schmitt-u37-forced-corridor-work"


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
    ordinary = (
        set(ORDINARY)
        | {n for g in GROUPS for n in g if n}
        | {n + "_SCHMITT" for g in GROUPS for n in g if n}
        | {"OK_19", "P19_ALLOW", "N19_ALLOW", "P12_ALLOW", "N12_ALLOW"}
    )
    candidates = {
        str(first(n, "uuid")[1]): (n, geometry(n, names))
        for k in ("segment", "via")
        for n in children(t, k)
        if names[str(first(n, "net")[1])] in ordinary
    }
    keys = {key(g) for n, g in candidates.values()}
    rows = []
    removed = []
    for num in ("7", "1", "2", "5", "6", "4", "8"):
        rt = Router(t)
        p = next(p for p in rt.by_ref["U37"] if p["pin"] == num)
        rt.geometry = [g for g in rt.geometry if not (key(g) in keys and g["net"] != p["net"])]
        before = {id(n) for n in t}
        if num == "7":
            site = (72.7, 46.0)
            got, reason = escape(rt, dict(p, xy=site), maxdistance=0.025, step=0.025)
            assert got, reason
            stem, why = connect(
                rt, p, [dict(xy=got["via"], kind="PCB_VIA")], radius=6, step=0.025, budget=500000
            )
            assert stem, why
            got["stem"] = stem
        else:
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
            dict(ref="U37", pin=num, net=p["net"], route=got, reason=reason, ripped_ordinary_objects=ripped)
        )
        print("U37", num, bool(got), "removed", len(ripped), reason, flush=True)
    for i, n in enumerate(t):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(
                        str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL,
                                f"rmx:E28:U37joint:{hashlib.sha256(blob).hexdigest()}:{i}:{sexpr(n)}",
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
                    (ROOT / "receiver_local_escape.py").read_bytes()
                ).hexdigest(),
                attempts=rows,
                removed_ordinary_objects=removed,
                affected_ordinary_nets=sorted({v["net"] for v in removed}),
                all_original_force_quiet_ground_pads_and_placements_preserved=True,
                actual_filled_force_changes_require_new_PDN=True,
                native_and_physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
