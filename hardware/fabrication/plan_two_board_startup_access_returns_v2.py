"""Provide nearby main-ground connections for the repaired control transitions."""
import json
import math
import copy
from pathlib import Path
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.plan_two_board_startup_access import CAP, BASE
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

PLAN=STAGING/'two-board-startup-access-plan-01/plan.json'
OUT=STAGING/'two-board-startup-access-plan-02'
SPACING=2.0


def relocate_aux(c,p,f,main,oldsite):
    net='PWR_V2V5_AUX'
    oldvia=next(o for o in c['objects'] if o['kind']=='PCB_VIA' and o['net']==net and o['position_mm']==oldsite)
    attached=[o for o in c['objects'] if o['kind']=='PCB_TRACK' and o['net']==net and o['uuid'] not in p['retired_objects'] and oldsite in [o['position_mm'],o['end_mm']]]
    assert attached
    replacement=[r for r in p['routes'] if r['net']==net and oldsite in [r['path_mm'][0],r['path_mm'][-1]]]
    assert replacement
    retired_now=set(p['retired_objects'])|{oldvia['uuid']}|{o['uuid'] for o in attached}
    routing.SIGNAL_LAYERS=tuple(c['copper_layers']);routing.WIDTH=.2
    source_screen=ViaScreen(dict(c,objects=[o for o in c['objects'] if o['uuid'] not in retired_now],zones=[]))
    for r in [x for x in p['routes'] if x not in replacement]+p['launches']:source_screen.added.append((r['net'],r.get('layer','B.Cu'),LineString(r['path_mm'])))
    for v in p['vias']:
        source_screen.vias.append((v['net'],v['position_mm']))
        for l in c['copper_layers']:source_screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
    relroutes=copy.deepcopy(replacement)
    for o in attached:
        l,=o['layers'];relroutes.append(dict(net=net,layer=l,width_mm=o['width_mm'],path_mm=[o['position_mm'],o['end_mm']],reference_layer={'F.Cu':'In1.Cu','B.Cu':'In6.Cu','In2.Cu':'In1.Cu','In3.Cu':'In4.Cu','In6.Cu':'In5.Cu'}[l],retired_uuids=[o['uuid']]))
    # The retired via's antipad is included as a predicted refill region;
    # the native audit must subsequently prove its actual ground coverage.
    required_refs={r['reference_layer'] for r in relroutes}
    ownholes=unary_union([Point(o['position_mm']).buffer(o['width_mm']/2+.215) for o in c['objects'] if o['kind']=='PCB_VIA' and o['net']==net])
    earlyquietpaths=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']
    earlyquietids={u for path in earlyquietpaths for q in json.loads(path.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
    earlyforbidden=unary_union([routing.shape(z['authored_outline']).buffer(.55) for z in c['zones'] if z['uuid'] in earlyquietids]+[routing.shape(z['polygons']).buffer(.55) for z in c['zones'] if z['net']!='PWR_AGND'])
    trialfields={l:f[l,main].buffer(.0015).union(ownholes) for l in required_refs}
    sites=sorted((math.dist(oldsite,[ix/4,iy/4]),[ix/4,iy/4]) for ix in range(math.floor((oldsite[0]-4)*4),math.ceil((oldsite[0]+4)*4)+1) for iy in range(math.floor((oldsite[1]-4)*4),math.ceil((oldsite[1]+4)*4)+1))
    selected=None
    for movement,site in sites:
        if movement>4 or earlyforbidden.intersects(Point(site)) or not source_screen.via_legal(net,site):continue
        candidates=[]
        for r in relroutes:
            start,end=r['path_mm'][0],r['path_mm'][-1]
            if start==oldsite:start=site
            if end==oldsite:end=site
            choices=[];field=trialfields[r['reference_layer']]
            for path in routing.candidate_paths(start,end):
                path=[x for i,x in enumerate(path) if not i or x!=path[i-1]];line=LineString(path)
                if source_screen.legal(net,r['layer'],path) and field.covers(line.buffer(r['width_mm']/2)):choices.append((line.length,path))
            if not choices:break
            length,path=min(choices);row=copy.deepcopy(r);row['path_mm']=path;row['length_mm']=length;candidates.append(row)
        if len(candidates)!=len(relroutes):continue
        count=len(source_screen.added);vc=len(source_screen.vias)
        for row in candidates:source_screen.added.append((net,row['layer'],LineString(row['path_mm'])))
        source_screen.vias.append((net,site))
        for l in c['copper_layers']:source_screen.added.append((net,l,Point(site).buffer(.2)))
        bridges=[]
        for ix in range(math.floor((site[0]-SPACING)*4),math.ceil((site[0]+SPACING)*4)+1):
            for iy in range(math.floor((site[1]-SPACING)*4),math.ceil((site[1]+SPACING)*4)+1):
                g=[ix/4,iy/4];point=Point(g);distance=math.dist(site,g)
                if distance>SPACING or earlyforbidden.intersects(point) or not all(f[l,main].covers(point.buffer(.31)) for l in required_refs):continue
                if source_screen.via_legal('PWR_AGND',g):bridges.append((distance,g))
        source_screen.added=source_screen.added[:count];source_screen.vias=source_screen.vias[:vc]
        if bridges:selected=(site,candidates,min(bridges));break
    assert selected,'No screened AUX relocation and ground pair found'
    newsite,relroutes,bridge=selected
    print('Relocated AUX',oldsite,newsite,'ground candidate',bridge,flush=True)
    p['routes']=[r for r in p['routes'] if r not in replacement]+relroutes
    p['retired_objects']=sorted(retired_now)
    p['vias'].append(dict(net=net,position_mm=newsite,size_mm=.6,drill_mm=.3,role='relocated AUX transition'))
    p.setdefault('relocated_aux_transitions',[]).append(dict(old_uuid=oldvia['uuid'],old_position_mm=oldsite,new_position_mm=newsite,retired_attached_tracks=[o['uuid'] for o in attached]))
    return p



def run():
    assert not OUT.exists()
    c=json.loads(CAP.read_text());p=json.loads(PLAN.read_text())
    for data in [c,p]:
        for n,h in data['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
    f,_=anchored_fields(c);main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
    p=relocate_aux(c,p,f,main,[134.5,159.])
    retired=set(p['retired_objects']);objects=[o for o in c['objects'] if o['uuid'] not in retired]
    holes={}
    for o in c['objects']:
        if o['kind']=='PCB_VIA':holes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
    holes={n:unary_union(v) for n,v in holes.items()}
    endpoints={}
    for r in p['routes']:
        for xy in [r['path_mm'][0],r['path_mm'][-1]]:
            if any(o['kind']=='PCB_VIA' and o['net']==r['net'] and math.dist(xy,o['position_mm'])<1e-6 for o in objects) or any(v['net']==r['net'] and math.dist(xy,v['position_mm'])<1e-6 for v in p['vias']):
                endpoints.setdefault((r['net'],tuple(xy)),set()).add(r['reference_layer'])
    layers=c['copper_layers'];unsupported=[]
    for (net,xy),refs in endpoints.items():
        for o in objects:
            if o['kind']!='PCB_TRACK' or o['net']!=net or not any(math.dist(xy,q)<1e-6 for q in [o['position_mm'],o['end_mm']]):continue
            layer,=o['layers'];i=layers.index(layer);adj={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)}
            # Measure the retained local copper outside its via antipad.
            line=LineString([o['position_mm'],o['end_mm']]);local=line.intersection(Point(xy).buffer(1.2)).buffer(o['width_mm']/2).difference(holes.get(net,Polygon()))
            candidates={l for (l,gid),g in f.items() if gid==main and l in adj and not local.is_empty and local.difference(g.buffer(.0015)).area<1e-6}
            if not local.is_empty and not candidates:unsupported.append(dict(track_uuid=o['uuid'],net=net,position_mm=xy,layer=layer))
            refs.update(candidates)
    assert not unsupported,unsupported
    routing.SIGNAL_LAYERS=tuple(layers);routing.WIDTH=.2
    screen=ViaScreen(dict(c,objects=objects,zones=[]))
    for r in [*p['routes'],*p['launches']]:screen.added.append((r['net'],r.get('layer','B.Cu'),LineString(r['path_mm'])))
    for v in p['vias']:
        screen.vias.append((v['net'],v['position_mm']))
        for l in layers:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
    quietpaths=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']
    quietids={u for path in quietpaths for q in json.loads(path.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
    forbidden=unary_union([routing.shape(z['authored_outline']).buffer(.55) for z in c['zones'] if z['uuid'] in quietids]+[routing.shape(z['polygons']).buffer(.55) for z in c['zones'] if z['net']!='PWR_AGND'])
    assert all(not forbidden.intersects(Point(r['new_position_mm'])) for r in p['relocated_aux_transitions'])
    isolated=unary_union([routing.shape(ps) for o in objects if o['net']=='PWR_AGND' and o['group']!=main for ps in o['layers'].values()]).buffer(.315)
    ground=[];transitions=[]
    for (net,xy),refs in sorted(endpoints.items()):
        # The AUX rail is a power-distribution node, not a logic edge. Its
        # board-level geometric target is 3 mm; logic transitions use 2 mm.
        # These targets do not substitute for loaded electrical qualification.
        spacing=3.0 if net=='PWR_V2V5_AUX' else SPACING
        if len(refs)==1:
            transitions.append(dict(net=net,position_mm=xy,reference_layers=sorted(refs),same_reference_plane=True));continue
        available=[]
        for o in objects:
            if o['kind']=='PCB_VIA' and o['net']=='PWR_AGND' and o['group']==main and not forbidden.intersects(Point(o['position_mm'])) and all(f[l,main].intersection(routing.shape(o['layers'][l])).area>1e-9 for l in refs):
                available.append((math.dist(xy,o['position_mm']),o['position_mm'],o['uuid']))
        for v in ground:
            if all(f[l,main].covers(Point(v['position_mm']).buffer(.31)) for l in refs):available.append((math.dist(xy,v['position_mm']),v['position_mm'],None))
        nearest=min(available,key=lambda x:x[0]) if available else None
        if nearest and nearest[0]<=spacing:
            d,site,u=nearest;transitions.append(dict(net=net,position_mm=xy,reference_layers=sorted(refs),ground_site_mm=site,ground_via_uuid=u,distance_mm=d,spacing_limit_mm=spacing));continue
        sites=sorted((math.dist(xy,(ix/4,iy/4)),[ix/4,iy/4]) for ix in range(math.floor((xy[0]-spacing)*4),math.ceil((xy[0]+spacing)*4)+1) for iy in range(math.floor((xy[1]-spacing)*4),math.ceil((xy[1]+spacing)*4)+1))
        found=None
        for d,site in sites:
            if d>spacing:continue
            point=Point(site)
            if forbidden.intersects(point) or isolated.intersects(point) or not all(f[l,main].covers(point.buffer(.31)) for l in refs):continue
            if screen.via_legal('PWR_AGND',site):found=(d,site);break
        if not found:
            nearby=[]
            for ix in range(math.floor((xy[0]-4)*4),math.ceil((xy[0]+4)*4)+1):
                for iy in range(math.floor((xy[1]-4)*4),math.ceil((xy[1]+4)*4)+1):
                    site=[ix/4,iy/4];point=Point(site);d=math.dist(xy,site)
                    if d>4 or forbidden.intersects(point) or isolated.intersects(point) or not all(f[l,main].covers(point.buffer(.31)) for l in refs):continue
                    if screen.via_legal('PWR_AGND',site):nearby.append((d,site))
            print('Closest wider-search ground sites',net,xy,sorted(nearby)[:4],'existing nearest',nearest,flush=True)
        assert found,(net,xy,refs,'no local ground bridge')
        d,site=found;v=dict(net='PWR_AGND',position_mm=site,size_mm=.6,drill_mm=.3,role='local reference transition stitch');ground.append(v)
        screen.vias.append(('PWR_AGND',site))
        for l in layers:screen.added.append(('PWR_AGND',l,Point(site).buffer(.2)))
        transitions.append(dict(net=net,position_mm=xy,reference_layers=sorted(refs),ground_site_mm=site,distance_mm=d,spacing_limit_mm=spacing,previous_nearest_mm=nearest[0] if nearest else None))
        print('Ground bridge',net,xy,site,sorted(refs),flush=True)
    sources=[Path(__file__),CAP,PLAN,*quietpaths,REPO/'hardware/fabrication/plan_two_board_startup_controls.py',REPO/'hardware/fabrication/plan_two_board_startup_access.py',REPO/'hardware/fabrication/route_two_board_power_layer_detours.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(p,source_sha256={str(s.relative_to(REPO)):sha(s) for s in sources},vias=p['vias']+ground,added_vias=len(p['vias'])+len(ground),ground_stitches=ground,reference_transitions=transitions,reference_transition_spacing_limits_mm=dict(logic=SPACING,AUX_power=3.0),transition_spacing_scope='Geometric layout targets: 2 mm logic, 3 mm AUX power. Not accepted signal-integrity, transient or thermal ratings.',native_validation_pending=True,fabrication_released=False)
    OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(signal_vias=len(p['vias']),ground_stitches=len(ground),reviewed_transition_sites=len(transitions))))


if __name__=='__main__':run()
