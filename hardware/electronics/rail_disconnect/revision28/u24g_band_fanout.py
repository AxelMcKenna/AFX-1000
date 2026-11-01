"""Physical local escapes for unchanged U24/C69 in the added routing band."""

import copy
import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..routing.check import point_segment
from .focused import legal_line
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u24g-band-placement-work"
WORK = ROOT / "generated/u24g-band-fanout-work"


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
    router = Router(tree)
    routes = []

    def via(net, point):
        conflicts = []
        for g in router.geometry:
            same = g["net"] == net
            if same and (g["kind"] in ("line", "rect") or g.get("through")):
                continue
            if g["kind"] == "line":
                distance = point_segment(point, g["start"], g["end"]) - g["width"] / 2
                need = 0.52
            elif g["kind"] == "via":
                distance = math.dist(point, g["xy"]) - g["radius"]
                need = 0.26 if same else 0.52
            else:
                distance = math.hypot(
                    *[max(abs(point[i] - g["xy"][i]) - g["size"][i] / 2, 0) for i in (0, 1)]
                )
                need = 0.52
            if distance < need - 1e-8:
                conflicts.append(dict(shape=g, distance=distance, requirement=need))
        assert not conflicts, (net, point, conflicts)
        router.via(net, point)

    for i in range(1, 15):
        pin = str(i)
        pad = next(p for p in router.by_ref["U24"] if p["pin"] == pin)
        x = (51 if i % 2 else 50) if i <= 7 else (60 if i % 2 == 0 else 61)
        point = (x, pad["xy"][1])
        points = [pad["xy"], point]
        if i == 6:
            point = (49, 47.3)
            points = [pad["xy"], (49, 46.7), point]
        elif i == 7:
            point = (49, 48.6)
            points = [pad["xy"], (48, 46.05), (48, 48.6), point]
        elif i == 8:
            point = (63.2, 48.2)
            points = [pad["xy"], (63.2, 46.05), point]
        elif i == 9:
            point = (61.5, 47.3)
            points = [pad["xy"], (61.5, 46.7), point]
        assert all(legal_line(router, pad["net"], 5, p, q, 0.2) for p, q in zip(points, points[1:])), (
            pin,
            points,
        )
        via(pad["net"], point)
        router.path(pad["net"], 5, points, 0.2)
        routes.append(dict(ref="U24", pin=pin, net=pad["net"], via=point))
    c1 = next(p for p in router.by_ref["C69"] if p["pin"] == "1")
    p14 = next(p for p in router.by_ref["U24"] if p["pin"] == "14")
    assert legal_line(router, "V2V5_AUX", 5, c1["xy"], p14["xy"], 0.2)
    router.path("V2V5_AUX", 5, [c1["xy"], p14["xy"]], 0.2)
    c2 = next(p for p in router.by_ref["C69"] if p["pin"] == "2")
    via("AGND", c2["xy"])
    routes.append(dict(ref="C69", pin="2", net="AGND", via=c2["xy"]))
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
        first(z, "uuid")[1] = a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:U24ground:{digest}:{layer}")))
        first(z, "priority")[1] = a("0")
        first(z, "min_thickness")[1] = a(".2")
        first(z, "polygon")[:] = read_sexpr(
            "(polygon (pts (xy 148.5 144) (xy 161.75 144) (xy 161.75 153.875) (xy 148.5 153.875)))"
        )
        tree.append(z)
        zones.append(sexpr(z))
    added = []
    for i, n in enumerate(tree):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:U24local:{digest}:{i}:{sexpr(n)}"))),
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
                all_original_copper_preserved=True,
                no_foreign_force_fill_in_new_drill_region=True,
                all_native_and_PDN_required=True,
                qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    assert source.read_bytes() == original
    print("U24 physical escapes written; native checks required", flush=True)


if __name__ == "__main__":
    main()
