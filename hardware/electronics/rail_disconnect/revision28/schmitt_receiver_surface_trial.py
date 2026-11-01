"""Trace-only nearby receiving repair to actual native same-net physical anchors."""

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
SOURCE = ROOT / "generated/schmitt-near-reconnect-work"
WORK = ROOT / "generated/schmitt-receiver-surface-trial-work"


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    rt = Router(t)
    graph_path = SOURCE / "generated/residual-components.json"
    graph = json.loads(graph_path.read_text())
    assert (
        next(
            v
            for p, v in graph["source_sha256"].items()
            if Path(p).resolve() == (SOURCE / "rail_disconnect.kicad_pcb").resolve()
        )
        == hashlib.sha256(blob).hexdigest()
    )
    rows = []
    for num in ("8", "2", "7", "3", "1", "6"):
        p = next(p for p in rt.by_ref["U36"] if p["pin"] == num)
        groups = graph["inventory"][p["net"]]["components"]
        group = next(
            g
            for g in groups
            if not any(n.get("ref") == "U36" and n.get("pin") == num for n in g)
            and any(n["kind"] == "PAD" for n in g)
        )
        if num == "8":
            target = next(p for p in rt.by_ref["C79"] if p["pin"] == "1")
            assert any(n.get("ref") == "C79" and n.get("pin") == "1" for n in group)
            targets = [dict(xy=target["xy"], ref="C79", pin="1", kind="PAD")]
        else:
            targets = []
            for n in group:
                if 5 not in n["layers"]:
                    continue
                for xy in [n["position_mm"]] + ([n["end_mm"]] if n["kind"] == "PCB_TRACK" else []):
                    targets.append(
                        dict(xy=xy, uuid=n["uuid"], kind=n["kind"], ref=n.get("ref"), pin=n.get("pin"))
                    )
            targets = sorted(targets, key=lambda n: math.dist(n["xy"], p["xy"]))[:32]
        got, reason = connect(rt, p, targets, radius=12, step=0.025, budget=500000)
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
                                f"rmx:E28:receiver-surface:{hashlib.sha256(blob).hexdigest()}:{i}:{sexpr(n)}",
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
    (WORK / "generated/surface-path-trial.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                native_component_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                path_recipe_sha256=hashlib.sha256(
                    (ROOT / "receiver_surface_path.py").read_bytes()
                ).hexdigest(),
                routes=rows,
                all_existing_Cu_preserved=True,
                new_drills_added=0,
                exact_full_segment_foreign_pad_track_drill_clearance_checked_mm=0.2,
                planner_extra_clearance_mm=0.02,
                filled_force_not_guarded_or_accepted=True,
                native_force_and_contact_correct_PDN_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
