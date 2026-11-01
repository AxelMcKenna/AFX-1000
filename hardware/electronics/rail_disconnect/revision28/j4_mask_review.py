"""Native pad/graphic plus actual Gerber proof of the private ground aperture.

This verifies drawn openings, not solder flow, registration, wetting, assembly
yield, contact resistance or physical fit. No source PCB is written.
"""

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import pcbnew

from hardware.qualification.boards.freerouting_bridge import copper

from ...common.sexpr import children, read_sexpr


def flashes_and_arcs(path):
    text = path.read_text()
    assert "%MOMM*%" in text and "%FSLAX46Y46*%" in text
    assert "%TF.FilePolarity,Negative*%" in text
    apertures = {int(i): float(d) for i, d in re.findall(r"%ADD(\d+)C,([\d.]+)\*%", text)}
    component, active, mode, previous = None, None, None, None
    flashes, arcs = [], []
    for line in text.splitlines():
        if line.startswith("%TO.C,"):
            component = line[len("%TO.C,") : -2]
        elif line == "%TD*%":
            component = None
        elif re.fullmatch(r"D\d+\*", line):
            active = int(line[1:-1])
        elif line in ("G01*", "G02*", "G03*"):
            mode = line[:3]
        elif component == "J4":
            m = re.fullmatch(r"X(-?\d+)Y(-?\d+)(?:I(-?\d+)J(-?\d+))?D(01|02|03)\*", line)
            if not m:
                continue
            x, y = int(m[1]) / 1e6, int(m[2]) / 1e6
            if m[5] == "03":
                flashes.append(dict(center=[x, y], diameter_mm=apertures[active]))
            elif m[5] == "01":
                assert mode == "G02" and previous is not None and m[3] is not None
                i, j = int(m[3]) / 1e6, int(m[4]) / 1e6
                radius = math.hypot(i, j)
                arcs.append(
                    dict(
                        center=[previous[0] + i, previous[1] + j],
                        start=list(previous),
                        end=[x, y],
                        path_radius_mm=radius,
                        aperture_diameter_mm=apertures[active],
                        outer_diameter_mm=2 * radius + apertures[active],
                        inner_diameter_mm=max(0, 2 * radius - apertures[active]),
                    )
                )
            previous = (x, y)
    return dict(flashes=flashes, arcs=arcs, gerber_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main(before, workspace):
    before, workspace = Path(before), Path(workspace)
    after = workspace / "rail_disconnect.kicad_pcb"
    old, new = pcbnew.LoadBoard(str(before)), pcbnew.LoadBoard(str(after))
    assert copper(old, pcbnew) == copper(new, pcbnew)

    def fp(tree):
        return next(
            f
            for f in children(tree, "footprint")
            if any(p[1] == "Reference" and p[2] == "J4" for p in children(f, "property"))
        )

    oldfp, newfp = fp(read_sexpr(before.read_text())), fp(read_sexpr(after.read_text()))

    def p1(f):
        return next(p for p in children(f, "pad") if p[1] == "1")

    assert p1(oldfp) == p1(newfp), "Positive pad/mask must stay literally identical"
    f = next(f for f in new.GetFootprints() if f.GetReference() == "J4")
    pads = {p.GetNumber(): p for p in f.Pads()}
    old_j4 = next(f for f in old.GetFootprints() if f.GetReference() == "J4")
    old_ground = next(p for p in old_j4.Pads() if p.GetNumber() == "2")
    assert pads["2"].GetSize() == old_ground.GetSize()
    assert pads["2"].GetDrillSize() == old_ground.GetDrillSize()
    assert pads["2"].GetShape() == old_ground.GetShape()
    assert pads["2"].GetAttribute() == old_ground.GetAttribute()
    assert pads["2"].GetNetname() == old_ground.GetNetname()
    assert pads["2"].GetPosition().x == old_ground.GetPosition().x
    assert pads["2"].GetPosition().y == old_ground.GetPosition().y + 3000000
    assert pads["1"].GetLayerSet().Contains(pcbnew.F_Mask) and pads["1"].GetLayerSet().Contains(pcbnew.B_Mask)
    assert pads["2"].GetLayerSet().Contains(pcbnew.F_Mask) and not pads["2"].GetLayerSet().Contains(
        pcbnew.B_Mask
    )
    assert all(p.GetSolderMaskExpansion(pcbnew.F_Mask) == 0 for p in pads.values())
    graphics = [g for g in f.GraphicalItems() if g.GetLayer() == pcbnew.B_Mask]
    assert len(graphics) == 1
    graphic = graphics[0]
    assert graphic.IsSolidFill() and graphic.GetWidth() == 0 and graphic.GetRadius() == 1300000
    assert graphic.GetStart() == pads["2"].GetPosition()
    plot = workspace / "generated/mask-gerbers"
    front = flashes_and_arcs(plot / "rail_disconnect-F_Mask.gts")
    back = flashes_and_arcs(plot / "rail_disconnect-B_Mask.gbs")
    targets = {n: [p.GetPosition().x / 1e6, -p.GetPosition().y / 1e6] for n, p in pads.items()}
    assert front["arcs"] == [] and len(front["flashes"]) == 2
    assert sorted((r["center"], r["diameter_mm"]) for r in front["flashes"]) == sorted(
        (p, 4.2) for p in targets.values()
    )
    assert back["flashes"] == [dict(center=targets["1"], diameter_mm=4.2)]
    assert len(back["arcs"]) == 2
    for arc in back["arcs"]:
        assert arc["center"] == targets["2"]
        assert abs(arc["outer_diameter_mm"] - 2.6) < 1e-12 and arc["inner_diameter_mm"] == 0
        assert abs(arc["path_radius_mm"] - 0.65) < 1e-12
    assert (
        back["arcs"][0]["start"] == back["arcs"][1]["end"]
        and back["arcs"][0]["end"] == back["arcs"][1]["start"]
    )
    report = dict(
        source_pcb_sha256=hashlib.sha256(before.read_bytes()).hexdigest(),
        candidate_pcb_sha256=hashlib.sha256(after.read_bytes()).hexdigest(),
        reviewer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        unchanged_all_native_tracks_vias_and_positive_pad=True,
        native_ground_F_mask_only_plus_separate_B_mask_circle=True,
        actual_front_mask_j4=front,
        actual_back_mask_j4=back,
        ground_back_opening_nominal_mm=2.6,
        positive_front_back_openings_nominal_mm=4.2,
        ground_front_opening_nominal_mm=4.2,
        full_native_all_mask_DRC_is_separate_required_evidence=True,
        mask_registration_edge_tolerance_and_fillets_accepted=False,
        fabricator_assembler_acceptance=False,
        joint_resistance_verified=False,
        physical_qualified=False,
    )
    (workspace / "generated/native-mask-and-gerber-review.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print("Native and actual Gerber ground aperture2.6mm verified; physical/process acceptance FALSE")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("before")
    p.add_argument("workspace")
    args = p.parse_args()
    main(args.before, args.workspace)
