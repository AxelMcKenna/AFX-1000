"""New PB27/northbolt geometry and mathematically conservative post fixtures."""

import json
import re
import shutil

from hardware.cad.a12.thermal.interior_airpath.assembly import triangles

from .ground_route import ROOT, sha, write


def inside(point,box):
    return all(box[1][j]<=point[j]<=box[2][j] for j in range(3))


def build():
    dst=ROOT/"variant5_model"
    if dst.exists():raise RuntimeError("Fresh variant destination required")
    positive=ROOT/"positive_variant27/generated"
    proof=json.loads((positive/"geometry.json").read_text())
    assert len(proof["parts"])==32
    shutil.copytree(ROOT/"variant4_model",dst)
    for p in dst.rglob("*.scad"):
        p.write_text(p.read_text().replace(str(ROOT/"variant4_model"),str(dst)).replace(str(ROOT/"positive_variant26/generated"),str(positive)))
    context=(ROOT/"generated/unified-context_v4.scad").read_text().replace(str(ROOT/"variant4_model"),str(dst))
    (ROOT/"generated/unified-context_v5.scad").write_text(context)
    previous=json.loads((ROOT/"generated/variant4-coverage.json").read_text())
    boxes=previous["actual_fixture_boxes"]
    design=json.loads((ROOT/"return_variant2/design.json").read_text())
    details=[]
    for name in ["ANA","DIG"]:
        key="AFX-A12-R03-"+name+"-POST"
        old=next(b for b in boxes if b[0]==key)
        cx,cy=design["retainers"]["locations"][name]
        top=design["retainers"]["stem_top_z"]
        r=design["retainers"]["stem_diameter"]/2
        split=[[key+"-stem",[cx-r-.005,cy-r-.005,-.005],[cx+r+.005,cy+r+.005,top+.005]],
               [key+"-head",[old[1][0],old[1][1],top-.005],old[2]]]
        meshfile=ROOT/"return_variant2/generated"/(key+".stl")
        # Every complete source triangle must be enclosed by ONE convexbox;
        # checking vertices independently against differentboxes is insufficient.
        count=0
        for tri in triangles(meshfile):
            if not any(all(inside(v,b) for v in tri) for b in split):
                raise RuntimeError("Uncovered complete source triangle: "+key)
            count+=1
        boxes=[b for b in boxes if b[0]!=key]+split
        details.append(dict(part=key,source_STL_sha256=sha(meshfile),full_triangles_enclosed=count,
             full_volume_basis="ActualpostconstructedastheunionofOD3stemZ0..8.7and4x14headabove8.7,minusbores/channel. Stem/headAABBunioncontainswholematerialincludinginterior;allcompletetrianglesindependentlycovered;noholeremovalcredit.",
             old_false_superset=old,new_supersets=split))
    assert len(boxes)==30
    source=(ROOT/"checks_v4.scad").read_text().replace("generated/unified-context_v4.scad","generated/unified-context_v5.scad")
    source=re.sub(r'^ua_return_part_boxes=.*;$','ua_return_part_boxes='+json.dumps(boxes)+';',source,flags=re.M)
    source=source.replace("PB26_","PB27_")
    (ROOT/"checks_v5.scad").write_text(source)
    entry=(ROOT/"generated/entry_v4.scad").read_text().replace(str(ROOT/"checks_v4.scad"),str(ROOT/"checks_v5.scad")).replace(str(ROOT/"positive_variant26/generated"),str(positive))
    (ROOT/"generated/entry_v5.scad").write_text(entry)
    (ROOT/"part_import_v5.py").write_text((ROOT/"part_import_v4.py").read_text().replace("checks_v4.scad","checks_v5.scad"))
    s=(ROOT/"verify_v4.py").read_text().replace('from .part_import_v4 import','from .part_import_v5 import').replace('entry_v4.scad','entry_v5.scad').replace('ROOT/"part_import_v4.py"','ROOT/"part_import_v5.py"')
    s=s.replace('ROOT/"variant4_stage.py",','ROOT/"variant4_stage.py",ROOT/"variant5_stage.py",ROOT/"generated/variant5-coverage.json",')
    s=s.replace('ROOT/"positive_variant26/generated"','ROOT/"positive_variant27/generated"').replace("PB26_","PB27_")
    (ROOT/"verify_v5.py").write_text(s)
    write(ROOT/"generated/variant5-coverage.json",dict(source_parts=20,pairs=60,fixtures=boxes,post_decomposition=details,
          source_sha256={str(p):sha(p) for p in [__import__("pathlib").Path(__file__),ROOT/"return_variant2/generate.py",positive/"geometry.json",ROOT/"checks_v5.scad",ROOT/"generated/entry_v5.scad"]},
          all_actual_material_and_tolerances_preserved=True,combined_margin_mm=.51,extra_subprimitive_reserve_mm=.005,
          full_union_empty_required=True,nonempty_is_unresolved_not_waived=True,physical_qualified=False))
    print(json.dumps(dict(material_parts=20,coverage_pairs=60,conservative_subfixtures=30)))


if __name__=="__main__":build()
