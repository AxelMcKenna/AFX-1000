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
    intended = {r[k]: kind for r in routes for k, kind in (
        ("segment", "segment"), ("zone", "zone"), ("new_ground_via", "via")
    )}
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
    new_zones = {(r["zone"], "In6.Cu") for r in routes}
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
    layer = after.GetLayerID("In6.Cu")
    for route in routes:
        trace = tracks[route["segment"]]
        assert trace.GetLayer() == pcbnew.B_Cu and trace.GetNetname() == route["net"]
        assert trace.GetWidth() == pcbnew.FromMM(route["width_mm"])
        field = fields[route["zone"], "In6.Cu"]
        assert field.OutlineCount() == 1 and zones[route["zone"]].GetNetname() == "LINK_AGND"
        pad = pads[route["through_pad"]]
        assert pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and pad.GetNetname() == trace.GetNetname()
        inner, outer = route["verified_ground_ring_beyond_pad_mm"]
        clearance = expanded_pad(pad, layer, inner)
        uncovered = copper(trace, trace.GetLayer())
        uncovered.BooleanSubtract(field)
        uncovered.BooleanSubtract(clearance)
        assert uncovered.Area() == 0, "Ground reference interrupted outside the plated-pad clearance"
        ring = expanded_pad(pad, layer, outer)
        ring.BooleanSubtract(clearance)
        ring.BooleanSubtract(field)
        assert ring.Area() == 0, "Incomplete ground ring at plated pad"
        ground = pads[route["ground_anchor"]]
        assert ground.GetNetname() == "LINK_AGND"
        connected = {o.m_Uuid.AsString() for o in after.GetConnectivity().GetConnectedItems(ground)}
        for uid in (route["new_ground_via"], route["existing_ground_via"]):
            via = tracks[uid]
            assert via.GetClass() == "PCB_VIA" and uid in connected
            overlap = copper(via, layer)
            overlap.BooleanIntersection(field)
            assert overlap.Area() > 0.01 * 1e12
        via = tracks[route["new_ground_via"]]
        assert via.GetDrillValue() == pcbnew.FromMM(0.30) and via.GetWidth(layer) == pcbnew.FromMM(0.60)
        assert via.TopLayer() == pcbnew.F_Cu and via.BottomLayer() == pcbnew.B_Cu
    return expected[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent", type=Path)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    print(f"Verified output returns with {verify(args.parent, args.project)} open connections")
