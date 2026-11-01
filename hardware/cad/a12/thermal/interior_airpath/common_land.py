"""Separate common nominal end-face shim; preserve the rejected bottom-only reuse."""

import json

from .fan_geometry import OUT, ROOT, SOURCE, sha


def build():
    if (ROOT/"handoff.json").exists() or (OUT/"nominal-common-land.stl").exists():
        raise RuntimeError("Common-land output is immutable")
    import cadquery as cq
    s=cq.importers.importStep(str(SOURCE)).val()
    bottom=[f for f in s.Faces() if f.geomType()=="PLANE" and f.BoundingBox().zlen<1e-4 and abs(f.Center().z+10.4)<1e-4][0].translate((0,0,10.4))
    top=cq.Compound.makeCompound([f for f in s.Faces() if f.geomType()=="PLANE" and f.BoundingBox().zlen<1e-4 and abs(f.Center().z)<1e-4])
    common=bottom.intersect(top)
    solids=[cq.Solid.extrudeLinear(f.outerWire(),f.innerWires(),cq.Vector(0,0,1)) for f in common.Faces()]
    shape=solids[0]
    for solid in solids[1:]:
        shape=shape.fuse(solid)
    assert shape.isValid()
    cq.exporters.export(shape,str(OUT/"nominal-common-land.stl"),tolerance=.01,angularTolerance=.03)
    bottom_ex=cq.Solid.extrudeLinear(bottom.outerWire(),bottom.innerWires(),cq.Vector(0,0,1))
    top_ex=[cq.Solid.extrudeLinear(f.outerWire(),f.innerWires(),cq.Vector(0,0,1)) for f in top.Faces()]
    top_shape=cq.Compound.makeCompound(top_ex)
    record=dict(
        source_STEP_sha256=sha(SOURCE),bottom_nominal_land_mm2=bottom.Area(),top_nominal_land_mm2=top.Area(),
        common_nominal_land_mm2=common.Area(),common_faces=len(common.Faces()),
        actual_common_shape_valid=shape.isValid(),actual_common_shape_solids=len(shape.Solids()),
        missing_bottom_volume_for1mm_profile_mm3=shape.cut(bottom_ex).Volume(),
        missing_top_volume_for1mm_profile_mm3=shape.cut(top_shape).Volume(),
        original_bottom_only_top_contact_rejection_preserved="fan-geometry.json",source_sha256={"common_land.py":sha(ROOT/"common_land.py"),"generated/fan-geometry.json":sha(OUT/"fan-geometry.json")},
        artifact_sha256={"nominal-common-land.stl":sha(OUT/"nominal-common-land.stl")},
        nominal_geometry_only=True,supplier_land_tolerances_and_matching_manufacture_approved=False,
        rotor_dynamic_clearance_and_airtightness_verified=False,physical_qualified=False,thermal_qualified=False)
    (OUT/"common-land.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({k:record[k] for k in ["common_nominal_land_mm2","common_faces","actual_common_shape_solids","missing_bottom_volume_for1mm_profile_mm3","missing_top_volume_for1mm_profile_mm3"]}))


if __name__=="__main__":
    build()
