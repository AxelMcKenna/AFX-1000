"""Reserve mutually compatible conventional via exits for the swapped IC pins."""
import argparse,json,math,time,uuid
from pathlib import Path
from shapely.geometry import LineString,Point
from hardware.fabrication.nf_connected_fanout_routes import fanouts
from hardware.fabrication.nf_softstart_joint_screen import ExistingViaScreen
from hardware.fabrication.audit_candidate import sha
from hardware.electronics.common.sexpr import a,read_sexpr,sexpr
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as routing

ROOT=Path(__file__).resolve().parent

def compatible(a,b):
    same=a['net']==b['net'];pa,pb=a['point'],b['point'];distance=math.dist(pa,pb)
    if distance<=.86 and not(same and distance<1e-7):return False
    if same:return True
    la,lb=LineString(a['runs'][0][1]),LineString(b['runs'][0][1])
    return la.distance(lb)>.361 and la.distance(Point(pb))>.59 and lb.distance(Point(pa))>.59

def solve(options,seconds=30):
    deadline=time.monotonic()+seconds;cache={};visits=0
    def match(ka,ia,kb,ib):
        key=tuple(sorted(((ka,ia),(kb,ib))))
        if key not in cache:cache[key]=compatible(options[ka][ia],options[kb][ib])
        return cache[key]
    def search(domains,assigned):
        nonlocal visits
        visits+=1
        if time.monotonic()>deadline or visits>100000:return None
        if not domains:return assigned
        key=min(domains,key=lambda k:len(domains[k]))
        for index in domains[key]:
            left={k:[i for i in ids if match(key,index,k,i)] for k,ids in domains.items() if k!=key}
            if any(not ids for ids in left.values()):continue
            result=search(left,dict(assigned,**{key:index}))
            if result is not None:return result
        return None
    result=search({k:list(range(len(v))) for k,v in options.items()},{});return result,visits

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',required=True);ap.add_argument('--label',required=True);args=ap.parse_args();assert all(v and all(c.isalnum() or c in '-_' for c in v) for v in vars(args).values())
    cp=ROOT/'staging'/args.capture/'capture.json';c=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(source.read_text());original=sexpr(board);count=len(board)
    surface.WIDTH=routing.WIDTH=.16;surface.MARGIN=.001;screen=ExistingViaScreen(c);objects={o['uuid']:o for o in c['objects']};options={};missing=[];skip=[]
    for pad in c['objects']:
        if pad.get('ref') not in ['U38','U41'] or pad.get('pin') in ['7','14']:continue
        key=pad['ref']+'.'+pad['pin'];group=pad['group']
        if group is None or any(objects[u]['kind']=='PCB_VIA' or objects[u]['kind']=='PAD' and len(objects[u]['layers'])>1 for u in c['groups'][group]):skip.append(key);continue
        # This two-pad net is a short, direct same-side join, not a via demand.
        if pad['net']=='/N12_PCLR1':skip.append(key);continue
        choices=fanouts(screen,pad,limit=40)
        for row in choices:row['net']=pad['net'];row['ref']=pad['ref'];row['pin']=pad['pin']
        print('Pin choices',key,len(choices),flush=True)
        if choices:options[key]=sorted(choices,key=lambda p:p['cost'])
        else:missing.append(key)
    solution,visits=solve(options);out=ROOT/'staging'/args.label;out.mkdir(exist_ok=False)
    inputs=[source,cp,Path(__file__),*[ROOT/n for n in ['nf_connected_fanout_routes.py','nf_pin_escape_routes.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py','nf_minimum_logic.py','route_nf_surface.py']]]
    data=dict(source_sha256={str(p):sha(p) for p in inputs},candidate_counts={k:len(v) for k,v in options.items()},missing_pin_exits=missing,existing_access_or_direct_join=skip,search_visits=visits,all_nonempty_demands_allocated=solution is not None,native_checks_pending=True,fabrication_released=False)
    if solution is None:
        data['candidate_options']=options;(out/'plan.json').write_text(json.dumps(data,indent=2)+'\n');print('No complete compatible allocation',flush=True);return
    chosen=[options[k][v] for k,v in solution.items()];data['allocated_escapes']=chosen
    assert all(compatible(p,q) for i,p in enumerate(chosen) for q in chosen[i+1:])
    vias=set()
    for row in chosen:
        net=row['net']
        for layer,points in row['runs']:
            assert screen.legal(net,layer,points)
            for p,q in zip(points,points[1:]):
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:swap-pin:{sha(cp)}:{net}:{layer}:{p}:{q}'))
                board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.16],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
        pt=tuple(row['point']);assert screen.via_legal(net,pt)
        if (net,pt) not in vias:
            vias.add((net,pt));uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:swap-pin-via:{sha(cp)}:{net}:{pt}'))
            board.append([a('via'),[a('at'),*pt],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
    assert sexpr(board[:count])==original
    pcb=out/source.name;pcb.write_text(sexpr(board)+'\n');data['candidate_PCB_sha256']=sha(pcb);data['added_vias']=len(vias)
    (out/'construction.json').write_text(json.dumps(data,indent=2)+'\n');print('Allocated',len(chosen),'pin exits; missing',missing,flush=True)

if __name__=='__main__':run()
