"""Extend adjacent ground reference beneath the remaining POWER_READY route.

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

BASE=STAGING/'two-board-power-control-return-planes-native-01'
CAP=STAGING/'two-board-power-routing-inputs-control-return-planes-01/capture.json'
OUT=STAGING/'two-board-ready-return-planes-plan-01'
MAIN={'In4.Cu':'787e0385-5c4c-5b8f-9a2a-017054f7da0e',
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
    extensions={'In4.Cu':box(199.5,121.5,223.5,132),'In6.Cu':box(204.5,125,223.5,132)}
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
    routes=[];vias=[];grid=[]
    # Existing main-ground vias and the plated connector ground pin provide
    # interlayer contact; no new drill hole or supply-plane antipad is added.
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
    survey=STAGING/'two-board-control-return-survey-after-03/survey.json'
    targets=[dict(ref='P_R204',pin='1')]
    sources=[Path(__file__),CAP,checkpoint,survey,*QUIET,REPO/'hardware/fabrication/route_two_board_power_layer_detours.py',
        REPO/'hardware/fabrication/route_two_board_power_local_v2.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},edited_zone_outlines=edits,discarded_detached_extensions=discarded,
        routes=routes,vias=vias,stitch_grid=grid,target_reference_pads=targets,allowed_ground_groups=group_pads,old_main_ground_group=main,
        existing_return_contacts=[dict(ref='P_J22',pin='2'),dict(uuid='d9188787-926f-5142-bb68-8c78df086dd8')],previous_opens=c['native_uncapped_opens'],new_open_count_requires_native_capture=True,
        scope='Ground reference beneath the existing POWER_READY route on B.Cu/In3.Cu. No existing object or supply copper may change. Supply bypass/source, startup timing, EMC, current and thermal qualification remain open.',
        native_validation_pending=True,fabrication_released=False)
    OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(ground_escapes=len(routes),ground_vias=len(vias),allowed_ground_groups=len(allowed),zone_extensions=[(e['layer'],e['added_authored_area_mm2']) for e in edits])))


if __name__=='__main__':run()
