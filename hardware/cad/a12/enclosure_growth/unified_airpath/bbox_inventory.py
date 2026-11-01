"""Identify conservative native AABB hits with actual part identities."""

import json
import math

from .ground_route import ROOT, sha, write


def build():
    import cadquery as cq

    target=ROOT/"generated/bbox-owner-inventory.json"
    if target.exists():raise RuntimeError("New inventory output required")
    coverage=json.loads((ROOT/"generated/variant2-coverage.json").read_text())
    shapes={n:cq.importers.importStep(str(ROOT/"inputs/PB02-generated"/(n+".step"))).val() for n in ["ANA-COVERED-ENVELOPE","DIG-COVERED-ENVELOPE","SUPPORT-ENVELOPE"]}
    rows=[]
    for p in coverage["parts"]:
        lo=[v-.51 for v in p["low"]];hi=[v+.51 for v in p["high"]]
        box=cq.Workplane("XY").box(*[b-a for a,b in zip(lo,hi)],centered=False).translate(tuple(lo)).val()
        for name,s in shapes.items():
            shared=box.intersect(s)
            vol=0 if shared.isNull() else shared.Volume()
            if vol>1e-9:
                actual=cq.importers.importStep(str(ROOT/"return_variant2/generated"/(p["name"]+".step"))).val()
                gap=actual.distance(s)
                rows.append(dict(return_part=p["name"],PB_part=name,bbox_intersection_mm3=vol,
                    actual_BREP_distance_mm=gap,Euclidean_sufficient_threshold_for_Linf_051_mm=.51*math.sqrt(3),
                    Euclidean_sufficient_gap=gap>.51*math.sqrt(3),
                    source_sha256={str(ROOT/"return_variant2/generated"/(p["name"]+".step")):sha(ROOT/"return_variant2/generated"/(p["name"]+".step")),str(ROOT/"inputs/PB02-generated"/(name+".step")):sha(ROOT/"inputs/PB02-generated"/(name+".step"))}))
    write(target,dict(rows=rows,source_sha256={str(__import__("pathlib").Path(__file__)):sha(__import__("pathlib").Path(__file__)),str(ROOT/"generated/variant2-coverage.json"):sha(ROOT/"generated/variant2-coverage.json")},native_superset_hits_are_not_actual_clash_claims=True,physical_qualified=False))
    print(json.dumps(rows),flush=True)


if __name__=="__main__":build()
