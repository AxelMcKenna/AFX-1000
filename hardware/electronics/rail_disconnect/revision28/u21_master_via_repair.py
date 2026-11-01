"""Move one ordinary control barrel and its two stems away from new U21 lands."""

import hashlib
import json
import math
import shutil
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.validation import make_valid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..revision26.layout import POWER_NETS

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u21-band-placement-work"
WORK = ROOT / "generated/u21-master-via-placement-work"
FILLED = ROOT / "generated/u25-fine-closure-work/generated/filled-u25-fine-closure1.kicad_pcb"
IDS = {
    "95e08454-b377-5adf-8f38-a8d8038e7cc5",
    "8d4645e2-5735-5600-8edf-f73eabe1cdd8",
    "1ab22b50-2a1d-5ff8-b6f9-03cedc1dd234",
}


def main():
    assert not WORK.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    tree = read_sexpr(original.decode())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    changes = []
    for kind in ("segment", "via"):
        for n in children(tree, kind):
            if str(first(n, "uuid")[1]) not in IDS:
                continue
            assert names[str(first(n, "net")[1])] == "E28_MASTER_ENABLE"
            before = sexpr(n)
            changed = 0
            for tag in ("at",) if kind == "via" else ("start", "end"):
                point = first(n, tag)
                if tuple(map(float, point[1:])) == (130.8, 145.5):
                    point[1:] = [a("132.2"), a("145.8")]
                    changed += 1
            assert changed == 1
            changes.append(dict(before=before, after=sexpr(n)))
    assert len(changes) == 3
    filled = read_sexpr(FILLED.read_text())
    radius_guard = 1 / math.cos(math.pi / 1024)
    envelopes = {
        layer: Point(32.2, 45.8).buffer(0.5 * radius_guard, resolution=256)
        for layer in ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")
    }
    for layer, endpoints in (
        ("In4.Cu", [(32.2, 45.8), (30, 44.7)]),
        ("B.Cu", [(31.6, 46.3), (32.2, 45.8)]),
    ):
        envelopes[layer] = envelopes[layer].union(
            LineString(endpoints).buffer(0.3 * radius_guard, resolution=256)
        )
    hits, invalid = [], []
    for z in children(filled, "zone"):
        if not children(z, "net"):
            continue
        net = str(first(z, "net")[-1]).lstrip("/")
        if net not in POWER_NETS:
            continue
        for poly in children(z, "filled_polygon"):
            layer = str(first(poly, "layer")[1])
            g = Polygon([(float(q[1]) - 100, float(q[2]) - 100) for q in first(poly, "pts")[1:]])
            if not g.is_valid:
                invalid.append(dict(net=net, layer=layer))
                g = make_valid(g)
            hit = envelopes[layer].intersection(g)
            if not hit.is_empty:
                hits.append(dict(net=net, layer=layer, area_mm2=hit.area))
    assert not hits, hits
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
    (WORK / "generated/master-via-repair.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(original).hexdigest(),
                filled_reference_sha256=hashlib.sha256(FILLED.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                actual_three_object_delta=changes,
                conservative_drill_annulus_and_new_trace_clearance_envelopes_force_hits=hits,
                invalid_input_rings_normalized_for_geometric_query=invalid,
                all_other_objects_and_semantic_nets_preserved=True,
                native_and_PDN_required=True,
                qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    assert source.read_bytes() == original


if __name__ == "__main__":
    main()
