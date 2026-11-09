"""Move the shared master-enable transition beyond the DC input plane edge."""
import copy
import json
import math
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.plan_two_board_startup_controls import CAP, anchored_fields
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

PLAN=STAGING/'two-board-startup-control-plan-04/plan.json'
OUT=STAGING/'two-board-startup-control-plan-05'


def run():
    assert not OUT.exists()
    c=json.loads(CAP.read_text());p=json.loads(PLAN.read_text())
    for data in [c,p]:
        for n,h in data['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
    fields,_=anchored_fields(c);objects={o['uuid']:o for o in c['objects']}
    main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
    net='/E_rail_disconnect/E28_MASTER_ENABLE';oldsite=[79.5,117.5];oldground=[78.75,118.]
    replaced=[r for r in p['routes'] if r['net']==net and any(math.dist(oldsite,x)<1e-6 for x in [r['path_mm'][0],r['path_mm'][-1]])]
    assert len(replaced)==3 and {r['layer'] for r in replaced}=={'F.Cu','B.Cu','In2.Cu'}
    fixed=[r for r in p['routes'] if r not in replaced]
    vias=[v for v in p['vias'] if v['position_mm'] not in [oldsite,oldground]]
    assert len(vias)==6
    supply={l:unary_union([routing.shape(z['polygons']) for z in c['zones'] if z['layer']==l and z['net']!='PWR_AGND']) for l in c['copper_layers']}
    all_supply=prep(unary_union(list(supply.values())).buffer(.55))
    holes={}
    for o in c['objects']:
        if o['kind']=='PCB_VIA':holes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
    holes={n:unary_union(v) for n,v in holes.items()}
    protected={l:[] for l in c['copper_layers']}
    for ref in p['retained_reference_bands']:
        o=objects[ref['track_uuid']]
        band=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(holes.get(o['net'],Polygon()))
        protected[ref['reference_layer']].append(band)
    for r in fixed:protected[r['reference_layer']].append(LineString(r['path_mm']).buffer(.1))
    protected_vias=prep(unary_union([g for v in protected.values() for g in v]).buffer(.64))
    protected={l:prep(unary_union(v).buffer(.435)) for l,v in protected.items()}
    refs={'F.Cu':'In1.Cu','B.Cu':'In6.Cu','In2.Cu':'In1.Cu'}
    routefields={l:prep(fields[ref,main].buffer(.0015).union(holes.get(net,Polygon())).buffer(-.100001)) for l,ref in refs.items()}
    supply_lines={l:prep(supply[l].buffer(.315)) for l in refs}
    routing.SIGNAL_LAYERS=tuple(refs);routing.WIDTH=.2
    class Screen(ViaScreen):
        def legal(self,n,l,points):
            line=LineString(points)
            if not routefields[l].covers(line) or protected[l].intersects(line) or supply_lines[l].intersects(line):return False
            return super().legal(n,l,points)
        def via_legal(self,n,xy):
            point=Point(xy)
            if all_supply.intersects(point) or n!='PWR_AGND' and protected_vias.intersects(point):return False
            return super().via_legal(n,xy)
    screen=Screen(dict(c,zones=[]))
    for r in fixed:screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
    for v in vias:
        screen.vias.append((v['net'],v['position_mm']))
        for l in refs:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
    quietpaths=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']
    quietids={u for f in quietpaths for q in json.loads(f.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
    forbidden=prep(unary_union([routing.shape(z['authored_outline']).buffer(.52) for z in c['zones'] if z['uuid'] in quietids]))
    sites=sorted((math.dist(oldsite,(ix/4,iy/4)),[ix/4,iy/4]) for ix in range(74*4,86*4+1) for iy in range(495,510))
    best=None;attempts=0
    for _,site in sites:
        if not screen.via_legal(net,site) or not all(routefields[l].covers(Point(site)) for l in refs):continue
        trial=[]
        for r in replaced:
            start,end=r['path_mm'][0],r['path_mm'][-1]
            if start==oldsite:start=site
            if end==oldsite:end=site
            path=screen.simple(net,r['layer'],start,end,70)
            if path is None:break
            row=copy.deepcopy(r);row['path_mm']=path[1];trial.append(row)
        if len(trial)!=3:continue
        attempts+=1
        # Temporarily include the proposed routes and signal via while finding
        # the adjacent stitch; restore the screen for other candidate sites.
        count=len(screen.added);vc=len(screen.vias)
        for r in trial:screen.added.append((net,r['layer'],LineString(r['path_mm'])))
        screen.vias.append((net,site))
        for l in refs:screen.added.append((net,l,Point(site).buffer(.2)))
        ground=None
        groundsites=sorted((math.dist(site,(ix/4,iy/4)),[ix/4,iy/4]) for ix in range(round(site[0]*4)-6,round(site[0]*4)+7) for iy in range(round(site[1]*4)-6,round(site[1]*4)+7))
        for distance,g in groundsites:
            if distance>1.5:continue
            point=Point(g)
            if forbidden.intersects(point) or not all(fields[l,main].covers(point.buffer(.31)) for l in ['In1.Cu','In6.Cu']):continue
            if screen.via_legal('PWR_AGND',g):ground=(distance,g);break
        screen.added=screen.added[:count];screen.vias=screen.vias[:vc]
        if ground:
            length=sum(LineString(r['path_mm']).length for r in trial)
            if best is None or length<best[0]:best=(length,site,ground,trial)
    assert best,dict(reason='No supply-preserving shared transition found',screened_complete_routes=attempts)
    length,site,(distance,ground),trial=best
    signal=dict(net=net,position_mm=site,size_mm=.6,drill_mm=.3)
    stitch=dict(net='PWR_AGND',position_mm=ground,size_mm=.6,drill_mm=.3,role='reference transition ground stitch')
    transitions=[t for t in p['reference_transitions'] if t['position_mm']!=oldsite]
    transitions.append(dict(net=net,position_mm=site,reference_layers=['In1.Cu','In6.Cu'],ground_via_mm=ground,distance_mm=distance))
    sources=[Path(__file__),CAP,PLAN,*quietpaths,REPO/'hardware/fabrication/plan_two_board_startup_controls.py',REPO/'hardware/fabrication/route_two_board_power_layer_detours.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(p,source_sha256={str(f.relative_to(REPO)):sha(f) for f in sources},routes=fixed+trial,vias=vias+[signal,stitch],
        ground_stitches=[v for v in vias if v['net']=='PWR_AGND']+[stitch],reference_transitions=transitions,
        supply_preserving_transition=dict(previous_site_mm=oldsite,new_site_mm=site,new_ground_site_mm=ground,ground_spacing_mm=distance,replaced_paths=replaced,new_paths=trial,screened_complete_routes=attempts),
        native_validation_pending=True,fabrication_released=False)
    for z in c['zones']:
        if z['net']=='PWR_AGND':continue
        affected=unary_union([LineString(r['path_mm']).buffer(.315) for r in result['routes'] if r['layer']==z['layer']]+[Point(v['position_mm']).buffer(.55) for v in result['vias']])
        assert not routing.shape(z['polygons']).intersects(affected),z['uuid']
    OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(joins=len(result['joins']),signal_vias=5,ground_stitches=3,transition_site=site,ground_site=ground,ground_spacing_mm=distance,replacement_path_length_mm=length)))


if __name__=='__main__':run()
