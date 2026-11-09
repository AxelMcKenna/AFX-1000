"""Add local main-ground stitches at startup signal reference-layer changes."""
import json
import math
from pathlib import Path
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.plan_two_board_startup_controls import CAP, anchored_fields
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

PLAN=STAGING/'two-board-startup-control-plan-03/plan.json'
OUT=STAGING/'two-board-startup-control-plan-04'
SPACING=1.5


def run():
    assert not OUT.exists()
    c=json.loads(CAP.read_text());p=json.loads(PLAN.read_text())
    for data in [c,p]:
        for n,h in data['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
    fields,_=anchored_fields(c);main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
    routing.SIGNAL_LAYERS=tuple(c['copper_layers']);routing.WIDTH=.2
    screen=ViaScreen(dict(c,zones=[]))
    for r in p['routes']:screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
    for v in p['vias']:
        screen.vias.append((v['net'],v['position_mm']))
        for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
    # The two master-enable branches can share the first through-via. Remove
    # the redundant return-layer transition and B.Cu spur, then screen the
    # replacement inner path against the complete candidate's copper.
    net='/E_rail_disconnect/E28_MASTER_ENABLE';retired_site=[80.,116.];shared_site=[79.5,117.5]
    middle=next(r for r in p['routes'] if r['net']==net and r['layer']=='In2.Cu' and r['path_mm'][-1]==retired_site)
    tail=next(r for r in p['routes'] if r['net']==net and r['layer']=='B.Cu' and r['path_mm'][0]==retired_site)
    options=[]
    for path in routing.candidate_paths(middle['path_mm'][0],shared_site):
        path=[pt for i,pt in enumerate(path) if not i or pt!=path[i-1]]
        line=LineString(path)
        if screen.legal(net,'In2.Cu',path) and fields['In1.Cu',main].buffer(.0015).covers(line.buffer(.1)):
            options.append((line.length,path))
    assert options,'shared master-enable via detour needs a different corridor'
    previous_middle=middle['path_mm'];middle['path_mm']=min(options)[1]
    p['routes'].remove(tail)
    p['vias']=[v for v in p['vias'] if not(v['net']==net and v['position_mm']==retired_site)]
    # Add the replacement path to the obstacle screen. Retired same-net copper
    # remains conservatively screened against subsequent ground-stitch sites.
    screen.added.append((net,'In2.Cu',LineString(middle['path_mm'])))
    quietpaths=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']
    quietids={u for f in quietpaths for q in json.loads(f.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
    forbidden=unary_union([routing.shape(z['authored_outline']).buffer(.52) for z in c['zones'] if z['uuid'] in quietids])
    transition_positions=[]
    for v in p['vias']:
        refs={r['reference_layer'] for r in p['routes'] if r['net']==v['net'] and any(math.dist(v['position_mm'],pt)<1e-6 for pt in [r['path_mm'][0],r['path_mm'][-1]])}
        if len(refs)>1:transition_positions.append(v['position_mm'])
    transitions=[];stitches=[]
    for v in p['vias']:
        xy=v['position_mm'];references={r['reference_layer'] for r in p['routes'] if r['net']==v['net'] and any(math.dist(xy,pt)<1e-6 for pt in [r['path_mm'][0],r['path_mm'][-1]])}
        assert references
        if len(references)==1:
            transitions.append(dict(net=v['net'],position_mm=xy,reference_layers=sorted(references),same_reference_plane=True));continue
        assert references=={'In1.Cu','In6.Cu'}
        existing=[]
        for o in c['objects']:
            if o['kind']=='PCB_VIA' and o['net']=='PWR_AGND' and o['group']==main and all(fields[l,main].intersection(routing.shape(o['layers'][l])).area>1e-9 for l in references):
                existing.append((math.dist(xy,o['position_mm']),o['uuid'],o['position_mm']))
        for stitch in stitches:existing.append((math.dist(xy,stitch['position_mm']),None,stitch['position_mm']))
        distance,uid,pos=min(existing,key=lambda x:x[0])
        if distance<=SPACING:
            transitions.append(dict(net=v['net'],position_mm=xy,reference_layers=sorted(references),existing_ground_via_uuid=uid,ground_via_mm=pos,distance_mm=distance));continue
        candidates=sorted((math.dist(xy,(ix/4,iy/4)),[ix/4,iy/4])
            for ix in range(math.floor((xy[0]-SPACING)*4),math.ceil((xy[0]+SPACING)*4)+1)
            for iy in range(math.floor((xy[1]-SPACING)*4),math.ceil((xy[1]+SPACING)*4)+1))
        candidates.sort(key=lambda row:(-sum(math.dist(row[1],w)<=SPACING for w in transition_positions),row[0]))
        selected=None
        for d,site in candidates:
            if d>SPACING:continue
            point=Point(site)
            if forbidden.intersects(point) or not all(fields[l,main].covers(point.buffer(.31)) for l in references):continue
            if screen.via_legal('PWR_AGND',site):selected=(d,site);break
        assert selected,(v,'no local ground stitch found',stitches,sorted(existing,key=lambda x:x[0])[:2])
        d,site=selected
        stitch=dict(net='PWR_AGND',position_mm=site,size_mm=.6,drill_mm=.3,role='reference transition ground stitch')
        stitches.append(stitch);screen.vias.append(('PWR_AGND',site))
        print('Stitch',xy,site,d,flush=True)
        for l in c['copper_layers']:screen.added.append(('PWR_AGND',l,Point(site).buffer(.2)))
        transitions.append(dict(net=v['net'],position_mm=xy,reference_layers=sorted(references),ground_via_mm=site,distance_mm=d,previous_nearest_ground_via_mm=pos,previous_distance_mm=distance))
    sources=[Path(__file__),CAP,PLAN,*quietpaths,REPO/'hardware/fabrication/plan_two_board_startup_controls.py',REPO/'hardware/fabrication/route_two_board_power_layer_detours.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(p,source_sha256={str(s.relative_to(REPO)):sha(s) for s in sources},vias=p['vias']+stitches,
        ground_stitches=stitches,reference_transitions=transitions,reference_transition_spacing_limit_mm=SPACING,
        shared_master_enable_via=dict(retired_site_mm=retired_site,shared_site_mm=shared_site,previous_middle_path_mm=previous_middle,new_middle_path_mm=middle['path_mm'],removed_spur=tail),
        transition_spacing_scope='Geometric layout target, not a measured signal-integrity limit',native_validation_pending=True,fabrication_released=False)
    OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(joins=len(result['joins']),signal_vias=len(p['vias']),ground_stitches=len(stitches),transitions=transitions)))


if __name__=='__main__':run()
