"""Route actual nearby U37/backbone terminals on B using exact corner clearance."""

import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, read_sexpr, sexpr
from .receiver_surface_path import connect
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-u37-backbone-clear-work"
WORK = ROOT / "generated/schmitt-u37-backbone-surface-work"


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    rt = Router(t)
    gp = SOURCE / "generated/residual-components.json"
    graph = json.loads(gp.read_text())
    assert (
        next(
            h
            for p, h in graph["source_sha256"].items()
            if Path(p).resolve() == (SOURCE / "rail_disconnect.kicad_pcb").resolve()
        )
        == hashlib.sha256(blob).hexdigest()
    )
    rows = []
    for ref, num in [("U37", n) for n in ("2", "7", "3", "1", "6", "5", "8", "4")] + [
        ("C80", "1"),
        ("C80", "2"),
    ]:
        p = next(p for p in rt.by_ref[ref] if p["pin"] == num)
        if p["net"] not in graph["inventory"]:
            rows.append(dict(ref=ref, pin=num, already_native_connected=True))
            continue
        groups = graph["inventory"][p["net"]]["components"]
        one = next(g for g in groups if any(n.get("ref") == ref and n.get("pin") == num for n in g))
        others = [g for g in groups if g is not one and any(n["kind"] == "PAD" for n in g)]
        if not others:
            rows.append(dict(ref=ref, pin=num, same_native_component_with_all_other_pads=True))
            continue
        main = max(others, key=lambda g: len(g))
        targets = []
        for n in main:
            if 5 not in n["layers"]:
                continue
            for xy in [n["position_mm"]] + ([n["end_mm"]] if n["kind"] == "PCB_TRACK" else []):
                targets.append(
                    dict(xy=xy, uuid=n["uuid"], kind=n["kind"], ref=n.get("ref"), pin=n.get("pin"))
                )
        targets = sorted(targets, key=lambda n: math.dist(n["xy"], p["xy"]))[:64]
        got, reason = connect(rt, p, targets, radius=15, step=0.025, budget=600000)
        rows.append(dict(ref=ref, pin=num, net=p["net"], route=got, reason=reason))
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
                                f"rmx:E28:U37backbone-surface:{hashlib.sha256(blob).hexdigest()}:{i}:{sexpr(n)}",
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
    (WORK / "generated/backbone-surface.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                native_component_graph_sha256=hashlib.sha256(gp.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                surface_recipe_sha256=hashlib.sha256(
                    (ROOT / "receiver_surface_path.py").read_bytes()
                ).hexdigest(),
                attempts=rows,
                all_source_copper_preserved=True,
                no_new_drills=True,
                all_force_fills_and_resistances_require_new_diagnostics=True,
                native_and_physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
