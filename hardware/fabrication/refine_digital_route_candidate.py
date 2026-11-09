"""Replay and shorten a complete proposal without changing its restoration scope."""
import argparse,copy,json,math,uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_route_shortcuts import simplify
from hardware.fabrication.digital_combine_costed_routes import center_vertices
from hardware.fabrication.digital_native_route_cleanup import prune_single_face_vias
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers


def run():
    parser=argparse.ArgumentParser()
    for key in ('source','capture','label'):parser.add_argument('--'+key,required=True)
    args=parser.parse_args()
    assert all(v and all(c.isalnum() or c in '-_' for c in v) for v in vars(args).values())
    rp=ROOT/'staging'/args.source/'construction.json';cp=ROOT/'staging'/args.capture/'capture.json'
    recipe,cap=[json.loads(p.read_text()) for p in (rp,cp)]
    assert recipe['candidate_emitted']
    for r in (recipe,cap):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    assert str(cp) in recipe['source_sha256']
    removed=set(recipe['removed_uuids'])
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
    assert len(cap['objects'])-len(work['objects'])==len(removed)
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    full=CloseMarginViaScreen(work,signal_layers=FACES)
    for r in recipe['routes']:add(full,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
    proposed=[];changes=[]
    for r in recipe['routes']:
        vias=[p for n,p in full.vias+full.new_vias if n==r['net']]
        normalized,centred=center_vertices(full,r,vias)
        short=simplify(full,r['net'],dict(runs=normalized['runs'],vias=normalized['new_vias_mm']))
        proposed.append(dict(net=r['net'],runs=short['runs'],new_vias_mm=short['vias']))
        changes.append(dict(net=r['net'],before_mm=r['planar_length_mm'],centered_vertices=centred))
    proposed,pruned=prune_single_face_vias(work,proposed)
    replay=CloseMarginViaScreen(work,signal_layers=FACES)
    routes=[add(replay,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm'])) for r in proposed]
    for row,r in zip(changes,routes):row['after_mm']=r['planar_length_mm']
    pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    before=read_sexpr(pcb.read_text());board=copy.deepcopy(before)
    retired=[n for tag in ('segment','via') for n in children(board,tag) if first(n,'uuid')[1] in removed]
    assert len(retired)==len(removed) and retired==recipe['removed_objects']
    for n in retired:board.remove(n)
    for r in routes:
        for face,path in r['runs']:
            for p,q in zip(path,path[1:]):
                if math.dist(p,q)<1e-7:continue
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:REFINED:{sha(rp)}:{r["net"]}:{face}:{p}:{q}'))
                board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),r['net']],[a('uuid'),uid]])
        for p in r['new_vias_mm']:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:REFINED-VIA:{sha(rp)}:{r["net"]}:{p}'))
            board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),r['net']],[a('uuid'),uid]])
    out=ROOT/'staging'/args.label;out.mkdir(exist_ok=False);dest=out/pcb.name
    dest.write_text(sexpr(board)+'\n')
    paths=[rp,cp,pcb,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_route_shortcuts.py','digital_combine_costed_routes.py','digital_native_route_cleanup.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]+[ROOT.parent/'electronics/common/sexpr.py']
    report=dict(source_sha256={str(p):sha(p) for p in paths},candidate_emitted=True,candidate_PCB_sha256=sha(dest),
                removed_uuids=sorted(removed),removed_objects=retired,routes=routes,refinement_changes=changes,pruned_unused_vias=pruned,
                geometry_delta=geometry_delta(before,board),expected_opens=recipe['expected_opens'],native_checks_pending=True,
                native_rules_relaxed=False,electrical_performance_qualified=False,fabrication_released=False)
    (out/'construction.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(changes),flush=True)


if __name__=='__main__':run()
