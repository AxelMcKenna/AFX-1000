"""Native polygon subtraction of actually filled force-zone copper.

Run with KiCad Python. This does not certify resistance; it independently
detects force-pour material removed by a proposed signal-routing pass.
"""

import argparse
import hashlib
import json
from pathlib import Path

import pcbnew

FORCE_NETS = {
    "P19_SRC",
    "P19",
    "N19_SRC",
    "N19",
    "P12_SRC",
    "P12",
    "N12_SRC",
    "N12",
    "V5_REG_SRC",
    "V5_REG",
    "5V_DIG_SRC",
    "5V_DIG",
}
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")


def union(board, net, layer):
    result = pcbnew.SHAPE_POLY_SET()
    for zone in board.Zones():
        if zone.GetNetname().lstrip("/") == net and zone.IsOnLayer(layer) and not zone.GetIsRuleArea():
            result.BooleanAdd(zone.GetFilledPolysList(layer))
    return result


def compare(original, candidate):
    old, new = pcbnew.LoadBoard(str(original)), pcbnew.LoadBoard(str(candidate))
    rows = []
    for net in sorted(FORCE_NETS):
        for layername in LAYERS:
            layer = old.GetLayerID(layername)
            before, after = union(old, net, layer), union(new, net, layer)
            if before.Area() == after.Area() == 0:
                continue
            lost, gained = pcbnew.SHAPE_POLY_SET(), pcbnew.SHAPE_POLY_SET()
            lost.BooleanSubtract(before, after)
            gained.BooleanSubtract(after, before)
            control = pcbnew.SHAPE_POLY_SET()
            control.BooleanSubtract(before, before)
            rows.append(
                dict(
                    net=net,
                    layer=layername,
                    original_area_mm2=before.Area() / 1e12,
                    candidate_area_mm2=after.Area() / 1e12,
                    lost_area_mm2=lost.Area() / 1e12,
                    gained_area_mm2=gained.Area() / 1e12,
                    lost_polygon_count=lost.OutlineCount(),
                    self_subtraction_control_mm2=control.Area() / 1e12,
                )
            )
    return dict(
        method="KiCad native integer SHAPE_POLY_SET BooleanSubtract of unioned filled zones",
        original_filled_pcb_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
        candidate_filled_pcb_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
        rows=rows,
        no_force_pour_material_removed_above_clipping_control=all(
            r["lost_area_mm2"] <= r["self_subtraction_control_mm2"] + 1e-8 for r in rows
        ),
        numerical_area_reporting_allowance_above_self_control_mm2=1e-8,
        physical_qualified=False,
        resistance_upper_bound_qualified=False,
        limitations=[
            "Compares filled zone material only; actual pads, tracks, barrels, terminal contact and conductivity need separate checks.",
            "Expanded or unchanged area is not a resistance, ampacity, dynamic, thermal or fabrication qualification.",
            "Integer clipping can leave tiny residual polygons even in self subtraction; each source union has an explicit self-control.",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = compare(args.original, args.candidate)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        "Force-zone material removed above clipping control:",
        not result["no_force_pour_material_removed_above_clipping_control"],
    )
    print("Total lost area mm2:", sum(row["lost_area_mm2"] for row in result["rows"]))
