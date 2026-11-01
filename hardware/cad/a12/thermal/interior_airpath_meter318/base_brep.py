"""Subtract exactly19 whole pins from the valid AP02 curved BREP."""

import json

from .stage import OUT, PARENT, ROOT, require_parent, sha, write


def build():
    target=OUT/"AP03-BASE.step"
    if target.exists() or (ROOT/"handoff.json").exists():
        raise RuntimeError("Existing actual part evidence cannot be overwritten")
    import cadquery as cq
    require_parent()
    d=json.loads((OUT/"analysis.json").read_text())
    parent=PARENT/"generated/AP02-BASE.step"
    original=cq.importers.importStep(str(parent)).val()
    if not original.isValid() or len(original.Solids())!=1:
        raise RuntimeError("Invalid source BREP")
    part=original
    for x,y in d["additional_whole_removed"]:
        cutter=cq.Workplane("XY").box(3,3,12.00001,centered=(True,True,False)).translate((x,y,-18.20001)).val()
        part=part.cut(cutter)
    if not part.isValid() or len(part.Solids())!=1:
        raise RuntimeError("Invalid actual new base")
    expected=original.Volume()-108*d["additional_count"]
    if abs(part.Volume()-expected)>.001:
        raise RuntimeError("Whole-pin-only mass balance failed")
    cq.exporters.export(part,str(target))
    back=cq.importers.importStep(str(target)).val()
    if not back.isValid() or len(back.Solids())!=1 or abs(back.Volume()-part.Volume())>.001:
        raise RuntimeError("Invalid STEP round-trip")
    native=json.loads((OUT/"current-native/verification.json").read_text())
    native_v=native["cases"]["base_geometry"]["statistics"]["volume_mm3"]
    result=dict(valid=True,solids=1,roundtrip_valid=True,roundtrip_solids=1,
                original_volume_mm3=original.Volume(),removed_pin_count=d["additional_count"],
                independent_expected_mm3=expected,actual_volume_mm3=part.Volume(),
                roundtrip_volume_mm3=back.Volume(),native_faceted_volume_mm3=native_v,
                exact_minus_native_mm3=part.Volume()-native_v,
                source_sha256={"base_brep.py":sha(ROOT/"base_brep.py"),
                    "generated/analysis.json":sha(OUT/"analysis.json"),
                    "generated/current-native/verification.json":sha(OUT/"current-native/verification.json"),
                    "AP02_BASE_STEP":sha(parent)},
                artifact_sha256={"AP03-BASE.step":sha(target)},physical_qualified=False,
                fabrication_released=False,thermal_qualified=False)
    write(OUT/"base-BREP-verification.json",result)
    print(json.dumps(result))


if __name__=="__main__":
    build()
