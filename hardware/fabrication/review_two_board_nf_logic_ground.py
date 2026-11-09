"""Audit NF reference-plane extension, ground joins and retained quiet stars."""
import json
import math
from pathlib import Path
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha, read_netlist
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
from hardware.fabrication.plan_two_board_nf_logic_ground import BASE, CAP
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.verify_native_zone_unfracture import verify_capture

OUT=STAGING/'two-board-power-nf-logic-ground-native-01'
AFTER=STAGING/'two-board-power-routing-inputs-nf-logic-ground-01/capture.json'
FILL=STAGING/'two-board-power-nf-logic-ground-filled-01/local-plane-fill.json'


def run():
    target=OUT/'nf-logic-ground-review.json';assert not target.exists()
    paths=[CAP,AFTER,OUT/'nf-logic-ground-routing.json',OUT/'review.json',FILL]
    before,after,r,native,fill=[json.loads(p.read_text()) for p in paths]
    for path,data in zip(paths,[before,after,r,native,fill]):
        for key in ['source_sha256','artifact_sha256']:
            for name,h in data.get(key,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else path.parent)/p
                assert sha(p)==h,(path,name)
    fidelity=verify_capture(after)
    old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
    tracks={u for route in r['routes'] for u in route['segment_uuids']};vias={v['uuid'] for v in r['vias']};added=tracks|vias
    assert len(tracks)==r['added_tracks'] and len(vias)==r['added_vias']
    physical=lambda o:{k:v for k,v in o.items() if k not in ['uuid','group']}
    aliases={}
    for u in old.keys()-new.keys():
        assert old[u]['kind']=='PAD'
        matches=[v for v in new.keys()-old.keys()-added if physical(old[u])==physical(new[v])]
        assert len(matches)==1,(u,'unmatched original pad');aliases[matches[0]]=u
    assert set(aliases)==new.keys()-old.keys()-added
    for o in after['objects']:o['uuid']=aliases.get(o['uuid'],o['uuid']);o['group']=aliases.get(o['group'],o['group'])
    after['all_groups']={aliases.get(g,g):[aliases.get(u,u) for u in members] for g,members in after['all_groups'].items()}
    new={o['uuid']:o for o in after['objects']}
    assert old.keys()==new.keys()-added and all(physical(o)==physical(new[u]) for u,o in old.items())
    b0,b1=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [BASE,OUT]]
    def strip(b):
        return [n for n in b if not(isinstance(n,list) and n and (n[0]=='zone' or n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in added))]
    assert strip(b0)==strip(b1),'undeclared authored geometry change'
    for route in r['routes']:
        assert len(route['segment_uuids'])==len(route['path_mm'])-1
        for uid,(a,b) in zip(route['segment_uuids'],zip(route['path_mm'],route['path_mm'][1:])):
            o=new[uid]
            assert o['kind']=='PCB_TRACK' and list(o['layers'])==[route['layer']] and o['net']==route['net'] and o['width_mm']==route['width_mm']==.2
            assert math.dist(a,o['position_mm'])<1e-6 and math.dist(b,o['end_mm'])<1e-6
    for v in r['vias']:
        o=new[v['uuid']]
        assert o['kind']=='PCB_VIA' and o['net']==v['net'] and o['width_mm']==v['size_mm']==.6 and o['drill_mm']==v['drill_mm']==.3
        assert math.dist(o['position_mm'],v['position_mm'])<1e-6 and o['span']==['F.Cu','B.Cu']
    expected={frozenset(g) for g in before['all_groups'].values()}
    actual={frozenset(set(g)-added) for g in after['all_groups'].values()}-{frozenset()}
    allowed=set(r['allowed_ground_groups'])
    main0=r['old_main_ground_group']
    assert main0 in allowed and len(allowed)==8
    merged=set()
    for gid in allowed:
        members=set(before['all_groups'][gid])
        assert all(old[u]['net']=='PWR_AGND' for u in members)
        expected.remove(frozenset(members));merged.update(members)
    expected.add(frozenset(merged))
    assert expected==actual,'native connectivity differs from the eight declared ground groups'
    main1=new[next(iter(before['all_groups'][main0]))]['group']
    assert all(new[u]['net']=='PWR_AGND' and new[u]['group']==main1 for u in added)
    closed=len(allowed)-1
    assert before['native_uncapped_opens']-after['native_uncapped_opens']==closed==7
    assert after['native_uncapped_opens']==native['opens']==2158
    a0,p0=read_netlist(BASE/'netlist.xml');a1,p1=read_netlist(OUT/'netlist.xml')
    assert a0.keys()==a1.keys() and p0==p1
    for f in BASE.glob('*.kicad_sch'):
        a,b=[read_sexpr((d/f.name).read_text()) for d in [BASE,OUT]]
        if f.name=='power_protection.kicad_sch':
            assert first(first(b,'title_block'),'rev')[1]=='TBP55-CANDIDATE'
            first(first(b,'title_block'),'rev')[:]=first(first(a,'title_block'),'rev')
        assert a==b,f.name
    z0,z1=[{z['uuid']:z for z in c['zones']} for c in [before,after]]
    assert z0.keys()==z1.keys() and len(z1)==47
    t0,t1=[{str(first(z,'uuid')[1]):z for z in children(b,'zone')} for b in [b0,b1]]
    edited={z['uuid']:z for z in r['edited_zone_outlines']}
    assert set(edited)=={'13cfea4d-d36e-5757-b531-ed680e4c4562','4b63f119-2e71-5d61-96f6-8b78a1f5c6cb'}
    stripfill=lambda z,edit=False:[n for n in z if not(isinstance(n,list) and n and n[0] in (['filled_polygon','polygon'] if edit else ['filled_polygon']))]
    changes=[]
    for u,z in z0.items():
        assert stripfill(t0[u],u in edited)==stripfill(t1[u],u in edited)
        if u in edited:
            wanted=Polygon(edited[u]['outer_mm'],edited[u]['holes_mm'])
            assert shape(z1[u]['authored_outline']).hausdorff_distance(wanted)<2e-6
            assert shape(z['authored_outline']).difference(wanted.buffer(.000002)).area<1e-6
        else:assert z['authored_outline']==z1[u]['authored_outline']
        if u not in r['refilled_existing_zones']:assert z==z1[u] and t0[u]==t1[u]
        else:changes.append(dict(zone_uuid=u,layer=z['layer'],changed_area_mm2=shape(z['polygons']).symmetric_difference(shape(z1[u]['polygons'])).area))
    assert set(fill['unchanged_existing_zone_canonical_polygon_match'])==z0.keys()-set(r['refilled_existing_zones'])
    quietpaths=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']
    quietids={u for p in quietpaths for q in json.loads(p.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
    assert all(z0[u]==z1[u] for u in quietids),'quiet field changed'
    supplyids={u for u,z in z0.items() if z['net']!='PWR_AGND'}
    assert len(supplyids)==11
    assert all(z0[u]==z1[u] for u in supplyids),'supply field changed; requires separate current-path review'
    digital,analog=quietpaths
    qs=json.loads(digital.read_text())['quiet_ground_islands']+json.loads(analog.read_text())['quiet_ground_islands'];quiet=[]
    def hits(cap,z):
        field=shape(z['polygons'])
        return {o['uuid'] for o in cap['objects'] if o['net']=='PWR_AGND' and o['layers'].get(z['layer']) and field.buffer(.0015).intersection(shape(o['layers'][z['layer']])).area>1e-9}
    for q in qs:
        zs=set(q['zone_uuids']);vs=[q['star_via'],*q['control_vias'],*q['extra_quiet_vias']];own={v['uuid'] for v in vs};contacts={}
        for u in zs:
            contacts[u]=hits(after,z1[u]);assert contacts[u]==hits(before,z0[u]) and contacts[u]<=own,(q['ref'],u,'contacts')
            assert len(z0[u]['polygons'])==len(z1[u]['polygons']),(u,'region count')
            field=shape(z1[u]['polygons'])
            assert all(field.distance(shape(z['polygons']))>=.1985 for uid,z in z1.items() if uid!=u and z['net']=='PWR_AGND' and z['layer']==z1[u]['layer'])
        reached={q['star_via']['uuid']};pending=set(zs)
        while True:
            prev=set(reached)
            for u in list(pending):
                if reached&contacts[u]:reached.update(contacts[u]);pending.remove(u)
            if reached==prev:break
        assert not pending and own<=reached
        for v in vs:
            sets=[]
            for cap,zmap in [(before,z0),(after,z1)]:
                o=next(o for o in cap['objects'] if o['uuid']==v['uuid'])
                sets.append({u for u,z in zmap.items() if u not in zs and z['net']=='PWR_AGND' and o['layers'].get(z['layer']) and shape(o['layers'][z['layer']]).intersects(shape(z['polygons']))})
            assert sets[0]==sets[1]
            if v['uuid']==q['star_via']['uuid']:assert sets[1] and all(z1[u]['layer']=='In5.Cu' for u in sets[1])
            else:assert not sets[1]
        quiet.append(dict(ref=q['ref'],contacts_preserved=True,owned_graph_connected=True,star_only_main_return=True))
    fields0,excluded0=anchored_fields(before);fields1,excluded1=anchored_fields(after)
    assert excluded0==excluded1,'unanchored fragment changed'
    def viaholes(objs):
        holes={}
        for o in objs.values():
            if o['kind']=='PCB_VIA':holes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
        return {n:unary_union(v) for n,v in holes.items()}
    holes0,holes1=viaholes(old),viaholes(new);references=[]
    # Prepared buffer maps avoid repeating expensive polygon buffering per track.
    f0={k:f.buffer(.0015) for k,f in fields0.items()};f1={k:f.buffer(.0015) for k,f in fields1.items()}
    layers=before['copper_layers']
    for u,o in old.items():
        if o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
        layer,=o['layers'];i=layers.index(layer);adj={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)}
        band=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(holes0.get(o['net'],Polygon()))
        if band.is_empty:continue
        for (l,gid),field in f0.items():
            if l not in adj or band.difference(field).area>=1e-6:continue
            anchor=before['all_groups'][gid][0]
            missing=band.difference(f1[l,new[anchor]['group']]).area
            assert missing<1e-6,(u,l,missing)
            references.append(dict(track_uuid=u,reference_layer=l,uncovered_mm2=missing))
    main=next(o['group'] for o in new.values() if o.get('ref')=='P_C103' and o.get('pin')=='2');newrefs=[]
    for route in r['routes']:
        assert route['reference_layer']=={'F.Cu':'In1.Cu','B.Cu':'In6.Cu','In2.Cu':'In1.Cu','In6.Cu':'In5.Cu'}[route['layer']]
        l=route['reference_layer'];band=LineString(route['path_mm']).buffer(.1).difference(holes1.get(route['net'],Polygon()))
        missing=band.difference(f1[l,main]).area
        assert missing<1e-6,(route['net'],route['layer'],missing)
        newrefs.append(dict(net=route['net'],layer=route['layer'],reference_layer=l,uncovered_mm2=missing))
    plane_stitches=[]
    for v in r['vias']:
        o=new[v['uuid']]
        assert o['net']=='PWR_AGND' and o['group']==main
        assert all(fields1[layer,main].intersection(shape(o['layers'][layer])).area>1e-9 for layer in ['In1.Cu','In6.Cu'])
        plane_stitches.append(dict(uuid=v['uuid'],position_mm=v['position_mm'],both_extended_planes_connected=True))
    for route in r['routes']:
        pad=next(o for o in new.values() if o.get('ref')==route['pad_ref'] and o.get('pin')==route['pad_pin'])
        assert pad['net']=='PWR_AGND' and pad['group']==main
    repaired=[]
    for ref,pin in [('N_U44','4'),('N_U46','4'),('N_U46','6'),('N_U46','13'),('N_U34','1'),('N_U34','4'),('N_R22','1')]:
        pad=next(o for o in new.values() if o.get('ref')==ref and o.get('pin')==pin)
        layer,=pad['layers'];ref_layer={'F.Cu':'In1.Cu','B.Cu':'In6.Cu'}[layer]
        band=Point(pad['position_mm']).buffer(.1)
        before_missing=band.difference(f0[ref_layer,main0]).area
        after_missing=band.difference(f1[ref_layer,main]).area
        assert before_missing>=1e-6 and after_missing<1e-6,(ref,pin,after_missing)
        repaired.append(dict(ref=ref,pin=pin,reference_layer=ref_layer,before_uncovered_mm2=before_missing,after_uncovered_mm2=after_missing))
    erc=json.loads((OUT/'erc.json').read_text());findings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(findings)==2 and all(v['severity']=='warning' for v in findings)
    assert native['geometry_findings']==native['schematic_parity_findings']==0
    sources=[Path(__file__),*paths,*quietpaths,BASE/'netlist.xml',OUT/'netlist.xml',OUT/'erc.json',REPO/'hardware/fabrication/plan_two_board_startup_controls.py',REPO/'hardware/fabrication/plan_two_board_nf_logic_ground.py',REPO/'hardware/fabrication/verify_native_zone_unfracture.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},zone_capture_fidelity=fidelity,
        generated_pad_identity_aliases=aliases,closed_connections=closed,new_opens=native['opens'],
        merged_ground_groups=r['allowed_ground_groups'],all_other_native_groups_preserved=True,
        all_original_objects_placements_and_schematic_nets_preserved=True,quiet_network_fields_preserved=7,
        all_eleven_supply_planes_unchanged=True,
        retained_reference_checks=references,new_reference_checks=newrefs,zone_changes=changes,
        plane_stitches=plane_stitches,repaired_pad_centers=repaired,quiet_returns=quiet,
        unanchored_fragments_preserved=True,geometry_errors=0,parity_errors=0,ERC_errors=0,ERC_warnings=2,
        startup_functionally_verified=False,fabrication_released=False)
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(opens=native['opens'],closed_connections=closed,retained_reference_checks=len(references),new_reference_checks=len(newrefs),quiet_networks_preserved=7)))


if __name__=='__main__':run()
