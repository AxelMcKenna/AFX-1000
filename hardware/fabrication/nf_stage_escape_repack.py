"""Apply the explicit U39 watchdog/stage escape plan to a current capture."""
import argparse,json,math,uuid
from pathlib import Path
from shapely.geometry import LineString
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.nf_softstart_joint_screen import ExistingViaScreen
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
import hardware.fabrication.route_nf_surface as surface

ROOT=Path(__file__).resolve().parent

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',required=True);ap.add_argument('--label',required=True);args=ap.parse_args()
    assert all(v and all(ch.isalnum() or ch in '-_' for ch in v) for v in [args.capture,args.label])
    cp=ROOT/'staging'/args.capture/'capture.json';c=json.loads(cp.read_text())
    plan_path=ROOT/'staging/nf-stage-escape-plan-01/plan.json';plan=json.loads(plan_path.read_text())
    for data in [c,plan]:assert all(sha(Path(p))==h for p,h in data['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(source.read_text())
    ids=set(plan['removed_ids']);removed=[o for o in c['objects'] if o['uuid'] in ids]
    assert len(removed)==6 and all(o['net']=='/N12_WD_ARMED' for o in removed)
    nodes=[n for tag in ['segment','via'] for n in children(board,tag) if first(n,'uuid')[1] in ids]
    assert len(nodes)==6
    for n in nodes:board.remove(n)
    c['objects']=[o for o in c['objects'] if o['uuid'] not in ids]
    surface.WIDTH=.16;surface.MARGIN=.001;screen=ExistingViaScreen(c)
    routes=[dict(net='/N12_STAGE_ENABLED',runs=[['F.Cu',plan['stage_path']]],vias=[plan['stage_via']]),
            dict(net='/N12_WD_ARMED',runs=plan['watchdog']['runs']+plan['inner'],vias=plan['watchdog']['vias']+plan['extra_vias'])]
    for route in routes:
        net=route['net'];vias=sorted(set(tuple(p) for p in route['vias']))
        assert all(screen.legal(net,l,pts) for l,pts in route['runs'])
        assert all(screen.via_legal(net,p) for p in vias)
        assert all(math.dist(p,q)>.86 for i,p in enumerate(vias) for q in vias[i+1:])
        for layer,points in route['runs']:
            screen.added.append((net,layer,LineString(points)))
            for p,q in zip(points,points[1:]):
                assert math.dist(p,q)>1e-7
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:stage-repack:{sha(cp)}:{net}:{layer}:{p}:{q}'))
                board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.16],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
        for p in vias:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:stage-repack-via:{sha(cp)}:{net}:{p}'))
            board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
            screen.new_vias.append((net,p))
    out=ROOT/'staging'/args.label;out.mkdir(exist_ok=False);pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,cp,plan_path,Path(__file__),ROOT/'nf_softstart_joint_screen.py',ROOT/'nf_softstart_cell_routes.py',ROOT/'nf_minimum_logic.py',ROOT/'route_nf_surface.py']
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),removed_objects=nodes,routes=routes,additional_affected_net='/N12_WD_ARMED',native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Repacked six watchdog copper objects; added stage escape and rejoined both watchdog branches')

if __name__=='__main__':run()
