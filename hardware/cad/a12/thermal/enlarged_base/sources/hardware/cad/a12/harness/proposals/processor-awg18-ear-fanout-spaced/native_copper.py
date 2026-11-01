"""Native integer all-Cu exclusion proof for H9's complete metal contact disk.

KiCad's generic pad keepout also rejects the empty own NPTH. The rule permits
pad objects, while this independent proof checks actual cached pad/track/via
shapes and native filled copper on ALL four layers. No soldermask credit.
"""

import hashlib
import json
import math
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def circle(x, y, r):
    p = pcbnew.SHAPE_POLY_SET()
    p.NewOutline()
    rad = r / math.cos(math.pi / 64)
    for i in range(64):
        p.Append(
            pcbnew.FromMM(x + rad * math.cos(i * 2 * math.pi / 64)),
            pcbnew.FromMM(y + rad * math.sin(i * 2 * math.pi / 64)),
        )
    p.Simplify()
    return p


def intersection(a, b):
    p = pcbnew.SHAPE_POLY_SET()
    p.BooleanIntersection(a, b)
    return p.Area() / 1e12


def union_fills(board, net, layer):
    p = pcbnew.SHAPE_POLY_SET()
    for z in board.Zones():
        if not z.GetIsRuleArea() and z.IsOnLayer(layer) and z.GetNetname().lstrip("/") == net:
            p.BooleanAdd(z.GetFilledPolysList(layer))
    return p


def run():
    path = ROOT / "generated/filled.kicad_pcb"
    parent = ROOT.parent / "processor-awg18-ear-fanout/generated/filled.kicad_pcb"
    b = pcbnew.LoadBoard(str(path))
    old = pcbnew.LoadBoard(str(parent))
    assert b.GetCopperLayerCount() == 4
    h9 = next(fp for fp in b.GetFootprints() if fp.GetReference() == "H9")
    pos = h9.GetPosition()
    assert pos.x == pcbnew.FromMM(252) and pos.y == pcbnew.FromMM(150.2)
    protect = circle(252, 150.2, 3.8)
    inside = intersection(protect, circle(252, 150.2, 0.5))
    outside = intersection(protect, circle(260, 150.2, 0.5))
    assert inside > 0.78 and outside == 0
    rows = []
    loss = []
    excluded = []
    for name in LAYERS:
        layer = b.GetLayerID(name)
        area = 0
        checked = 0
        for fp in b.GetFootprints():
            for pad in fp.Pads():
                if not pad.IsOnLayer(layer):
                    continue
                if fp.GetReference() == "H9":
                    assert pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH and not pad.GetNetname()
                    assert (
                        pad.GetSize().x
                        == pad.GetSize().y
                        == pad.GetDrillSize().x
                        == pad.GetDrillSize().y
                        == pcbnew.FromMM(2.4)
                    )
                    excluded.append(
                        dict(
                            layer=name,
                            ref="H9",
                            reason="Actual empty NPTH bore; size equals drill, no copper annulus/net",
                        )
                    )
                    continue
                poly = pcbnew.SHAPE_POLY_SET()
                pad.TransformShapeToPolygon(poly, layer, 0, pcbnew.FromMM(0.001), pcbnew.ERROR_OUTSIDE)
                a = intersection(protect, poly)
                assert a <= 1e-8, (name, fp.GetReference(), pad.GetNumber(), a)
                area += a
                checked += 1
        track_area = 0
        for track in b.GetTracks():
            if not track.IsOnLayer(layer):
                continue
            poly = pcbnew.SHAPE_POLY_SET()
            track.TransformShapeToPolygon(poly, layer, 0, pcbnew.FromMM(0.001), pcbnew.ERROR_OUTSIDE)
            a = intersection(protect, poly)
            assert a <= 1e-8, (name, "track/via", a)
            track_area += a
        fill_area = 0
        for z in b.Zones():
            if z.GetIsRuleArea() or not z.IsOnLayer(layer):
                continue
            a = intersection(protect, z.GetFilledPolysList(layer))
            assert a <= 1e-8, (name, "filled copper", z.GetNetname(), a)
            fill_area += a
        rows.append(
            dict(
                layer=name,
                checked_actual_pad_shapes=checked,
                pad_intersection_mm2=area,
                track_via_intersection_mm2=track_area,
                filled_copper_intersection_mm2=fill_area,
            )
        )
        for net in ["5V_DIG", "AGND"]:
            before, after = union_fills(old, net, layer), union_fills(b, net, layer)
            lost = pcbnew.SHAPE_POLY_SET()
            lost.BooleanSubtract(before, after)
            gained = pcbnew.SHAPE_POLY_SET()
            gained.BooleanSubtract(after, before)
            loss.append(
                dict(
                    layer=name,
                    net=net,
                    parent_area_mm2=before.Area() / 1e12,
                    candidate_area_mm2=after.Area() / 1e12,
                    lost_area_mm2=lost.Area() / 1e12,
                    gained_area_mm2=gained.Area() / 1e12,
                )
            )
    report = dict(
        method=__doc__,
        source_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
        actual_filled_pcb_sha256=sha(path),
        parent_actual_filled_pcb_sha256=sha(parent),
        native_version=pcbnew.GetBuildVersion(),
        source_code_sha256=sha(Path(__file__)),
        protected_full_disk_centre_native_mm=[252, 150.2],
        protected_minimum_radius_mm=3.8,
        circumscribed64_polygon_area_mm2=protect.Area() / 1e12,
        inside_positive_control_area_mm2=inside,
        outside_negative_control_area_mm2=outside,
        rows=rows,
        only_excluded_empty_NPTH_pad=excluded,
        actual_all_four_layer_copper_clear=True,
        loss_of_actual_filled_copper=loss,
        no_soldermask_insulation_credit=True,
        area_change_is_not_resistance_or_ampacity_proof=True,
        parent_PDN_inheritance_allowed=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (ROOT / "generated/native-metal-clearance.json").write_text(json.dumps(report, indent=2) + "\n")
    print("All4layers copper clear", [(r["layer"], r["filled_copper_intersection_mm2"]) for r in rows])
    print("Lostfilltotal", sum(r["lost_area_mm2"] for r in loss))


if __name__ == "__main__":
    run()
