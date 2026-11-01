"""Physical local escapes for unchanged U21/C66 in the added routing band."""

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
SOURCE = ROOT / "generated/u21-master-via-placement-work"
WORK = ROOT / "generated/u21-band-fanout-work"


def main():
    assert not WORK.exists()
    for name in ("numeric-MCAD-screen.json", "numeric-mesh-screen.json"):
        report = json.loads((SOURCE / "generated" / name).read_text())
        assert all(
            hashlib.sha256((ROOT.parents[3] / p).read_bytes()).hexdigest() == h
            for p, h in report["source_sha256"].items()
        )
    assert report["captured_mesh_screen_clear"]
    source = SOURCE / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    tree = read_sexpr(original.decode())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    replace_nets = {"E28_ARM_BAR", "E28_FAULT_BAR", "E28_ARMED", "E28_FAULT_SET"}
    expected = {
        "E28_ARM_BAR": {("U21", "1"), ("U21", "6")},
        "E28_FAULT_BAR": {("U21", "10"), ("U21", "12")},
        "E28_ARMED": {("U21", "3"), ("U21", "4"), ("U25", "9")},
        "E28_FAULT_SET": {("U21", "8"), ("U25", "8")},
    }
    parts = json.loads((SOURCE / "components.json").read_text())
    for net in replace_nets:
        assert {
            (p["ref"], str(q["number"])) for p in parts for q in p["pins"] if q["net"] == net
        } == expected[net]
    old = [
        n
        for kind in ("segment", "via")
        for n in children(tree, kind)
        if names[str(first(n, "net")[1])] in replace_nets
    ]
    removed_ordinary = [sexpr(n) for n in old]
    tree[:] = [n for n in tree if n not in old]
    router = Router(tree)
    routes = []

    def xy(pin):
        return next(p["xy"] for p in router.by_ref["U21"] if p["pin"] == str(pin))

    locals = [
        ("E28_ARM_BAR", [xy(1), (26.5, 49.95), (26.5, 46.7), xy(6)]),
        ("E28_ARMED", [xy(3), (25.8, 48.65), (25.8, 48), xy(4)]),
        ("E28_FAULT", [xy(9), (28.5, 46.7), (28.5, 49.3), xy(13)]),
        ("E28_FAULT_BAR", [xy(10), (29.2, 47.35), (29.2, 48.65), xy(12)]),
    ]
    for net, points in locals:
        assert all(legal_line(router, net, 5, p, q, 0.2) for p, q in zip(points, points[1:])), (net, points)
        router.path(net, 5, points, 0.2)
    stems = []
    for i in (2, 3, 5, 7, 8, 9, 11, 14):
        pad = next(p for p in router.by_ref["U21"] if p["pin"] == str(i))
        point = (pad["xy"][0] + (-1.5 if i <= 7 else 1.5), pad["xy"][1])
        if i == 8:
            point = (28, 46.05)
        elif i == 9:
            point = (28.5, 46.7)
        assert legal_line(router, pad["net"], 5, pad["xy"], point, 0.2)
        router.path(pad["net"], 5, [pad["xy"], point], 0.2)
        stems.append(dict(pad, xy=point))
    # Reserve all neighboring pin stems BEFORE choosing drills. This prevents
    # one early greedy via from caging the later real package terminals.
    order = ["8", "9", "11", "14", "2", "3", "5", "7"]
    for p in sorted(stems, key=lambda p: order.index(p["pin"])):
        result, reason = escape(router, p, maxdistance=4, step=0.025)
        assert result is not None, (p["pin"], reason)
        routes.append(dict(ref="U21", pin=p["pin"], net=p["net"], **result))
    c1 = next(p for p in router.by_ref["C66"] if p["pin"] == "1")
    p14 = next(p for p in router.by_ref["U21"] if p["pin"] == "14")
    assert legal_line(router, "V2V5_AUX", 5, c1["xy"], p14["xy"], 0.2)
    router.path("V2V5_AUX", 5, [c1["xy"], p14["xy"]], 0.2)
    c2 = next(p for p in router.by_ref["C66"] if p["pin"] == "2")
    result, reason = escape(router, c2, maxdistance=2, step=0.025)
    assert result is not None, reason
    routes.append(dict(ref="C66", pin="2", net="AGND", **result))
    zones = []
    for layer in ("In1.Cu", "In4.Cu"):
        template = next(
            z
            for z in children(tree, "zone")
            if children(z, "net_name")
            and str(first(z, "net_name")[1]).lstrip("/") == "AGND"
            and first(z, "layer")[1] == layer
        )
        z = copy.deepcopy(template)
        z[:] = [
            n for n in z if not (isinstance(n, list) and n and n[0] in ("filled_polygon", "fill_segments"))
        ]
        first(z, "uuid")[1] = a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:U21ground:{digest}:{layer}")))
        first(z, "priority")[1] = a("0")
        first(z, "min_thickness")[1] = a(".2")
        first(z, "polygon")[:] = read_sexpr(
            "(polygon (pts (xy 120.5 144) (xy 133.75 144) (xy 133.75 153.875) (xy 120.5 153.875)))"
        )
        tree.append(z)
        zones.append(sexpr(z))
    added = []
    for i, n in enumerate(tree):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:U21local:{digest}:{i}:{sexpr(n)}"))),
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
    (WORK / "generated/local-escapes.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=digest,
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                actual_pad_escapes=routes,
                added_copper=added,
                added_ground_zones=zones,
                removed_four_declared_ordinary_control_nets=removed_ordinary,
                actual_unchanged_semantic_terminal_sets={k: sorted(v) for k, v in expected.items()},
                local_crosscoupled_wires=locals,
                all_other_original_copper_preserved=True,
                no_foreign_force_fill_in_new_drill_region=True,
                all_native_and_PDN_required=True,
                qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    assert source.read_bytes() == original
    print("U21 physical escapes written; native checks required", flush=True)


if __name__ == "__main__":
    main()
