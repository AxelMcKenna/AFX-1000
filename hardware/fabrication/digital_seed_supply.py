"""Wide two-face Seed VIN feed, keeping through holes outside SMD copper."""
import json,math,uuid
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from hardware.fabrication.digital_power_finish import Screen
from hardware.fabrication.route_nf_surface import shape,candidate_paths
from hardware.fabrication.audit_candidate import sha
from hardware.electronics.common.sexpr import a,read_sexpr,sexpr
ROOT=Path(__file__).resolve().parent

def run():
    cp=ROOT/'staging/digital-plane-escape-inputs-286/capture.json';c=json.loads(cp.read_text())
    proof=ROOT/'staging/digital-power-finish-01/construction.json';d=json.loads(proof.read_text())
    for data in [c,d]:assert all(sha(Path(p))==h for p,h in data['source_sha256'].items())
    source=proof.parent/'digital_core.kicad_pcb';assert sha(source)==d['candidate_PCB_sha256']
    screen=Screen(c)
    screen.added=[(r['net'],r['face'],LineString(r['points_mm']),r['width_mm']) for r in d['routes']]
    net='/PROCESSOR/SEED_VIN';start=(40.855,23.);end=(12.54,26.76)
    copper=[(o,shape(ps)) for o in c['objects'] for l,ps in o['layers'].items() if ps]
    index=STRtree([g for o,g in copper]);drills=[(o['position_mm'],max(o['drill_mm'])/2) for o in c['objects'] if o['kind']=='PAD' and any(o['drill_mm'])]
    drills += [(o['position_mm'],.15) for o in c['objects'] if o['kind']=='PCB_VIA']
    def via_ok(xy):
        p=Point(xy)
        if not screen.outline.buffer(-.81).covers(p):return False
        for i in index.query(p.buffer(.52)):
            o,g=copper[int(i)]
            if o['net']!=net and p.distance(g)<.511:return False
            if o['kind']=='PAD' and not any(o['drill_mm']) and p.distance(g)<.301:return False
        if any(math.dist(xy,q)<r+.411 for q,r in drills):return False
        return all(n==net or p.distance(g)>.511+w/2 for n,l,g,w in screen.added)
    selected=None
    sites=sorted((math.hypot(dx,dy),round(start[0]+dx*.25,6),round(start[1]+dy*.25,6)) for dx in range(-20,21) for dy in range(-20,21) if dx or dy)
    attempted=0
    for _,x,y in sites:
        xy=(x,y)
        if not via_ok(xy):continue
        left=[]
        for p in candidate_paths(start,xy):
            p=[v for i,v in enumerate(p) if not i or v!=p[i-1]]
            if len(p)>1 and LineString(p).length<=5 and screen.legal(net,'B.Cu',p,1.):left.append(p)
        if not left:continue
        attempted+=1
        right=screen.route(net,'F.Cu',xy,end,1.)
        if right:selected=(xy,min(left,key=lambda p:LineString(p).length),right);break
        if attempted>=12:break
    assert selected,'No bounded wide two-face Seed supply route'
    xy,left,right=selected;board=read_sexpr(source.read_text());old,count=sexpr(board),len(board)
    for face,path in [('B.Cu',left),('F.Cu',right)]:
        for p,q in zip(path,path[1:]):
            ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:Seed:{sha(source)}:{face}:{p}:{q}'))
            board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),1.],[a('layer'),face],[a('net'),net],[a('uuid'),ident]])
    ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:Seedvia:{sha(source)}:{xy}'))
    board.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),ident]])
    assert sexpr(board[:count])==old
    out=ROOT/'staging/digital-seed-supply-01';out.mkdir(exist_ok=False);dest=out/source.name;dest.write_text(sexpr(board)+'\n')
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [source,cp,proof,Path(__file__),ROOT/'digital_power_finish.py',ROOT/'route_nf_surface.py']},candidate_PCB_sha256=sha(dest),
        net=net,paths={'B.Cu':left,'F.Cu':right},width_mm=1.,via_mm=xy,via_uuid=ident,length_mm=LineString(left).length+LineString(right).length,
        original_authored_geometry_exact=True,native_checks_pending=True,current_capacity_and_voltage_interval_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Seed feed',xy,'length',LineString(left).length+LineString(right).length,flush=True)

if __name__=='__main__':run()
