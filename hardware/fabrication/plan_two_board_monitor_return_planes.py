"""Extend main reference planes under the monitor logic along the C-board upper arm.

This is a candidate geometry plan. Native refill, ground-group reconciliation,
quiet-star ownership and reference audits are required before accepting it.
"""
import json
import math
from pathlib import Path
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

BASE=STAGING/'two-board-power-western-logic-returns-native-02'
CAP=STAGING/'two-board-power-routing-inputs-western-logic-returns-02/capture.json'
OUT=STAGING/'two-board-monitor-return-planes-plan-01'
MAIN={'In1.Cu':'13cfea4d-d36e-5757-b531-ed680e4c4562',
      'In6.Cu':'4b63f119-2e71-5d61-96f6-8b78a1f5c6cb'}
QUIET=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',
       STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']


def run():
    assert not OUT.exists()
    c=json.loads(CAP.read_text())
    checkpoint=BASE/'final-review.json'
    for data in [c,json.loads(checkpoint.read_text())]:
        for n,h in data['source_sha256'].items():
            assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
    zones={z['uuid']:z for z in c['zones']}
    quiet=[q for p in QUIET for q in json.loads(p.read_text())['quiet_ground_islands']]
    quietids={u for q in quiet for u in q['zone_uuids']}
    allowed_board=routing.shape(c['outline']).buffer(-.51)
    # Follow the actual C-shaped board: the empty centre is not PCB material.
    region=unary_union([box(9,31,232,39.49),box(9,31,26,120)])
    extensions={'In1.Cu':region,'In6.Cu':region}
    fields={};edits=[];discarded=[]
    for layer,region in extensions.items():
        original=routing.shape(zones[MAIN[layer]]['authored_outline'])
        region=region.intersection(allowed_board)
        for u,z in zones.items():
            if z['layer']==layer and z['net']=='PWR_AGND' and u!=MAIN[layer]:
                region=region.difference(routing.shape(z['authored_outline']).buffer(.215))
        assert original.intersection(region).area>1,('inadequate authored overlap',layer)
        field=original.union(region).simplify(.00001,preserve_topology=True)
        if field.geom_type=='MultiPolygon':
            attached=[g for g in field.geoms if g.intersection(original).area>1e-6]
            discarded.extend(dict(layer=layer,area_mm2=g.area,bounds_mm=list(g.bounds),reason='New detached sliver excluded from authored ground extension') for g in field.geoms if g.intersection(original).area<=1e-6)
            assert len(attached)==1
            field=attached[0]
        assert field.is_valid and field.geom_type=='Polygon'
        assert original.difference(field).area<1e-6
        fields[layer]=field
        edits.append(dict(uuid=MAIN[layer],layer=layer,outer_mm=list(field.exterior.coords),
            holes_mm=[list(h.coords) for h in field.interiors],added_authored_area_mm2=field.difference(original).area))
    routing.SIGNAL_LAYERS=tuple(c['copper_layers']);routing.WIDTH=.2
    screen=ViaScreen(dict(c,zones=[]))
    dc_zones={z['uuid'] for z in c['zones'] if z['net']=='PWR_DC_IN' and z['layer'] in ['In2.Cu','In3.Cu']}
    assert len(dc_zones)==2
    forbidden=unary_union([routing.shape(z['authored_outline']).buffer(.55) for u,z in zones.items() if u in quietids]
        +[routing.shape(z['polygons']).buffer(.55) for z in c['zones'] if z['net']!='PWR_AGND' and z['uuid'] not in dc_zones])
    via_allowed=fields['In1.Cu'].intersection(fields['In6.Cu']).buffer(-.61)
    def legal_via(xy):
        pt=Point(xy)
        return via_allowed.covers(pt) and not forbidden.intersects(pt) and screen.via_legal('PWR_AGND',xy)
    vias=[];routes=[];supply_exceptions=[]
    def add_via(xy,role):
        affected=[u for u in dc_zones if routing.shape(zones[u]['polygons']).intersects(Point(xy).buffer(.51))]
        if affected:supply_exceptions.append(dict(position_mm=list(xy),affected_supply_zone_uuids=sorted(affected),reason='Monitor reference ground stitch; input-plane topology and resistance comparison required'))
        vias.append(dict(net='PWR_AGND',position_mm=list(xy),size_mm=.6,drill_mm=.3,role=role))
        screen.vias.append(('PWR_AGND',list(xy)))
        for layer in c['copper_layers']:
            screen.added.append(('PWR_AGND',layer,Point(xy).buffer(.2)))
    # Ground the remaining targeted logic packages without
    # moving any component or treating a plane below an SMD pad as a connection.
    for ref,pin in [('M_U10', '7'), ('M_U11', '7'), ('M_U12', '7'), ('M_U9', '7')]:
        pad=next(o for o in c['objects'] if o.get('ref')==ref and o.get('pin')==pin)
        assert pad['net']=='PWR_AGND' and len(pad['layers'])==1
        layer,=pad['layers'];reference={'F.Cu':'In1.Cu','B.Cu':'In6.Cu'}[layer]
        xy=pad['position_mm'];chosen=None
        sites=sorted((math.dist(xy,[ix/4,iy/4]),[ix/4,iy/4])
            for ix in range(math.floor((xy[0]-3.5)*4),math.ceil((xy[0]+3.5)*4)+1)
            for iy in range(math.floor((xy[1]-3.5)*4),math.ceil((xy[1]+3.5)*4)+1))
        for distance,site in sites:
            if distance>3.5 or not legal_via(site):continue
            path=screen.simple('PWR_AGND',layer,xy,site,5.5)
            if path and fields[reference].covers(LineString(path[1]).buffer(.1)):
                chosen=(path,site);break
        if not chosen:
            counts={'inside_reference':0,'outside_preserved_fields':0,'legal_via':0,'simple_route':0}
            candidates=[]
            for distance,site in sites:
                if distance>3.5 or not via_allowed.covers(Point(site)):continue
                counts['inside_reference']+=1
                if forbidden.intersects(Point(site)):continue
                counts['outside_preserved_fields']+=1
                if not screen.via_legal('PWR_AGND',site):continue
                counts['legal_via']+=1
                candidates.append(site)
                if screen.simple('PWR_AGND',layer,xy,site,5.5):counts['simple_route']+=1
            print(ref,counts,'legal sites',candidates[:8],flush=True)
        assert chosen,('no local ground escape',ref,pin)
        (length,path),site=chosen
        routes.append(dict(net='PWR_AGND',layer=layer,reference_layer=reference,width_mm=.2,path_mm=path,
            pad_ref=ref,pad_pin=pin,source_group=pad['group'],length_mm=length))
        screen.added.append(('PWR_AGND',layer,LineString(path)))
        add_via(site,'local logic ground return: '+ref+'.'+pin)
    # Distributed stitches join the two extended reference layers. The 10 mm
    # search grid is a placement target, not an EMC or current-rating claim.
    grid=[]
    main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
    existing_stitches=[o['position_mm'] for o in c['objects'] if o['kind']=='PCB_VIA' and o['net']=='PWR_AGND' and o['group']==main and all(fields[l].covers(Point(o['position_mm']).buffer(.31)) for l in fields)]
    for x,ys in [(x,[35]) for x in range(18,229,30)]+[(18,list(range(45,116,20)))]:
        for y in ys:
            if any(math.dist([x,y],pos)<4 for pos in existing_stitches+[v['position_mm'] for v in vias]):continue
            sites=sorted((math.dist([x,y],[x+dx/2,y+dy/2]),[x+dx/2,y+dy/2]) for dx in range(-4,5) for dy in range(-4,5))
            found=next((site for distance,site in sites if distance<=2 and legal_via(site)),None)
            if found:add_via(found,'distributed reference-plane stitch')
            grid.append(dict(target_mm=[x,y],selected_mm=found))
    assert sum(g['selected_mm'] is not None for g in grid)>=4
    # Approval envelope for new connections: only the named main-ground net,
    # and only groups with copper touching the added region or a declared pad
    # escape. The independent native audit reports every actual merged group.
    main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
    additions={layer:fields[layer].difference(routing.shape(zones[u]['authored_outline'])) for layer,u in MAIN.items()}
    allowed={main,*[r['source_group'] for r in routes]}
    for o in c['objects']:
        if o['net']=='PWR_AGND' and o['group']:
            if any(o['layers'].get(layer) and routing.shape(o['layers'][layer]).intersects(g) for layer,g in additions.items()):allowed.add(o['group'])
    group_pads={gid:[dict(ref=o['ref'],pin=o['pin']) for o in c['objects'] if o['group']==gid and o['kind']=='PAD'] for gid in sorted(allowed)}
    survey=STAGING/'two-board-logic-ground-access-survey-04/survey.json'
    targets=[dict(ref=ref,pin=pin) for ref,pin in [('M_U10', '7'), ('M_U11', '7'), ('M_U12', '7'), ('M_U9', '7')]]
    sources=[Path(__file__),CAP,checkpoint,survey,*QUIET,REPO/'hardware/fabrication/route_two_board_power_layer_detours.py',
        REPO/'hardware/fabrication/route_two_board_power_local_v2.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},edited_zone_outlines=edits,discarded_detached_extensions=discarded,
        routes=routes,vias=vias,supply_plane_via_exceptions=supply_exceptions,stitch_grid=grid,target_reference_pads=targets,allowed_ground_groups=group_pads,old_main_ground_group=main,
        previous_opens=c['native_uncapped_opens'],new_open_count_requires_native_capture=True,
        scope='Main-ground reference extension and four local ground returns in the monitor logic along the C-board upper arm. Supply bypass/source, startup timing, EMC, current and thermal qualification remain open.',
        native_validation_pending=True,fabrication_released=False)
    OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(ground_escapes=len(routes),ground_vias=len(vias),allowed_ground_groups=len(allowed),zone_extensions=[(e['layer'],e['added_authored_area_mm2']) for e in edits])))


if __name__=='__main__':run()
