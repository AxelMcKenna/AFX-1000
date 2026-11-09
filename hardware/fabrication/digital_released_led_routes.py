"""Jointly route LED13/14/16 in space released by full-net CONTROL13 shortening."""
import copy,itertools,json,math,time,uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_screen_branch import branch
from hardware.fabrication.digital_continuous_net_route import route
from hardware.fabrication.digital_combine_costed_routes import center_vertices
from hardware.fabrication.digital_route_shortcuts import simplify
from hardware.fabrication.digital_native_route_cleanup import prune_single_face_vias
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers


def run():
    cp=ROOT/'staging/digital-control13-shortened-inputs-28/capture.json'
    sp=ROOT/'staging/digital-remaining-region-survey-28-01/diagnosis.json'
    cap,survey=[json.loads(p.read_text()) for p in (cp,sp)]
    for r in (cap,survey):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    nets=sorted(survey['individually_connected_nets']);assert nets==['/LED/LED_13','/LED/LED_14','/LED/LED_16']
    assert not any(o['net'] in nets and o['kind'] in ('PCB_TRACK','PCB_VIA') for o in cap['objects'])
    pads={n:[o for o in cap['objects'] if o['net']==n and o['kind']=='PAD'] for n in nets}
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    base=CloseMarginViaScreen(cap,signal_layers=FACES);attempts=[];best=[];deadline=time.monotonic()+240
    for order in itertools.permutations(nets):
        if time.monotonic()>deadline:break
        screen=branch(base);selected=[];attempt=dict(order=order,results=[]);attempts.append(attempt)
        for net in order:
            if time.monotonic()>deadline:break
            source,target=sorted(pads[net],key=lambda o:any(o['drill_mm']))
            assert source['layers'].get('F.Cu') and any(target['drill_mm'])
            ends={(f,tuple(target['position_mm'])) for f in FACES}
            raw=route(screen,net,'F.Cu',source['position_mm'],ends,min(deadline,time.monotonic()+30),existing_crossings=[(target['position_mm'],list(FACES))])
            item=dict(net=net,found=bool(raw));attempt['results'].append(item)
            if raw:
                normalized,centred=center_vertices(screen,dict(net=net,runs=raw['runs'],new_vias_mm=raw['vias']),[])
                simple=simplify(screen,net,dict(runs=normalized['runs'],vias=normalized['new_vias_mm']))
                r=add(screen,net,simple);selected.append(r);item.update(length_mm=r['planar_length_mm'],via_count=len(r['new_vias_mm']),centered_vertices=centred)
            print('Order',len(attempts),item,flush=True)
        if len(selected)>len(best) or len(selected)==len(best) and sum(r['planar_length_mm'] for r in selected)<sum(r['planar_length_mm'] for r in best):best=selected
        if len(best)==len(nets):break
    best,pruned=prune_single_face_vias(cap,best)
    replay=branch(base)
    for r in best:add(replay,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
    pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    before=read_sexpr(pcb.read_text());board=copy.deepcopy(before)
    for r in best:
        for face,path in r['runs']:
            for p,q in zip(path,path[1:]):
                if math.dist(p,q)<1e-7:continue
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:RELEASED-LEDS:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),r['net']],[a('uuid'),uid]])
        for p in r['new_vias_mm']:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:RELEASED-LEDS-VIA:{sha(cp)}:{r["net"]}:{p}'))
            board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),r['net']],[a('uuid'),uid]])
    out=ROOT/'staging/digital-released-led-routes-01';out.mkdir(exist_ok=False)
    paths=[cp,sp,pcb,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_screen_branch.py','digital_continuous_net_route.py','digital_region_reachability.py','digital_polygon_path.py','digital_planned_region_screen.py','digital_combine_costed_routes.py','digital_route_shortcuts.py','digital_native_route_cleanup.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]+[ROOT.parent/'electronics/common/sexpr.py']
    report=dict(source_sha256={str(p):sha(p) for p in paths},candidate_emitted=bool(best),attempts=attempts,routes=best,pruned_unused_vias=pruned,
                removed_uuids=[],removed_objects=[],expected_opens=28-len(best),native_rules_relaxed=False,electrical_performance_qualified=False,fabrication_released=False)
    if best:
        dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
        report.update(candidate_PCB_sha256=sha(dest),geometry_delta=geometry_delta(before,board),native_checks_pending=True)
    (out/'construction.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Complete jointly screened nets:',[r['net'] for r in best],flush=True)


if __name__=='__main__':run()
