"""Add actual legal via points in regions missed by the routing grid.

Each bridge includes independently screened surface leads to nearby grid
nodes. Copper rules, drill exclusions and layer access are unchanged.
"""
import math,time
import numpy as np
from shapely import contains_xy
from shapely.geometry import Point

def bridges(screen,net,xs,ys,layers,free,via_mask,deadline):
    height,width=len(ys),len(xs);size=height*width
    step=float(xs[1]-xs[0]);allowed=screen.via_outline.difference(screen.obstacles(net))
    parts=[allowed] if allowed.geom_type=='Polygon' else list(getattr(allowed,'geoms',[]))
    result={};points=[]
    for region in parts:
        if time.monotonic()>deadline:break
        if region.is_empty or region.geom_type!='Polygon' or region.area<1e-10:continue
        xmin,ymin,xmax,ymax=region.bounds
        ix0=max(0,int(math.ceil((xmin-xs[0])/step)));ix1=min(width,int(math.floor((xmax-xs[0])/step))+1)
        iy0=max(0,int(math.ceil((ymin-ys[0])/step)));iy1=min(height,int(math.floor((ymax-ys[0])/step))+1)
        if ix0<ix1 and iy0<iy1:
            yy,xx=np.nonzero(via_mask.reshape(height,width)[iy0:iy1,ix0:ix1])
            if len(xx) and contains_xy(region,xs[xx+ix0],ys[yy+iy0]).any():continue
        # No regular grid point can use this connected conventional-via area.
        samples=[region.representative_point(),region.centroid]
        for point in samples:
            p=(round(point.x,6),round(point.y,6))
            if p in points or not screen.via_legal(net,p):continue
            ix=round((p[0]-xs[0])/step);iy=round((p[1]-ys[0])/step);nodes=[]
            for li,face in enumerate(layers):
                candidates=[]
                for dx in range(-2,3):
                    for dy in range(-2,3):
                        x,y=ix+dx,iy+dy
                        if not (0<=x<width and 0<=y<height):continue
                        k=li*size+y*width+x
                        if not free[k]:continue
                        q=(round(float(xs[x]),6),round(float(ys[y]),6));d=math.dist(p,q)
                        candidates.append((d,k,q))
                for d,k,q in sorted(candidates):
                    if d<1e-7 or screen.legal(net,face,[p,q]):nodes.append((k,d));break
            if len(nodes)<2:continue
            points.append(p)
            for k,d in nodes:
                for other,e in nodes:
                    if k!=other:result.setdefault(k,[]).append((other,2.5+d+e,p))
    return result,points
