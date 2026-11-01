"""Analytical pilot-hole BREP for the actual two PEEK prototype parts."""

import argparse
import hashlib
import json
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def box(a, b):
    return (
        cq.Workplane("XY").box(*(b[i] - a[i] for i in range(3)), centered=(False, False, False)).translate(a)
    )


def cylinder(p, r, h, d=(0, 0, 1)):
    return cq.Workplane(obj=cq.Solid.makeCylinder(r, h, cq.Vector(*p), cq.Vector(*d)))


def shapes():
    base = box((58, 17.5, 4.8), (93, 21, 13))
    for u in [61, 90]:
        base = base.union(cylinder((u, 21, 0), 3, 5))
    cap = box((58, 21, 5.3), (93, 24.5, 13))
    for u in [68, 73, 79, 84]:
        cut = cylinder((u, 21, 4.7), 0.825, 8.5)
        base = base.cut(cut)
        cap = cap.cut(cut)
    for u in [61, 90]:
        base = base.cut(cylinder((u, 21, -0.01), 0.8, 4.11))
        base = base.cut(cylinder((u, 21.01, 9), 0.8, 3.01, (0, -1, 0)))
        cap = cap.cut(cylinder((u, 24.6, 9), 1.3, 3.7, (0, -1, 0)))
    return dict(base=base, cap=cap)


def drawing(out):
    s = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1100" viewBox="0 0 1400 1100">',
        '<rect width="1400" height="1100" fill="white"/><style>text{font-family:sans-serif;fill:#142c3d;font-size:19px}.title{font-size:28px;font-weight:bold}.small{font-size:16px}.dim{stroke:#174e73;stroke-width:1;fill:none}</style>',
        '<text x="40" y="45" class="title">NC265 FORCE-PIGTAIL STRAIN PROTOTYPE — RECEIVING REQUIREMENTS</text>',
        '<text x="40" y="80">149×39 PCB • u→X172+u, v→Z3.5+v, normal w→Y180.5−w • dimensions mm</text>',
        '<text x="40" y="110">No full-unit fit, material, insulation compression, thread, pull, creep, torque or fabrication approval.</text>',
    ]

    def line(a, b):
        s.append(f'<path class="dim" d="M{a[0]},{a[1]}L{b[0]},{b[1]}"/>')

    scale = 24
    x0 = 80
    y0 = 160

    def xy(u, w):
        return x0 + (u - 58) * scale, y0 + (13 - w) * scale

    # Front normal/u view: actual lower bridge and two source-backed posts.
    x, y = xy(58, 13)
    s.append(f'<rect x="{x}" y="{y}" width="840" height="196.8" fill="#b9d4e5" stroke="#174e73"/>')
    for u in [61, 90]:
        x, y = xy(u - 3, 5)
        s.append(f'<rect x="{x}" y="{y}" width="144" height="120" fill="#b9d4e5" stroke="#174e73"/>')
        x, y = xy(u, 0)
        line((x, y), (x, y + 24))
        s.append(f'<text x="{x - 40}" y="{y + 48}">H{101 if u == 61 else 102}</text>')
    for u, label in zip([68, 73, 79, 84], ["J2.1", "J2.2", "J4.1", "J4.2"]):
        x, y = xy(u, 13)
        s.append(f'<rect x="{x - 19.8}" y="{y}" width="39.6" height="196.8" fill="white" stroke="#174e73"/>')
        s.append(f'<text x="{x - 25}" y="{y - 12}">{label}</text>')
    line((80, 500), (920, 500))
    s.append('<text x="440" y="525">35 overall u (58..93)</text>')
    s += [
        '<text x="980" y="175">Post OD6.0 nominal</text>',
        '<text x="980" y="205">OD6.1 receiving max</text>',
        '<text x="980" y="240">Post w0..5.0</text>',
        '<text x="980" y="270">Lower bridge w4.8..13</text>',
        '<text x="980" y="305">Cap w5.3..13</text>',
        '<text x="980" y="335">Post-to-cap gap0.3</text>',
        '<text x="980" y="370">Base v17.5..21</text>',
        '<text x="980" y="400">Cap v21..24.5</text>',
        '<text x="40" y="590" class="title">MATCHED WIRE / HARDWARE DATUMS</text>',
        '<text x="40" y="625">Channel centres u68,73,79,84 / v21. Prototype Ø1.65; match EACH measured wire to OD−0.05 trial.</text>',
        '<text x="40" y="655">Nominal wire Ø1.70; ±0.01 measurement / ±0.02 machining imply 0.02..0.08 diametric trial compression.</text>',
        '<text x="40" y="685">This is a bench starting point. MPPE damage/grip/creep/hot pull and allowed load profile remain unknown.</text>',
        '<text x="40" y="725">PCB anchors (61,21)/(90,21): NPTH nominalØ2.6 / finished MINØ2.5; all6Cu layers R3.7 exclusion.</text>',
        '<text x="40" y="755">Force holes: nominalØ2.2 / finished MINØ2.1 / Ø3.8 land. Gauge Ø1.4 bare +0.3 centre +0.005 reserve.</text>',
        '<text x="40" y="795">Material: MCAM Ketron1000 natural unfilled PEEK. Datasheet properties are indicative, not guaranteed allowables.</text>',
        '<text x="40" y="825">Mount: Accu SPP-M2-5-A2 + HPW-M2-A2-BL. Cap: SPP-M2-6-A2 + same washer. M2×0.4 tapped PEEK.</text>',
        '<text x="40" y="855">Base tap pilotsØ1.6: mount depth4.1; cap depth3.0. STEP shows pilot holes; actual thread process unqualified.</text>',
        '<text x="40" y="885">Nominal thread overlaps3.05 /2.15. Incoming length±0.1 is a project requirement, not catalog guarantee.</text>',
        '<text x="40" y="925">Rear head+washer reaches w−3.83 max (worldY184.33); distinct from the 1.5 rear lead policy.</text>',
        '<text x="40" y="955">Cap head+washer maxv26.57 (worldZ30.07). Local post/solder clearance tested at maxOD6.1 +0.45 margin.</text>',
        '<text x="40" y="995">Whole PCB uses actual components/layout and supports separately. Solder joints are NOT strain anchors.</text>',
        '<text x="40" y="1045" class="small">Review drawing: module geometry.scad and pilot-hole STEP are authoritative candidate sources; no scale-from-screen manufacturing.</text>',
        "</svg>",
    ]
    (out / "NC265-strain-drawing.svg").write_text("\n".join(s) + "\n")


def run(out):
    if out.exists():
        raise RuntimeError("Fresh BREP output required")
    out.mkdir()
    records = {}
    for name, shape in shapes().items():
        solid = shape.val()
        solids = solid.Solids()
        if not solid.isValid() or len(solids) != 1 or solid.Volume() <= 0:
            raise ValueError("Invalid analytical part")
        p = out / ("NC265-" + name + "-pilot.step")
        cq.exporters.export(shape, str(p))
        b = solid.BoundingBox()
        records[name] = dict(
            file=str(p),
            sha256=sha(p),
            volume_mm3=solid.Volume(),
            solids=len(solids),
            valid=solid.isValid(),
            bounds_mm=[[b.xmin, b.ymin, b.zmin], [b.xmax, b.ymax, b.zmax]],
            thread_form_is_NOT_modeled=True,
        )
    drawing(out)
    sources = [
        Path(__file__),
        ROOT / "ports-v2.json",
        ROOT / "mechanical-v2/geometry.scad",
        ROOT / "mechanical-v2/datums.json",
    ]
    (out / "BREP.json").write_text(
        json.dumps(
            dict(
                CadQuery_version=cq.__version__,
                parts=records,
                source_sha256={str(p): sha(p) for p in sources},
                analytical_cylinders_and_planes=True,
                physical_qualified=False,
                fabrication_released=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(dict(parts=len(records), valid_single_solids=True, CadQuery=cq.__version__)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output.resolve())
