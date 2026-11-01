"""Rebuild the blank's single moved return support bore, not a weld repair."""

import json

from .ground_route import ROOT, sha, write


def build():
    import cadquery as cq

    out=ROOT/"generated/UA01-BASE.step"
    if out.exists():raise RuntimeError("Fresh part output required")
    parent=ROOT.parents[1]/"thermal/interior_airpath_meter318/generated/AP03-BASE.step"
    original=cq.importers.importStep(str(parent)).val()
    assert original.isValid() and len(original.Solids())==1
    # Reconstruct the stock volume at the old tool feature in the design BREP,
    # then cut the new sole feature. No previously fabricated plate is claimed.
    def feature(x,y):
        return cq.Solid.makeCylinder(1.2,6.2,cq.Vector(x,y,-6.2)).fuse(
            cq.Solid.makeCone(2.4,1.2,1.2,cq.Vector(x,y,-6.2))).clean()
    blank=original.fuse(feature(166,133.125)).clean()
    part=blank.cut(feature(166,134.625)).clean()
    assert part.isValid() and len(part.Solids())==1
    assert abs(part.Volume()-original.Volume())<1e-5
    cq.exporters.export(part,str(out))
    back=cq.importers.importStep(str(out)).val()
    assert back.isValid() and len(back.Solids())==1 and abs(back.Volume()-part.Volume())<1e-5
    write(ROOT/"generated/base-BREP-verification.json",dict(
        original_volume_mm3=original.Volume(),actual_volume_mm3=part.Volume(),
        roundtrip_valid_single_solid=True,volume_unchanged_for_same_feature_translation=True,
        old_support_axis=[166,133.125],new_support_axis=[166,134.625],
        through_diameter=2.4,countersink_diameter=4.8,countersink_depth=1.2,plate_thickness=6.2,
        old_and_new_holes_not_both_present=True,
        fabrication_method="Newplatefromblankwithnewsolehole,NOTfillingorweldinganoldplate",
        source_sha256={str(__import__("pathlib").Path(__file__)):sha(__import__("pathlib").Path(__file__)),str(parent):sha(parent)},
        artifact_sha256={str(out):sha(out)},physical_qualified=False,thermal_qualified=False,fabrication_released=False))
    print(json.dumps(dict(valid_single_solid=True,volume_mm3=part.Volume(),same_total_hole_volume=True)))


if __name__=="__main__":build()
