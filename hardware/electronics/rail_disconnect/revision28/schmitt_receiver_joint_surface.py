"""Targeted ordinary-control cage ripup; real surface paths and complete ledger."""

import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..routing.check import point_segment, segment_distance
from .ordinary_joint_ripup7 import ORDINARY
from .receiver_surface_path import connect
from .repair import Router
from .schmitt_cone_candidate import GROUPS

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-receiver-surface-trial-work"
GRAPH_SOURCE = ROOT / "generated/schmitt-near-reconnect-work"
WORK = ROOT / "generated/schmitt-receiver-joint-surface-work"
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")


def geometry(n, names):
    net = names[str(first(n, "net")[1])]
    if n[0] == "via":
        return dict(
            kind="via",
            net=net,
            xy=tuple(float(v) - 100 for v in first(n, "at")[1:]),
            radius=float(first(n, "size")[1]) / 2,
            layers=tuple(range(6)),
        )
    return dict(
        kind="line",
        net=net,
        start=tuple(float(v) - 100 for v in first(n, "start")[1:]),
        end=tuple(float(v) - 100 for v in first(n, "end")[1:]),
        width=float(first(n, "width")[1]),
        layers=(LAYERS.index(str(first(n, "layer")[1])),),
    )


def key(g):
    if g["kind"] == "line":
        return (
            "line",
            g["net"],
            tuple(g["layers"]),
            tuple(round(float(v), 6) for v in g["start"]),
            tuple(round(float(v), 6) for v in g["end"]),
            round(g["width"], 6),
        )
    if g["kind"] == "via":
        return ("via", g["net"], tuple(round(float(v), 6) for v in g["xy"]), round(g["radius"], 6))
    return None


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    before = read_sexpr((GRAPH_SOURCE / "rail_disconnect.kicad_pcb").read_text())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(t, "net")}
    graph_path = GRAPH_SOURCE / "generated/residual-components.json"
    graph = json.loads(graph_path.read_text())
    signals = {"P19_OV_OK", "N19_OV_OK", "P12_OV_OK", "P19_OV_OK_SCHMITT", "P12_OV_OK_SCHMITT"}
    assert sorted(map(sexpr, children(t, "footprint"))) == sorted(map(sexpr, children(before, "footprint")))
    for net in signals:

        def objects(tree):
            return sorted(
                sexpr(n)
                for k in ("segment", "via")
                for n in children(tree, k)
                if names[str(first(n, "net")[1])] == net
            )

        assert objects(t) == objects(before), net
    ordinary = (
        set(ORDINARY) | {n for g in GROUPS for n in g if n} | {n + "_SCHMITT" for g in GROUPS for n in g if n}
    )
    candidates = {
        str(first(n, "uuid")[1]): (n, geometry(n, names))
        for k in ("segment", "via")
        for n in children(t, k)
        if names[str(first(n, "net")[1])] in ordinary
    }
    keys = {key(g) for n, g in candidates.values()}
    removed = []
    results = []
    for num in ("2", "7", "3", "1", "6"):
        rt = Router(t)
        p = next(p for p in rt.by_ref["U36"] if p["pin"] == num)
        group = next(
            g
            for g in graph["inventory"][p["net"]]["components"]
            if not any(n.get("ref") == "U36" and n.get("pin") == num for n in g)
            and any(n["kind"] == "PAD" for n in g)
        )
        present = {
            str(first(n, "uuid")[1])
            for k in ("segment", "via")
            for n in children(t, k)
            if children(n, "uuid")
        }
        targets = []
        for n in group:
            if 5 not in n["layers"] or (n["kind"] != "PAD" and n["uuid"] not in present):
                continue
            for xy in [n["position_mm"]] + ([n["end_mm"]] if n["kind"] == "PCB_TRACK" else []):
                targets.append(
                    dict(xy=xy, uuid=n["uuid"], kind=n["kind"], ref=n.get("ref"), pin=n.get("pin"))
                )
        targets = sorted(targets, key=lambda n: math.dist(n["xy"], p["xy"]))[:32]
        # Physical lands, drills of every force/quiet net, and prior new paths remain.
        rt.geometry = [g for g in rt.geometry if not (key(g) in keys and g["net"] != p["net"])]
        added_before = {id(n) for n in t}
        got, reason = connect(rt, p, targets, radius=12, step=0.025, budget=500000)
        new = [n for n in t if id(n) not in added_before and isinstance(n, list) and n and n[0] == "segment"]
        ripped = []
        if got:
            for uid, (n, g) in candidates.items():
                if n not in t or g["net"] == p["net"]:
                    continue
                hit = False
                for newnode in new:
                    ng = geometry(newnode, names)
                    if 5 not in g["layers"]:
                        continue
                    if g["kind"] == "line":
                        distance = (
                            segment_distance(ng["start"], ng["end"], g["start"], g["end"])
                            - ng["width"] / 2
                            - g["width"] / 2
                        )
                    else:
                        distance = (
                            point_segment(g["xy"], ng["start"], ng["end"]) - ng["width"] / 2 - g["radius"]
                        )
                    if distance < 0.200001:
                        hit = True
                        break
                if hit:
                    t.remove(n)
                    ripped.append(dict(uuid=uid, net=g["net"], literal=sexpr(n)))
                    removed.append(ripped[-1])
        results.append(
            dict(ref="U36", pin=num, net=p["net"], route=got, reason=reason, ripped_ordinary_objects=ripped)
        )
        print("U36", num, bool(got), "ripped", len(ripped), reason, flush=True)
    for i, n in enumerate(t):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(
                        str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL,
                                f"rmx:E28:receiver-joint-surface:{hashlib.sha256(blob).hexdigest()}:{i}:{sexpr(n)}",
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
    (WORK / "generated/joint-surface.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                native_signal_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(),
                source_graph_5_target_signals_literal_Cu_and_all_footprints_equivalent=True,
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                path_recipe_sha256=hashlib.sha256(
                    (ROOT / "receiver_surface_path.py").read_bytes()
                ).hexdigest(),
                attempts=results,
                removed_ordinary_objects=removed,
                affected_ordinary_nets=sorted({v["net"] for v in removed}),
                all_affected_connections_require_fresh_native_reconnect=True,
                all_physical_pads_force_reference_and_ground_Cu_preserved=True,
                new_drills_added=0,
                local_force_fill_changes_require_extraction=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
