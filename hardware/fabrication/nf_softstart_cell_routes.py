"""Route the SS/TMR cell with explicit escapes and standard same-net via joints."""
import copy
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

class JointScreen(routing.LayerScreen):
    def via_legal(self,net,xy):
        point=Point(xy)
        if not self.via_outline.covers(point):return False
        for other,position in self.vias+self.new_vias:
            if math.dist(position,xy)<1e-7:return other==net
            if math.dist(position,xy)<=.86:return False
        for index in self.via_tree.query(point.buffer(.6)):
            other,obstacle,kind=self.via_geometry[int(index)]
            if other==net and kind=='PCB_TRACK':continue
            clearance=.41 if kind=='HOLE' else .31 if kind=='KEEPOUT' or other==net else .51
            if point.distance(obstacle)<=clearance:return False
        return all(other==net or point.distance(line)>.61 for other,_,line in self.added)



def run():
    path=ROOT/'staging/nf-remote-timing-inputs-172/capture.json'
    c=json.loads(path.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'))
    board=read_sexpr(source.read_text())
    base=ROOT/'staging/nf-ct-local-native-01/negative_startup_physical.kicad_pcb'
    base_capture=ROOT/'staging/nf-ct-local-inputs-166/capture.json'
    original=read_sexpr(base.read_text());old_c=json.loads(base_capture.read_text())
    assert all(sha(Path(p))==h for p,h in old_c['source_sha256'].items())
    restored_refs={'C92','C95'}
    def ref(f):return next(p[2] for p in children(f,'property') if p[1]=='Reference')
    for f in list(children(board,'footprint')):
        if ref(f) in restored_refs:
            replacement=next(x for x in children(original,'footprint') if ref(x)==ref(f))
            board[board.index(f)]=copy.deepcopy(replacement)
    c['objects']=[o for o in c['objects'] if o.get('ref') not in restored_refs]+[copy.deepcopy(o) for o in old_c['objects'] if o.get('ref') in restored_refs]
    extra_uid='67e998ce-2dfc-538b-9583-30ac9a324c81'
    extra=next(o for o in c['objects'] if o['uuid']==extra_uid)
    c['objects']=[o for o in c['objects'] if o['uuid']!=extra_uid]
    c['objects'],removed=prune_leaf_returns(c)
    ids={o['uuid'] for o in removed}
    ids.add(extra_uid)
    c['objects']=[o for o in c['objects'] if o['uuid'] not in ids]
    removed_nodes=[]
    for n in list(children(board,'segment')+children(board,'via')):
        if first(n,'uuid')[1] in ids:removed_nodes.append(n);board.remove(n)
    assert len(removed_nodes)==len(ids)==18
    routing.WIDTH=surface.WIDTH=.2
    surface.MARGIN=.001
    screen=JointScreen(c)
    pads={(o['ref'],o['pin']):o for o in c['objects'] if o['kind']=='PAD'}
    plan_path=ROOT/'staging/nf-remote-timing-plan-01/plan.json';plan=json.loads(plan_path.read_text());plan['placements']=[r for r in plan['placements'] if r['selected']['ref'] in {'C53','C54'}]
    tasks=[]
    for r in plan['placements']:
        for t in r['selected']['displaced_logic_tracks']:
            tasks.append(dict(name='restore:'+t['net'],net=t['net'],start=t['start_mm'],end=t['end_mm'],start_layer='B.Cu',end_layer='B.Cu'))
    tasks.append(dict(name='restore:front-fault',net=extra['net'],start=extra['position_mm'],end=extra['end_mm'],start_layer='F.Cu',end_layer='F.Cu'))
    for r in plan['placements']:
        row=r['selected'];ref=row['ref'];owner=row['owner']
        cap,target=pads[ref,'1'],pads[owner,row['owner_timing_pin']]
        assert cap['net']==target['net']
        tasks.append(dict(name=ref+':timing',net=cap['net'],start=([27.9,29.7] if ref=='C53' else [25.7,29.2]),end=cap['position_mm'],start_layer='In2.Cu',end_layer='B.Cu'))
        if cap['net'].startswith('/N12_') and ref in ['C53','C54']:
            cap,target=pads[ref,'2'],pads[owner,row['owner_reference_pin']]
            assert cap['net']==target['net']=='/N12_P03_SRC'
            tasks.append(dict(name=ref+':return',net=cap['net'],start=[22.3,26.4],end=cap['position_mm'],start_layer='B.Cu',end_layer='B.Cu'))
    results=[];failed=[]
    def append(task,runs,fresh):
        net=task['net']
        for layer,points in runs:
            screen.added.append((net,layer,LineString(points)))
            for start,end in zip(points,points[1:]):
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:remote-timing:{sha(path)}:{net}:{layer}:{start}:{end}'))
                board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),.2],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
        for pt in fresh:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:remote-timing-via:{sha(path)}:{net}:{pt}'))
            board.append([a('via'),[a('at'),*pt],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
            screen.new_vias.append((net,pt))
        results.append(dict(task=task,runs=runs,new_vias_mm=fresh,planar_length_mm=sum(LineString(p).length for l,p in runs)))
        print('Routed',task['name'],'vias',len(fresh),'length',round(results[-1]['planar_length_mm'],3),flush=True)
    escapes=[('/N12_SS',[[26.7875,27.35],[26.7875,29.7],[27.9,29.7]]),
             ('/N12_TMR',[[26.1525,27.35],[26.1525,29.2],[25.7,29.2]]),
             ('/N12_P03_SRC',[[22.3425,27.35],[22.3,26.4]])]
    for net,points in escapes:
        assert screen.legal(net,'F.Cu',points) and screen.via_legal(net,points[-1]),net
        append(dict(name='escape:'+net,net=net),[('F.Cu',points)],[points[-1]])
    for task in tasks:
        net=task['net']
        route=screen.route(net,task['start_layer'],task['start'],task['end_layer'],task['end'],time.monotonic()+35,budget=160000)
        if not route:failed.append(task);print('No route',task['name'],flush=True);continue
        runs,vias=routing.simplify(screen,net,route)
        fresh=[p for p in vias if not any(n==net and math.dist(p,q)<1e-7 for n,q in screen.vias+screen.new_vias)]
        assert all(screen.via_legal(net,p) for p in fresh)
        append(task,runs,fresh)
    out=ROOT/'staging/nf-softstart-cell-routes-01';out.mkdir(exist_ok=False)
    pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,path,base,base_capture,plan_path,Path(__file__),ROOT/'nf_ct_leaf_cleanup.py',ROOT/'nf_minimum_logic.py',ROOT/'route_nf_surface.py']
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),routes=results,failed=failed,removed_leaf_objects=removed_nodes,
        new_width_mm=.2,new_via_mm=[.6,.3],restored_unfinished_placements=['C92','C95'],same_net_track_via_joints_allowed=True,native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')


if __name__=='__main__':run()
