"""Independent exact BREP export of EB01, with unresolved threads as callouts."""

import json
from importlib.metadata import version

import cadquery as cq

from .stage import OUT, ROOT, sha, write


def export():
    d = json.loads((ROOT / "design.json").read_text())
    a = json.loads((OUT / "analysis.json").read_text())
    base = cq.Workplane("XY").box(334,188.4,6.2,centered=(False,False,False)).translate((0,0,-6.2)).edges("|Z").fillet(7).val()
    solids = [cq.Solid.makeBox(3,3,12,cq.Vector(x-1.5,y-1.5,-18.2)) for x,y in a["pins"]["centres"]]
    for r in a["retained_thermal_lands"]:
        x,y,w,h = r["metal_global"]
        land = cq.Solid.makeBox(w,h,5.28,cq.Vector(x,y,0))
        if "corner_relief" in r:
            cx,cy = r["relief_centre_global"]
            land = land.cut(cq.Solid.makeCylinder(r["corner_relief"]["metal_radius_mm"],5.48,cq.Vector(cx,cy,-.1)))
        solids.append(land)
    solids += [cq.Solid.makeCylinder(3,6.3,cq.Vector(x,y,0)) for x,y in a["retained_supports"]]
    base = base.fuse(*solids).clean()
    cuts = []
    for x,y in a["shell_fasteners"]:
        cuts += [cq.Solid.makeCylinder(1.7,6.4,cq.Vector(x,y,-6.3)),cq.Solid.makeCone(3.3,1.7,1.6,cq.Vector(x,y,-6.2))]
    for x,y in a["foot_axes"]:
        cuts += [cq.Solid.makeCylinder(1.7,6.4,cq.Vector(x,y,-6.3)),cq.Solid.makeCone(1.7,3.3,1.6,cq.Vector(x,y,-1.6))]
    cuts += [cq.Solid.makeCylinder(.65,3.7,cq.Vector(x,y,2.7)) for x,y in a["retained_supports"]]
    for x,y in d["return_support_attachments"]["centres"]:
        cuts += [cq.Solid.makeCylinder(1.2,6.4,cq.Vector(x,y,-6.3)),cq.Solid.makeCone(2.4,1.2,1.2,cq.Vector(x,y,-6.2))]
    base = base.cut(*cuts).clean()
    assert base.isValid() and len(base.Solids())==1
    target = OUT / "AFX-EB01-BASE.step"
    cq.exporters.export(base,str(target))
    cq.exporters.export(base,str(OUT / "AFX-EB01-BASE.stl"),tolerance=.02,angularTolerance=.1)
    rt = cq.importers.importStep(str(target)).val()
    assert rt.isValid() and len(rt.Solids())==1 and abs(rt.Volume()-base.Volume()) < .001
    foot = cq.Solid.makeCylinder(9,19).cut(cq.Solid.makeCylinder(1.25,13,cq.Vector(0,0,6))).clean()
    assert foot.isValid() and len(foot.Solids())==1
    cq.exporters.export(foot,str(OUT / "AFX-EB01-FOOT.step"))
    rt_foot = cq.importers.importStep(str(OUT / "AFX-EB01-FOOT.step")).val()
    assert rt_foot.isValid() and abs(rt_foot.Volume()-foot.Volume()) < .001
    native = json.loads((OUT / "verification.json").read_text())["cases"]["metal_geometry"]["statistics"]
    delta = abs(native["volume_mm3"]-base.Volume())/base.Volume()
    assert delta < .0001
    write(OUT / "cad-verification.json",dict(cadquery_version=version("cadquery"),ocp_version=version("cadquery-ocp"),
        base_valid=True,base_solids=1,base_volume_mm3=base.Volume(),base_surface_area_mm2=base.Area(),
        base_aluminum_mass_at_typical2700kgm3_kg=base.Volume()*2.7e-6,
        foot_valid=True,foot_solids=1,foot_volume_mm3=foot.Volume(),four_foot_mass_typical_kg=4*foot.Volume()*2.7e-6,
        step_roundtrip_valid=True,step_native_volume_relative_difference=delta,
        native_boolean_receipt_sha256=sha(OUT / "verification.json"),
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/"cad.py",ROOT/"design.json",OUT/"analysis.json"]},
        artifact_sha256={p.name:sha(p) for p in OUT.glob("AFX-EB01-*.step")},
        thread_helices_modelled=False,material_certified=False,thermal_qualified=False,physical_qualified=False,fabrication_released=False))
    print(json.dumps(dict(base_mm3=base.Volume(),native_delta=delta,foot_mm3=foot.Volume())),flush=True)


if __name__=="__main__":
    export()
