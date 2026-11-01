"""Exact-curve AP02 metal-base STEP from immutable FI01 base and actual cuts."""

import json
import math

from .plan import plan
from .stage import FI, OUT, ROOT, sha, write


def build():
    target = OUT / "AP02-BASE.step"
    if (ROOT / "handoff.json").exists() or target.exists():
        raise RuntimeError("AP02baseSTEP is immutable; use a new candidate")
    import cadquery as cq

    source = FI / "generated/AFX-FI01-BASE.step"
    data = plan()
    old = cq.importers.importStep(str(source)).val()
    assert old.isValid() and len(old.Solids()) == 1
    shape = old
    for x, y in data["pins"]["removed_centres"]:
        shape = shape.cut(cq.Solid.makeBox(3, 3, 12, cq.Vector(x - 1.5, y - 1.5, -18.2)))
    after_pins = shape.Volume()

    def rounded_prism(x, y, w, h, r):
        a = cq.Solid.makeBox(w - 2 * r, h, 6.4, cq.Vector(x + r, y, -6.3))
        a = a.fuse(cq.Solid.makeBox(w, h - 2 * r, 6.4, cq.Vector(x, y + r, -6.3)))
        for cx in [x + r, x + w - r]:
            for cy in [y + r, y + h - r]:
                a = a.fuse(cq.Solid.makeCylinder(r, 6.4, cq.Vector(cx, cy, -6.3)))
        return a

    left = rounded_prism(38, 164, 72, 19, 1).cut(
        cq.Solid.makeCylinder(6, 6.4, cq.Vector(93.0871, 168.9352, -6.3))
    )
    right = rounded_prism(231.5, 154, 45, 29, 1)
    shape = shape.cut(left).cut(right)
    assert shape.isValid() and len(shape.Solids()) == 1
    expected = (
        old.Volume() - 108 * data["pins"]["removed_count"] - 6.2 * data["inlet"]["nominal_total_net_mm2"]
    )
    if not math.isclose(shape.Volume(), expected, abs_tol=0.001):
        raise RuntimeError("Actual cut volume does not match independent wholepin/window balance")
    cq.exporters.export(shape, str(target))
    check = cq.importers.importStep(str(target)).val()
    assert (
        check.isValid()
        and len(check.Solids()) == 1
        and math.isclose(check.Volume(), shape.Volume(), abs_tol=0.001)
    )
    b = check.BoundingBox()
    proof = json.loads((OUT / "current-native/verification.json").read_text())
    native = proof["cases"]["base_geometry"]["statistics"]["volume_mm3"]
    write(
        OUT / "base-BREP-verification.json",
        dict(
            source_sha256={
                "base_brep.py": sha(ROOT / "base_brep.py"),
                "parent_BASE_STEP": sha(source),
                "plan.py": sha(ROOT / "plan.py"),
                "current_native_proof": sha(OUT / "current-native/verification.json"),
            },
            artifact_sha256={target.name: sha(target)},
            parent_valid=True,
            parent_solids=1,
            new_valid=True,
            new_solids=1,
            roundtrip_valid=True,
            roundtrip_solids=1,
            parent_volume_mm3=old.Volume(),
            after_exact_wholepin_removal_mm3=after_pins,
            removed_wholepins=data["pins"]["removed_count"],
            exact_curve_new_volume_mm3=shape.Volume(),
            independent_volume_balance_mm3=expected,
            native_faceted_volume_mm3=native,
            relative_curve_vs_native_volume_difference=abs(native - shape.Volume()) / shape.Volume(),
            bounds_mm=[b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax],
            actual_thermal_lands_supports_and_retained_holes_unchanged=True,
            native_STL_and_exact_curves_have_declared_tessellation_difference=True,
            physical_qualified=False,
            thermal_qualified=False,
            fabrication_released=False,
        ),
    )
    print(
        json.dumps(
            dict(
                valid=True,
                solids=1,
                volume_mm3=shape.Volume(),
                native_relative_difference=abs(native - shape.Volume()) / shape.Volume(),
            )
        )
    )


if __name__ == "__main__":
    build()
