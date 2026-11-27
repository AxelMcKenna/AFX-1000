"""Replace the timeout route cutting F_U11's reference with an In2 route.

Retire the complete In1 path between its existing through vias. Reuse those
vias, add nearby reference-return stitches, and require native refill/audit.
"""
import copy
import json
import math
from pathlib import Path
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
from hardware.fabrication.route_polygon_corridor import corridor_path
import hardware.fabrication.route_nf_surface as routing

CAP = STAGING/'two-board-power-routing-inputs-western-logic-returns-01/capture.json'
PLAN = STAGING/'two-board-western-logic-returns-plan-01/plan.json'
OUT = STAGING/'two-board-western-logic-returns-plan-02'


def run():
    assert not OUT.exists()
    c, p = [json.loads(f.read_text()) for f in [CAP, PLAN]]
    for data in [c, p]:
        for name, digest in data['source_sha256'].items():
            path = Path(name)
            assert sha(path if path.is_absolute() else REPO/path) == digest, name
    net='/E_rail_disconnect/E28_TIMEOUT_RAW'
    retired=[o for o in c['objects'] if o['kind']=='PCB_TRACK' and o['net']==net and list(o['layers'])==['In1.Cu']]
    assert len(retired)==28
    start,end=[81.2,146.8],[103.5,149.05]
    # Every inner-path terminal must be one of these two existing through vias.
    degree={}
    for o in retired:
        for pt in [o['position_mm'],o['end_mm']]:degree[tuple(pt)]=degree.get(tuple(pt),0)+1
    assert {pt for pt,n in degree.items() if n==1}=={tuple(start),tuple(end)}
    assert all(n in [1,2] for n in degree.values())
    endpoints=[]
    for pt in [start,end]:
        matches=[o for o in c['objects'] if o['kind']=='PCB_VIA' and o['net']==net and o['position_mm']==pt]
        assert len(matches)==1 and matches[0]['span']==['F.Cu','B.Cu']
        endpoints.append(matches[0])
    removed={o['uuid'] for o in retired}
    fields,_=anchored_fields(c)
    main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
    quiet_paths=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',
                 STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']
    quiet_ids={u for f in quiet_paths for q in json.loads(f.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
    quiet=unary_union([routing.shape(z['authored_outline']).buffer(.55) for z in c['zones'] if z['uuid'] in quiet_ids])
    supply=unary_union([routing.shape(z['polygons']).buffer(.55) for z in c['zones'] if z['net']!='PWR_AGND'])
    supply_lines=unary_union([routing.shape(z['polygons']).buffer(.315) for z in c['zones'] if z['net']!='PWR_AGND' and z['layer']=='In2.Cu'])
    authored=unary_union([routing.shape(z['authored_outline']) for z in c['zones'] if z['net']=='PWR_AGND' and z['layer']=='In1.Cu' and z['uuid'] not in quiet_ids])
    healed=unary_union([LineString([o['position_mm'],o['end_mm']]).buffer(.35) for o in retired])
    obstacles=unary_union([routing.shape(o['layers']['In1.Cu']).buffer(.215) for o in c['objects']
                          if o['uuid'] not in removed and o['net']!='PWR_AGND' and 'In1.Cu' in o['layers']])
    predicted=fields['In1.Cu',main].union(healed).intersection(authored).difference(obstacles)
    ownholes=unary_union([Point(o['position_mm']).buffer(o['width_mm']/2+.215) for o in c['objects'] if o['kind']=='PCB_VIA' and o['net']==net])
    route_field=predicted.buffer(.0015).union(ownholes).buffer(-.100001)
    routing.SIGNAL_LAYERS=tuple(c['copper_layers']);routing.WIDTH=.2
    screen=ViaScreen(dict(c,zones=[],objects=[o for o in c['objects'] if o['uuid'] not in removed]))
    def legal(path):
        line=LineString(path)
        return route_field.covers(line) and not supply_lines.intersects(line) and not quiet.intersects(line) and screen.legal(net,'In2.Cu',path)
    paths=[path for path in routing.candidate_paths(start,end) if legal(path)]
    if paths:
        path=min(paths,key=lambda x:LineString(x).length)
    else:
        bounds=box(min(start[0],end[0])-6,min(start[1],end[1])-6,max(start[0],end[0])+6,max(start[1],end[1])+6)
        obs=[g.buffer(d+.002,quad_segs=32) for n,g,d in screen.geometry['In2.Cu'] if n!=net and g.intersects(bounds)]
        obs.extend(point.buffer(radius+.112,quad_segs=32) for ref,point,radius in screen.mounts)
        free=bounds.intersection(route_field).intersection(screen.outline).difference(unary_union(obs)).difference(quiet).difference(supply_lines)
        path=corridor_path(free,start,end,legal)
    assert path and LineString(path).length<55,'No referenced In2 replacement found'
    screen.added.append((net,'In2.Cu',LineString(path)))
    p=copy.deepcopy(p)
    p['retired_objects']=sorted(removed)
    p['routes'].append(dict(net=net,layer='In2.Cu',reference_layer='In1.Cu',width_mm=.2,path_mm=path,
                            length_mm=LineString(path).length,role='Replacement for the complete original In1 timeout path'))
    isolated=unary_union([routing.shape(g) for o in c['objects'] if o['net']=='PWR_AGND' and o['group']!=main for g in o['layers'].values()]).buffer(.315)
    bridges=[]
    for endpoint,refs in zip(endpoints,[['In1.Cu','In6.Cu'],['In1.Cu','In5.Cu','In6.Cu']]):
        xy=endpoint['position_mm'];site=None
        sites=sorted((math.dist(xy,[ix/20,iy/20]),[ix/20,iy/20]) for ix in range(math.floor((xy[0]-2)*20),math.ceil((xy[0]+2)*20)+1)
                     for iy in range(math.floor((xy[1]-2)*20),math.ceil((xy[1]+2)*20)+1))
        for distance,trial in sites:
            if distance>2:break
            point=Point(trial)
            if quiet.intersects(point) or supply.intersects(point) or isolated.intersects(point):continue
            if not all((predicted if l=='In1.Cu' else fields[l,main]).covers(point.buffer(.31)) for l in refs):continue
            if screen.via_legal('PWR_AGND',trial):site=trial;break
        assert site,('No nearby reference stitch',xy)
        p['vias'].append(dict(net='PWR_AGND',position_mm=site,size_mm=.6,drill_mm=.3,role='Timeout reference transition stitch'))
        screen.vias.append(('PWR_AGND',site))
        for layer in c['copper_layers']:screen.added.append(('PWR_AGND',layer,Point(site).buffer(.2)))
        bridges.append(dict(signal_via_uuid=endpoint['uuid'],signal_position_mm=xy,ground_site_mm=site,
                            reference_layers=refs,distance_mm=math.dist(xy,site),spacing_limit_mm=2.0))
    p['reference_transitions']=bridges
    p['signal_replacement']=dict(net=net,retired_track_uuids=sorted(removed),retired_layer='In1.Cu',new_layer='In2.Cu',
                                  reused_endpoint_vias=[o['uuid'] for o in endpoints],complete_native_reference_audit_required=True)
    sources=[Path(__file__),CAP,PLAN,*quiet_paths,*[REPO/'hardware/fabrication'/name for name in
             ['plan_two_board_startup_controls.py','route_two_board_power_layer_detours.py','route_nf_surface.py','route_polygon_corridor.py']]]
    p['source_sha256']={str(f.relative_to(REPO)):sha(f) for f in sources}
    OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(retired_tracks=len(retired),replacement_path_mm=path,ground_bridges=bridges)))


if __name__=='__main__':run()
