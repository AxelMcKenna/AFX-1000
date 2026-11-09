"""Reroute the entire CONTROL13 net between its actual connector and IC pads."""
import copy,json,math,time,uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES
from hardware.fabrication.digital_costed_region_route_v3 import route
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_combine_costed_routes import center_vertices
from hardware.fabrication.digital_route_shortcuts import simplify
from hardware.fabrication.digital_native_route_cleanup import prune_single_face_vias
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

NET='/CONTROLS/CONTROL_13'


def run():
    cp=ROOT/'staging/digital-led10-closed-inputs-28/capture.json'
    cap=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
    pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    source=next(o for o in cap['objects'] if o.get('ref')=='J2001' and o.get('pin')=='14')
    target=next(o for o in cap['objects'] if o.get('ref')=='U2001' and o.get('pin')=='7')
    assert source['net']==target['net']==NET and source['position_mm']==[27.24,4.46] and target['position_mm']==[11.635,23.65]
    assert any(source['drill_mm']) and not any(target['drill_mm']) and target['layers'].get('B.Cu')
    retired_objects=[o for o in cap['objects'] if o['net']==NET and o['kind'] in ('PCB_TRACK','PCB_VIA')]
    removed={o['uuid'] for o in retired_objects}
    seeds=[o['position_mm'] for o in retired_objects if o['kind']=='PCB_VIA']
    old_length=sum(math.dist(o['position_mm'],o['end_mm']) for o in retired_objects if o['kind']=='PCB_TRACK')
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    screen=CloseMarginViaScreen(work,signal_layers=FACES)
    search=route(screen,NET,[(f,source['position_mm']) for f in FACES],[('B.Cu',target['position_mm'])],time.monotonic()+180,max_refinements=160,via_candidates=seeds)
    selected=None;centered=[];pruned=[]
    if search['route']:
        raw=search['route']
        normalized,centered=center_vertices(screen,dict(net=NET,runs=raw['runs'],new_vias_mm=raw['vias']),[])
        simplified=simplify(screen,NET,dict(runs=normalized['runs'],vias=normalized['new_vias_mm']))
        selected=add(screen,NET,simplified)
        routes,pruned=prune_single_face_vias(work,[selected]);selected=routes[0]
    emitted=bool(selected and selected['planar_length_mm']<old_length-1e-5)
    paths=[cp,pcb,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_costed_region_route.py','digital_costed_region_route_v2.py','digital_costed_region_route_v3.py','digital_polygon_path.py','digital_region_reachability.py','digital_planned_region_screen.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_combine_costed_routes.py','digital_route_shortcuts.py','digital_native_route_cleanup.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]+[ROOT.parent/'electronics/common/sexpr.py']
    out=ROOT/'staging/digital-control13-full-shortening-01';out.mkdir(exist_ok=False)
    report=dict(source_sha256={str(p):sha(p) for p in paths},candidate_emitted=emitted,search=search,removed_uuids=sorted(removed),
                routes=[selected] if selected else [],centered_vertices=centered,pruned_unused_vias=pruned,before_length_mm=old_length,
                before_via_count=len(seeds),expected_opens=28,native_rules_relaxed=False,electrical_performance_qualified=False,fabrication_released=False)
    if emitted:
        before=read_sexpr(pcb.read_text());board=copy.deepcopy(before)
        retired=[n for tag in ('segment','via') for n in children(board,tag) if first(n,'uuid')[1] in removed]
        assert len(retired)==len(removed)
        for n in retired:board.remove(n)
        for face,path in selected['runs']:
            for p,q in zip(path,path[1:]):
                if math.dist(p,q)<1e-7:continue
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:CONTROL13-FULL:{sha(cp)}:{face}:{p}:{q}'))
                board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),NET],[a('uuid'),uid]])
        for p in selected['new_vias_mm']:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:CONTROL13-FULL-VIA:{sha(cp)}:{p}'))
            board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),NET],[a('uuid'),uid]])
        dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
        report.update(candidate_PCB_sha256=sha(dest),removed_objects=retired,geometry_delta=geometry_delta(before,board),native_checks_pending=True)
    (out/'construction.json').write_text(json.dumps(report,indent=2)+'\n')
    print('CONTROL13 complete shortening:',emitted,old_length,'->',selected['planar_length_mm'] if selected else None,flush=True)


if __name__=='__main__':run()
