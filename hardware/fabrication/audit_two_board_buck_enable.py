"""Independent native delta, connection and filled-plane audit for U23 enable."""
import copy,json,math
from pathlib import Path
from shapely.affinity import rotate,translate
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,read_netlist,sha
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.audit_two_board_buck_input import orientation
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-buck-input-native-01'
OUT=STAGING/'two-board-power-buck-enable-native-01'
BEFORE=STAGING/'two-board-power-routing-inputs-2511-buck-input/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2508-buck-enable/capture.json'
FILLED=STAGING/'two-board-power-buck-enable-filled-01'

def run():
    rp=OUT/'buck-enable-routing.json';r=json.loads(rp.read_text())
    before,after=[json.loads(p.read_text()) for p in [BEFORE,AFTER]]
    fill_path=FILLED/'local-plane-fill.json';fill=json.loads(fill_path.read_text())
    for data in [r,before,after,fill]:
        for n,h in data['source_sha256'].items():assert sha(REPO/n)==h,n
    for n,h in fill['artifact_sha256'].items():assert sha(FILLED/n)==h,n
    trees=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
    fps=[{prop(f,'Reference')[2]:f for f in children(t,'footprint')} for t in trees]
    assert fps[0].keys()==fps[1].keys() and len(fps[0])==1103
    assert r['moves']==[dict(ref='P_R225',old_xy=[307.5,141.5],new_xy=[301.5,130.6],rotation_added_degrees=-90)]
    for ref,old in fps[0].items():
        new=fps[1][ref]
        if ref!='P_R225':assert geometry(old)==geometry(new),ref;continue
        assert list(map(float,first(new,'at')[1:3]))==[301.5,130.6] and (orientation(new)-orientation(old))%360==270
        restored=copy.deepcopy(new);first(restored,'at')[:]=first(old,'at')
        for tag in ['pad','property','fp_text']:
            aa,bb=children(old,tag),children(restored,tag);assert len(aa)==len(bb)
            for a,b in zip(aa,bb):
                oa,na=children(a,'at'),children(b,'at');assert len(oa)==len(na)
                for x,y in zip(oa,na):
                    assert x[1:3]==y[1:3] and (orientation(b)-orientation(a))%360==270
                    y[:]=x
        assert geometry(old)==geometry(restored)
    def shell(t):return [n for n in t if not(isinstance(n,list) and n and n[0] in ['footprint','segment','via','arc','net','zone'])]
    assert shell(trees[0])==shell(trees[1])
    oldparts,oldpins=read_netlist(BASE/'netlist.xml');parts,pins=read_netlist(OUT/'netlist.xml')
    assert oldpins==pins and oldparts.keys()==parts.keys() and len(parts)==1088
    for ref in parts:
        for f in ['value','footprint']:assert oldparts[ref].findtext(f)==parts[ref].findtext(f)
    old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
    removed=set(r['removed_copper_uuids']);assert len(removed)==4
    assert all(old[u]['net']=='/P_power_supply/P03_A_MODE' for u in removed)
    assert sum(old[u]['kind']=='PCB_TRACK' for u in removed)==3 and sum(old[u]['kind']=='PCB_VIA' for u in removed)==1
    assert not removed & new.keys()
    physical=lambda o:{k:v for k,v in o.items() if k not in ['uuid','group']}
    aliases={}
    for u in old.keys()-new.keys()-removed:
        assert old[u]['kind']=='PAD' and old[u]['ref']!='P_R225'
        hits=[v for v in new.keys()-old.keys() if physical(old[u])==physical(new[v])]
        assert len(hits)==1;aliases[u]=hits[0]
    assert len(aliases)==len(set(aliases.values()))
    oldkeys={aliases.get(u,u) for u in old if u not in removed};errors=[]
    for u,o in old.items():
        if u in removed:continue
        n=new[aliases.get(u,u)]
        if o.get('ref')!='P_R225':assert physical(o)==physical(n),u;continue
        assert o['kind']==n['kind']=='PAD' and o['net']==n['net'] and o['pin']==n['pin'] and o['drill_mm']==n['drill_mm']==[0,0]
        assert (n['orientation_degrees']-o['orientation_degrees'])%360==270
        transform=lambda g:translate(rotate(g,90,origin=(307.5,141.5)),-6,-10.9)
        assert transform(Point(o['position_mm'])).distance(Point(n['position_mm']))<2e-6
        assert o['layers'].keys()==n['layers'].keys()
        for l,ps in o['layers'].items():
            if not ps:assert not n['layers'][l];continue
            e=transform(shape(ps)).hausdorff_distance(shape(n['layers'][l]));assert e<3e-6;errors.append(e)
    assert len(errors)==2
    groups={u:set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        mapped={aliases.get(u,u) for u in g if u not in removed};assert mapped and mapped<=groups[next(iter(mapped))]
    pad=lambda ref,pin:next(o for o in new.values() if o.get('ref')==ref and o.get('pin')==pin)
    joins=[(('P_U23','7'),('P_R224','2')),(('P_U23','7'),('P_R225','1')),(('P_R225','2'),('P_U23','5')),(('P_U23','2'),('P_R223','1'))]
    allowed=set()
    for a,b in joins:
        group=groups[pad(*a)['uuid']];assert pad(*b)['uuid'] in group;allowed.update(group)
    mounts=[o for o in new.values() if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])];assert len(mounts)==15
    added=set()
    for route in r['routes']:
        pts=route['path_mm'];assert len(pts)==len(route['segment_uuids'])+1
        assert abs(LineString(pts).length-route['length_mm'])<2e-6 and route['length_mm']<=route['maximum_length_mm']
        for u,p,q in zip(route['segment_uuids'],pts,pts[1:]):
            assert u not in added and u not in oldkeys;added.add(u);o=new[u]
            assert o['kind']=='PCB_TRACK' and o['net']==route['net'] and o['width_mm']==route['width_mm']==.2
            assert set(o['layers'])=={route['layer']} and math.dist(o['position_mm'],p)<2e-6 and math.dist(o['end_mm'],q)<2e-6
            assert u in allowed
            assert all(LineString([p,q]).distance(Point(m['position_mm']))>max(3.6,max(m['drill_mm'])/2+.5)+.11-2e-6 for m in mounts)
    for v in r['vias']:
        u=v['uuid'];assert u not in added and u not in oldkeys;added.add(u);o=new[u]
        assert o['kind']=='PCB_VIA' and o['net']==v['net'] and o['width_mm']==.6 and o['drill_mm']==.3 and o['via_type']==4
        assert o['position_mm']==v['position_mm'] and o['span']==['F.Cu','B.Cu'] and set(o['layers'])==set(after['copper_layers']) and u in allowed
    assert added==new.keys()-oldkeys and len(added)==13
    # Only saved native fill can be adopted; zone settings and outlines stay exact.
    zones=lambda t:{str(first(z,'uuid')[1]):z for z in children(t,'zone')}
    oldz,newz=map(zones,trees);fz=zones(read_sexpr((FILLED/'power_protection.kicad_pcb').read_text()))
    assert oldz.keys()==newz.keys()==fz.keys() and len(newz)==2 and newz==fz
    strip=lambda z:[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')]
    assert all(strip(oldz[u])==strip(newz[u]) for u in oldz)
    zone_before={z['uuid']:z for z in before['zones']};zone_after={z['uuid']:z for z in after['zones']}
    modified_locations=[old[u]['position_mm'] for u in removed if old[u]['kind']=='PCB_VIA']+[v['position_mm'] for v in r['vias']]
    # KiCad removes sub-minimum-width copper between adjacent antipads.
    # Bound that cleanup by via radius + clearance + unchanged 0.25 mm zone
    # minimum thickness + 0.01 mm polygon allowance; do not require a pure disc.
    assert all(float(first(z,'min_thickness')[1])==.25 for z in newz.values())
    permitted=unary_union([Point(p).buffer(.76) for p in modified_locations]);plane_checks=[];planes={}
    for u,z in zone_after.items():
        assert not z['keepout'] and z['authored_outline']==zone_before[u]['authored_outline']
        g=shape(z['polygons']);previous=shape(zone_before[u]['polygons']);assert g.is_valid and g.geom_type=='Polygon' and len(z['polygons'])==1
        unexplained=g.symmetric_difference(previous).difference(permitted).area;assert unexplained<1e-5,(u,unexplained)
        gaps=[g.distance(shape(o['layers'][z['layer']])) for o in new.values() if o['net']!=z['net'] and o['layers'].get(z['layer'])]
        assert min(gaps)>=.1985
        # Every previously touching same-net via still touches its original plane.
        contacts=[]
        for o in old.values():
            if o['kind']!='PCB_VIA' or o['net']!=z['net'] or not previous.buffer(.0015).covers(shape(o['layers'][z['layer']])):continue
            assert o['uuid'] in new and g.buffer(.0015).covers(shape(new[o['uuid']]['layers'][z['layer']]))
            contacts.append(o['uuid'])
        plane_checks.append(dict(layer=z['layer'],net=z['net'],area_mm2=g.area,area_change_mm2=g.area-previous.area,unchanged_plane_contacts=len(contacts),unexplained_fill_change_mm2=unexplained,refill_change_radius_bound_mm=.76,minimum_foreign_copper_gap_mm=min(gaps),single_contiguous_filled_polygon=True))
        planes[z['layer']]=g
    control=json.loads((BASE/'buck-control-routing.json').read_text());sense=next(t for t in control['routes'] if t['label']=='output-sense-In2')
    corridor=LineString(sense['path_mm']).buffer(.1)
    for v in control['vias']:
        if v['net']=='/P_power_supply/P03_PRE6V':corridor=corridor.difference(Point(v['position_mm']).buffer(.515))
    assert corridor.difference(planes['In1.Cu']).area<1e-6
    smd=[shape(ps) for o in new.values() if o['kind']=='PAD' and not any(o['drill_mm']) for l,ps in o['layers'].items() if l in ['F.Cu','B.Cu'] and ps]
    tree=STRtree(smd);gaps=[]
    for o in new.values():
        if o['kind']=='PCB_VIA':
            p=Point(o['position_mm']);gap=p.distance(smd[int(tree.nearest(p))])-o['drill_mm']/2;assert gap>=.15-2e-6;gaps.append(gap)
    assert len(gaps)==151
    drc=json.loads((OUT/'drc.json').read_text());erc=json.loads((OUT/'erc.json').read_text());native=json.loads((OUT/'review.json').read_text())
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(warnings)==2 and all(v['type']=='ground_pin_not_ground' and v['severity']=='warning' for v in warnings)
    assert before['native_uncapped_opens']==2511 and after['native_uncapped_opens']==native['opens']==2508
    paths=[Path(__file__),rp,BEFORE,AFTER,fill_path,BASE/'power_protection.kicad_pcb',OUT/'power_protection.kicad_pcb',OUT/'netlist.xml',OUT/'review.json',OUT/'drc.json',OUT/'erc.json']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},components=1088,footprints=1103,
        unchanged_complete_pin_net_map=True,moved_footprints=1,changed_native_pad_instances=2,maximum_native_pad_polygon_error_mm=max(errors),
        intentionally_replaced_MODE_tracks=3,intentionally_replaced_MODE_vias=1,all_other_copper_objects_unchanged=True,
        all_previous_native_connection_groups_preserved=len(before['all_groups']),added_segments=11,added_vias=2,
        old_opens=2511,new_opens=2508,connections_closed=3,verified_endpoint_joins=joins,
        local_plane_checks=plane_checks,sense_trace_projection_coverage_preserved=True,
        vias_screened=len(gaps),minimum_all_via_drill_to_SMD_mm=min(gaps),geometry_findings=0,parity_findings=0,erc_errors=0,erc_warnings=2,
        local_enable_connected=True,full_enable_electrical_qualification=False,full_installed_fit_verified=False,fabrication_released=False)
    with (OUT/'buck-enable-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))

if __name__=='__main__':run()
