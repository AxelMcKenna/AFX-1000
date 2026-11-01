"""Conservative panel web screen; geometry distances are not strength approval."""

import json
import math

from .stage import OUT, ROOT, sha, write


def gap(a, b):
    return math.hypot(max(0, a[0]-b[2], b[0]-a[2]), max(0, a[1]-b[3], b[1]-a[3]))


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
            neighbours.append(dict(id=o[0], conservative_AABB_gap_mm=gap(pocket,box)))
        for i, point in enumerate(cfg["fasteners"]):
            # This is a conservative6.4mm fastener-head keepout, larger than its panel bore.
            box=[point[0]-3.2,point[1]-3.2,point[0]+3.2,point[1]+3.2]
            neighbours.append(dict(id="fastener_"+str(i),conservative_AABB_gap_mm=gap(pocket,box)))
        rows.append(dict(id=p[0],pocket_XY=pocket,own_round_bore_to_pocket_web_mm=5.1-p[4]/2,
            nearest_other_opening_or_fastener=min(neighbours,key=lambda r:r["conservative_AABB_gap_mm"]),
            nominal_panel_roof_mm=45.6-44.7))
    write(OUT / "panel-webs.json",dict(source_sha256={"webs.py":sha(ROOT/"webs.py"),"geometry.scad":sha(ROOT/"geometry.scad"),"generated/config.json":sha(OUT/"config.json")},
        rows=rows,min_own_bore_web_mm=min(r["own_round_bore_to_pocket_web_mm"] for r in rows),
        min_other_AABB_gap_mm=min(r["nearest_other_opening_or_fastener"]["conservative_AABB_gap_mm"] for r in rows),
        explicit_hold="0.35mm nominal radial web and0.9mm nominal pocket roof are geometry facts, not accepted printable/structural minima; process/load validation required",
        topology_checked_by_full_native_panel=True,strength_or_process_qualified=False,physical_qualified=False))


if __name__ == "__main__":
    build()
