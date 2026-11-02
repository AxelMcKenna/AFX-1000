"""Join same-layer signal groups on the six-layer candidate using screened paths."""
import itertools,json,math,time,uuid
from pathlib import Path
from shapely.geometry import LineString
from hardware.fabrication.route_nf_surface import Screen
from hardware.fabrication.route_nf_surface import candidate_paths
from hardware.fabrication.audit_candidate import sha
from hardware.electronics.common.sexpr import a,read_sexpr,sexpr
ROOT=Path(__file__).resolve().parent

def run():
    cp=ROOT/'staging/digital-six-inputs-130/capture.json';c=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'))
    b=read_sexpr(source.read_text());original,count=sexpr(b),len(b);s=Screen(c)
    objects={o['uuid']:o for o in c['objects']};routes=[];deferred=[];deadline=time.monotonic()+180
    nets=sorted({objects[ids[0]]['net'] for ids in c['groups'].values()} - {'AGND','5V_DIG','V3V3_IO','/PROCESSOR/SEED_VIN','/PROCESSOR/V3V3_ANALOG'},key=lambda n: ('LED_' not in n,n))
    for net in nets:
        groups=[]
        for ids in c['groups'].values():
            if objects[ids[0]]['net']!=net:continue
            contacts=set()
            for uid in ids:
                o=objects[uid]
                for face in ['In3.Cu','F.Cu','B.Cu']:
                    if not o['layers'].get(face):continue
                    contacts.add((face,tuple(o['position_mm'])))
                    if 'end_mm' in o:contacts.add((face,tuple(o['end_mm'])))
            groups.append(contacts)
        while len(groups)>1 and time.monotonic()<deadline:
            options=[]
            for i,j in itertools.combinations(range(len(groups)),2):
                pairs=sorted((math.dist(p,q),face,p,q) for face,p in groups[i] for side,q in groups[j] if side==face)
                options += [(dist,i,j,face,p,q) for dist,face,p,q in pairs[:5]]
            options.sort();chosen=None
            for lower,i,j,face,p,q in options:
                if chosen and lower>=chosen[0]:break
                for path in candidate_paths(p,q):
                    path=[v for k,v in enumerate(path) if not k or v!=path[k-1]]
                    length=LineString(path).length
                    if length>lower*2+4 or (chosen and length>=chosen[0]):continue
                    if s.legal(net,face,path):chosen=(length,i,j,face,path)
            if chosen is None:
                for lower,i,j,face,p,q in options[:8]:
                    if time.monotonic()>=deadline:break
                    path=None
                    if path:chosen=(LineString(path).length,i,j,face,path);break
            if chosen is None:break
            length,i,j,face,path=chosen
            for p,q in zip(path,path[1:]):
                ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:six-direct:{sha(cp)}:{net}:{face}:{p}:{q}'))
                b.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),net],[a('uuid'),ident]])
            s.added.append((net,face,LineString(path)))
            groups[i]|=groups[j]|{(face,tuple(p)) for p in path};groups.pop(j)
            routes.append(dict(net=net,face=face,points_mm=path,width_mm=.2,length_mm=length))
            print(net,'groups',len(groups),'route',round(length,3),flush=True)
        deferred.append(dict(net=net,remaining_screened_groups=len(groups),contacts=[sorted(g) for g in groups]))
    assert sexpr(b[:count])==original
    out=ROOT/'staging/digital-six-direct-01';out.mkdir(exist_ok=False);dest=out/source.name;dest.write_text(sexpr(b)+'\n')
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [source,cp,Path(__file__),ROOT/'route_nf_surface.py']},candidate_PCB_sha256=sha(dest),routes=routes,deferred=deferred,original_authored_geometry_exact=True,native_checks_pending=True,current_capacity_noise_and_return_paths_qualified=False,fabrication_released=False),indent=2)+'\n')

if __name__=='__main__':run()
