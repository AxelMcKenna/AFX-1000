"""Try LED70 with explicit SERIAL2, LED71 and BYPASS restoration obligations."""
import copy
import itertools
import json
import math
import time
import uuid
from pathlib import Path
from shapely.geometry import LineString
from shapely.ops import unary_union
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_polygon_path import route as planar_route
from hardware.fabrication.digital_region_reachability import reachability
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha, geometry_delta
from hardware.fabrication.digital_serial1_joint_repair import ROOT, FACES
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_screen_branch import branch
from hardware.fabrication.digital_serial1_joint_escape_survey import compatible
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_costed_region_route_v3 import route
from hardware.fabrication.digital_combine_costed_routes import center_vertices
from hardware.fabrication.digital_native_route_cleanup import prune_single_face_vias
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

LED='/LED/LED_70'
SERIAL='/LED/SERIAL_2'
REMOVED={'7e03dc2e-6f9f-5dd4-a4b5-9e2f7edb2cc3','8602846c-d284-5967-bc0c-9d355123234f','8b58276c-f669-50f1-b0a3-12523b18bc66','c2536eb1-6c53-598b-b984-ac13eb8bc4b7','e7d61ac3-4984-5a01-b3b6-f2915c82245d'}

REMOVED |= {'06f9e3d2-5a93-5ea4-a3ad-d7cbbd854198', '0bf7e4c4-4ee0-5bd5-b801-b3322145325b', '0ef23665-fca6-54e0-80cb-8c1a6887fea7'}
TASKS = [
    (SERIAL, 'F.Cu', (84.3,20.15), (88.231317,22.832103)),
    ('/LED/LED_71', 'In5.Cu', (84.,20.725), (87.2,24.)),
    ('BYPASS_SENSE', 'In3.Cu', (84.646505,19.716767), (84.757064,22.105205)),
]

def repair(screen, net, face, start, end, deadline):
    frozen = PlannedRegionScreen(screen, net)
    free = frozen.outline.difference(unary_union([g.buffer(d+.0005, quad_segs=32) for n,g,d in frozen.geometry[face] if n != net]))
    p = planar_route(frozen, net, face, start, end, free, deadline)
    if p:
        return dict(runs=[(face,p)],vias=[])
    starts=[(f,start) for f in FACES] if net=='/LED/LED_71' else [(face,start)]
    ends=[(f,end) for f in FACES] if net==SERIAL else [(face,end)]
    diagnostic=reachability(frozen,net,starts,ends,FACES)
    print(net, 'multilayer free space', diagnostic['connected'],flush=True)
    if not diagnostic['connected']:
        return None
    return route(screen,net,starts,ends,deadline,max_refinements=32)['route']


def run():
    cp=ROOT/'staging/digital-costed-shortening-inputs-30/capture.json'
    cap=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
    assert len([o for o in cap['objects'] if o['uuid'] in REMOVED]) == 8
    assert all(o['kind']=='PCB_TRACK' and o['net'] in {SERIAL,'/LED/LED_71','BYPASS_SENSE'} for o in cap['objects'] if o['uuid'] in REMOVED)
    work=copy.deepcopy(cap)
    work['objects']=[o for o in cap['objects'] if o['uuid'] not in REMOVED]
    surface.WIDTH=layers.WIDTH=.2
    surface.MARGIN=.001
    surface.SIGNAL_LAYERS=FACES
    base=CloseMarginViaScreen(work,signal_layers=FACES)
    source=next(o for o in cap['objects'] if o.get('ref')=='U3003' and o.get('pin')=='27')
    target=next(o for o in cap['objects'] if o.get('ref')=='J3004' and o.get('pin')=='2')
    assert source['net']==target['net']==LED and source['position_mm']==[82.75,21.375]
    ends=[(f,target['position_mm']) for f in FACES if target['layers'].get(f)]
    escapes=[]
    for x,y in itertools.product([round(84.25+i*.025,6) for i in range(17)],[round(21.275+i*.025,6) for i in range(9)]):
        p=(x,y)
        if not base.via_legal(LED,p):
            continue
        choices=[path for path in surface.candidate_paths(source['position_mm'],p) if base.legal(LED,'F.Cu',path)]
        if choices:
            path=min(choices,key=lambda p:LineString(p).length)
            escapes.append(dict(point=p,runs=[('F.Cu',path)],vias=[p],cost=LineString(path).length+2.5))
    selected=None
    attempts=[]
    deadline=time.monotonic()+240
    seen=set()
    for escape in sorted(escapes,key=lambda e:e['cost']):
        if time.monotonic()>=deadline or len(attempts)>=12:
            break
        signature=tuple(round(v,1) for v in escape['point'])
        if signature in seen:
            continue
        seen.add(signature)
        screen=branch(base)
        routes=[add(screen,LED,escape)]
        attempt=dict(via=escape['point'],repairs=[])
        attempts.append(attempt)
        for net,face,start,end in TASKS:
            result=repair(screen,net,face,start,end,min(deadline,time.monotonic()+55))
            attempt['repairs'].append(dict(net=net,found=bool(result)))
            print('via',escape['point'],net,'restored',bool(result),flush=True)
            if not result:
                break
            routes.append(add(screen,net,result))
        if len(routes)!=4:
            continue
        result=route(screen,LED,[(f,escape['point']) for f in FACES],ends,min(deadline,time.monotonic()+65),max_refinements=32)
        attempt['search']=result
        if result['route']:
            raw=result['route']
            proposed=dict(net=LED,runs=raw['runs'],new_vias_mm=raw['vias'])
            existing=[p for n,p in screen.vias+screen.new_vias if n==LED]
            normalized,changes=center_vertices(screen,proposed,existing)
            routes.append(add(screen,LED,dict(runs=normalized['runs'],vias=normalized['new_vias_mm'])))
            attempt['centered_vertices']=changes
            selected,pruned=prune_single_face_vias(work,routes)
            break
    pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    paths=[cp,pcb,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_screen_branch.py','digital_serial1_joint_escape_survey.py','digital_xlat_escape_repair.py','digital_costed_region_route.py','digital_costed_region_route_v2.py','digital_costed_region_route_v3.py','digital_combine_costed_routes.py','digital_native_route_cleanup.py','digital_planned_region_screen.py','digital_polygon_path.py','digital_region_reachability.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-led70-coordinated-detour-02'
    out.mkdir(exist_ok=False)
    report=dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=sorted(REMOVED),escapes=escapes,restoration_tasks=TASKS,
        attempts=attempts,candidate_emitted=bool(selected),native_rules_relaxed=False,fabrication_released=False)
    if selected:
        before=read_sexpr(pcb.read_text())
        board=copy.deepcopy(before)
        retired=[n for n in children(board,'segment') if first(n,'uuid')[1] in REMOVED]
        assert len(retired)==8
        for n in retired:
            board.remove(n)
        for r in selected:
            for face,path in r['runs']:
                for p,q in zip(path,path[1:]):
                    if math.dist(p,q)<1e-7:
                        continue
                    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:LED70-COORDINATED:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                    board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),r['net']],[a('uuid'),uid]])
            for p in r['new_vias_mm']:
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:LED70-COORDINATED-VIA:{sha(cp)}:{r["net"]}:{p}'))
                board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),r['net']],[a('uuid'),uid]])
        dest=out/pcb.name
        dest.write_text(sexpr(board)+'\n')
        report.update(candidate_PCB_sha256=sha(dest),routes=selected,pruned_unused_vias=pruned,removed_objects=retired,
                      geometry_delta=geometry_delta(before,board),expected_opens=29,native_checks_pending=True)
    (out/'construction.json').write_text(json.dumps(report,indent=2)+'\n')
    print('LED70 complete candidate:',bool(selected),flush=True)


if __name__=='__main__':
    run()
