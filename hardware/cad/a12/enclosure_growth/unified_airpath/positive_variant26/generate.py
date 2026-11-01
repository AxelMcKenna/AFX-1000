"""Separate orthogonal machined positive-link candidate; no operating-port edits."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]
OUT = ROOT / "generated"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load():
    return json.loads((ROOT / "design.json").read_text())


def direction(a, b):
    delta = [b[i] - a[i] for i in range(3)]
    axes = [i for i, v in enumerate(delta) if abs(v) > 1e-7]
    assert len(axes) == 1, (a, b, "Candidate paths use orthogonal segments")
    return axes[0]


def shape(d, name, maximum=False, wrap=0):
    import cadquery as cq

    p = d["paths"][name]["points"]
    w = d["bar"]["width_range"][1] if maximum else d["bar"]["width"]
    t = d["bar"]["thickness_range"][1] if maximum else d["bar"]["thickness"]
    land = d["bar"]["landing_range"][1] if maximum else d["bar"]["landing_diameter"]
    solids = []
    for index, (a, b) in enumerate(zip(p, p[1:])):
        axis = direction(a, b)
        if axis == 0:
            solids.append(
                cq.Solid.makeBox(
                    abs(b[0] - a[0]) + 2 * wrap,
                    w + 2 * wrap,
                    t + 2 * wrap,
                    cq.Vector(min(a[0], b[0]) - wrap, a[1] - w / 2 - wrap, a[2] - wrap),
                )
            )
        elif axis == 1:
            solids.append(
                cq.Solid.makeBox(
                    w + 2 * wrap,
                    abs(b[1] - a[1]) + 2 * wrap,
                    t + 2 * wrap,
                    cq.Vector(a[0] - w / 2 - wrap, min(a[1], b[1]) - wrap, a[2] - wrap),
                )
            )
        else:
            neighbor = direction(p[index - 1], a) if index else direction(b, p[index + 2])
            assert neighbor in (0, 1)
            dims = [t + 2 * wrap, w + 2 * wrap] if neighbor == 0 else [w + 2 * wrap, t + 2 * wrap]
            solids.append(
                cq.Solid.makeBox(
                    *dims,
                    abs(b[2] - a[2]) + t + 2 * wrap,
                    cq.Vector(a[0] - dims[0] / 2, a[1] - dims[1] / 2, min(a[2], b[2]) - wrap),
                )
            )
    for index, q in enumerate(p):
        if index in (0, len(p) - 1):
            disk = cq.Solid.makeCylinder(land / 2 + wrap, t + 2 * wrap, cq.Vector(q[0], q[1], q[2] - wrap))
            if name == "DIG" and index == 0:
                flat = d["cap"]["dig_e28_copper_flat_plus_x"] + wrap
                disk = disk.cut(cq.Solid.makeBox(20, 30, 20, cq.Vector(q[0] + flat, q[1] - 15, q[2] - 5)))
            solids.append(disk)
        elif direction(p[index - 1], q) in (0, 1) and direction(q, p[index + 1]) in (0, 1):
            solids.append(
                cq.Solid.makeCylinder(w / 2 + wrap, t + 2 * wrap, cq.Vector(q[0], q[1], q[2] - wrap))
            )
    result = solids[0].fuse(*solids[1:]).clean()
    for q in (p[0], p[-1]):
        hole = d["bar"]["hole_range"][0] if maximum else d["bar"]["hole_diameter"]
        result = result.cut(
            cq.Solid.makeCylinder(hole / 2, max(t + 2 * wrap + 2, 8), cq.Vector(q[0], q[1], q[2] - wrap - 1))
        )
    assert result.isValid() and len(result.Solids()) == 1
    return result


def fasteners(d, name, end, maximum=False):
    import cadquery as cq

    q = d["paths"][name]["points"][0 if end == 0 else -1]
    h = d["terminal_hardware"]
    t = d["bar"]["thickness_range"][1] if maximum else d["bar"]["thickness"]
    z = q[2] + t + h["washer_thickness"]
    tip = q[2] + 1.0 + 0.45 - 8.2 if maximum else z - h["length"]
    screw = cq.Solid.makeCylinder(h["shaft_diameter_envelope"] / 2, z - tip, cq.Vector(q[0], q[1], tip)).fuse(
        cq.Solid.makeCylinder(
            h["head_diameter_envelope"] / 2, h["head_height_envelope"], cq.Vector(q[0], q[1], z)
        )
    )
    washer = cq.Solid.makeCylinder(
        h["washer_od_envelope"] / 2, h["washer_thickness"], cq.Vector(q[0], q[1], q[2] + t)
    ).cut(cq.Solid.makeCylinder(1.6, h["washer_thickness"] + 0.02, cq.Vector(q[0], q[1], q[2] + t - 0.01)))
    return screw.fuse(washer).clean()


def main():
    import cadquery as cq

    from .caps import pieces as cap_pieces
    from .support import parts as support_parts

    d = load()
    OUT.mkdir(exist_ok=True)
    report = {}
    assembly = []
    for name in d["paths"]:
        cu = shape(d, name)
        covered = shape(d, name, maximum=True, wrap=d["insulation"]["maximum_build_each_face_allocation_mm"])
        # Remove the wrapped-region envelope at bare landing faces. Actual
        # terminal caps provide insulation around those intentional contacts.
        for q in (d["paths"][name]["points"][0], d["paths"][name]["points"][-1]):
            covered = covered.cut(cq.Solid.makeCylinder(5.3, 8, cq.Vector(q[0], q[1], q[2] - 2)))
        envelope = covered.fuse(
            *[cap_pieces(d, name, i, True)["ENVELOPE"] for i in (0, 1)]
            + [fasteners(d, name, i, True) for i in (0, 1)]
        ).clean()
        assert len(envelope.Solids()) == 1, "Insulation envelope must continuously reach terminal caps"
        cap_parts = [
            (name + "-CAP" + str(i) + "-" + k, v) for i in (0, 1) for k, v in cap_pieces(d, name, i).items()
        ]
        for label, obj in (
            [(name + "-CU", cu), (name + "-COVERED-ENVELOPE", envelope)]
            + cap_parts
            + [(name + "-FASTENER" + str(i), fasteners(d, name, i)) for i in (0, 1)]
        ):
            assert obj.isValid()
            cq.exporters.export(obj, str(OUT / (label + ".step")))
            cq.exporters.export(obj, str(OUT / (label + ".stl")), tolerance=0.01, angularTolerance=0.05)
            report[label] = dict(volume_mm3=obj.Volume(), solid_count=len(obj.Solids()), valid=obj.isValid())
        assembly.extend([cu] + [v for k, v in cap_parts] + [fasteners(d, name, i) for i in (0, 1)])
    supports = support_parts(d)
    for label, obj in supports.items():
        cq.exporters.export(obj, str(OUT / (label + ".step")))
        cq.exporters.export(obj, str(OUT / (label + ".stl")), tolerance=0.01)
        report[label] = dict(volume_mm3=obj.Volume(), solid_count=len(obj.Solids()), valid=obj.isValid())
    support_bounds = (
        list(support_parts(d, True).values())
        + list(support_parts(d, True, film_override=0).values())
        + list(supports.values())
    )
    support_envelope = support_bounds[0].fuse(*support_bounds[1:]).clean()
    cq.exporters.export(support_envelope, str(OUT / "SUPPORT-ENVELOPE.stl"), tolerance=0.01)
    cq.exporters.export(support_envelope, str(OUT / "SUPPORT-ENVELOPE.step"))
    assembly += list(supports.values())
    cq.exporters.export(cq.Compound.makeCompound(assembly), str(OUT / "positive-links.step"))
    cq.exporters.export(cq.Compound.makeCompound(assembly), str(OUT / "positive-links.stl"), tolerance=0.01)
    minimum = (d["bar"]["width_range"][0] * d["bar"]["thickness_range"][0]) - 4 * d["bar"][
        "maximum_edge_break"
    ] ** 2
    neck = (d["bar"]["landing_range"][0] - d["bar"]["hole_range"][1]) * d["bar"]["thickness_range"][
        0
    ] - 4 * d["bar"]["maximum_edge_break"] ** 2
    report["analytical_bulk_minimum_mm2"] = minimum
    report["analytical_neck_minimum_mm2"] = neck
    report["normal_corner_sections_independently_checked"] = False
    report["source_sha256"] = {
        q.name: sha(q)
        for q in [ROOT / "design.json", ROOT / "generate.py", ROOT / "caps.py", ROOT / "support.py"]
    }
    report["physical_qualified"] = False
    (OUT / "geometry.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
