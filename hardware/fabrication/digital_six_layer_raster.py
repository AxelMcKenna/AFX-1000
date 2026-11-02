"""Bounded six-layer signal completion with exact native-polygon screens."""
import argparse,itertools,json,math,time,uuid
from pathlib import Path
from shapely.geometry import LineString
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.nf_multilayer_raster_directed as search
from hardware.fabrication.nf_softstart_joint_screen import ExistingViaScreen
from hardware.fabrication.audit_candidate import sha
from hardware.electronics.common.sexpr import a,children,read_sexpr,sexpr

ROOT=Path(__file__).resolve().parent

def run():
    parser=argparse.ArgumentParser();parser.add_argument('--capture',required=True);parser.add_argument('--label',required=True)
    parser.add_argument('--seconds',type=int,default=240);parser.add_argument('--per-route',type=int,default=6);args=parser.parse_args()
    for value in [args.capture,args.label]:assert value and all(c.isalnum() or c in '-_' for c in value)
    assert 1<=args.seconds<=600 and 1<=args.per_route<=30
    cp=ROOT/'staging'/args.capture/'capture.json';c=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));b=read_sexpr(source.read_text());original,count=sexpr(b),len(b)
    surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2
    surface.MARGIN=.01;search.LAYERS=('F.Cu','In3.Cu','B.Cu')
    s=ExistingViaScreen(c,signal_layers=('F.Cu','In3.Cu','B.Cu'));objects={o['uuid']:o for o in c['objects']}
    nets=sorted({objects[ids[0]]['net'] for ids in c['groups'].values()},key=lambda n: ('SDMMC' not in n,not any(k in n for k in ['BCLK','/WS','_DATA']), 'POT_' not in n,n.startswith('/LED/LED_'),n))
    routes=[];attempts=[];deadline=time.monotonic()+args.seconds
    for net in nets:
        if time.monotonic()>deadline:break
        if not net or net.startswith('unconnected-') or net in ['AGND','5V_DIG','V3V3_IO','/PROCESSOR/SEED_VIN','/PROCESSOR/V3V3_ANALOG']:continue
        groups=[]
        for key,ids in c['groups'].items():
            if objects[ids[0]]['net']!=net:continue
            contacts=set()
            for uid in ids:
                o=objects[uid]
                for face in search.LAYERS:
                    if not o['layers'].get(face):continue
                    for xy in [o['position_mm']]+([o['end_mm']] if 'end_mm' in o else []):contacts.add((face,tuple(xy)))
            groups.append(dict(keys={key},contacts=contacts))
        failed=set()
        while len(groups)>1 and time.monotonic()<deadline:
            choices=[]
            for i,j in itertools.combinations(range(len(groups)),2):
                key=(tuple(sorted(groups[i]['keys'])),tuple(sorted(groups[j]['keys'])))
                if key in failed:continue
                dist=min(math.dist(p,q) for face,p in groups[i]['contacts'] for side,q in groups[j]['contacts'])
                choices.append((dist,i,j,key))
            if not choices:break
            dist,i,j,key=min(choices);left,right=groups[i],groups[j]
            def portal(face,point,key):return dict(point=point,layers=[face],runs=[],vias=[],cost=0.,group=key)
            starts=[portal(l,p,min(left['keys'])) for l,p in sorted(left['contacts'])]
            ends={l:[portal(l,p,min(right['keys'])) for side,p in sorted(right['contacts']) if side==l] for l in search.LAYERS}
            found=search.route_multi(s,net,starts,ends,min(deadline,time.monotonic()+args.per_route),max_visits=120000)
            attempts.append(dict(net=net,groups=[list(key[0]),list(key[1])],found=bool(found)))
            if not found:failed.add(key);continue
            assert all(s.legal(net,face,path) for face,path in found['runs'])
            fresh=[p for p in found['vias'] if not any(other==net and math.dist(p,q)<1e-7 for other,q in s.vias+s.new_vias)]
            assert all(s.via_legal(net,p) for p in fresh)
            for face,path in found['runs']:
                s.added.append((net,face,LineString(path)))
                for p,q in zip(path,path[1:]):
                    if math.dist(p,q)<1e-7:continue
                    ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:six-raster:{sha(cp)}:{net}:{face}:{p}:{q}'))
                    b.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),net],[a('uuid'),ident]])
                left['contacts']|={(face,tuple(p)) for p in path}
            for p in fresh:
                ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:six-rastervia:{sha(cp)}:{net}:{p}'))
                b.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),ident]])
                s.new_vias.append((net,p));left['contacts']|={(l,tuple(p)) for l in search.LAYERS}
            left['keys']|=right['keys'];left['contacts']|=right['contacts'];groups.pop(j)
            found.update(net=net,new_vias_mm=fresh,planar_length_mm=sum(LineString(p).length for l,p in found['runs']));routes.append(found)
            print('Signal route',net,round(found['planar_length_mm'],3),'mm',len(fresh),'new vias',flush=True)
    assert sexpr(b[:count])==original
    out=ROOT/'staging'/args.label;out.mkdir(exist_ok=False);dest=out/source.name;dest.write_text(sexpr(b)+'\n')
    inputs=[source,cp,Path(__file__)]+[ROOT/p for p in ['route_nf_surface.py','nf_minimum_logic.py','nf_pin_escape_routes.py','nf_multilayer_raster_directed.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py']]
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),routes=routes,attempts=attempts,
        added_segments=len(children(b,'segment'))-len(children(read_sexpr(original),'segment')),added_vias=len(s.new_vias),
        source_geometry_exact=True,signal_layers=list(search.LAYERS),width_mm=.2,minimum_screened_hole_edge_to_SMD_mm=.16,
        search_seconds=args.seconds,native_checks_pending=True,signal_integrity_and_fabrication_qualified=False),indent=2)+'\n')
    print('Completed',len(routes),'signal joins;',len(attempts),'attempts',flush=True)

if __name__=='__main__':run()
