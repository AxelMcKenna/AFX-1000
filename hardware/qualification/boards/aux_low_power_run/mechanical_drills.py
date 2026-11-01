"""Explicit unplated-hole obstacles omitted by copper-only pad exports."""

from shapely.geometry import Point

from hardware.electronics.common.sexpr import children, first
from hardware.electronics.output_stage.check_placement import transform


def unplated_holes(tree):
    result=[]
    for fp in children(tree,"footprint"):
        ref=next(p[2] for p in children(fp,"property") if p[1]=="Reference")
        for pad in children(fp,"pad"):
            if pad[2]!="np_thru_hole":
                continue
            drill=first(pad,"drill")
            assert len(drill)==2,"A slotted hole needs an oriented native drill outline"
            diameter=float(drill[1])
            position=tuple(transform(fp,first(pad,"at")[1:3]))
            result.append(dict(ref=ref,position_mm=position,diameter_mm=diameter))
    return result


def hole_obstacles(tree,relative=False):
    offset=100 if relative else 0
    # Ordinary foreign-copper routing adds0.2mm clearance. A further0.05mm
    # halo enforces the board's0.25mm copper-to-unplated-hole clearance.
    return [Point(x-offset,y-offset).buffer(row["diameter_mm"]/2+.05)
            for row in unplated_holes(tree) for x,y in [row["position_mm"]]]
