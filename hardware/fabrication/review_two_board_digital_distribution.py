"""Independent native-copper review of digital source distribution and quiet returns."""
import json
import math
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, read_netlist, sha
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.verify_native_zone_unfracture import verify_capture

BASE=STAGING/'two-board-power-regulator-distribution-native-04'
OUT=STAGING/'two-board-power-digital-distribution-native-02'
FILLED=STAGING/'two-board-power-digital-distribution-filled-02'
BEFORE=STAGING/'two-board-power-routing-inputs-2369-regulator-distribution-04/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2340-digital-distribution-02/capture.json'


def run():
    sources=[Path(__file__),BEFORE,AFTER,OUT/'digital-distribution-routing.json',FILLED/'local-plane-fill.json',
             BASE/'power_protection.kicad_pcb',OUT/'power_protection.kicad_pcb',BASE/'netlist.xml',OUT/'netlist.xml',
             OUT/'review.json',OUT/'erc.json',REPO/'hardware/fabrication/route_nf_surface.py',
             REPO/'hardware/fabrication/verify_native_zone_unfracture.py']
    before,after,report,fill=[json.loads(p.read_text()) for p in sources[1:5]]
    for p in [BEFORE,AFTER,OUT/'digital-distribution-routing.json',FILLED/'local-plane-fill.json',OUT/'review.json']:
        d=json.loads(p.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in d.get(field,{}).items():
                q=Path(name)
                if not q.is_absolute():q=(REPO if name.startswith(('hardware/','tests/')) else p.parent)/q
                assert sha(q)==h,(p,name)
    fidelity=verify_capture(after)
    b0,b1=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
    old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
    physical=lambda o:{k:v for k,v in o.items() if k not in ['uuid','group']}
    aliases={}
    for u in old.keys()-new.keys():
        assert old[u]['kind']=='PAD'
        hits=[v for v in new.keys()-old.keys() if physical(old[u])==physical(new[v])]
        assert len(hits)==1;aliases[u]=hits[0]
    mapped={aliases.get(u,u) for u in old};assert len(mapped)==len(old)
    assert all(physical(o)==physical(new[aliases.get(u,u)]) for u,o in old.items())
    additions={u for r in report['routes'] for u in r['segment_uuids']}|{v['uuid'] for v in report['vias']}
    assert set(new)-mapped==additions
    strip=lambda b:[n for n in b if not(isinstance(n,list) and n and (n[0]=='zone' or
           (n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in additions)))]
    assert strip(b0)==strip(b1),'Unexpected non-zone board edit'
    parts0,pins0=read_netlist(BASE/'netlist.xml');parts1,pins1=read_netlist(OUT/'netlist.xml')
    assert parts0.keys()==parts1.keys() and pins0==pins1
    assert all(parts0[r].findtext(k)==parts1[r].findtext(k) for r in parts0 for k in ['value','footprint','datasheet'])
    members={u:set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        mappedg={aliases.get(u,u) for u in g};assert mappedg<=members[next(iter(mappedg))]
    pad=lambda r,p:next(o for o in new.values() if o.get('ref')==r and o.get('pin')==p)
    oldpad=lambda r,p:next(o for o in old.values() if o.get('ref')==r and o.get('pin')==p)
    joins=[];expected_merges=0
    for net,groups in report['intended_previous_groups'].items():
        expected={aliases.get(u,u) for gid in groups for u in before['all_groups'][gid]}
        expected|={u for u in additions if new[u]['net']==net}
        anchor=pad('P_L20','2') if net=='PWR_5V_DIG_SRC' else pad('P_C103','2')
        assert members[anchor['uuid']]==expected,(net,len(members[anchor['uuid']]),len(expected))
        joins.append(dict(net=net,previous_groups=len(groups),final_objects=len(expected)));expected_merges+=len(groups)-1
    assert expected_merges==29 and before['native_uncapped_opens']==2369 and after['native_uncapped_opens']==2340
    for ref in ['E_U15','E_U16','E_U17','E_U33']:
        for pin in ['5','12']:assert pad(ref,pin)['group']==pad('P_L20','2')['group']
        for pin in ['6','11']:assert pad(ref,pin)['group']!=pad('P_L20','2')['group']
    assert pad('E_J4','1')['group']!=pad('E_J11','1')['group']
    aux=oldpad('P_U102','4')
    assert members[pad('P_U102','4')['uuid']]=={aliases.get(u,u) for u in before['all_groups'][aux['group']]}
    assert pad('P_U102','4')['group']!=pad('P_C103','2')['group']
    for pin in ['1','2']:assert members[pad('G_NT1',pin)['uuid']]=={pad('G_NT1',pin)['uuid']}
    for r in report['routes']:
        for u,p,q in zip(r['segment_uuids'],r['path_mm'],r['path_mm'][1:]):
            o=new[u];assert o['kind']=='PCB_TRACK' and o['net']==r['net'] and list(o['layers'])==[r['layer']]
            assert math.dist(o['position_mm'],p)<1e-7 and math.dist(o['end_mm'],q)<1e-7 and abs(o['width_mm']-r['width_mm'])<1e-8
    for v in report['vias']:
        o=new[v['uuid']];assert o['kind']=='PCB_VIA' and o['net']==v['net'] and o['position_mm']==v['position_mm']
        assert o['drill_mm']==.3 and o['width_mm']==.6
    z0,z1=[{z['uuid']:z for z in c['zones']} for c in [before,after]]
    t0,t1=[{str(first(z,'uuid')[1]):z for z in children(b,'zone')} for b in [b0,b1]]
    declared={z['uuid']:z for z in report['new_zones']};edited={z['uuid']:z for z in report['edited_existing_zone_outlines']}
    changed=set(report['refilled_existing_zones']);assert z1.keys()-z0.keys()==declared.keys() and len(z1)==30
    without=lambda z,k:[n for n in z if not(isinstance(n,list) and n and n[0] in k)]
    deltas=[]
    for u in z0:
        assert without(t0[u],['filled_polygon','polygon'])==without(t1[u],['filled_polygon','polygon'])
        if u not in edited:assert without(t0[u],['filled_polygon'])==without(t1[u],['filled_polygon'])
        else:
            r=edited[u];assert shape(z1[u]['authored_outline']).hausdorff_distance(Polygon(r['outer_mm'],r['holes_mm']))<1e-6
        if u not in changed:assert t0[u]==t1[u] and z0[u]==z1[u]
        else:
            a,b=shape(z0[u]['polygons']),shape(z1[u]['polygons'])
            deltas.append(dict(uuid=u,layer=z0[u]['layer'],removed_mm2=a.difference(b).area,added_mm2=b.difference(a).area))
    assert len(fill['unchanged_existing_zone_canonical_polygon_match'])==20
    assert all(fill['unchanged_existing_zone_canonical_polygon_match'].values())
    def contacts(g,layer,net,cap):
        candidates=[shape(z['polygons']) for z in cap['zones'] if z['layer']==layer and z['net']==net]
        region=g.buffer(.0015)
        while True:
            hits=[h for h in candidates if region.intersects(h)]
            expanded=unary_union([region,*[h.buffer(.0015) for h in hits]])
            if expanded.equals(region):break
            region=expanded
        hits=[o for o in cap['objects'] if o['net']==net and o['layers'].get(layer) and region.intersection(shape(o['layers'][layer])).area>1e-9]
        assert hits;return hits
    zones=[]
    for u,r in declared.items():
        z=z1[u];g=shape(z['polygons']);authored=Polygon(r['outer_mm'],r['holes_mm'])
        assert z['net']==r['net'] and z['layer']==r['layer'] and shape(z['authored_outline']).hausdorff_distance(authored)<1e-6
        assert authored.buffer(2e-6).covers(g)
        assert int(first(t1[u],'priority')[1])==r['priority']
        assert first(t1[u],'connect_pads')[1]=='yes' and float(first(first(t1[u],'connect_pads'),'clearance')[1])==.2
        anchor=pad('P_L20','2') if z['net']=='PWR_5V_DIG_SRC' else pad('P_C103','2')
        for p in z['polygons']:assert all(o['uuid'] in members[anchor['uuid']] for o in contacts(Polygon(p['outer'],p['holes']),z['layer'],z['net'],after))
        gap=min(g.distance(shape(o['layers'][z['layer']])) for o in new.values() if o['net']!=z['net'] and o['layers'].get(z['layer']))
        assert gap>=.1985
        zones.append(dict(uuid=u,label=r['label'],area_mm2=g.area,pieces=len(z['polygons']),minimum_foreign_copper_gap_mm=gap))
    quiet=[]
    for ref in ['E_U15','E_U16','E_U17','E_U33']:
        r=next(z for z in report['new_zones'] if z['label']==ref+'-quiet-ground');g=shape(z1[r['uuid']]['polygons'])
        own=[v for route,v in zip(report['routes'],report['vias']) if route['ref']==ref and route['pin'] in ['2','4','8']]
        star=next(v for route,v in zip(report['routes'],report['vias']) if route['ref']==ref and route['pin']=='8')
        hit={o['uuid'] for o in new.values() if o['net']=='PWR_AGND' and o['layers'].get('In1.Cu') and g.intersects(shape(o['layers']['In1.Cu']))}
        assert hit=={v['uuid'] for v in own},(ref,hit)
        assert all(g.distance(shape(z['polygons']))>=.1985 for u,z in z1.items() if u!=r['uuid'] and z['layer']=='In1.Cu' and z['net']=='PWR_AGND')
        for v in own:
            o=new[v['uuid']]
            touched={z['layer'] for u,z in z1.items() if u!=r['uuid'] and z['net']=='PWR_AGND' and o['layers'].get(z['layer']) and shape(o['layers'][z['layer']]).intersects(shape(z['polygons']))}
            if v['uuid']==star['uuid']:assert 'In5.Cu' in touched
            else:assert not touched,(ref,v['uuid'],touched)
        quiet.append(dict(ref=ref,zone_uuid=r['uuid'],island_contact_vias=sorted(hit),single_plane_connection_via=star['uuid']))
    # Check every via barrel against every SMD land, including same-net lands.
    smd=[shape(ps) for o in new.values() if o['kind']=='PAD' and not any(o['drill_mm']) for l,ps in o['layers'].items() if l in ['F.Cu','B.Cu'] and ps]
    tree=STRtree(smd);min_gap=100
    for o in new.values():
        if o['kind']!='PCB_VIA':continue
        p=Point(o['position_mm']);gap=p.distance(smd[int(tree.nearest(p))])-o['drill_mm']/2
        assert gap>=.15-1e-8,(o['uuid'],gap);min_gap=min(min_gap,gap)
    # Existing fully referenced tracks must retain the same physical ground group.
    def references(cap):
        refs={}
        for z in cap['zones']:
            if z['net']!='PWR_AGND':continue
            g=shape(z['polygons']);groups={o['group'] for o in contacts(g,z['layer'],z['net'],cap)};assert len(groups)==1
            refs.setdefault((z['layer'],next(iter(groups))),[]).append(g)
        return {k:unary_union(v) for k,v in refs.items()}
    refs0,refs1=references(before),references(after);coverage=[];layers=after['copper_layers']
    for u,o in old.items():
        if o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
        layer,=o['layers'];i=layers.index(layer);adjacent={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)}
        g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2)
        for v in old.values():
            if v['kind']=='PCB_VIA' and v['net']==o['net']:g=g.difference(Point(v['position_mm']).buffer(v['width_mm']/2+.215))
        if g.is_empty:continue
        for (rlayer,gid),reference in refs0.items():
            if rlayer not in adjacent or g.difference(reference.buffer(.0015)).area>=1e-6:continue
            anchor=before['all_groups'][gid][0];target=refs1[(rlayer,new[aliases.get(anchor,anchor)]['group'])]
            uncovered=g.difference(target.buffer(.0015)).area;assert uncovered<1e-6,(u,uncovered)
            coverage.append(dict(track_uuid=u,reference_layer=rlayer,uncovered_mm2=uncovered))
    source=next(z for z in report['new_zones'] if z['net']=='PWR_5V_DIG_SRC');g=shape(z1[source['uuid']]['polygons'])
    for o in new.values():
        if o['net']=='PWR_5V_DIG_SRC' and o['layers'].get('In5.Cu'):g=g.difference(shape(o['layers']['In5.Cu']).buffer(.215))
    unref=g.difference(refs1[('In5.Cu',pad('P_C103','2')['group'])].buffer(.0015))
    native=json.loads((OUT/'review.json').read_text());assert native['geometry_findings']==native['schematic_parity_findings']==0
    erc=json.loads((OUT/'erc.json').read_text());warnings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(warnings)==2 and all(v['severity']=='warning' and v['type']=='ground_pin_not_ground' for v in warnings)
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},zone_capture_fidelity=fidelity,
                old_opens=2369,new_opens=2340,closed_connections=29,all_prior_groups_preserved=len(before['all_groups']),
                all_old_objects_preserved=len(old),added_tracks=report['added_tracks'],added_vias=report['added_vias'],
                all_footprints_unchanged=len(children(b0,'footprint')),unchanged_pin_net_entries=len(pins0),
                old_non_zone_board_tree_exact=True,unchanged_existing_fills=20,refilled_zone_deltas=deltas,
                native_group_merges=joins,new_zones=zones,quiet_ground_islands=quiet,
                input_output_protection_separation_preserved=True,AUX_group_and_copper_preserved=True,G_NT1_still_isolated=True,
                all_vias_screened=sum(o['kind']=='PCB_VIA' for o in new.values()),minimum_all_via_drill_to_SMD_mm=min_gap,
                previous_full_width_adjacent_ground_cases_preserved=len(coverage),prior_reference_coverage=coverage,
                source_In5_reference_screen_area_mm2=g.area,source_In5_reference_uncovered_mm2=unref.area,
                source_In5_reference_uncovered_components=[dict(area_mm2=p.area,bounds_mm=p.bounds) for p in getattr(unref,'geoms',[unref]) if not p.is_empty],
                geometry_errors=0,parity_errors=0,ERC_errors=0,ERC_warnings=2,
                complete_current_thermal_noise_and_return_qualification=False,fabrication_released=False)
    with (OUT/'digital-distribution-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ['new_opens','all_prior_groups_preserved','all_vias_screened','minimum_all_via_drill_to_SMD_mm','previous_full_width_adjacent_ground_cases_preserved','source_In5_reference_uncovered_mm2']}))

if __name__=='__main__':run()
