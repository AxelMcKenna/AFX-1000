"""Exact authored-port projection sensitivities, not a flow/pressure solution."""

import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.interior_airpath.polygon_contract import primitive_contracts

from .capture import ROOT, UA, sha


def build():
    import cadquery as cq

    target = ROOT / "generated/port-shadow.json"
    if target.exists():
        raise RuntimeError("New projection result required")
    data = json.loads((ROOT / "generated/model233.json").read_text())

    def polygon(points):
        return cq.Workplane("XY").polyline(points).close().extrude(1).val()

    def rounded(x, y, width, depth, radius):
        points = []
        for cx, cy, start in [
            (x + radius, y + radius, 180),
            (x + width - radius, y + radius, 270),
            (x + width - radius, y + depth - radius, 0),
            (x + radius, y + depth - radius, 90),
        ]:
            points += [
                (
                    cx + radius * math.cos(math.radians(start + i * 90 / 24)),
                    cy + radius * math.sin(math.radians(start + i * 90 / 24)),
                )
                for i in range(25)
            ]
        return polygon(points)

    island = polygon(
        [
            (93.0871 + 6 * math.cos(2 * math.pi * i / 256), 168.9352 + 6 * math.sin(2 * math.pi * i / 256))
            for i in range(256)
        ]
    )
    ports = rounded(38, 164, 72, 19, 1).cut(island).fuse(rounded(231.5, 154, 45, 29, 1)).clean()
    expected = primitive_contracts()["inlet_area_gauge"]["volume"] * 10
    assert ports.isValid() and abs(ports.Volume() - expected) < 1e-7

    def rectangle(x, y, width, depth):
        return cq.Solid.makeBox(width, depth, 1, cq.Vector(x, y, 0))

    def project(rows):
        hits = []
        for b in rows:
            if b[1] + b[4] < 38 or b[1] > 276.5 or b[2] + b[5] < 154 or b[2] > 183:
                continue
            hit = rectangle(b[1], b[2], b[4], b[5]).intersect(ports)
            if not hit.isNull() and hit.Volume() > 1e-9:
                hits.append(hit)
        if not hits:
            return None
        result = hits[0]
        for hit in hits[1:]:
            result = result.fuse(hit)
        return result.clean()

    rows = data["boxes"] + data["tails"] + data["mates"]
    for b in data["boards"]:
        x, y, z = b["origin"]
        width, height = b["size"]
        rows.append([b["id"] + "_FR4", x, y, z, width, 1.76, height])
    projections = {}
    for ident in ["NF233", "FPC84"]:
        p = project([b for b in rows if b[0].startswith(ident)])
        projections[ident] = p
    board_trill = rectangle(82, 158, 53.848, 21.844).intersect(ports)
    combined = projections["NF233"].fuse(projections["FPC84"]).fuse(board_trill).clean()
    bundles = project(data["prospective_straight_bundle_receivers"])
    plus_bundle = combined.fuse(bundles).clean()
    result = dict(
        authored_port_net_mm2=ports.Volume(),
        primary_profile_independent_agreement_mm2=abs(ports.Volume() - expected),
        NF233_receiving_body_projection_overlap_mm2=projections["NF233"].Volume(),
        FPC84_receiving_body_projection_overlap_mm2=projections["FPC84"].Volume(),
        retained_Trill_board_projection_overlap_mm2=board_trill.Volume(),
        combined_receiving_and_Trill_projection_overlap_mm2=combined.Volume(),
        port_area_outside_solid_receiver_projection_mm2=ports.Volume() - combined.Volume(),
        optional_fully_opaque_bundle_receiver_additional_overlap_mm2=plus_bundle.Volume() - combined.Volume(),
        optional_area_outside_all_receiver_projections_mm2=ports.Volume() - plus_bundle.Volume(),
        assumptions=[
            "Actual faceted AP03 port profiles; constant1mm extrusion computes planar area.",
            "All NF/FPC source courtyard prisms, board and complete rear1mm receiving envelopes projected onto inlet.",
            "TMR/WIMA/selected bodies plus explicit unaccepted package/mate limits remain conditional.",
            "Vertical projection is neither a flow solution nor proof that every projected region is physically impermeable.",
            "The10mm straight bundle box is allocated wiring space, not a solid object: fully opaque subtraction is a separate conservative sensitivity only.",
            "No installed flow, pressure coefficient or cooling qualification follows; no positive credit for0.7mm board-to-floor gap.",
        ],
        source_sha256={
            str(p): sha(p) for p in [Path(__file__), ROOT / "generated/model233.json", UA / "handoff.json"]
        },
        native_or_CFD_validation=False,
        physical_qualified=False,
        thermal_qualified=False,
    )
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k.endswith("mm2")}))


if __name__ == "__main__":
    build()
