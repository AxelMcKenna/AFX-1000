"""Bounded ordinary trace/barrel ripup for one ALL_RAILS_ALLOW connection.

Only explicitly listed ordinary control traces and at most three associated
barrels may move. Pads, quiet references, force fields, ground references and
local latch feedback links remain hard obstacles. Every affected net must be
reconnected before acceptance.
"""

import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..routing.check import point_segment, segment_distance
from .filled_surface_path import path_between
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u21-band-reconnect1-work"
WORK = ROOT / "generated/u21-ordinary-via-ripup-work"
ORDINARY = {
    "E28_ARMED",
    "E28_FAULT",
    "E28_FAULT_SET",
    "E28_FAULT_ANY",
    "E28_MASTER_ENABLE",
    "E28_NORMAL_PRE",
    "E28_NORMAL_OK",
    "E28_NOT_NORMAL_OK",
    "E28_OUT_ARM_BAR",
    "E28_OUT_ARMED",
    "E28_OUT_READY",
    "E28_OUT_VALID_ACTIVE",
    "E28_NOT_OUT_READY",
    "E28_OUTPUT_READY",
    "E28_RESET",
    "E28_RESET_OUT",
    "E28_RUN_AND_SOURCE",
    "E28_NOT_RUN",
    "E28_NOT_AUX",
    "E28_RUN_LOGIC",
    "E28_NOT_FAULT",
    "E28_SOURCE_READY_LOGIC",
    "E28_SOURCE_READY",
    "E28_NOT_SOURCE_READY",
    "E28_NOT_ARMED",
    "E28_OUT_UV_FAULT",
    "E28_TIMEOUT_FAULT",
    "E28_REF_HEALTH_FAULT",
    "E28_USER_AUX",
    "E28_SAFE_STAGE",
    "E28_SAFE_REQUEST",
    "E28_AUX_VALID",
    "P03_SOURCES_READY",
    "POWER_RUN",
}
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")


def main():
    assert not WORK.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    tree = read_sexpr(original.decode())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    filled_path = SOURCE / "generated/filled-u21-reconnect1.kicad_pcb"
    filled = read_sexpr(filled_path.read_text())
    pads_path = SOURCE / "generated/native-pads.json"
    pads = json.loads(pads_path.read_text())
    assert pads["source_pcb_sha256"] == hashlib.sha256(filled_path.read_bytes()).hexdigest()
    graph_path = SOURCE / "generated/residual-components.json"
    graph = json.loads(graph_path.read_text())
    assert [h for p, h in graph["source_sha256"].items() if Path(p).resolve() == source.resolve()] == [digest]
    row = graph["inventory"]["ALL_RAILS_ALLOW"]
    group = next(g for g in row["components"] if any(p.get("ref") == "U21" for p in g))
    start = next(p["position_mm"] for p in group if p["kind"] == "PCB_VIA")
    others = [g for g in row["components"] if g is not group]
    goals = [p["position_mm"] for g in others for p in g if p["kind"] == "PCB_VIA"]
    goals = sorted(goals, key=lambda p: math.dist(p, start))[:3]
    local_path = ROOT / "generated/u21-band-fanout-work/generated/local-escapes.json"
    local_data = json.loads(local_path.read_text())
    protected = []
    for net, points in local_data["local_crosscoupled_wires"]:
        protected.extend((net, p, q) for p, q in zip(points, points[1:]))

    def protected_local(g):
        if g["kind"] != "line" or g["layers"] != (5,):
            return False
        return any(
            g["net"] == net
            and (
                (math.dist(g["start"], p) < 1e-6 and math.dist(g["end"], q) < 1e-6)
                or (math.dist(g["start"], q) < 1e-6 and math.dist(g["end"], p) < 1e-6)
            )
            for net, p, q in protected
        )

    candidates = []
    for kind in ("segment", "via"):
        for n in children(tree, kind):
            net = names[str(first(n, "net")[1])]
            if net not in ORDINARY:
                continue
            g = dict(
                kind="line" if kind == "segment" else "via", net=net, uuid=str(first(n, "uuid")[1]), node=n
            )
            if kind == "segment":
                g.update(
                    layers=(LAYERS.index(str(first(n, "layer")[1])),),
                    start=[float(v) - 100 for v in first(n, "start")[1:]],
                    end=[float(v) - 100 for v in first(n, "end")[1:]],
                    width=float(first(n, "width")[1]),
                )
            else:
                g.update(
                    layers=tuple(range(6)),
                    xy=[float(v) - 100 for v in first(n, "at")[1:]],
                    radius=float(first(n, "size")[1]) / 2,
                )
            if not protected_local(g):
                candidates.append(g)
    router = Router(tree)
    router.geometry = [
        g
        for g in router.geometry
        if not (g["kind"] in ("line", "via") and g["net"] in ORDINARY and not protected_local(g))
    ]
    attempts, solutions = [], []
    for target in goals:
        for layer in (1, 4, 2, 5):
            try:
                points, visited = path_between(
                    router,
                    start,
                    target,
                    layer,
                    filled,
                    pads,
                    margin=4,
                    step=0.025,
                    net="ALL_RAILS_ALLOW",
                )
            except AssertionError as error:
                attempts.append(dict(target=target, layer=layer, failure=str(error)))
                continue
            ripped = [
                r
                for r in candidates
                if layer in r["layers"]
                and any(
                    (segment_distance(p, q, r["start"], r["end"]) < 0.2 + 0.1 + r["width"] / 2 + 1e-6)
                    if r["kind"] == "line"
                    else (point_segment(r["xy"], p, q) < 0.2 + 0.1 + r["radius"] + 1e-6)
                    for p, q in zip(points, points[1:])
                )
            ]
            nets = sorted({r["net"] for r in ripped})
            attempt = dict(
                target=target,
                layer=layer,
                points_mm=points,
                visited=visited,
                affected_nets=nets,
                removed_segment_count=len(ripped),
            )
            attempts.append(attempt)
            if len(nets) <= 4 and len(ripped) <= 30 and sum(r["kind"] == "via" for r in ripped) <= 3:
                solutions.append(
                    (
                        len(nets),
                        len(ripped),
                        sum(math.dist(p, q) for p, q in zip(points, points[1:])),
                        attempt,
                        ripped,
                    )
                )
    if not solutions:
        out = SOURCE / "generated/ordinary-via-ripup-rejected.json"
        assert not out.exists()
        out.write_text(
            json.dumps(dict(source_pcb_sha256=digest, attempts=attempts, qualified=False), indent=2) + "\n"
        )
        raise AssertionError("No bounded ordinary trace-only solution; source preserved")
    _, _, _, selected, ripped = min(solutions, key=lambda x: x[:3])
    removed = [r["node"] for r in ripped]
    tree[:] = [n for n in tree if n not in removed]
    actual = Router(tree)
    actual.path("ALL_RAILS_ALLOW", selected["layer"], selected["points_mm"], 0.2)
    added = []
    for i, n in enumerate(tree):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:ordinaryripup:{digest}:{i}:{sexpr(n)}"))),
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
    (WORK / source.name).write_text(sexpr(tree) + "\n")
    (WORK / "generated/ordinary-via-ripup.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=digest,
                filled_pcb_sha256=hashlib.sha256(filled_path.read_bytes()).hexdigest(),
                actual_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(),
                pad_geometry_sha256=hashlib.sha256(pads_path.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                explicit_ordinary_trace_allowlist=sorted(ORDINARY),
                actual_source_and_target_barrels=[start, selected["target"]],
                attempts=attempts,
                selected=selected,
                removed_actual_segments=[
                    dict(uuid=r["uuid"], net=r["net"], literal=sexpr(r["node"])) for r in ripped
                ],
                added_actual_copper=added,
                no_pad_rule_footprint_force_or_reference_primitive_changes=True,
                retained_local_latch_links=protected,
                local_latch_geometry_source_sha256=hashlib.sha256(local_path.read_bytes()).hexdigest(),
                native_all_affected_connectivity_and_PDN_pending=True,
                qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    assert source.read_bytes() == original
    print("Selected", selected["layer"], selected["affected_nets"], len(ripped), flush=True)


if __name__ == "__main__":
    main()
