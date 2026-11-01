"""Independent exact authored planar profiles, not ideal area-as-flow claims."""

import math


def clip(poly, axis, threshold, greater):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ina=(a[axis]>=threshold) if greater else (a[axis]<=threshold)
        inb=(b[axis]>=threshold) if greater else (b[axis]<=threshold)
        if ina:
            result.append(a)
        if ina!=inb:
            t=(threshold-a[axis])/(b[axis]-a[axis])
            result.append([a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])])
    return result


def area(poly):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2


def circle(radius,n,cx=0,cy=0):
    return [[cx+radius*math.cos(2*math.pi*i/n),cy+radius*math.sin(2*math.pi*i/n)] for i in range(n)]


def primitive_contracts():
    corner_loss=4-48*math.sin(2*math.pi/96)
    island=area(clip(circle(6,256,93.0871,168.9352),1,164,True))
    inlet=72*19+45*29-2*corner_loss-island
    guard=sum(area(clip(clip(circle(18.75,256),0,c-2,True),0,c+2,False)) for c in range(-15,16,5))
    exhaust=4*36-1.5**2*corner_loss
    return {
        "inlet_area_gauge":dict(volume=inlet*.1,bounds=[[38,154,0],[276.5,183,.1]]),
        "exhaust_area_gauge":dict(volume=exhaust*.1,bounds=[[0,0,0],[4,36,.1]]),
        "guard_area_gauge":dict(volume=guard*.1,bounds=[[-17,-18.75,0],[17,18.75,.1]]),
        "upper_gasket_geometry":dict(volume=(2*(2*(76+46.4)-8)+2*(2*(49+46.4)-8))*.5,bounds=[[36,142,-6.7],[278.5,188.4,-6.2]]),
    }


def primitive_errors(name,stats):
    p=primitive_contracts()[name]
    bad=[]
    if not math.isclose(stats["volume_mm3"],p["volume"],abs_tol=.002):
        bad.append("independent-primitive-volume-mismatch")
    if any(abs(a-b)>1e-4 for x,y in zip([stats["min_mm"],stats["max_mm"]],p["bounds"]) for a,b in zip(x,y)):
        bad.append("independent-primitive-bounds-mismatch")
    if not stats["closed_oriented_boundary"] or stats["degenerate_triangles_excluded"]:
        bad.append("invalid-primitive-boundary")
    return bad
