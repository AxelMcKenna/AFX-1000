"""Independent exact-faceted floor-port vertical projection sensitivity.

Not a minimum flow throat, pressure model or installed cooling result: air can
turn under elevated components. Empty projection does not establish airflow.
"""

import json
import math
from pathlib import Path

from .capture import ROOT, sha, write


def build():
    import cadquery as cq

    out = ROOT / "generated/floor-port-projection.json"
    if out.exists():
        raise RuntimeError("New output required")
    source = ROOT / "tail_shape/model.json"
    d = json.loads(source.read_text())

    def poly(points):
        return cq.Workplane("XY").polyline(points).close().extrude(1).val()

    def disk(x, y, r, n):
        return poly(
            [(x + r * math.cos(i * 2 * math.pi / n), y + r * math.sin(i * 2 * math.pi / n)) for i in range(n)]
        )

    def rounded(x, y, w, h, r):
        points = []
        for cx, cy, start in [
            (x + r, y + r, 180),
            (x + w - r, y + r, 270),
            (x + w - r, y + h - r, 0),
            (x + r, y + h - r, 90),
        ]:
            points += [
                (
                    cx + r * math.cos(math.radians(start + i * 90 / 24)),
                    cy + r * math.sin(math.radians(start + i * 90 / 24)),
                )
                for i in range(25)
            ]
        return poly(points)

    def rect(x, y, w, h):
        return cq.Solid.makeBox(w, h, 1, cq.Vector(x, y, 0))

    ports = (
        rounded(38, 164, 72, 19, 1)
        .cut(disk(93.0871, 168.9352, 6, 256))
        .fuse(rounded(231.5, 154, 45, 29, 1))
        .clean()
    )
    assert ports.isValid()
    rows = d["boxes"] + d["tails"] + d["mates"]
    for b in d["boards"]:
        x, y, z = b["origin"]
        rows.append([b["id"] + "_FR4", x, y, z, b["size"][0], 1.76, b["size"][1]])

    def project(selected):
        hits = []
        for b in selected:
            if b[1] + b[4] < 38 or b[1] > 276.5 or b[2] + b[5] < 154 or b[2] > 183:
                continue
            h = rect(b[1], b[2], b[4], b[5]).intersect(ports)
            if not h.isNull() and h.Volume() > 1e-10:
                hits.append(h)
        assert hits
        return hits[0].fuse(*hits[1:]).clean()

    nf = project([r for r in rows if r[0].startswith("NF265_")])
    fpc = project([r for r in rows if r[0].startswith("FPC91_")])
    trill = rect(82, 158, 53.848, 21.844).intersect(ports)
    strain = rect(230, 167.5, 35, 8.2)
    for u in [61, 90]:
        strain = strain.fuse(rect(172 + u - 3.05, 175.5, 6.1, 5))
        strain = strain.fuse(rect(172 + u - 2.5, 181.94, 5, 2.39))
        strain = strain.fuse(disk(172 + u, 171.5, 2.5, 128))
    strain = strain.intersect(ports).clean()
    combined = nf.fuse(fpc).fuse(trill).fuse(strain).clean()
    assert all(s.isValid() for s in [nf, fpc, trill, strain, combined])
    cq.exporters.export(ports, str(ROOT / "generated/floor-port-profile.step"))
    cq.exporters.export(combined, str(ROOT / "generated/receiving-shadow.step"))
    write(
        out,
        dict(
            authored_net_port_area_mm2=ports.Volume(),
            NF265_receiving_projection_mm2=nf.Volume(),
            FPC91_receiving_projection_mm2=fpc.Volume(),
            retained_Trill_board_projection_mm2=trill.Volume(),
            NC265_strain_receiving_projection_mm2=strain.Volume(),
            combined_union_projection_mm2=combined.Volume(),
            vertical_uncovered_projection_sensitivity_mm2=ports.Volume() - combined.Volume(),
            actual_new_electrical_parts=356,
            scope="newNF/FPCcourtyard+mate+tailreceivers/FR4,actualNC265strainreceivers,andretainedTrillPCBprojection; oldmounts/otheroldunitparts notsubtracted",
            minimum_flow_throat_established=False,
            airflow_or_pressure_qualified=False,
            installed_cooling_qualified=False,
            physical_qualified=False,
            notes=[
                "Actual96facetroundedcorners/256facetedR6island; primaryactualAP03source bound.",
                "Projection sensitivity only: elevated bodies allow lateral turns; no flow pass/fail.",
                "All selected package/process/mate/trim/strain requirements remain unaccepted.",
                "No complete localconnectorfanout/remoteharness obstruction claimed.",
            ],
            source_sha256={
                str(p): sha(p)
                for p in [
                    Path(__file__),
                    source,
                    ROOT
                    / "context/hardware/cad/a12/enclosure_growth/unified_airpath/generated/unified-context_v6.scad",
                    ROOT
                    / "inputs/hardware/qualification/boards/nf_connector_receiving265/mechanical-v2/geometry.scad",
                ]
            },
        ),
    )
    print(out.read_text())


if __name__ == "__main__":
    build()
