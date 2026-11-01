"""Separate offset ANA return-retainer prototype for the copied J4 ear.

Keeps the base screw/stem at its original inter-board location. The head and
cap move 4 mm along the actual copper ramp; a PEEK arm supports that head.
No installed return parts, board or case files are changed.
"""

import json
from pathlib import Path

from hardware.cad.a12.returns.generate import load, seat

from ..generate import REPO, sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "returns/generated"
OUT = ROOT / "proposals/j4-ear/retainer"


def build():
    import cadquery as cq

    OUT.mkdir(parents=True, exist_ok=True)
    d = load()
    cx, cy = d["retainers"]["locations"]["ANA"]
    assert [cx, cy] == [166, 133.125]
    delta_x = 4.0
    delta_z = seat(d, "ANA", cx + delta_x) - seat(d, "ANA", cx)
    source_parts = {
        n: SOURCE / ("AFX-A12-R01-ANA-" + n + ".step") for n in ["POST", "CAP", "CAP-SCREW0", "CAP-SCREW1"]
    }
    inputs = [
        Path(__file__),
        ROOT.parent / "returns/design.json",
        ROOT.parent / "returns/generate.py",
        *source_parts.values(),
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in inputs}

    def box(x, y, z, dx, dy, dz):
        return cq.Solid.makeBox(dx, dy, dz, cq.Vector(x, y, z))

    old_post = cq.importers.importStep(str(source_parts["POST"])).val()
    stem_top = d["retainers"]["stem_top_z"]
    # Preserve the actual machined lower stem and its blind M2 base bore.
    stem = old_post.intersect(box(cx - 10, cy - 10, 0, 20, 20, stem_top))
    stem = stem.fuse(cq.Solid.makeCylinder(1.5, 11 - stem_top, cq.Vector(cx, cy, stem_top)))
    head = old_post.intersect(box(cx - 10, cy - 10, stem_top, 20, 20, 30))
    head = head.translate((delta_x, 0, delta_z))
    # The raised underside clears the actual low P03 J103 probe reserve.
    head = head.intersect(box(cx - 10, cy - 10, 9.2, 30, 20, 30))
    arm = box(cx, cy - 1.5, 9.2, delta_x + 1, 3, 1.8)
    parts = {"POST": stem.fuse(arm, head).clean()}
    for name in ["CAP", "CAP-SCREW0", "CAP-SCREW1"]:
        parts[name] = cq.importers.importStep(str(source_parts[name])).val().translate((delta_x, 0, delta_z))
    result = {}
    for name, shape in parts.items():
        assert shape.isValid() and len(shape.Solids()) == 1, (name, "Invalid or disjoint part")
        step, stl = OUT / (name + ".step"), OUT / (name + ".stl")
        cq.exporters.export(shape, str(step))
        cq.exporters.export(shape, str(stl), tolerance=0.005, angularTolerance=0.04)
        back = cq.importers.importStep(str(step)).val()
        assert back.isValid() and abs(back.Volume() - shape.Volume()) < 1e-5
        b = shape.BoundingBox()
        result[name] = dict(
            volume_mm3=shape.Volume(),
            valid_single_solid=True,
            step_roundtrip=True,
            bbox_min_mm=[b.xmin, b.ymin, b.zmin],
            bbox_max_mm=[b.xmax, b.ymax, b.zmax],
        )
    scad = "module proposed_ana_retainer(){" + "".join('import("' + n + '.stl");' for n in parts) + "}\n"
    (OUT / "retainer.scad").write_text(scad)
    assert all(sha(REPO / n) == h for n, h in hashes.items()), "Retainer source changed"
    report = dict(
        scope="Isolated offset-head PEEK ANA retention prototype; no manufactured or structural qualification",
        source_sha256=hashes,
        parts=result,
        head_shift_mm=[delta_x, 0, delta_z],
        unchanged_stem_center_mm=[cx, cy],
        new_head_center_mm=[cx + delta_x, cy],
        head_bottom_z_mm=9.2,
        arm_box_mm=[cx, cy - 1.5, 9.2, delta_x + 1, 3, 1.8],
        minimum_round_stock_requirement_mm=20,
        stock_supplier_selected=False,
        cap_seat_and_fastener_thread_geometry_translated_from_actual_source=True,
        structural_deflection_creep_and_shock_verified=False,
        physical_fit_verified=False,
        fabrication_released=False,
        artifacts_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in (".step", ".stl", ".scad")
        },
    )
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(parts=result, head_shift_mm=report["head_shift_mm"]), indent=2))
    return report


if __name__ == "__main__":
    build()
