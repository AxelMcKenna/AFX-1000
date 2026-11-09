"""Extend main reference planes into the NF fault-logic region.

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

BASE=STAGING/'two-board-power-startup-controls-native-04'
CAP=STAGING/'two-board-power-routing-inputs-startup-controls-04/capture.json'
OUT=STAGING/'two-board-nf-logic-ground-plan-01'
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
    extensions={'In1.Cu':box(210,139,326,180),'In6.Cu':box(150,140,326,180)}
    fields={};edits=[]
    for layer,region in extensions.items():
        original=routing.shape(zones[MAIN[layer]]['authored_outline'])
        region=region.intersection(allowed_board)
        for u,z in zones.items():
            if z['layer']==layer and z['net']=='PWR_AGND' and u!=MAIN[layer]:
                region=region.difference(routing.shape(z['authored_outline']).buffer(.215))
        assert original.intersection(region).area>1,('inadequate authored overlap',layer)
        field=original.union(region).simplify(.00001,preserve_topology=True)
        assert field.is_valid and field.geom_type=='Polygon'
        assert original.difference(field).area<1e-6
        fields[layer]=field
        edits.append(dict(uuid=MAIN[layer],layer=layer,outer_mm=list(field.exterior.coords),
            holes_mm=[list(h.coords) for h in field.interiors],added_authored_area_mm2=field.difference(original).area))
    routing.SIGNAL_LAYERS=tuple(c['copper_layers']);routing.WIDTH=.2
    screen=ViaScreen(dict(c,zones=[]))
    forbidden=unary_union([routing.shape(z['authored_outline']).buffer(.55) for u,z in zones.items() if u in quietids]
        +[routing.shape(z['polygons']).buffer(.55) for z in c['zones'] if z['net']!='PWR_AGND'])
    via_allowed=fields['In1.Cu'].intersection(fields['In6.Cu']).buffer(-.61)
    def legal_via(xy):
        pt=Point(xy)
        return via_allowed.covers(pt) and not forbidden.intersects(pt) and screen.via_legal('PWR_AGND',xy)
    vias=[];routes=[]
    def add_via(xy,role):
        vias.append(dict(net='PWR_AGND',position_mm=list(xy),size_mm=.6,drill_mm=.3,role=role))
        screen.vias.append(('PWR_AGND',list(xy)))
        for layer in c['copper_layers']:
            screen.added.append(('PWR_AGND',layer,Point(xy).buffer(.2)))
    # Ground the logic packages and the adjacent fault-input pull-down without
    # moving any component or treating a plane below an SMD pad as a connection.
    for ref,pin in [('N_U44','7'),('N_U46','7'),('N_U34','2'),('N_R22','2')]:
        pad=next(o for o in c['objects'] if o.get('ref')==ref and o.get('pin')==pin)
        assert pad['net']=='PWR_AGND' and len(pad['layers'])==1
        layer,=pad['layers'];reference={'F.Cu':'In1.Cu','B.Cu':'In6.Cu'}[layer]
        xy=pad['position_mm'];chosen=None
        sites=sorted((math.dist(xy,[ix/4,iy/4]),[ix/4,iy/4])
            for ix in range(math.floor((xy[0]-2)*4),math.ceil((xy[0]+2)*4)+1)
            for iy in range(math.floor((xy[1]-2)*4),math.ceil((xy[1]+2)*4)+1))
        for distance,site in sites:
            if distance>2 or not legal_via(site):continue
            path=screen.simple('PWR_AGND',layer,xy,site,3)
            if path and fields[reference].covers(LineString(path[1]).buffer(.1)):
                chosen=(path,site);break
        assert chosen,('no local ground escape',ref,pin)
        (length,path),site=chosen
        routes.append(dict(net='PWR_AGND',layer=layer,reference_layer=reference,width_mm=.2,path_mm=path,
            pad_ref=ref,pad_pin=pin,source_group=pad['group'],length_mm=length))
        screen.added.append(('PWR_AGND',layer,LineString(path)))
        add_via(site,'local logic ground return: '+ref+'.'+pin)
    # Distributed stitches join the two extended reference layers. The 10 mm
    # search grid is a placement target, not an EMC or current-rating claim.
    grid=[]
    for x in range(220,321,10):
        for y in [145,155,165,175]:
            if any(math.dist([x,y],v['position_mm'])<4 for v in vias):continue
            sites=sorted((math.dist([x,y],[x+dx/2,y+dy/2]),[x+dx/2,y+dy/2]) for dx in range(-4,5) for dy in range(-4,5))
            found=next((site for distance,site in sites if distance<=2 and legal_via(site)),None)
            if found:add_via(found,'distributed reference-plane stitch')
            grid.append(dict(target_mm=[x,y],selected_mm=found))
    assert sum(g['selected_mm'] is not None for g in grid)>=30
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
    sources=[Path(__file__),CAP,checkpoint,*QUIET,REPO/'hardware/fabrication/route_two_board_power_layer_detours.py',
        REPO/'hardware/fabrication/route_two_board_power_local_v2.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},edited_zone_outlines=edits,
        routes=routes,vias=vias,stitch_grid=grid,allowed_ground_groups=group_pads,old_main_ground_group=main,
        previous_opens=c['native_uncapped_opens'],new_open_count_requires_native_capture=True,
        scope='Main-ground reference extension and four local ground returns only. Supply bypass/source, startup timing, EMC, current and thermal qualification remain open.',
        native_validation_pending=True,fabrication_released=False)
    OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(ground_escapes=len(routes),ground_vias=len(vias),allowed_ground_groups=len(allowed),zone_extensions=[(e['layer'],e['added_authored_area_mm2']) for e in edits])))


if __name__=='__main__':run()
