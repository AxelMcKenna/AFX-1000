"""Verify the paired output traces, plated-pad clearances and ground stitches in KiCad."""

import argparse
import hashlib
import json
from pathlib import Path

import pcbnew

from hardware.cad.signal_completion.verify_reference_extension import copper
from hardware.electronics.common.sexpr import first, read_sexpr
from hardware.fabrication.verify_power_surface_refill import filled_polygons, pad_groups, same_filled_area


def expanded_pad(pad, layer, distance):
    polygon = pcbnew.SHAPE_POLY_SET()
    pad.TransformShapeToPolygon(
        polygon, layer, pcbnew.FromMM(distance), pcbnew.FromMM(0.001), pcbnew.ERROR_OUTSIDE
    )
    return polygon


def segment_ids(route):
    return route["segments"] if "segments" in route else [route["segment"]]


def check_return(route, board, tracks, pads, field, layer):
    if "ground_rings" in route:
        rings = route["ground_rings"]
    else:
        inner, outer = route["verified_ground_ring_beyond_pad_mm"]
        rings = [dict(pad=route["through_pad"], inner_mm=inner, outer_mm=outer)]
    clearances = pcbnew.SHAPE_POLY_SET()
    for ring in rings:
        pad = pads[ring["pad"]]
        assert pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and pad.GetNetname() == route["net"]
        clearances.BooleanAdd(expanded_pad(pad, layer, 0.21))
        inner = expanded_pad(pad, layer, ring["inner_mm"])
        outer = expanded_pad(pad, layer, ring["outer_mm"])
        if "neighbor_via" in ring:
            via = tracks[ring["neighbor_via"]]
            assert via.GetClass() == "PCB_VIA" and via.GetNetname() != pad.GetNetname()
            inner.BooleanAdd(expanded_pad(via, layer, ring["inner_mm"]))
            outer.BooleanAdd(expanded_pad(via, layer, ring["outer_mm"]))
        outer.BooleanSubtract(inner)
        outer.BooleanSubtract(field)
        assert outer.Area() == 0, "Incomplete ground ring around clearance opening"
    signal = board.GetLayerID(route.get("signal_layer", "B.Cu"))
    for uid in segment_ids(route):
        trace = tracks[uid]
        assert trace.GetLayer() == signal and trace.GetNetname() == route["net"]
        assert trace.GetWidth() == pcbnew.FromMM(route["width_mm"])
        gap = copper(trace, signal)
        gap.BooleanSubtract(field)
        gap.BooleanSubtract(clearances)
        assert gap.Area() == 0, "Ground reference interrupted outside a plated-pad clearance"


def verify(parent, project):
    name = "signal_main.kicad_pcb"
    report = json.loads((project / "native-review.json").read_text())
    routes = json.loads((project / "reference-review.json").read_text())["routes"]
    original, candidate = [(p / name).read_bytes() for p in (parent, project)]
    assert hashlib.sha256(original).hexdigest() == report["parent_sha256"]
    assert hashlib.sha256(candidate).hexdigest() == report["pcb_sha256"]
    prefix = original.rstrip()[:-1]
    assert candidate.startswith(prefix)
    added = read_sexpr("(" + candidate[len(prefix):].decode())
    intended = {}
    for route in routes:
        intended[route["zone"]] = "zone"
        intended[route["new_ground_via"]] = "via"
        intended.update(dict.fromkeys(segment_ids(route), "segment"))
    assert len(added) == len(intended)
    assert {first(node, "uuid")[1]: node[0] for node in added} == intended

    before, after = [pcbnew.LoadBoard(str((p / name).resolve())) for p in (parent, project)]
    pads = {f.GetReference() + ":" + p.GetNumber(): p for f in after.GetFootprints() for p in f.Pads()}
    count, original_groups = pad_groups(before)
    expected_groups = set(original_groups)
    for route in routes:
        assert all(pads[p].GetNetname() == route["net"] for p in route["pads"])
        joined = {
            next(g for g in expected_groups if pads[p].m_Uuid.AsString() in g) for p in route["pads"]
        }
        assert len(joined) == 2
        expected_groups.difference_update(joined)
        expected_groups.add(frozenset.union(*joined))
    assert count == report["baseline_opens"]
    expected = count - len(routes), expected_groups
    assert expected[0] == report["native_opens"] and pad_groups(after) == expected

    saved, saved_after = filled_polygons(before), filled_polygons(after)
    new_zones = {(r["zone"], r.get("reference_layer", "In6.Cu")) for r in routes}
    assert saved.keys() | new_zones == saved_after.keys()
    assert all(p.Format() == saved_after[key].Format() for key, p in saved.items())
    for board in (before, after):
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    assert pad_groups(before) == (count, original_groups) and pad_groups(after) == expected
    previous, fields = filled_polygons(before), filled_polygons(after)
    assert all(same_filled_area(p, fields[key]) for key, p in previous.items())
    assert all(same_filled_area(saved_after[key], fields[key]) for key in new_zones)
    tracks = {item.m_Uuid.AsString(): item for item in after.GetTracks()}
    zones = {item.m_Uuid.AsString(): item for item in after.Zones()}
    for route in routes:
        name = route.get("reference_layer", "In6.Cu")
        layer = after.GetLayerID(name)
        field = fields[route["zone"], name]
        assert field.OutlineCount() == 1 and zones[route["zone"]].GetNetname() == "LINK_AGND"
        check_return(route, after, tracks, pads, field, layer)
        ground = pads[route["ground_anchor"]]
        assert ground.GetNetname() == "LINK_AGND"
        connected = {o.m_Uuid.AsString() for o in after.GetConnectivity().GetConnectedItems(ground)}
        if "ground_pad" in route:
            contact = pads[route["ground_pad"]]
            assert contact.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
        else:
            contact = tracks[route["existing_ground_via"]]
            assert contact.GetClass() == "PCB_VIA"
        via = tracks[route["new_ground_via"]]
        assert via.GetClass() == "PCB_VIA"
        for item in (via, contact):
            assert item.GetNetname() == "LINK_AGND" and item.m_Uuid.AsString() in connected
            overlap = copper(item, layer)
            overlap.BooleanIntersection(field)
            assert overlap.Area() > 0.01 * 1e12
        assert via.GetDrillValue() == pcbnew.FromMM(0.30) and via.GetWidth(layer) == pcbnew.FromMM(0.60)
        assert via.TopLayer() == pcbnew.F_Cu and via.BottomLayer() == pcbnew.B_Cu
    return expected[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent", type=Path)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    print(f"Verified output returns with {verify(args.parent, args.project)} open connections")
