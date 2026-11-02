"""Expand the bounded no-escape search to 12 mm, retaining exact segment checks."""
from hardware.fabrication.nf_pin_escape_routes import *

def local_grid_path(screen, net, layer, start, end, budget=100000):
    """Bounded surface detour with exact segment screens, including diagonals."""
    step = .05
    origin = tuple(round(v/step) for v in start)
    goal = tuple(round(v/step) for v in end)
    def xy(key):
        return tuple(round(v*step, 6) for v in key)
    if not screen.legal(net, layer, [start, xy(origin)]) or not screen.legal(net, layer, [xy(goal), end]):
        # Equal points need no bridge, whereas legal() rejects zero length.
        if (math.dist(start, xy(origin)) > 1e-6 and not screen.legal(net, layer, [start, xy(origin)])) or (math.dist(end, xy(goal)) > 1e-6 and not screen.legal(net, layer, [xy(goal), end])):
            return None
    lower = tuple(min(u, v)-100 for u, v in zip(origin, goal))
    upper = tuple(max(u, v)+100 for u, v in zip(origin, goal))
    queue = [(math.dist(origin, goal), 0., origin)]
    cost, parent, valid = {origin: 0.}, {}, {}
    visits = 0
    while queue and visits < budget:
        _, distance, key = heapq.heappop(queue)
        if distance > cost[key]+1e-9:
            continue
        visits += 1
        if key == goal:
            keys = [key]
            while key in parent:
                key = parent[key]
                keys.append(key)
            points = [tuple(start)]+[xy(k) for k in reversed(keys)]+[tuple(end)]
            points = [p for i, p in enumerate(points) if i == 0 or p != points[i-1]]
            # Keep only necessary turns; preserve exact source endpoints.
            simple = [points[0]]
            index = 0
            while index < len(points)-1:
                target = index+1
                for j in range(index+2, len(points)):
                    if screen.legal(net, layer, [points[index], points[j]]):
                        target = j
                simple.append(points[target])
                index = target
            assert screen.legal(net, layer, simple)
            return simple
        for dx, dy in itertools.product((-1, 0, 1), repeat=2):
            if dx == dy == 0:
                continue
            neighbor = (key[0]+dx, key[1]+dy)
            if not all(lo <= v <= hi for lo, v, hi in zip(lower, neighbor, upper)):
                continue
            candidate = distance+math.hypot(dx, dy)
            if candidate >= cost.get(neighbor, math.inf)-1e-9:
                continue
            edge = tuple(sorted((key, neighbor)))
            if edge not in valid:
                valid[edge] = screen.legal(net, layer, [xy(key), xy(neighbor)])
            if not valid[edge]:
                continue
            cost[neighbor], parent[neighbor] = candidate, key
            heapq.heappush(queue, (candidate+math.dist(neighbor, goal), candidate, neighbor))
    return None

import itertools
from scipy.ndimage import label as components
base_fanouts=fanouts

def fanouts(screen,pad,limit=32):
    result=base_fanouts(screen,pad,limit)
    if result:return result
    start=tuple(pad['position_mm']);layer=next(iter(pad['layers']));net=pad['net'];step=.05
    xs=np.arange(math.floor((start[0]-12)/step),math.ceil((start[0]+12)/step)+1)*step
    ys=np.arange(math.floor((start[1]-12)/step),math.ceil((start[1]+12)/step)+1)*step
    xx,yy=np.meshgrid(xs,ys)
    obstacles=[g.buffer(d) for n,g,d in screen.geometry[layer] if n!=net]
    obstacles += [g.buffer(WIDTH+surface.CLEARANCE+surface.MARGIN) for n,l,g in screen.added if l==layer and n!=net]
    obstacles += [Point(p).buffer(.3+WIDTH/2+.2+.01) for n,p in screen.new_vias if n!=net]
    free=contains_xy(screen.outline,xx,yy)&~contains_xy(unary_union(obstacles),xx,yy)
    labels,_=components(free,np.ones((3,3)))
    ix=round((start[0]-xs[0])/step);iy=round((start[1]-ys[0])/step);ident=labels[iy,ix]
    if ident==0:return result
    indexes=np.argwhere(labels==ident)
    choices=sorted(((float(xs[x]),float(ys[y])) for y,x in indexes),key=lambda p:math.dist(start,p))
    picked=[]
    for point in choices:
        if math.dist(start,point)>12 or any(math.dist(point,p)<.29 for p in picked):continue
        if screen.via_legal(net,point):picked.append(point)
        if len(picked)>=24:break
    print('Reachable-region via choices',pad['ref'],pad['pin'],len(picked),flush=True)
    for point in picked:
        path=local_grid_path(screen,net,layer,start,point)
        if path:
            print('Fine local escape',pad['ref'],pad['pin'],point,flush=True)
            result.append(dict(point=point,runs=[(layer,path)],vias=[point],cost=LineString(path).length,group=pad['group'],pad=[pad['ref'],pad['pin']]))
            if len(result)>=4:break
    return result

