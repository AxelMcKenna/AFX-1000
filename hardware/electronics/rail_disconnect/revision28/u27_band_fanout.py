"""Real local U27/C72 fanout in the independently screened logic band."""

import copy
import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .repair import Router
from .u23_band_route_2d import path_between

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u27-band-placement-work"
WORK = ROOT / "generated/u27-band-fanout-work"


def main():
    assert not WORK.exists()
    for name in ("numeric-MCAD-screen.json", "numeric-mesh-screen.json"):
        report = json.loads((SOURCE / "generated" / name).read_text())
        assert all(
            hashlib.sha256((ROOT.parents[3] / p).read_bytes()).hexdigest() == h
            for p, h in report["source_sha256"].items()
        )
    assert report["captured_mesh_screen_clear"]
    original = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    source_sha = hashlib.sha256(original).hexdigest()
    tree = read_sexpr(original.decode())
    net_ids = {str(n[2]).lstrip("/"): str(n[1]) for n in children(tree, "net")}
    removed = []
    added = []

    def ident(kind, payload):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:U27band:{source_sha}:{kind}:{payload}"))

    def segment(net, one, two, width=0.2, layer="B.Cu"):
        if math.dist(one, two) < 1e-8:
            return
        uid = ident("segment", (net, one, two, width, layer))
        node = read_sexpr(
            f'(segment (start {one[0] + 100:.6f} {one[1] + 100:.6f}) (end {two[0] + 100:.6f} {two[1] + 100:.6f}) (width {width}) (layer "{layer}") (net {net_ids[net]}) (uuid {uid}))'
        )
        tree.append(node)
        added.append(sexpr(node))

    def via(net, xy):
        uid = ident("via", (net, xy))
        node = read_sexpr(
            f'(via (at {xy[0] + 100:.6f} {xy[1] + 100:.6f}) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net {net_ids[net]}) (uuid {uid}))'
        )
        tree.append(node)
        added.append(sexpr(node))

    router = Router(tree)

    def pad(ref, pin):
        found = [p for p in router.by_ref[ref] if p["pin"] == str(pin)]
        assert len(found) == 1
        return found[0]

    fanout = {
        1: 92.5,
        2: 91.5,
        3: 92.5,
        4: 91.5,
        5: 92.5,
        6: 91.5,
        8: 101.5,
        9: 102.5,
        11: 102.5,
        12: 101.5,
        13: 102.5,
    }
    anchors = []
    for pin, x in fanout.items():
        p = pad("U27", pin)
        xy = (x, p["xy"][1])
        segment(p["net"], p["xy"], xy)
        via(p["net"], xy)
        anchors.append(dict(ref="U27", pin=str(pin), net=p["net"], via_xy_mm=xy))
    segment("E28_SOURCE_READY_LOGIC", pad("U27", 5)["xy"], pad("U27", 10)["xy"])
    g = pad("U27", 7)["xy"]
    segment("AGND", g, (92.5, g[1]), 0.3)
    via("AGND", (92.5, g[1]))
    cap_g = pad("C72", 2)["xy"]
    segment("AGND", cap_g, (101.25, cap_g[1]), 0.3)
    via("AGND", (101.25, cap_g[1]))
    segment("V2V5_AUX", pad("U27", 14)["xy"], pad("C72", 1)["xy"], 0.3)
    zones = []
    for layer in ("In1.Cu", "In4.Cu"):
        candidates = [
            z
            for z in children(tree, "zone")
            if children(z, "net_name")
            and str(first(z, "net_name")[1]).lstrip("/") == "AGND"
            and first(z, "layer")[1] == layer
            and not children(z, "keepout")
        ]
        assert candidates
        zone = copy.deepcopy(candidates[0])
        zone[:] = [
            n for n in zone if not (isinstance(n, list) and n and n[0] in ("filled_polygon", "fill_segments"))
        ]
        first(zone, "uuid")[1] = a(ident("zone", layer))
        first(zone, "min_thickness")[1] = a(".2")
        first(zone, "priority")[1] = a("0")
        polygon = first(zone, "polygon")
        polygon[:] = read_sexpr(
            "(polygon (pts (xy 190 144) (xy 203.75 144) (xy 203.75 153.875) (xy 190 153.875)))"
        )
        tree.append(zone)
        zones.append(sexpr(zone))
    # This feed is actual B.Cu, from an existing connected AUX bypass pad.
    # No foreign B.Cu filled zone overlaps this local surface corridor.
    router = Router(tree)
    source = next(p for p in router.by_ref["C71"] if p["pin"] == "1")
    target = next(p for p in router.by_ref["C72"] if p["pin"] == "1")
    assert source["net"] == target["net"] == "V2V5_AUX"
    points, visited = path_between(
        router, source["xy"], target["xy"], 5, margin=2, step=0.025, net="V2V5_AUX"
    )
    for one, two in zip(points, points[1:]):
        segment("V2V5_AUX", one, two, 0.2)
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
    result = dict(
        source_pcb_sha256=source_sha,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        removed_source_copper=[sexpr(n) for n in removed],
        no_other_old_copper_removed_or_moved=True,
        new_copper=added,
        added_AGND_zones=zones,
        local_control_fanout=anchors,
        actual_bypass_feed=dict(source="C71.1", target="C72.1", points_mm=points, visited_cells=visited),
        all_original_power_zone_contracts_unchanged=True,
        actual_circuit_parts_values_and_ports_unchanged=True,
        J8_proposal_not_adopted=True,
        native_global_reconnection_and_PDN_MCAD_required=True,
        qualified=False,
    )
    (WORK / "generated/local-fanout.json").write_text(json.dumps(result, indent=2) + "\n")
    assert (SOURCE / "rail_disconnect.kicad_pcb").read_bytes() == original
    print("Local real fanout complete; global reconnections and native checks pending", flush=True)


if __name__ == "__main__":
    main()
