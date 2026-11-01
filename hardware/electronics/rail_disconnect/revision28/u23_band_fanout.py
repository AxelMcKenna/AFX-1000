"""Real local U23/C68 fanout in the independently screened logic band."""

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
SOURCE = ROOT / "generated/u23-band-placement-work"
WORK = ROOT / "generated/u23-band-fanout-work"


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
    internal = net_ids["E28_FAULT_A"]
    parts = json.loads((SOURCE / "components.json").read_text())
    assert {
        (p["ref"], str(pin["number"])) for p in parts for pin in p["pins"] if pin["net"] == "E28_FAULT_A"
    } == {("U23", "8"), ("U23", "12")}
    removed = [
        n
        for n in tree
        if isinstance(n, list) and n and n[0] in ("segment", "via") and str(first(n, "net")[1]) == internal
    ]
    locked = {
        r["uuid"]
        for r in json.loads((ROOT / "generated/leaf-prune-source-lock-contract.json").read_text())[
            "locked_copper"
        ]
    }
    assert not {str(first(n, "uuid")[1]) for n in removed} & locked
    tree[:] = [n for n in tree if n not in removed]
    added = []

    def ident(kind, payload):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:U23band:{source_sha}:{kind}:{payload}"))

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

    fanout = {1: 120.5, 2: 119.5, 3: 120.5, 5: 120.5, 6: 119.5, 9: 130.5, 10: 129.5, 11: 130.5, 13: 130.5}
    anchors = []
    for pin, x in fanout.items():
        p = pad("U23", pin)
        xy = (x, p["xy"][1])
        segment(p["net"], p["xy"], xy)
        via(p["net"], xy)
        anchors.append(dict(ref="U23", pin=str(pin), net=p["net"], via_xy_mm=xy))
    segment("E28_RESET", pad("U23", 3)["xy"], pad("U23", 4)["xy"])
    p8, p12 = pad("U23", 8)["xy"], pad("U23", 12)["xy"]
    for one, two in zip((p8, (126, p8[1]), (126, p12[1])), ((126, p8[1]), (126, p12[1]), p12)):
        segment("E28_FAULT_A", one, two)
    g = pad("U23", 7)["xy"]
    segment("AGND", g, (120.5, g[1]), 0.3)
    via("AGND", (120.5, g[1]))
    cap_g = pad("C68", 2)["xy"]
    segment("AGND", cap_g, (129.25, cap_g[1]), 0.3)
    via("AGND", (129.25, cap_g[1]))
    segment("V2V5_AUX", pad("U23", 14)["xy"], pad("C68", 1)["xy"], 0.3)
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
        polygon = first(zone, "polygon")
        polygon[:] = read_sexpr(
            "(polygon (pts (xy 218 144) (xy 234.75 144) (xy 234.75 153.875) (xy 218 153.875)))"
        )
        tree.append(zone)
        zones.append(sexpr(zone))
    # This feed is actual B.Cu, from an existing connected AUX bypass pad.
    # No foreign B.Cu filled zone overlaps this local surface corridor.
    router = Router(tree)
    source = next(p for p in router.by_ref["C73"] if p["pin"] == "1")
    target = next(p for p in router.by_ref["C68"] if p["pin"] == "1")
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
        removed_obsolete_U23_internal_FAULT_A_copper=[sexpr(n) for n in removed],
        no_other_old_copper_removed_or_moved=True,
        new_copper=added,
        added_AGND_zones=zones,
        local_control_fanout=anchors,
        actual_bypass_feed=dict(source="C73.1", target="C68.1", points_mm=points, visited_cells=visited),
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
