"""Exact editable keeper BREP, not a STEP wrapper around a triangulated mesh."""

import json
from pathlib import Path

from .capture import ROOT, sha


def build():
    import cadquery as cq

    folder = ROOT / "generated/keeper-BREP"
    if folder.exists():
        raise RuntimeError("New CAD outputs required")
    folder.mkdir()
    rows = {}
    native = json.loads((ROOT / "generated/native-mount5/verification.json").read_text())
    for i, (name, x, top) in enumerate(
        [("NF_LEFT", 210, 42.5), ("NF_RIGHT", 310, 42.5), ("FPC_LEFT", 31, 41.5), ("FPC_RIGHT", 68.5, 41.5)]
    ):
        profile = [
            (179.9, top - 1.2),
            (180.5, top - 1.2),
            (180.5, top + 0.2),
            (182.5, top + 0.2),
            (182.5, top - 0.95),
            (185.7, top - 0.95),
            (185.7, 43.6),
            (179.9, 43.6),
        ]
        plane = cq.Plane(origin=(x - 3, 0, 0), xDir=(0, 1, 0), normal=(1, 0, 0))
        outer = cq.Workplane(plane).polyline(profile).close().extrude(6).val()
        hole = cq.Solid.makeCylinder(1.2, 7, cq.Vector(x, 184, top - 1), cq.Vector(0, 0, 1))
        part = outer.cut(hole).clean()
        assert part.isValid() and len(part.Solids()) == 1
        p = folder / (name + ".step")
        cq.exporters.export(part, str(p))
        back = cq.importers.importStep(str(p)).val()
        assert back.isValid() and len(back.Solids()) == 1 and abs(back.Volume() - part.Volume()) < 1e-7
        saved = native["cases"]["keeper_" + str(i)]["statistics"]["volume_mm3"]
        difference = saved - part.Volume()
        assert 0 <= difference < 0.05, (name, difference)
        rows[name] = dict(
            path=str(p.relative_to(ROOT)),
            sha256=sha(p),
            valid_single_solid=True,
            volume_mm3=part.Volume(),
            native_faceted_bore_part_volume_mm3=saved,
            native_minus_analytic_volume_mm3=difference,
            only_nominal_2p4_circular_bore_vs_native64gon_difference=True,
            roundtrip_valid=True,
        )
    (folder / "verification.json").write_text(
        json.dumps(
            dict(
                parts=rows,
                source_sha256={
                    str(p): sha(p)
                    for p in [
                        Path(__file__),
                        ROOT / "mount_variant5/checks.scad",
                        ROOT / "generated/native-mount5/verification.json",
                    ]
                },
                manufacturing_tolerances_accepted=False,
                physical_qualified=False,
                fabrication_released=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(dict(editable_valid_STEP_parts=4, roundtrip=True, physical_qualified=False)))


if __name__ == "__main__":
    build()
