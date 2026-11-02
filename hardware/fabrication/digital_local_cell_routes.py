"""Route declared short DC01 local cells; conventional vias avoid SMD lands."""
import itertools,json,math,uuid
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import Screen,shape,candidate_paths

ROOT=Path(__file__).resolve().parent

def run():
    cp=ROOT/'staging/digital-power-cell-inputs-466/capture.json';capture=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in capture['source_sha256'].items())
    source=next(Path(p) for p in capture['source_sha256'] if p.endswith('.kicad_pcb'))
    plan=ROOT/'staging/digital-power-cell-plan-01/plan.json';rows=json.loads(plan.read_text())['placements']
    pcb=read_sexpr(source.read_text());original=sexpr(pcb);count=len(pcb)
    screen=Screen(capture);pads={(o['ref'],o['pin']):o for o in capture['objects'] if o['kind']=='PAD' and o.get('pin')}
    copper=[(o,shape(ps)) for o in capture['objects'] for layer,ps in o['layers'].items() if ps]
    copper_index=STRtree([g for o,g in copper]);drills=[o for o in capture['objects'] if o['kind']=='PAD' and any(o['drill_mm'])]
    smd=[shape(ps) for o in capture['objects'] if o['kind']=='PAD' and not any(o['drill_mm']) for layer,ps in o['layers'].items() if layer in ['F.Cu','B.Cu'] and ps]
    smd_index=STRtree(smd);vias=[];routed=[];deferred=[]
    def via_ok(net,xy):
        point=Point(xy)
        if not shape(capture['outline']).buffer(-.81).covers(point):return False
        for i in copper_index.query(point.buffer(.52)):
            other,g=copper[int(i)]
            if other['net']!=net and point.distance(g)<.511:return False
        if any(point.distance(smd[int(i)])<.301 for i in smd_index.query(point.buffer(.302))):return False
        if any(math.dist(xy,o['position_mm'])<.15+max(o['drill_mm'])/2+.261 for o in drills):return False
        if any(math.dist(xy,v['xy'])<(.561 if v['net']==net else .811) for v in vias):return False
        for other,layer,g in screen.added:
            if other!=net and point.distance(g)<.611:return False
        return True
    def path_for(net,layer,start,end,limit):
        paths=[]
        for path in candidate_paths(start,end):
            path=[p for i,p in enumerate(path) if not i or p!=path[i-1]]
            if len(path)<2:continue
            length=sum(math.dist(p,q) for p,q in zip(path,path[1:]))
            if length<=limit and screen.legal(net,layer,path):paths.append((length,path))
        return min(paths,key=lambda x:x[0]) if paths else None
    def add_track(net,layer,path):
        for start,end in zip(path,path[1:]):
            ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:local:{sha(source)}:{net}:{layer}:{start}:{end}'))
            pcb.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),.2],[a('layer'),layer],[a('net'),net],[a('uuid'),ident]])
        screen.added.append((net,layer,LineString(path)))
    for row in rows:
        p=pads[(row['ref'],'1')];q=pads[(row['owner'],row['owner_pin'])];assert p['net']==q['net'];net=p['net']
        start,end=tuple(p['position_mm']),tuple(q['position_mm']);limit=2*row['maximum_project_pin_distance_mm']+2
        chosen=None
        for layer in ['F.Cu','B.Cu']:
            if layer not in p['layers'] or layer not in q['layers']:continue
            result=path_for(net,layer,start,end,limit)
            if result and (chosen is None or result[0]<chosen[0]):chosen=(result[0],[(layer,result[1])],None)
        if chosen is None:
            pl=next(l for l in ['F.Cu','B.Cu'] if l in p['layers']);ql=next(l for l in ['F.Cu','B.Cu'] if l in q['layers'])
            if pl!=ql:
                cx,cy=[(x+y)/2 for x,y in zip(start,end)]
                sites=sorted((math.dist(start,(ix/4,iy/4))+math.dist(end,(ix/4,iy/4)),(ix/4,iy/4))
                             for ix in range(math.floor((cx-4)*4),math.ceil((cx+4)*4)+1)
                             for iy in range(math.floor((cy-4)*4),math.ceil((cy+4)*4)+1))
                for lower,xy in sites:
                    if lower>limit or (chosen and lower>=chosen[0]):continue
                    if not via_ok(net,xy):continue
                    left=path_for(net,pl,start,xy,limit);right=path_for(net,ql,xy,end,limit)
                    if left and right and left[0]+right[0]<=limit:
                        chosen=(left[0]+right[0],[(pl,left[1]),(ql,right[1])],xy)
        if chosen is None:
            deferred.append(dict(ref=row['ref'],owner=row['owner'],net=net,reason='No bounded local path meeting copper/drill screens'));continue
        length,paths,via=chosen
        for layer,path in paths:add_track(net,layer,path)
        if via:
            ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:localvia:{sha(source)}:{net}:{via}'))
            pcb.append([a('via'),[a('at'),*via],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),ident]])
            vias.append(dict(uuid=ident,net=net,xy=via))
            for layer in ['F.Cu','B.Cu']:screen.added.append((net,layer,Point(via).buffer(.2)))
        routed.append(dict(ref=row['ref'],owner=row['owner'],owner_pin=row['owner_pin'],net=net,length_mm=length,paths=paths,via_mm=via))
        print('Local route',row['ref'],round(length,3),'mm',flush=True)
    assert sexpr(pcb[:count])==original
    out=ROOT/'staging/digital-local-cell-routes-01';out.mkdir(exist_ok=False);dest=out/source.name;dest.write_text(sexpr(pcb)+'\n')
    inputs=[source,cp,plan,Path(__file__),ROOT/'route_nf_surface.py']
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),
        routes=routed,added_vias=vias,deferred=deferred,original_authored_geometry_exact=True,
        all_signal_tracks_on_outer_layers=True,minimum_screened_hole_edge_to_SMD_copper_mm=.151,
        ground_returns_power_distribution_and_thermal_paths_unfinished=True,native_checks_pending=True,fabrication_released=False),indent=2)+'\n')
    print('Routed',len(routed),'local cells;',len(deferred),'deferred;',len(vias),'conventional vias')

if __name__=='__main__':run()
