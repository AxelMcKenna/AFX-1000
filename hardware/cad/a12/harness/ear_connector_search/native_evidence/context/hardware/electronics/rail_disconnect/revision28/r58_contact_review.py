"""Read-only native R58 pad/barrel containment for the isolated−0.2mm move."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import pcbnew

from hardware.qualification.boards.freerouting_bridge import copper


def review(before, after):
    old = pcbnew.LoadBoard(str(before))
    new = pcbnew.LoadBoard(str(after))
    assert copper(old, pcbnew) == copper(new, pcbnew), (
        "Any routing or via change is forbidden in this proposal"
    )
    originals = {fp.GetReference(): fp for fp in old.GetFootprints()}
    candidates = {fp.GetReference(): fp for fp in new.GetFootprints()}
    assert set(originals) == set(candidates)
    moved = []
    for ref, a in originals.items():
        b = candidates[ref]
        assert a.GetValue() == b.GetValue() and a.GetLayer() == b.GetLayer()
        assert a.GetOrientationDegrees() == b.GetOrientationDegrees()
        if a.GetPosition() != b.GetPosition():
            moved.append(ref)
    assert moved == ["R58"]
    a, b = originals["R58"].GetPosition(), candidates["R58"].GetPosition()
    assert b.x == a.x and b.y == a.y - pcbnew.FromMM(0.2)
    rows = []
    original_pads = {p.GetNumber(): p for p in originals["R58"].Pads()}
    for pad in candidates["R58"].Pads():
        previous = original_pads[pad.GetNumber()]
        assert pad.GetNetname() == previous.GetNetname() and pad.GetSize() == previous.GetSize()
        assert pad.GetPosition().x == previous.GetPosition().x
        assert pad.GetPosition().y == previous.GetPosition().y - pcbnew.FromMM(0.2)
        matches = [
            v
            for v in new.GetTracks()
            if isinstance(v, pcbnew.PCB_VIA)
            and v.GetNetname() == pad.GetNetname()
            and v.GetPosition() == previous.GetPosition()
        ]
        assert len(matches) == 1, "Require the actual unchanged old pad-centred barrel"
        via = matches[0]
        radius = via.GetWidth(pcbnew.F_Cu) / 2 + pcbnew.FromMM(0.001)
        disk = pcbnew.SHAPE_POLY_SET()
        disk.NewOutline()
        for i in range(128):
            angle = 2 * math.pi * i / 128
            r = radius / math.cos(math.pi / 128)
            point = via.GetPosition()
            disk.Append(round(point.x + r * math.cos(angle)), round(point.y + r * math.sin(angle)))
        land = pcbnew.SHAPE_POLY_SET()
        pad.TransformShapeToPolygon(land, pcbnew.F_Cu, 0, pcbnew.FromMM(0.001), pcbnew.ERROR_INSIDE)
        outside = pcbnew.SHAPE_POLY_SET()
        outside.BooleanSubtract(disk, land)
        assert outside.Area() == 0, "Complete via outer land plus1um guard must remain in the new native pad"
        rows.append(
            dict(
                pin=pad.GetNumber(),
                net=pad.GetNetname(),
                via_uuid=via.m_Uuid.AsString(),
                unchanged_barrel_center_mm=[via.GetPosition().x / 1e6, via.GetPosition().y / 1e6],
                new_native_pad_center_mm=[pad.GetPosition().x / 1e6, pad.GetPosition().y / 1e6],
                full_outer_barrel_land_plus_001mm_contained_in_native_pad=True,
                copper_outside_pad_mm2=outside.Area() / 1e12,
            )
        )
    return dict(
        source_sha256=hashlib.sha256(before.read_bytes()).hexdigest(),
        candidate_sha256=hashlib.sha256(after.read_bytes()).hexdigest(),
        native_version=pcbnew.Version(),
        reviewer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        only_moved_reference="R58",
        delta_board_y_mm=-0.2,
        all_actual_copper_tracks_vias_and_holes_unchanged=True,
        j4_and_all_other_poses_unchanged=True,
        contacts=rows,
        connected_trace_repair_necessary=False,
        trace_repair_count=0,
        solder_mask_paste_process_and_wire_assembly_accepted=False,
        physical_qualified=False,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("before", type=Path)
    p.add_argument("after", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    x = review(a.before, a.after)
    a.output.write_text(json.dumps(x, indent=2) + "\n")
    print(x)
