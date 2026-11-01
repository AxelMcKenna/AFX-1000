"""Four direct imports require exact source triangles and strict topology.

No Boolean result may use this exception: a literal STL import reports PolySet.
"""

from hardware.cad.a12.thermal.interior_airpath.assembly import digest, triangles
from hardware.cad.a12.thermal.interior_airpath.verify import mesh

from .ground_route import ROOT

NAMES={"part_"+s for s in ["ANA_POST","ANA_CAP","DIG_POST","DIG_CAP"]}


def errors(name,row,folder):
    if name not in NAMES:return ["unknown-pure-import"]
    source=ROOT/"return_variant3/generated"/("AFX-A12-R04-"+name[5:].replace("_","-")+".stl")
    declaration='if(ua_case=="'+name+'")import("'+str(source)+'");'
    if (ROOT/"checks_v6.scad").read_text().count(declaration)!=1:
        return ["not-the-named-direct-import-fixture"]
    output=folder/(name+".stl");log=(folder/(name+".log")).read_text()
    if row["returncode"] or not output.exists() or "WARNING" in log or "ERROR" in log:
        return ["failed-direct-import"]
    if "Top level object is a 3D object (PolySet)" not in log:
        return ["unexpected-direct-import-status"]
    actual=mesh(output);expected=mesh(source)
    if actual!=expected or actual!=row["statistics"] or digest(triangles(output))!=digest(triangles(source)):
        return ["direct-import-not-exact-source-triangles"]
    if not actual["closed_oriented_boundary"] or actual["degenerate_triangles_excluded"] or actual["volume_mm3"]<=0:
        return ["invalid-direct-import-boundary"]
    return []
