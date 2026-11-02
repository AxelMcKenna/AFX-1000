"""Local CT/return routing and the one explicitly displaced logic connection.

Only vacated leaf copper on the two local reference nets is pruned. This is a
planning candidate; full independent native verification is required.
"""
import json
import math
import time
import uuid
from pathlib import Path
from shapely.geometry import Point,LineString
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.nf_minimum_logic import LayerScreen,simplify,sha,WIDTH,DIAMETER,DRILL
from hardware.fabrication.route_nf_surface import shape

ROOT=Path(__file__).resolve().parent
REFERENCES={'/N12_P03_SRC','/N19_P03_SRC'}


def prune_leaf_returns(capture):
    active={o['uuid']:o for o in capture['objects']}
    geometry={(o['uuid'],layer):shape(polys) for o in capture['objects'] if o['net'] in REFERENCES for layer,polys in o['layers'].items()}
    removed=[]
    while True:
        selected=None
        for uid,o in active.items():
            if o['net'] not in REFERENCES or o['kind'] not in ('PCB_TRACK','PCB_VIA'):continue
            neighbours=[(k,v) for k,v in active.items() if k!=uid and v['net']==o['net']]
            if o['kind']=='PCB_TRACK':
                layer=next(iter(o['layers']))
                if any(not any(layer in v['layers'] and geometry[k,layer].distance(Point(pt))<.00001 for k,v in neighbours) for pt in [o['position_mm'],o['end_mm']]):
                    selected=uid;break
            else:
                # A via with contacts on fewer than two layers has no remaining
                # interlayer function. Reference nets have no filled zones.
                assert not any(z['net']==o['net'] and not z['keepout'] for z in capture['zones'])
                contact_layers={layer for k,v in neighbours for layer in v['layers'] if geometry[k,layer].distance(Point(o['position_mm']))<.00001}
                if len(contact_layers)<2:
                    selected=uid;break
        if selected is None:break
        removed.append(active.pop(selected))
        assert len(removed)<100,'Unexpectedly broad pruning'
    return list(active.values()),removed


def run():
    capture_path=ROOT/'staging/nf-ct-placement-inputs-173/capture.json';capture=json.loads(capture_path.read_text())
    assert all(sha(Path(p))==h for p,h in capture['source_sha256'].items())
    source=next(Path(p) for p in capture['source_sha256'] if p.endswith('.kicad_pcb'))
    board=read_sexpr(source.read_text())
    output=ROOT/'staging/nf-ct-routes-01';assert not output.exists()
    capture['objects'],removed=prune_leaf_returns(capture)
    ids={o['uuid'] for o in removed};removed_nodes=[]
    for node in list(children(board,'segment')+children(board,'via')):
        if first(node,'uuid')[1] in ids:removed_nodes.append(node);board.remove(node)
    assert len(removed_nodes)==len(ids)
    screen=LayerScreen(capture,signal_layers=('F.Cu','B.Cu'))
    pads={(o['ref'],o['pin']):o for o in capture['objects'] if o['kind']=='PAD'}
    plan_path=ROOT/'staging/nf-ct-placement-search-01/plan.json';plan=json.loads(plan_path.read_text());tasks=[]
    for entry in plan['placements']:
        row=entry['selected'];ref,owner=row['ref'],row['owner']
        for cap_pin,owner_pin in [('1','5'),('2','2')]:
            cap,target=pads[ref,cap_pin],pads[owner,owner_pin];assert cap['net']==target['net']
            tasks.append(dict(net=cap['net'],name=f'{ref}.{cap_pin}-{owner}.{owner_pin}',start=target['position_mm'],start_layer='F.Cu',end=cap['position_mm'],end_layer='B.Cu'))
    # Restore the displaced logic path first, so timing routing cannot strand it.
    for entry in plan['placements']:
        for t in entry['selected']['displaced_logic_tracks']:
            tasks.insert(0,dict(net=t['net'],name=t['uuid'],start=t['start_mm'],start_layer='B.Cu',end=t['end_mm'],end_layer='B.Cu'))
    results=[];failed=[]
    for task in tasks:
        net=task['net']
        path=screen.route(net,task['start_layer'],task['start'],task['end_layer'],task['end'],time.monotonic()+20,budget=110000)
        if not path:
            failed.append(task);print('No route',task['name'],flush=True);continue
        runs,vias=simplify(screen,net,path)
        fresh=[p for p in vias if not any(n==net and math.dist(p,q)<1e-7 for n,q in screen.vias+screen.new_vias)]
        assert all(screen.via_legal(net,p) for p in fresh)
        for layer,points in runs:
            screen.added.append((net,layer,LineString(points)))
            for start,end in zip(points,points[1:]):
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:local-CT:{sha(capture_path)}:{net}:{layer}:{start}:{end}'))
                board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),WIDTH],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
        for point in fresh:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:local-CT-via:{sha(capture_path)}:{net}:{point}'))
            board.append([a('via'),[a('at'),*point],[a('size'),DIAMETER],[a('drill'),DRILL],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
            screen.new_vias.append((net,point))
        results.append(dict(task=task,runs=runs,new_vias_mm=fresh,planar_length_mm=sum(LineString(p).length for l,p in runs)))
        print('Routed',task['name'],'vias',len(fresh),'length',round(results[-1]['planar_length_mm'],3),flush=True)
    output.mkdir();pcb=output/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,capture_path,plan_path,Path(__file__),ROOT/'nf_minimum_logic.py',ROOT/'route_nf_surface.py']
    (output/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),routes=results,failed=failed,removed_leaf_objects=removed_nodes,
        new_width_mm=WIDTH,new_via_mm=[DIAMETER,DRILL],native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Pruned',len(removed_nodes),'vacated reference leaf objects; routed',len(results),'of',len(tasks),'tasks',flush=True)


if __name__=='__main__':run()
