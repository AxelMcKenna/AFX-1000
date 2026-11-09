"""Repair In6 ground-reference access beneath the U22/U23/U28 logic banks."""
import json
import math
from collections import defaultdict
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, sha
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

BASE=STAGING/'two-board-power-startup-controls-native-03'
CAP=STAGING/'two-board-power-routing-inputs-startup-controls-03/capture.json'
SURVEY=STAGING/'two-board-startup-reference-access-01/survey.json'
OUT=STAGING/'two-board-startup-access-plan-01'
MAIN6='4b63f119-2e71-5d61-96f6-8b78a1f5c6cb'


def run():
    assert not OUT.exists()
    c=json.loads(CAP.read_text());survey=json.loads(SURVEY.read_text())
    for d in [c,survey]:
        for n,h in d['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    centers={prop(f,'Reference')[2]:list(map(float,first(f,'at')[1:3])) for f in children(board,'footprint')}
    objects={o['uuid']:o for o in c['objects']};zones={z['uuid']:z for z in c['zones']}
    fields,excluded=anchored_fields(c)
    buffered_fields={k:f.buffer(.0015) for k,f in fields.items()}
    main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
    surface_retired={o['uuid'] for o in c['objects'] if o['kind']=='PCB_TRACK' and o['net']=='/E_rail_disconnect/E28_OUT_ARM_BAR' and list(o['layers'])==['B.Cu']}
    assert len(surface_retired)==6
    bar=dict(net='/E_rail_disconnect/E28_OUT_ARM_BAR',layer='B.Cu',width_mm=.2,
        path_mm=[[125.7,148.8625],[125.7,147.5],[128.95,147.5],[128.95,148.8625]],reference_layer='In6.Cu',
        label='Move U22 latch feedback inside the package to free pins 2 through 5',retired_uuids=sorted(surface_retired))
    launches=[]
    for row in survey['pad_access']:
        if row['ref'] not in ['E_U22','E_U23','E_U28']:continue
        assert row['layer']=='B.Cu'
        xy=row['position_mm'];center=centers[row['ref']];axis=max([0,1],key=lambda i:abs(xy[i]-center[i]))
        end=list(xy);end[axis]+=math.copysign(2.5,xy[axis]-center[axis])
        path=[xy,end]
        if (row['ref'],row['pin'])==('E_U23','11'):
            path=[xy,[136.7,157.],[137.1,157.3],[138.3625,157.3]]
        launches.append(dict(ref=row['ref'],pin=row['pin'],net=row['net'],path_mm=path,width_mm=.2,previously_covered=row['covered']))
    routing.SIGNAL_LAYERS=('B.Cu',);routing.WIDTH=.2
    surface=ViaScreen(dict(c,objects=[o for o in c['objects'] if o['uuid'] not in surface_retired],zones=[]))
    assert surface.legal(bar['net'],'B.Cu',bar['path_mm']),'U22 internal feedback path blocked'
    surface.added.append((bar['net'],'B.Cu',LineString(bar['path_mm'])))
    blocked=[(r['ref'],r['pin']) for r in launches if not surface.legal(r['net'],'B.Cu',r['path_mm'])]
    assert not blocked,('B.Cu launch corridor requires a detour',blocked)
    target=unary_union([LineString(r['path_mm']).buffer(.1) for r in [*launches,bar]])
    holes={}
    for o in c['objects']:
        if o['kind']=='PCB_VIA':holes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
    holes={n:unary_union(v) for n,v in holes.items()}
    # Existing B.Cu/In5 traces that already have an In6 return must retain it.
    reserved=[target];references=[]
    for o in c['objects']:
        if o['uuid'] in surface_retired or o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND' or list(o['layers']) not in [['B.Cu'],['In5.Cu']]:continue
        band=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(holes.get(o['net'],Polygon()))
        if band.is_empty:continue
        for (l,gid),field in buffered_fields.items():
            if l=='In6.Cu' and band.difference(field).area<1e-6:
                reserved.append(band);references.append(dict(track_uuid=o['uuid'],ground_group=gid))
    protected=prep(unary_union([target.buffer(.435),unary_union(reserved[1:]).buffer(.315)]))
    target_keepout=target.buffer(.435)
    retired={o['uuid'] for o in c['objects'] if o['kind']=='PCB_TRACK' and o['net']!='PWR_AGND' and list(o['layers'])==['In6.Cu'] and LineString([o['position_mm'],o['end_mm']]).intersects(target_keepout)}
    assert retired
    alternate={'PWR_V2V5_AUX','PWR_ALL_RAILS_ALLOW'}
    # These crowded In6 corridors have no planar detour. Expand to existing
    # through-via terminals so their complete spans can use a signal layer.
    for net in alternate:
        rows=[o for o in c['objects'] if o['kind']=='PCB_TRACK' and o['net']==net and list(o['layers'])==['In6.Cu']]
        stops={tuple(o['position_mm']) for o in c['objects'] if o['kind']=='PCB_VIA' and o['net']==net}
        changed=True
        while changed:
            changed=False
            points={tuple(x) for o in rows if o['uuid'] in retired for x in [o['position_mm'],o['end_mm']]}-stops
            for o in rows:
                if o['uuid'] not in retired and any(tuple(x) in points for x in [o['position_mm'],o['end_mm']]):retired.add(o['uuid']);changed=True
    # A via under the reserved launch cannot be repaired by moving traces alone.
    for o in c['objects']:
        if o['kind']=='PCB_VIA' and o['net']!='PWR_AGND':
            assert Point(o['position_mm']).distance(target)>o['width_mm']/2+.215,(o['uuid'],'via blocks a launch')
    bynet=defaultdict(list)
    for u in retired:bynet[objects[u]['net']].append(objects[u])
    tasks=[]
    for net,rows in bynet.items():
        graph=defaultdict(set)
        for o in rows:
            a,b=tuple(o['position_mm']),tuple(o['end_mm']);graph[a].add(b);graph[b].add(a)
        pending=set(graph)
        while pending:
            connected={min(pending)};todo=list(connected)
            while todo:
                a=todo.pop()
                for b in graph[a]-connected:connected.add(b);todo.append(b)
            pending-=connected;ends=sorted(v for v in connected if len(graph[v])==1)
            assert (net in alternate and len(ends)>=2) or (len(ends)==2 and all(len(graph[v])<=2 for v in connected)),(net,ends)
            used=[o for o in rows if tuple(o['position_mm']) in connected]
            for xy in connected-set(ends):
                for other in c['objects']:
                    if other['net']!=net or other['uuid'] in retired or not other['layers'].get('In6.Cu'):continue
                    g=routing.shape(other['layers']['In6.Cu'])
                    if Point(xy).distance(g)<1e-6:
                        assert other['kind']=='PCB_VIA' and any(Point(end).distance(g)<1e-6 for end in ends),(net,xy,'intermediate connection')
            old_length=sum(math.dist(o['position_mm'],o['end_mm']) for o in used)
            if net in alternate:
                terminals={tuple(o['position_mm']) for o in c['objects'] if o['kind']=='PCB_VIA' and o['net']==net}
                assert set(ends)<=terminals
                connected_ends={ends[0]};remaining=set(ends[1:])
                while remaining:
                    distance,a,b=min((math.dist(a,b),a,b) for a in connected_ends for b in remaining)
                    tasks.append(dict(net=net,start=list(a),end=list(b),retired_uuids=[o['uuid'] for o in used],old_length_mm=old_length,alternate_layer=True))
                    connected_ends.add(b);remaining.remove(b)
            else:tasks.append(dict(net=net,start=list(ends[0]),end=list(ends[1]),retired_uuids=[o['uuid'] for o in used],old_length_mm=old_length))
    quietpaths=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']
    quietids={u for p in quietpaths for q in json.loads(p.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
    quiet=prep(unary_union([routing.shape(z['authored_outline']).buffer(.435) for u,z in zones.items() if u in quietids and z['layer']=='In6.Cu']))
    other_protected={l:[] for l in ['In2.Cu','In3.Cu','F.Cu']};via_bands=[target]
    layers=c['copper_layers']
    for o in c['objects']:
        if o['uuid'] in retired|surface_retired or o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
        layer,=o['layers'];i=layers.index(layer);adj={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)}
        band=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(holes.get(o['net'],Polygon()))
        if band.is_empty:continue
        for (l,gid),field in buffered_fields.items():
            if l in adj and band.difference(field).area<1e-6:
                via_bands.append(band)
                if l in other_protected:other_protected[l].append(band)
    other_protected={l:prep(unary_union(v).buffer(.315)) for l,v in other_protected.items()}
    routing.SIGNAL_LAYERS=('In6.Cu','In2.Cu','In3.Cu','F.Cu');routing.WIDTH=.2
    supplies={l:prep(unary_union([routing.shape(z['polygons']) for z in c['zones'] if z['layer']==l and z['net']!='PWR_AGND']).buffer(.315)) for l in routing.SIGNAL_LAYERS}
    via_forbidden=prep(unary_union([unary_union(via_bands).buffer(.64),unary_union([routing.shape(z['polygons']) for z in c['zones'] if z['net']!='PWR_AGND']).buffer(.55),unary_union([routing.shape(z['authored_outline']) for u,z in zones.items() if u in quietids]).buffer(.52)]))
    quiet_layers={l:prep(unary_union([routing.shape(z['authored_outline']).buffer(.435) for u,z in zones.items() if u in quietids and z['layer']==l])) for l in routing.SIGNAL_LAYERS}
    cache={}
    class Screen(ViaScreen):
        def via_legal(self,net,xy):
            return not via_forbidden.intersects(Point(xy)) and super().via_legal(net,xy)
        def legal(self,net,layer,points):
            line=LineString(points)
            if (protected if layer=='In6.Cu' else other_protected[layer]).intersects(line) or quiet_layers[layer].intersects(line) or supplies[layer].intersects(line):return False
            key=(net,layer);reference={'In6.Cu':'In5.Cu','In3.Cu':'In4.Cu','In2.Cu':'In1.Cu','F.Cu':'In1.Cu'}[layer]
            if key not in cache:cache[key]=prep(buffered_fields[reference,main].union(holes.get(net,Polygon())).buffer(-.100001))
            if not cache[key].covers(line):return False
            return super().legal(net,layer,points)
    screen=Screen(dict(c,objects=[o for o in c['objects'] if o['uuid'] not in retired|surface_retired],zones=[]))
    routes=[bar];failed=[];vias=[]
    for task in sorted(tasks,key=lambda t:(t['net']!='PWR_V2V5_AUX',t['old_length_mm'],t['net'])):
        net,start,end=task['net'],task['start'],task['end'];limit=task['old_length_mm']*1.8+8
        choices=['In2.Cu','F.Cu','In3.Cu','In6.Cu'] if task.get('alternate_layer') else ['In6.Cu']
        best=None;layer=None
        for candidate in choices:
            route=screen.simple(net,candidate,start,end,limit)
            if route is None:
                path=screen.grid_path(net,candidate,start,end,budget=40000)
                if path and LineString(path).length<=limit:route=(LineString(path).length,path)
            if route is not None:best=route;layer=candidate;break
        if best is None:
            if net=='PWR_NF_GLOBAL_MASTER':
                left=screen.escapes(net,'In6.Cu',start);right=screen.escapes(net,'In6.Cu',end)
                pairs=sorted((a[0]+math.dist(a[1],b[1])+b[0],a,b) for a in left for b in right if math.dist(a[1],b[1])>.81)
                detour=None
                for lower,a,b in pairs:
                    if lower>limit or detour and lower>=detour[0]:continue
                    for midlayer in ['In2.Cu','F.Cu','In3.Cu']:
                        middle=screen.simple(net,midlayer,a[1],b[1],limit-a[0]-b[0])
                        if middle:
                            length=a[0]+middle[0]+b[0]
                            if detour is None or length<detour[0]:detour=(length,[('In6.Cu',a[2]),(midlayer,middle[1]),('In6.Cu',list(reversed(b[2])))],[a[1],b[1]])
                if detour:
                    length,paths,positions=detour
                    for l,path in paths:
                        routes.append(dict(task,layer=l,width_mm=.2,path_mm=path,length_mm=LineString(path).length,reference_layer={'In6.Cu':'In5.Cu','In3.Cu':'In4.Cu','In2.Cu':'In1.Cu','F.Cu':'In1.Cu'}[l]))
                        screen.added.append((net,l,LineString(path)))
                    for site in positions:
                        vias.append(dict(net=net,position_mm=site,size_mm=.6,drill_mm=.3));screen.vias.append((net,site))
                        for l in routing.SIGNAL_LAYERS:screen.added.append((net,l,Point(site).buffer(.2)))
                    print('Two-via detour',net,round(length,3),positions,flush=True);continue
            chosen=None
            step=.5 if math.dist(start,end)<20 else 1.
            sites=sorted((math.dist(start,(ix*step,iy*step))+math.dist(end,(ix*step,iy*step)),[ix*step,iy*step]) for ix in range(math.floor((min(start[0],end[0])-3)/step),math.ceil((max(start[0],end[0])+3)/step)+1) for iy in range(math.floor((min(start[1],end[1])-3)/step),math.ceil((max(start[1],end[1])+3)/step)+1))
            searched=0
            for lower,site in sites:
                if lower>limit or chosen and lower>=chosen[0]:continue
                if not screen.via_legal(net,site):continue
                searched+=1
                if searched>160:break
                firsts=[(l,screen.simple(net,l,start,site,limit)) for l in choices]
                seconds=[(l,screen.simple(net,l,site,end,limit)) for l in choices]
                for la,pa in firsts:
                    for lb,pb in seconds:
                        if la==lb or pa is None or pb is None:continue
                        length=pa[0]+pb[0]
                        if length<=limit and (chosen is None or length<chosen[0]):chosen=(length,site,[(la,pa[1]),(lb,pb[1])])
            if chosen:
                length,site,paths=chosen
                for l,path in paths:
                    routes.append(dict(task,layer=l,width_mm=.2,path_mm=path,length_mm=LineString(path).length,reference_layer={'In6.Cu':'In5.Cu','In3.Cu':'In4.Cu','In2.Cu':'In1.Cu','F.Cu':'In1.Cu'}[l]))
                    screen.added.append((net,l,LineString(path)))
                vias.append(dict(net=net,position_mm=site,size_mm=.6,drill_mm=.3));screen.vias.append((net,site))
                for l in routing.SIGNAL_LAYERS:screen.added.append((net,l,Point(site).buffer(.2)))
                print('Bridged',net,site,round(length,3),flush=True);continue
            failed.append(task);print('Deferred',net,start,end,flush=True);continue
        length,path=best;routes.append(dict(task,layer=layer,width_mm=.2,path_mm=path,length_mm=length,reference_layer={'In6.Cu':'In5.Cu','In3.Cu':'In4.Cu','In2.Cu':'In1.Cu','F.Cu':'In1.Cu'}[layer]))
        screen.added.append((net,layer,LineString(path)));print('Detour',net,layer,round(task['old_length_mm'],3),'to',round(length,3),flush=True)
    assert not failed,failed
    extension=target.buffer(.6)
    for o in c['objects']:
        if o['net']=='PWR_AGND' and o['group']!=main and o['layers'].get('In6.Cu'):
            extension=extension.difference(routing.shape(o['layers']['In6.Cu']).buffer(.215))
    for u,z in zones.items():
        if u!=MAIN6 and z['layer']=='In6.Cu' and z['net']=='PWR_AGND':extension=extension.difference(routing.shape(z['authored_outline']).buffer(.215))
    outline=routing.shape(zones[MAIN6]['authored_outline']).union(extension).simplify(.00001,preserve_topology=True)
    assert outline.geom_type=='Polygon' and outline.is_valid
    assert outline.covers(target)
    sources=[Path(__file__),CAP,SURVEY,BASE/'power_protection.kicad_pcb',*quietpaths,REPO/'hardware/fabrication/plan_two_board_startup_controls.py',REPO/'hardware/fabrication/route_two_board_power_layer_detours.py',REPO/'hardware/fabrication/route_two_board_power_local_v2.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},launches=launches,retired_objects=sorted(retired|surface_retired),routes=routes,
        main_In6_outline=dict(outer_mm=list(outline.exterior.coords),holes_mm=[list(r.coords) for r in outline.interiors]),
        prior_In6_reference_bands=references,excluded_unanchored_fragments=excluded,vias=vias,added_vias=len(vias),expected_opens=2167,
        reference_fill_margin_mm=.125,native_validation_pending=True,fabrication_released=False)
    OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(launches=len(launches),previously_uncovered=sum(not x['previously_covered'] for x in launches),retired_tracks=len(retired),detours=len(routes),new_tracks=sum(len(r['path_mm'])-1 for r in routes))))


if __name__=='__main__':run()
