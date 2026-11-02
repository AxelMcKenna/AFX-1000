"""Route short opposite-side pin joins through one shared legal via."""
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
    xs=np.arange(math.floor((start[0]-5)/step),math.ceil((start[0]+5)/step)+1)*step
    ys=np.arange(math.floor((start[1]-5)/step),math.ceil((start[1]+5)/step)+1)*step
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
        if math.dist(start,point)>5 or any(math.dist(point,p)<.29 for p in picked):continue
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

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);ap.add_argument('--capture',required=True);ap.add_argument('--ref',default='U44');ap.add_argument('--pins',default='1,8,9,11,12');ap.add_argument('--seconds',type=int,default=30);args=ap.parse_args()
    assert args.label and all(c.isalnum() or c in '-_' for c in args.label)
    out=ROOT/'staging'/args.label;assert not out.exists()
    capture_path=ROOT/'staging'/args.capture/'capture.json';c=json.loads(capture_path.read_text())
    assert all(sha(p)==d for p,d in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(source.read_text());original=sexpr(board);count=len(board)
    surface.WIDTH=routing.WIDTH=WIDTH;surface.MARGIN=.001
    screen=ExistingViaScreen(c);routes=[];attempts=[]
    for pin in args.pins.split(','):
        pad=next(o for o in c['objects'] if o.get('ref')==args.ref and o.get('pin')==pin);net=pad['net']
        print('Planning '+args.ref+'.'+pin,net,flush=True)
        starts=fanouts(screen,pad);ends={l:[] for l in INNER}
        others=[o for o in c['objects'] if o['net']==net and o['group']!=pad['group']]
        for obj in others:
            for layer in INNER:
                if layer in obj['layers']:
                    for point in [obj['position_mm']]+([obj['end_mm']] if 'end_mm' in obj else []):
                        ends[layer].append(dict(point=tuple(point),runs=[],vias=[],cost=0,group=obj['group']))
        # Explicit escapes are needed for isolated surface target pads too.
        for obj in others:
            if obj['kind']=='PAD' and len(obj['layers'])==1:
                for portal in fanouts(screen,obj,limit=16):
                    for layer in INNER:ends[layer].append(portal)
        found=None
        shared=[]
        for start in starts:
            for obj in others:
                if obj['kind']!='PAD':continue
                for layer in obj['layers']:
                    if layer not in surface.SIGNAL_LAYERS:continue
                    for path in surface.candidate_paths(tuple(obj['position_mm']),start['point']):
                        path=[p for i,p in enumerate(path) if i==0 or p!=path[i-1]]
                        if screen.legal(net,layer,path):
                            shared.append(dict(runs=start['runs']+[(layer,path)],vias=start['vias'],groups=[start['group'],obj['group']],portals=[start['point']],search_visits=0))
                            break
        if shared:found=min(shared,key=lambda r:sum(LineString(p).length for l,p in r['runs']))
        for layer in INNER:
            if found:break
            if starts and ends[layer]:found=route_layer(screen,net,layer,starts,ends[layer],time.monotonic()+args.seconds)
            if found:break
        attempts.append(dict(pin=pin,net=net,start_portals=len(starts),end_portals={l:len(e) for l,e in ends.items()},found=bool(found)))
        if not found:print('No route',pin,flush=True);continue
        assert all(screen.legal(net,l,p) for l,p in found['runs'])
        vias=sorted(set(tuple(p) for p in found['vias']))
        assert all(screen.via_legal(net,p) for p in vias)
        assert all(math.dist(p,q)>.86 for i,p in enumerate(vias) for q in vias[i+1:])
        for layer,points in found['runs']:
            screen.added.append((net,layer,LineString(points)))
            for p,q in zip(points,points[1:]):
                if math.dist(p,q)<1e-7:continue
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:pin-escape:{sha(capture_path)}:{net}:{layer}:{p}:{q}'))
                board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),WIDTH],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
        for p in vias:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:pin-escape-via:{sha(capture_path)}:{net}:{p}'))
            board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
            screen.new_vias.append((net,p))
        found.update(net=net,pin=pin,new_vias_mm=vias,planar_length_mm=sum(LineString(p).length for l,p in found['runs']));routes.append(found)
        print('Planned',pin,layer,round(found['planar_length_mm'],3),'mm',len(vias),'vias',flush=True)
    assert sexpr(board[:count])==original
    out.mkdir();pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,capture_path,Path(__file__),ROOT/'nf_pin_escape_routes.py',ROOT/'nf_pin_escape_continue.py',ROOT/'nf_pin_escape_shared.py',ROOT/'route_nf_surface.py',ROOT/'nf_minimum_logic.py',ROOT/'nf_softstart_joint_screen.py',ROOT/'nf_softstart_cell_routes.py']
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),routes=routes,attempts=attempts,route_count=len(routes),all_original_objects_exact=True,new_width_mm=WIDTH,new_via_mm=[.6,.3],reserved_planes_have_no_new_tracks=True,raster_step_mm=STEP,raster_extra_margin_mm=RASTER_MARGIN,native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Finished',len(routes),'routes',flush=True)

if __name__=='__main__':run()
