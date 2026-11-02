"""Restore displaced paths and route four local timing cells on six layers."""
import json
import math
import time
import uuid
from pathlib import Path
from shapely.geometry import LineString, Point
import hardware.fabrication.nf_minimum_logic as routing
import hardware.fabrication.route_nf_surface as surface
from hardware.fabrication.nf_ct_leaf_cleanup import prune_leaf_returns
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha

ROOT=Path(__file__).resolve().parent


def run():
    path=ROOT/'staging/nf-remote-timing-inputs-172/capture.json'
    c=json.loads(path.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'))
    board=read_sexpr(source.read_text())
    c['objects'],removed=prune_leaf_returns(c)
    ids={o['uuid'] for o in removed}
    ground_stubs={'8b6e7d47-92b8-4cbb-90e7-75888bbb5584','934ff358-94cb-4844-904b-dc3defce7e9b'}
    terminal_vias={'23a12ced-fd92-49e4-bf89-da68bf373671','d8140e96-c2f9-4914-86ac-7167ebe69e57'}
    for o in c['objects']:
        if o['uuid'] in terminal_vias:
            contacts=[q for q in c['objects'] if q['net']==o['net'] and q['uuid']!=o['uuid'] and
                      any(surface.shape(poly).distance(Point(o['position_mm']))<.00001 for poly in q['layers'].values())]
            assert {q['uuid'] for q in contacts}<=ground_stubs
    ids|=ground_stubs|terminal_vias
    c['objects']=[o for o in c['objects'] if o['uuid'] not in ids]
    removed_nodes=[]
    for n in list(children(board,'segment')+children(board,'via')):
        if first(n,'uuid')[1] in ids:removed_nodes.append(n);board.remove(n)
    assert len(removed_nodes)==len(ids)==21
    routing.WIDTH=surface.WIDTH=.2
    surface.MARGIN=.001
    screen=routing.LayerScreen(c)
    pads={(o['ref'],o['pin']):o for o in c['objects'] if o['kind']=='PAD'}
    plan_path=ROOT/'staging/nf-remote-timing-plan-01/plan.json';plan=json.loads(plan_path.read_text())
    tasks=[]
    for r in plan['placements']:
        for t in r['selected']['displaced_logic_tracks']:
            tasks.append(dict(name='restore:'+t['net'],net=t['net'],start=t['start_mm'],end=t['end_mm'],start_layer='B.Cu',end_layer='B.Cu'))
    for r in plan['placements']:
        row=r['selected'];ref=row['ref'];owner=row['owner']
        cap,target=pads[ref,'1'],pads[owner,row['owner_timing_pin']]
        assert cap['net']==target['net']
        tasks.append(dict(name=ref+':timing',net=cap['net'],start=target['position_mm'],end=cap['position_mm'],start_layer='F.Cu',end_layer='B.Cu'))
        if cap['net'].startswith('/N12_') and ref in ['C53','C54']:
            cap,target=pads[ref,'2'],pads[owner,row['owner_reference_pin']]
            assert cap['net']==target['net']=='/N12_P03_SRC'
            tasks.append(dict(name=ref+':return',net=cap['net'],start=target['position_mm'],end=cap['position_mm'],start_layer='F.Cu',end_layer='B.Cu'))
    results=[];failed=[]
    def append(task,runs,fresh):
        net=task['net']
        for layer,points in runs:
            screen.added.append((net,layer,LineString(points)))
            for start,end in zip(points,points[1:]):
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:remote-timing:{sha(path)}:{net}:{layer}:{start}:{end}'))
                board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),routing.WIDTH],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
        for pt in fresh:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:remote-timing-via:{sha(path)}:{net}:{pt}'))
            board.append([a('via'),[a('at'),*pt],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
            screen.new_vias.append((net,pt))
        results.append(dict(task=task,runs=runs,new_vias_mm=fresh,planar_length_mm=sum(LineString(p).length for l,p in runs)))
        print('Routed',task['name'],'vias',len(fresh),'length',round(results[-1]['planar_length_mm'],3),flush=True)
    for task in tasks:
        if not task['name'].startswith('restore:') and routing.WIDTH==.2:
            routing.WIDTH=surface.WIDTH=.16
            old=screen;screen=routing.LayerScreen(c)
            screen.added=[(n,l,g.buffer(.02)) for n,l,g in old.added];screen.new_vias=old.new_vias
        net=task['net']
        route=screen.route(net,task['start_layer'],task['start'],task['end_layer'],task['end'],time.monotonic()+35,budget=160000)
        if not route:failed.append(task);print('No route',task['name'],flush=True);continue
        runs,vias=routing.simplify(screen,net,route)
        fresh=[p for p in vias if not any(n==net and math.dist(p,q)<1e-7 for n,q in screen.vias+screen.new_vias)]
        assert all(screen.via_legal(net,p) for p in fresh)
        append(task,runs,fresh)
    ground=surface.shape([p for z in c['zones'] if z['net']=='/AGND' and z['layer']=='In1.Cu' and not z['keepout'] for p in z['polygons']]).buffer(-.35)
    for ref in ['C92','C95']:
        cap=pads[ref,'2'];start=cap['position_mm'];assert cap['net']=='/AGND';choices=[]
        for ix in range(-50,51):
            for iy in range(-50,51):
                pt=tuple(round(v+d/10,6) for v,d in zip(start,(ix,iy)))
                if math.dist(start,pt)<.8 or not ground.covers(Point(pt)) or not screen.via_legal('/AGND',pt):continue
                for route in surface.candidate_paths(start,pt):
                    if screen.legal('/AGND','B.Cu',route):choices.append((LineString(route).length,pt,route));break
        task=dict(name=ref+':ground',net='/AGND',start=start)
        if choices:
            _,pt,route=min(choices);append(task,[('B.Cu',route)],[pt])
        else:failed.append(task);print('No ground',ref,flush=True)
    out=ROOT/'staging/nf-remote-timing-routes-02';out.mkdir(exist_ok=False)
    pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,path,plan_path,Path(__file__),ROOT/'nf_ct_leaf_cleanup.py',ROOT/'nf_minimum_logic.py',ROOT/'route_nf_surface.py']
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),routes=results,failed=failed,removed_leaf_objects=removed_nodes,
        logic_and_capacitor_reference_width_mm=.16,restored_trace_width_mm=.2,numerical_planning_margin_mm=.001,new_via_mm=[.6,.3],native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')


if __name__=='__main__':run()
