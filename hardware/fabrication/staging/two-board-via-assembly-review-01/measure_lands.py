"""Measure through-via drill proximity to surface-mount lands using KiCad 10."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import pcbnew as k


def cell_range(low, high, size):
    return range(low // size, high // size + 1)


def screen(board_path):
    board = k.LoadBoard(str(board_path))
    cell = k.FromMM(5)
    pads = defaultdict(list)
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetDrillSize().x or pad.GetDrillSize().y:
                continue
            for layer, paste in ((k.F_Cu, k.F_Paste), (k.B_Cu, k.B_Paste)):
                if not pad.IsOnLayer(layer):
                    continue
                geometry = k.SHAPE_POLY_SET()
                pad.TransformShapeToPolygon(
                    geometry, layer, 0, k.FromMM(0.001), k.ERROR_OUTSIDE
                )
                geometry.Simplify()
                bounds = geometry.BBox()
                label = (
                    footprint.GetReference(),
                    pad.GetNumber(),
                    pad.m_Uuid.AsString(),
                    board.GetLayerName(layer),
                    pad.IsOnLayer(paste),
                )
                for x in cell_range(bounds.GetLeft(), bounds.GetRight(), cell):
                    for y in cell_range(bounds.GetTop(), bounds.GetBottom(), cell):
                        pads[x, y].append((label, geometry))

    via_sizes = Counter()
    entries = []
    for via in board.GetTracks():
        if via.GetClass() != "PCB_VIA":
            continue
        assert (
            via.GetViaType() == k.VIATYPE_THROUGH
        ), "Blind/buried vias require a layer-span check"
        pos = via.GetPosition()
        drill = via.GetDrillValue()
        diameters = [via.GetWidth(l) for l in board.GetEnabledLayers().CuStack()]
        via_sizes[(drill, min(diameters))] += 1
        radius = drill // 2
        window = radius + k.FromMM(0.1)
        found = {}
        for x in cell_range(pos.x - window, pos.x + window, cell):
            for y in cell_range(pos.y - window, pos.y + window, cell):
                for label, geometry in pads[x, y]:
                    if label in found:
                        continue
                    found[label] = geometry.Distance(pos) - radius
        near = [
            dict(
                ref=ref,
                pin=pin,
                pad_uuid=uid,
                layer=layer,
                pad_has_paste_layer=paste,
                drill_edge_gap_mm=k.ToMM(gap),
            )
            for (ref, pin, uid, layer, paste), gap in sorted(found.items())
            if gap < k.FromMM(0.1)
        ]
        if near:
            entries.append(
                dict(
                    via_uuid=via.m_Uuid.AsString(),
                    net=via.GetNetname(),
                    xy_mm=[k.ToMM(pos.x), k.ToMM(pos.y)],
                    drill_mm=k.ToMM(drill),
                    lands=near,
                )
            )
    entries.sort(key=lambda v: v["via_uuid"])
    overlaps = [
        v for v in entries if any(p["drill_edge_gap_mm"] < 0 for p in v["lands"])
    ]
    return dict(
        board=board_path.name,
        sha256=hashlib.sha256(board_path.read_bytes()).hexdigest(),
        kicad_version=k.GetMajorMinorPatchVersion(),
        copper_layers=board.GetCopperLayerCount(),
        nominal_thickness_mm=k.ToMM(board.GetDesignSettings().GetBoardThickness()),
        through_vias=sum(via_sizes.values()),
        via_geometry=[
            dict(
                drill_mm=k.ToMM(drill),
                minimum_land_diameter_mm=k.ToMM(land),
                nominal_annular_ring_mm=k.ToMM(land - drill) / 2,
                count=count,
            )
            for (drill, land), count in sorted(via_sizes.items())
        ],
        vias_with_drill_edge_within_0p1mm_of_smd_land=len(entries),
        vias_intersecting_smd_land=len(overlaps),
        vias_intersecting_paste_target_land=sum(
            any(
                p["drill_edge_gap_mm"] < 0 and p["pad_has_paste_layer"]
                for p in v["lands"]
            )
            for v in overlaps
        ),
        polygon_approximation_mm=0.001,
        contacts=entries,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = screen(args.board)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            name: value
            for name, value in result.items()
            if name not in ("contacts", "via_geometry")
        },
        flush=True,
    )
