"""Route short opposite-side pin joins through one shared legal via."""
from hardware.fabrication.nf_pin_escape_routes import *


base_fanouts=fanouts

def fanouts(screen,pad,limit=32):
    result=base_fanouts(screen,pad,limit)
    if result:return result
    start=tuple(pad['position_mm']);layer=next(iter(pad['layers']));net=pad['net'];choices=[]
    for x in range(round((start[0]-4)/.2),round((start[0]+4)/.2)+1):
        for y in range(round((start[1]-4)/.2),round((start[1]+4)/.2)+1):
            point=(round(x*.2,6),round(y*.2,6))
            if math.dist(start,point)<=4 and screen.via_legal(net,point):choices.append(point)
    picked=[]
    for p in sorted(choices,key=lambda p:math.dist(start,p)):
        if all(math.dist(p,q)>=.59 for q in picked):picked.append(p)
        if len(picked)>=12:break
    for point in picked:
        path=screen.grid_path(net,layer,start,point,budget=20000)
        if path:
            print('Local detour escape',pad['ref'],pad['pin'],point,flush=True)
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
