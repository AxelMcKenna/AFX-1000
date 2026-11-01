"""Conservative panel web screen; geometry distances are not strength approval."""

import json
import math

from .stage import OUT, ROOT, sha, write


def gap(a, b):
    return math.hypot(max(0, a[0]-b[2], b[0]-a[2]), max(0, a[1]-b[3], b[1]-a[3]))


def point_segment(p, a, b):
    vx,vy=b[0]-a[0],b[1]-a[1]
    t=max(0,min(1,((p[0]-a[0])*vx+(p[1]-a[1])*vy)/(vx*vx+vy*vy)))
    return math.hypot(p[0]-a[0]-t*vx,p[1]-a[1]-t*vy)


def inside(p, poly):
    result=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a[1]>p[1]) != (b[1]>p[1]) and p[0] < (b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:
            result=not result
    return result


def poly_gap(first, second):
    if any(inside(p,second) for p in first) or any(inside(p,first) for p in second):
        return 0
    best=float("inf")
    for a,b in zip(first,first[1:]+first[:1]):
        for c,d in zip(second,second[1:]+second[:1]):
            def cross(p,q,r):
                return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
            if cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0:
                return 0
            best=min(best,point_segment(a,c,d),point_segment(b,c,d),point_segment(c,a,b),point_segment(d,a,b))
    return best


def rect_poly(b):
    return [[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]]


def aperture_gap(pocket,o):
    if o[1]=="knob":
        return max(0,math.hypot(max(0,pocket[0]-o[2],o[2]-pocket[2]),max(0,pocket[1]-o[3],o[3]-pocket[3]))-o[4]/2)
    if o[1]=="sector":
        # Exact source sector() construction:24 angular divisions per ring edge.
        pts=[]
        for radius,indices in [(o[5],range(25)),(o[4],range(24,-1,-1))]:
            for i in indices:
                a=math.radians(o[6]+(o[7]-o[6])*i/24)
                pts.append([o[2]+radius*math.cos(a),o[3]+radius*math.sin(a)])
        return poly_gap(rect_poly(pocket),pts)
    box=[o[2]-o[4]/2,o[3]-o[5]/2,o[2]+o[4]/2,o[3]+o[5]/2]
    return gap(pocket,box)


def build():
    if (ROOT / "handoff.json").exists() or (OUT / "panel-webs.json").exists():
        raise RuntimeError("Web report destination is immutable")
    cfg = json.loads((OUT / "config.json").read_text())
    rows = []
    pots = [r for r in cfg["openings"] if r[1] == "knob" and r[4:6] == [9.5,9.5]]
    assert len(pots) == 10
    for p in pots:
        x,y = p[2:4]
        pocket = [x-1.2,y+5.1,x+1.2,y+6.9]
        neighbours = []
        for o in cfg["openings"]:
            if o[0] == p[0]:
                continue
            if o[1] == "sector":
                radius=max(o[4],o[5])
                box=[o[2]-radius,o[3]-radius,o[2]+radius,o[3]+radius]
            else:
                box=[o[2]-o[4]/2,o[3]-o[5]/2,o[2]+o[4]/2,o[3]+o[5]/2]
            neighbours.append(dict(id=o[0], conservative_AABB_gap_mm=gap(pocket,box),planar_gap_mm=aperture_gap(pocket,o)))
        for i, point in enumerate(cfg["fasteners"]):
            # This is a conservative6.4mm fastener-head keepout, larger than its panel bore.
            box=[point[0]-3.2,point[1]-3.2,point[0]+3.2,point[1]+3.2]
            neighbours.append(dict(id="fastener_"+str(i),conservative_AABB_gap_mm=gap(pocket,box),planar_gap_mm=gap(pocket,box)))
        rows.append(dict(id=p[0],pocket_XY=pocket,own_round_bore_to_pocket_web_mm=5.1-p[4]/2,
            nearest_other_opening_or_fastener=min(neighbours,key=lambda r:r["planar_gap_mm"]),
            nominal_panel_roof_mm=45.6-44.7))
    write(OUT / "panel-webs.json",dict(source_sha256={"webs.py":sha(ROOT/"webs.py"),"geometry.scad":sha(ROOT/"geometry.scad"),"generated/config.json":sha(OUT/"config.json")},
        rows=rows,min_own_bore_web_mm=min(r["own_round_bore_to_pocket_web_mm"] for r in rows),
        min_other_planar_gap_mm=min(r["nearest_other_opening_or_fastener"]["planar_gap_mm"] for r in rows),
        method="Exact rectangle/circle distances, exact authored24-division sector polygons, conservative6.4mm square fastener-head reserves; nominal XY only",
        explicit_hold="0.35mm nominal radial web and0.9mm nominal pocket roof are geometry facts, not accepted printable/structural minima; process/load validation required",
        topology_checked_by_full_native_panel=True,strength_or_process_qualified=False,physical_qualified=False))


if __name__ == "__main__":
    build()
