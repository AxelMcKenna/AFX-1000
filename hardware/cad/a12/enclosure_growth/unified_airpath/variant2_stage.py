"""Preserve first failures; NEW delayed-dogleg model and conservative coverage."""

import json
import re
import shutil

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

from .ground_route import ROOT, sha, write


def build():
    dst=ROOT/"variant2_model"
    if dst.exists():
        raise RuntimeError("Fresh model destination required")
    original=json.loads((ROOT/"generated/first-native/verification.json").read_text())
    assert len(original["cases"])==13 and not original["all_requested_clear"]
    assert all(sha(__import__("pathlib").Path(n))==h for n,h in original["input_sha256"].items())
    shutil.copytree(ROOT/"derived_model",dst)
    for p in dst.rglob("*.scad"):
        p.write_text(p.read_text().replace(str(ROOT/"derived_model"),str(dst)))
    new_returns=ROOT/"return_variant2/generated/returns.scad"
    text=re.sub(r'import\("([^\"]+)"\)',lambda m:'import("'+str(new_returns.parent/m.group(1))+'")',new_returns.read_text())
    (dst/"context/hardware/cad/a12/returns/generated/returns.scad").write_text(text)
    (ROOT/"generated/unified-context_v2.scad").write_text((ROOT/"generated/unified-context.scad").read_text().replace(str(ROOT/"derived_model"),str(dst)))
    cad=json.loads((ROOT/"return_variant2/generated/cad-verification.json").read_text())
    parts=[]
    for p in sorted((ROOT/"return_variant2/generated").glob("*.stl")):
        if "ASSEMBLY" in p.name:continue
        stat=mesh(p)
        assert stat["closed_oriented_boundary"] and not stat["degenerate_triangles_excluded"]
        label=p.stem
        key=label if label in cad else label.replace("AFX-A12-R03-","").replace("-END","_END").replace("-CAP-SCREW","_CAP_SCREW").replace("-BASE-SCREW","_BASE_SCREW").replace("-WASHER","_WASHER").replace("-SCREW","_SCREW")
        # Independent containment uses both actualSTLcoordinates and exactCQ
        # partbounds; neither representation may extend beyond its fixture.
        row=cad[key]
        low=[min(a,b) for a,b in zip(stat["min_mm"],row["bbox_min_mm"])]
        high=[max(a,b) for a,b in zip(stat["max_mm"],row["bbox_max_mm"])]
        parts.append(dict(name=label,source=str(p),source_sha256=sha(p),low=low,high=high,
                     statistics=stat,exact_CQ_valid_single_solid=row["valid_single_solid"],
                     exact_CQ_STEP_roundtrip=row["step_roundtrip_volume_matches"]))
    assert len(parts)==20
    fixtures="ua_return_part_boxes="+json.dumps([[p["name"],p["low"],p["high"]] for p in parts])+";\n"
    fixtures+='module ua_return_bbox_supersets(m=.51){for(b=ua_return_part_boxes)translate([b[1][0]-m,b[1][1]-m,b[1][2]-m])cube([b[2][0]-b[1][0]+2*m,b[2][1]-b[1][1]+2*m,b[2][2]-b[1][2]+2*m]);}\n'
    source=(ROOT/"checks.scad").read_text().replace("generated/unified-context.scad","generated/unified-context_v2.scad")
    source=source.replace('ua_expand(.16)ua_returns();ua_expand(.35)ua_pb("ANA-COVERED-ENVELOPE");','ua_return_bbox_supersets();ua_pb("ANA-COVERED-ENVELOPE");')
    source=source.replace('ua_expand(.16)ua_returns();ua_expand(.35)ua_pb("DIG-COVERED-ENVELOPE");','ua_return_bbox_supersets();ua_pb("DIG-COVERED-ENVELOPE");')
    source=source.replace('ua_expand(.16)ua_returns();ua_expand(.35)ua_PB_support();','ua_return_bbox_supersets();ua_PB_support();')
    for name in ["ANA-POST","ANA-CAP","DIG-POST","DIG-CAP"]:
        p=ROOT/"return_variant2/generated"/("AFX-A12-R03-"+name+".stl")
        source+='\nif(ua_case=="part_'+name.replace('-','_')+'")import("'+str(p)+'");\n'
    (ROOT/"checks_v2.scad").write_text(fixtures+source)
    old_entry=(ROOT/"generated/entry.scad").read_text()
    (ROOT/"generated/entry_v2.scad").write_text(old_entry.replace(str(ROOT/"checks.scad"),str(ROOT/"checks_v2.scad")))
    pairs=[[p["name"],n] for p in parts for n in ["ANA-COVERED-ENVELOPE","DIG-COVERED-ENVELOPE","SUPPORT-ENVELOPE"]]
    write(ROOT/"generated/variant2-coverage.json",dict(parts=parts,full_pair_coverage=pairs,
        actual_individual_parts=20,pair_count=60,native_superset_union_cases=3,
        set_identity="For everyi,j: empty((AABB(A_i)⊕Cube(.51))∩B_j) implies empty((A_i⊕Cube(.16))∩(B_j⊕Cube(.35))) by symmetricMinkowskisum/emptiness equivalence, not pointwiseintersectioncontainment. Threeemptyunions establishall60pairs;nonemptyneedsnarrowerexactchecks,neverwaiver.",
        combined_Linf_margin_mm=.51,original_return_margin_mm=.16,original_PB_margin_mm=.35,
        compound_topology_failure_preserved=True,retention_review_not_single_manufacturable_part=True,
        source_sha256={str(p):sha(p) for p in [__import__("pathlib").Path(__file__),new_returns,
            ROOT/"return_variant2/generated/cad-verification.json",ROOT/"checks_v2.scad",ROOT/"generated/entry_v2.scad"]},
        source_models_unchanged_for_first_native=True,physical_qualified=False))
    print(json.dumps(dict(individual_parts=20,coverage_pairs=60,union_superset_cases=3)))


if __name__=="__main__":
    build()
