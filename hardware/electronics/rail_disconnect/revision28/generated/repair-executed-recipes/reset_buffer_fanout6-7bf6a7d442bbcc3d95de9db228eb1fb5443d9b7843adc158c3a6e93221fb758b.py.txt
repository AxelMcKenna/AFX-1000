"""Actual255-part cell escapes and preserved terminal stems; ordinary copper only."""

import copy
import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .band_local_escape import escape
from .focused import legal_line
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/reset-triple-ready-placement4-work"
WORK = ROOT / "generated/reset-triple-ready-fanout6-work"


def main():
    assert not WORK.exists()
    original = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    tree = read_sexpr(original.decode())
    digest = hashlib.sha256(original).hexdigest()
    nets = {str(n[2]).lstrip("/"): str(n[1]) for n in children(tree, "net")}
    old = read_sexpr((ROOT / "generated/timeout-pullup-placement-work/rail_disconnect.kicad_pcb").read_text())
    # Reuse only the exact tested two-track+barrel dense package escapes,
    # retargeted to their actual new raw/positive nets, no legacy long stubs.
    groups = [
        (
            "E28_TIMEOUT_RAW",
            [
                "b5b33545-5033-55fd-bea2-eb86ec9b1267",
                "921c6385-1239-5f67-aad0-41fd60a6d8e2",
                "8de0050c-31ee-54ee-a0f6-a979e54c4dda",
            ],
        ),
        (
            "E28_AUX_RESET_N",
            [
                "dedf7b69-6537-5c91-977e-eb5af7f14021",
                "91d7e727-d6f7-5278-a494-6ee4b72ad68a",
                "a894f6fd-db7e-57bb-94d2-9f744bad7f54",
            ],
        ),
        ("POS_OUTPUT_READY", ["6c7e4ba4-8831-5fc6-978d-df215a05b5db"]),
    ]
    # U27's preserved B stem ends at92.5,48.15; restore its original through barrel.
    uv = next(
        n
        for n in children(old, "via")
        if tuple(map(float, first(n, "at")[1:])) == (192.5, 148.15) and str(first(n, "net")[1]) == "174"
    )
    groups[-1][1].append(str(first(uv, "uuid")[1]))
    reused = []
    for net, ids in groups:
        for ident in ids:
            n = copy.deepcopy(
                next(
                    n
                    for n in old
                    if isinstance(n, list)
                    and n
                    and n[0] in ("segment", "via")
                    and str(first(n, "uuid")[1]) == ident
                )
            )
            first(n, "net")[1] = a(nets[net])
            tree.append(n)
            reused.append(dict(new_net=net, literal=sexpr(n)))
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    parts = json.loads((SOURCE / "components.json").read_text())
    assert {(c["ref"], p["number"]) for c in parts for p in c["pins"] if p["net"] == "E28_NOT_RUN"} == {
        ("U23", "1"),
        ("U28", "2"),
        ("U28", "9"),
    }
    removed = [
        n
        for n in tree
        if isinstance(n, list)
        and n
        and n[0] in ("segment", "via")
        and names[str(first(n, "net")[1])]
        in {"E28_NOT_RUN", "E28_OUTPUT_PERMISSION", "E28_SAFE_STAGE", "E28_RESET", "E28_SAFE_REQUEST"}
    ]
    # Two ordinary horizontal cages intersect the formerlyunusedU25.6 escape.
    cages = []
    for n in children(tree, "segment"):
        net = names[str(first(n, "net")[1])]
        start = tuple(round(float(v) - 100, 6) for v in first(n, "start")[1:])
        end = tuple(round(float(v) - 100, 6) for v in first(n, "end")[1:])
        if (net == "E28_ARMED" and {start, end} == {(36.3, 46.6), (40.9, 46.6)}) or (
            net == "POWER_RUN" and {start, end} == {(53.2, 46.6), (34.8, 46.6)}
        ):
            cages.append(n)
    assert len(cages) == 2
    removed.extend(cages)
    tree[:] = [n for n in tree if n not in removed]
    rt = Router(tree)
    routes = []
    # Alternate inner/outer escape vias; all eight real0.5pitch lands remain intact.
    points = {
        1: (101.45, 50.25),
        2: (103.35, 49.75),
        3: (101.45, 49.25),
        4: (103.35, 48.75),
        5: (104.65, 48.75),
        6: (106.6, 49.25),
        7: (104.65, 49.75),
        8: (106.6, 50.25),
    }
    for n, end in points.items():
        p = next(p for p in rt.by_ref["U35"] if p["pin"] == str(n))
        path = [p["xy"], end] if n not in (1, 2, 7, 8) else [p["xy"], (end[0], p["xy"][1]), end]
        path = [q for i, q in enumerate(path) if not i or q != path[i - 1]]
        assert all(legal_line(rt, p["net"], 5, a, b, 0.2) for a, b in zip(path, path[1:])), ("stem", n)
        rt.path(p["net"], 5, path, 0.2)
    for n in (1, 2, 3, 4, 5, 6, 7, 8):
        p = next(p for p in rt.by_ref["U35"] if p["pin"] == str(n))
        p = dict(p, xy=points[n])
        r, reason = escape(rt, p, maxdistance=0.05, step=0.025)
        assert r, (n, reason)
        routes.append(dict(ref="U35", pin=n, net=p["net"], **r))
    for ref, pins in [
        ("C78", ("1", "2")),
        ("R143", ("1", "2")),
        ("R136", ("1", "2")),
        ("R135", ("1",)),
        ("U25", ("6", "4", "5")),
    ]:
        for num in pins:
            p = next(p for p in rt.by_ref[ref] if p["pin"] == num)
            if ref == "U25":
                paths = {
                    "6": [p["xy"], (39.7, 46.7), (40.3, 46.15), (40.45, 46.15)],
                    "4": [p["xy"], (40.0, 48.0), (40.0, 48.2)],
                    "5": [p["xy"], (39.8, 47.35)],
                }
                path = paths[num]
                assert all(legal_line(rt, p["net"], 5, a, b, 0.2) for a, b in zip(path, path[1:])), (
                    ref,
                    num,
                    "explicit path",
                )
                rt.path(p["net"], 5, path, 0.2)
                p = dict(p, xy=path[-1])
            r, reason = escape(rt, p, maxdistance=3, step=0.025)
            assert r, (ref, num, reason)
            routes.append(dict(ref=ref, pin=num, net=p["net"], **r))
    added = []
    for i, n in enumerate(tree):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(
                        str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL, f"rmx:E28:resettriplefanout:{digest}:{i}:{sexpr(n)}"
                            )
                        )
                    ),
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
    (WORK / "generated/local-escapes.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=digest,
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                preserved_tested_escapes=reused,
                removed_same_package_NOT_RUN_cage=[sexpr(n) for n in removed],
                actual_new_copper=added,
                routes=routes,
                qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(routes, indent=2), flush=True)


if __name__ == "__main__":
    main()
