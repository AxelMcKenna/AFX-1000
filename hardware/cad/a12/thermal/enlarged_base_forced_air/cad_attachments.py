"""Exact nominal tray/guard/spacer BREP; actual material/process unapproved."""

import json
from importlib.metadata import version

import cadquery as cq

from .analytical import perforations, volumes
from .stage import OUT, ROOT, sha, write


def rounded(w, h, r, z, thickness):
    return (
        cq.Workplane("XY")
        .box(w, h, thickness, centered=(False, False, False))
        .translate((0, 0, z))
        .edges("|Z")
        .fillet(r)
        .val()
    )


def export():
    if (ROOT / "handoff.json").exists():
        raise RuntimeError("Sealed parts cannot be overwritten")
    plan = json.loads((ROOT / "parent_evidence/forced_air_prototype/space-plan.json").read_text())
    feet = plan["foot_centres_xy_mm"]
    fans = plan["fan_centres_xy_mm"]
    tray = rounded(334, 188.4, 7, -26.2, 1.5)
    ring = rounded(334, 188.4, 7, -24.7, 18.5).cut(rounded(330, 184.4, 5, -24.71, 18.52).translate((2, 2, 0)))
    solids = [ring]
    for x, y in feet:
        solids += [
            cq.Solid.makeCylinder(12, 16.5, cq.Vector(x, y, -24.7)),
            cq.Solid.makeCylinder(13, 2, cq.Vector(x, y, -8.2)),
        ]
    tray = tray.fuse(*solids).clean()
    cuts = []
    for x, y in feet:
        cuts += [
            cq.Solid.makeCylinder(10.25, 18.01, cq.Vector(x, y, -26.21)),
            cq.Solid.makeCylinder(1.7, 2.02, cq.Vector(x, y, -8.21)),
        ]
    for x, y in fans:
        cuts.append(cq.Solid.makeCylinder(18.75, 1.52, cq.Vector(x, y, -26.21)))
        cuts += [
            cq.Solid.makeCylinder(2.2, 1.52, cq.Vector(x + dx, y + dy, -26.21))
            for dx in [-16, 16]
            for dy in [-16, 16]
        ]
    cuts.append(cq.Solid.makeBox(266, 2.02, 14, cq.Vector(34, -0.01, -22.2)))
    tray = tray.cut(*cuts).clean()
    guard = rounded(44, 44, 3, -27.7, 1).translate((-22, -22, 0))
    holes = [cq.Solid.makeCylinder(2.2, 1.02, cq.Vector(x, y, -27.71)) for x in [-16, 16] for y in [-16, 16]]
    holes += [cq.Solid.makeCylinder(2.1, 1.02, cq.Vector(x, y, -27.71)) for x, y in perforations()]
    guard = guard.cut(*holes).clean()
    spacer = (
        cq.Solid.makeCylinder(9, 6, cq.Vector(0, 0, -14.2))
        .cut(cq.Solid.makeCylinder(1.7, 6.02, cq.Vector(0, 0, -14.21)))
        .clean()
    )
    assert tray.isValid() and guard.isValid() and spacer.isValid()
    assert len(tray.Solids()) == len(guard.Solids()) == len(spacer.Solids()) == 1
    guards = cq.Compound.makeCompound([guard.translate((x, y, 0)) for x, y in fans])
    spacers = cq.Compound.makeCompound([spacer.translate((x, y, 0)) for x, y in feet])
    parts = {"AFX-FI01-TRAY": tray, "AFX-FI01-GUARDS": guards, "AFX-FI01-SPACERS": spacers}
    expected = volumes(True)
    checks = {}
    for name, obj in parts.items():
        target = OUT / (name + ".step")
        cq.exporters.export(obj, str(target))
        rt = cq.importers.importStep(str(target)).val()
        assert (
            rt.isValid() and len(rt.Solids()) == len(obj.Solids()) and abs(rt.Volume() - obj.Volume()) < 0.001
        )
        key = {"AFX-FI01-TRAY": "tray", "AFX-FI01-GUARDS": "guards", "AFX-FI01-SPACERS": "spacers"}[name]
        assert abs(obj.Volume() - expected[key]) < 0.001
        checks[name] = dict(
            valid=True,
            solids=len(obj.Solids()),
            volume_mm3=obj.Volume(),
            analytic_exact_curves_mm3=expected[key],
            step_roundtrip_valid=True,
            sha256=sha(target),
        )
    write(
        OUT / "cad-attachments-verification.json",
        dict(
            scope=__doc__,
            cadquery_version=version("cadquery"),
            ocp_version=version("cadquery-ocp"),
            parts=checks,
            all_shapes_in_assembly_coordinates=True,
            perforations_per_guard=len(perforations()),
            source_sha256={
                str(p.relative_to(ROOT)): sha(p)
                for p in [
                    ROOT / "cad_attachments.py",
                    ROOT / "analytical.py",
                    ROOT / "parent_evidence/forced_air_prototype/space-plan.json",
                    OUT / "fa-scoped.scad",
                ]
            },
            actual_material_manufacturing_strength_or_airflow_accepted=False,
            physical_qualified=False,
            thermal_qualified=False,
            fabrication_released=False,
        ),
    )
    print(
        json.dumps({n: dict(solids=r["solids"], volume_mm3=r["volume_mm3"]) for n, r in checks.items()}),
        flush=True,
    )


if __name__ == "__main__":
    export()
