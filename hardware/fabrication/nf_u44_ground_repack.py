"""Move only U44's local ground escape to make room for two logic pin exits."""
import copy,json,math,uuid
from pathlib import Path
from shapely.geometry import LineString
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as routing
from hardware.fabrication.nf_softstart_joint_screen import ExistingViaScreen
from hardware.fabrication.audit_candidate import sha
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr

ROOT=Path(__file__).resolve().parent
REMOVED={'2f4bdde6-a413-4620-aaa4-b05be9d73512','e09a6184-0ffb-48bb-8e5f-6953d34299f4','87c603f4-4c4b-47b2-996a-2ef4c573cb11','faea1aca-4f9c-49ad-ba99-acefcedd13d6'}

def run():
    path=ROOT/'staging/nf-pin-escape-inputs-159/capture.json';c=json.loads(path.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(source.read_text())
    removed=[n for n in children(board,'segment')+children(board,'via') if first(n,'uuid')[1] in REMOVED]
    assert len(removed)==4 and all(first(n,'net')[-1]=='/AGND' for n in removed)
    for n in removed:board.remove(n)
    c['objects']=[o for o in c['objects'] if o['uuid'] not in REMOVED]
    surface.WIDTH=routing.WIDTH=.2;surface.MARGIN=.001;screen=ExistingViaScreen(c)
    net='/AGND';via=(143.0,7.1)
    paths=[('F.Cu',[(140.0875,6.8),via]),('B.Cu',[(144.2125,2.899999),(141.4875,3.9)])]
    print('via legal',screen.via_legal(net,via),'paths legal',[screen.legal(net,l,p) for l,p in paths],flush=True)
    assert screen.via_legal(net,via)
    assert all(screen.legal(net,l,p) for l,p in paths)
    for layer,points in paths:
        for p,q in zip(points,points[1:]):
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:U44-ground-repack:{sha(path)}:{layer}:{p}:{q}'))
            board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:U44-ground-repack-via:{sha(path)}:{via}'))
    board.append([a('via'),[a('at'),*via],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
    out=ROOT/'staging/nf-u44-ground-repack-01';out.mkdir(exist_ok=False);pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[path,source,Path(__file__),ROOT/'nf_softstart_joint_screen.py',ROOT/'nf_softstart_cell_routes.py',ROOT/'nf_minimum_logic.py',ROOT/'route_nf_surface.py']
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),removed_objects=removed,new_via_mm=[.6,.3],new_via_position_mm=via,new_tracks=paths,new_track_width_mm=.2,changed_net=net,all_component_poses_exact=True,native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')

if __name__=='__main__':run()
