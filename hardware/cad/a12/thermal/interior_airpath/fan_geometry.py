"""AP02 nominal frame-land extraction from external official Sunon STEP.

This validates nominal CAD only; exact delivery/tolerances/warp/rotor dynamics
and matching gasket manufacture remain unapproved physical interfaces.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
SOURCE = Path("/private/tmp/afx-sunon-mf4010-official-cad/Doc-0178239-4-0 (2).stp")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    if (ROOT / "handoff.json").exists() or (OUT / "nominal-frame-land.stl").exists():
        raise RuntimeError("Nominal frame extraction requires a new destination")
    import cadquery as cq
    s=cq.importers.importStep(str(SOURCE)).val()
    assert s.isValid() and len(s.Solids())==1
    b=s.BoundingBox()
    bottom=[f for f in s.Faces() if f.geomType()=="PLANE" and f.BoundingBox().zlen<1e-4 and abs(f.Center().z+10.4)<1e-4]
    assert len(bottom)==1
    face=bottom[0].translate((0,0,10.4))
    land=cq.Solid.extrudeLinear(face.outerWire(),face.innerWires(),cq.Vector(0,0,1))
    # The unmodified bottom-frame land is checked against BOTH nominal end
    # faces. No bounding square is counted as actual sealing material.
    slab0=cq.Solid.makeBox(60,60,.02,cq.Vector(-30,-30,-.02))
    slab1=cq.Solid.makeBox(60,60,.02,cq.Vector(-30,-30,-10.4))
    frame_top=s.intersect(slab0)
    frame_bottom=s.intersect(slab1)
    top_missing=land.translate((0,0,-.02)).intersect(slab0).cut(frame_top).Volume()
    bottom_missing=land.translate((0,0,-10.4)).intersect(slab1).cut(frame_bottom).Volume()
    OUT.mkdir(parents=True,exist_ok=True)
    cq.exporters.export(land,str(OUT / "nominal-frame-land.stl"),tolerance=.01,angularTolerance=.03)
    record=dict(
        source=dict(url="https://www.sunonusa.com/wp-content/uploads/2026/02/MF4010-Doc-0178239-4-0-3D.zip",external_STEP=str(SOURCE),
            STEP_sha256=sha(SOURCE),external_zip="/private/tmp/afx-sunon-mf4010-official-cad.zip",
            zip_sha256=sha(Path("/private/tmp/afx-sunon-mf4010-official-cad.zip")),
            exact_part_linkage="Manufacturer-hosted genericMF4010 CAD linked from exactMF40100V1-1000U-G99 product listing; not a tolerance-controlled delivery drawing"),
        step_header_name="_K201003850G-1_",step_header_date="2020-11-30T",
        CAD_valid=True,CAD_solids=1,CAD_faces=len(s.Faces()),CAD_bounds_mm=[b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax],
        nominal_clamp_face_separation_mm=10.4,nominal_matched_shim_mm=2.1,matched_total_stack_requirement_mm=12.5,
        nominal_bottom_planar_land_mm2=face.Area(),bottom_nominal_missing_volume_mm3=bottom_missing,top_nominal_missing_volume_mm3=top_missing,
        derived_land_only=True,vendor_STEP_redistributed=False,face_land_has_no_supplier_tolerance_approval=True,
        bottom_ring_outer_square39_inner_circle37p5_not_accepted_as_sealing_land=True,
        source_sha256={"fan_geometry.py":sha(Path(__file__))},artifact_sha256={"nominal-frame-land.stl":sha(OUT/"nominal-frame-land.stl")},
        gasket_manufacturing_registration_compression_and_air_leak_verified=False,physical_qualified=False,thermal_qualified=False)
    (OUT / "fan-geometry.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({k:record[k] for k in ["nominal_bottom_planar_land_mm2","bottom_nominal_missing_volume_mm3","top_nominal_missing_volume_mm3","nominal_matched_shim_mm"]}))


if __name__=="__main__":
    build()
