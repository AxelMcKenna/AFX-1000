"""Route open digital nets through screened local escapes and all four signal layers.

Only complete group joins are emitted. Existing geometry is immutable. This
planner is bounded and must be followed by independent native verification.
"""
import argparse,itertools,json,math,time,uuid
from pathlib import Path
from shapely.geometry import LineString
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.digital_native_spacing_search_v3 as search
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.audit_candidate import sha
from hardware.electronics.common.sexpr import a,children,read_sexpr,sexpr
ROOT=Path(__file__).resolve().parent


from hardware.fabrication.digital_continuous_escape_options_v3 import escape_options


def multilayer_portals(contacts,escaped,key):
    # Captured contacts stay on their real layers. Only a newly drilled via
    # grants additional layer access to a surface escape.
    out=[dict(point=p,layers=[face],runs=[],vias=[],cost=0.,group=key) for face,p in sorted(contacts)]
    for option in escaped:
        row=dict(option)
        if row['vias']:row['layers']=list(surface.SIGNAL_LAYERS)
        out.append(row)
    return out


def run():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',required=True);ap.add_argument('--label',required=True)
    ap.add_argument('--nets',nargs='+',required=True);ap.add_argument('--seconds',type=int,default=600);ap.add_argument('--per-route',type=int,default=30)
    args=ap.parse_args();assert 1<=args.seconds<=600 and 1<=args.per_route<=120
    for label in (args.capture,args.label):assert label and all(c.isalnum() or c in '-_' for c in label)
    cp=ROOT/'staging'/args.capture/'capture.json';c=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    pcb=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(pcb.read_text());original,count=sexpr(board),len(board)
    surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01
    surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu');search.LAYERS=surface.SIGNAL_LAYERS
    screen=DigitalViaScreen(c,signal_layers=surface.SIGNAL_LAYERS);objects={o['uuid']:o for o in c['objects']}
    open_nets={objects[ids[0]]['net'] for ids in c['groups'].values()};assert set(args.nets)<=open_nets
    deadline=time.monotonic()+args.seconds;routes=[];attempts=[];domains=[]
    for net in args.nets:
        if time.monotonic()>deadline:break
        assert net and not net.startswith('unconnected-') and net not in ('AGND','5V_DIG','V3V3_IO','/PROCESSOR/SEED_VIN','/PROCESSOR/V3V3_ANALOG')
        groups=[]
        for key,ids in c['groups'].items():
            if objects[ids[0]]['net']!=net:continue
            contacts=set()
            for uid in ids:
                o=objects[uid]
                for face in surface.SIGNAL_LAYERS:
                    if not o['layers'].get(face):continue
                    for xy in [o['position_mm']]+([o['end_mm']] if 'end_mm' in o else []):contacts.add((face,tuple(xy)))
            portals=escape_options(screen,net,contacts,key,min(deadline,time.monotonic()+20),target_layer='In5.Cu')
            if portals:
                portals=multilayer_portals(contacts,portals,key)
            domains.append(dict(net=net,group=key,contact_count=len(contacts),portal_count=len(portals),portals=portals))
            print('Access',net,key[:8],len(portals),'portals',flush=True)
            groups.append(dict(keys={key},portals=portals))
        failed=set()
        while len(groups)>1 and time.monotonic()<deadline:
            choices=[]
            for i,j in itertools.combinations(range(len(groups)),2):
                left,right=groups[i],groups[j];key=(tuple(sorted(left['keys'])),tuple(sorted(right['keys'])))
                if key in failed or not left['portals'] or not right['portals']:continue
                d=min(math.dist(p['point'],q['point']) for p in left['portals'] for q in right['portals']);choices.append((d,i,j,key))
            if not choices:break
            _,i,j,key=min(choices);left,right=groups[i],groups[j]
            result=search.route_multi(screen,net,left['portals'],{face:right['portals'] for face in search.LAYERS},min(deadline,time.monotonic()+args.per_route),max_visits=5000000)
            attempts.append(dict(net=net,groups=[list(key[0]),list(key[1])],found=bool(result)))
            if result is None:failed.add(key);continue
            assert all(screen.legal(net,face,path) for face,path in result['runs'])
            fresh=[tuple(p) for p in result['vias'] if not any(other==net and math.dist(p,q)<1e-7 for other,q in screen.vias+screen.new_vias)]
            assert all(screen.via_legal(net,p) for p in fresh)
            assert all(math.dist(p,q)>.56 for p,q in itertools.combinations(fresh,2))
            direct=[]
            for face,path in result['runs']:
                screen.added.append((net,face,LineString(path)))
                for p,q in zip(path,path[1:]):
                    if math.dist(p,q)<1e-7:continue
                    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:multilayer-escape:{sha(cp)}:{net}:{face}:{p}:{q}'))
                    board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),net],[a('uuid'),uid]])
                direct += [dict(point=p,layers=[face],runs=[],vias=[],cost=0.,group=min(left['keys'])) for p in path]
            for p in fresh:
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:multilayer-escape-via:{sha(cp)}:{net}:{p}'))
                board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),uid]])
                screen.new_vias.append((net,p));direct.append(dict(point=p,layers=list(search.LAYERS),runs=[],vias=[],cost=0.,group=min(left['keys'])))
            left['keys']|=right['keys'];left['portals']=direct+[p for p in left['portals']+right['portals'] if not p['vias']];groups.pop(j)
            result.update(net=net,new_vias_mm=fresh,planar_length_mm=sum(LineString(p).length for _,p in result['runs']));routes.append(result)
            print('Joined',net,round(result['planar_length_mm'],3),'mm',len(fresh),'new vias',flush=True)
    assert sexpr(board[:count])==original
    out=ROOT/'staging'/args.label;out.mkdir(exist_ok=False);dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
    inputs=[pcb,cp,Path(__file__)]+[ROOT/p for p in ['route_nf_surface.py','nf_minimum_logic.py','digital_continuous_escape_options_v3.py','digital_visibility_escape.py','nf_pin_escape_routes.py','digital_native_spacing_search_v3.py','digital_via_spacing_v2.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py']]
    with (out/'construction.json').open('x') as f:json.dump(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),routes=routes,attempts=attempts,access_domains=domains,added_segments=len(children(board,'segment'))-len(children(read_sexpr(original),'segment')),added_vias=len(screen.new_vias),source_geometry_exact=True,signal_layers=list(surface.SIGNAL_LAYERS),global_route_layers=list(search.LAYERS),width_mm=.2,minimum_screened_hole_edge_to_SMD_mm=.16,search_seconds=args.seconds,selected_nets=args.nets,native_checks_pending=True,physical_qualified=False,fabrication_released=False),f,indent=2);f.write('\n')
    print('Completed',len(routes),'joins from',len(attempts),'attempts',flush=True)
if __name__=='__main__':run()
