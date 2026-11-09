"""Independently audit additive startup routing and anchored return coverage."""
import json
import math
from pathlib import Path
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha, read_netlist
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
BASE=STAGING/'two-board-power-nf-logic-ground-native-02'
CAP=STAGING/'two-board-power-routing-inputs-nf-logic-ground-02/capture.json'
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.verify_native_zone_unfracture import verify_capture

OUT=STAGING/'two-board-power-nf-logic-detours-native-02'
AFTER=STAGING/'two-board-power-routing-inputs-nf-logic-detours-02/capture.json'
FILL=STAGING/'two-board-power-nf-logic-detours-filled-03/local-plane-fill.json'


def run():
    target=OUT/'nf-logic-detour-review.json';assert not target.exists()
    paths=[CAP,AFTER,OUT/'nf-logic-detour-routing.json',OUT/'review.json',FILL]
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
    for join in r['joins']:
        a,b=join['source_groups']
        wa=before['all_groups'][a][0];wb=before['all_groups'][b][0]
        assert old[wa]['net']==old[wb]['net']==join['net']
        ga=next(g for g in expected if wa in g);gb=next(g for g in expected if wb in g)
        assert ga!=gb;expected.remove(ga);expected.remove(gb);expected.add(ga|gb)
    assert expected==actual,'native connectivity differs from declared joins'
    assert all(new[u].get('group') for u in added)
    assert before['native_uncapped_opens']-after['native_uncapped_opens']==len(r['joins'])==r['expected_closed_connections']
    assert after['native_uncapped_opens']==native['opens']==r['expected_opens']
    a0,p0=read_netlist(BASE/'netlist.xml');a1,p1=read_netlist(OUT/'netlist.xml')
    assert a0.keys()==a1.keys() and p0==p1
    for f in BASE.glob('*.kicad_sch'):
        a,b=[read_sexpr((d/f.name).read_text()) for d in [BASE,OUT]]
        if f.name=='power_protection.kicad_sch':
            assert first(first(b,'title_block'),'rev')[1]=='TBP59-CANDIDATE'
            first(first(b,'title_block'),'rev')[:]=first(first(a,'title_block'),'rev')
        assert a==b,f.name
    z0,z1=[{z['uuid']:z for z in c['zones']} for c in [before,after]]
    assert z0.keys()==z1.keys() and len(z1)==47
    t0,t1=[{str(first(z,'uuid')[1]):z for z in children(b,'zone')} for b in [b0,b1]]
    stripfill=lambda z:[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')]
    changes=[]
    for u,z in z0.items():
        assert stripfill(t0[u])==stripfill(t1[u]) and z['authored_outline']==z1[u]['authored_outline']
        if u not in r['refilled_existing_zones']:assert z==z1[u] and t0[u]==t1[u]
        else:changes.append(dict(zone_uuid=u,layer=z['layer'],changed_area_mm2=shape(z['polygons']).symmetric_difference(shape(z1[u]['polygons'])).area))
    retained=z0.keys()-set(r['refilled_existing_zones'])
    rounded=fill['retained_existing_zone_rounding_only']
    assert set(rounded)=={'0552f897-fa23-5173-9e85-a8133b7a4048'}
    assert set(fill['unchanged_existing_zone_canonical_polygon_match'])|set(rounded)==retained
    assert set(fill['original_fill_retained_exactly'])==retained
    from hardware.fabrication.verify_native_zone_unfracture import verify
    diagnosis_path=STAGING/'two-board-nf-detour-refill-diagnosis-01/native-comparison.json'
    diagnosis=json.loads(diagnosis_path.read_text())
    assert len(diagnosis['unexpected_native_fill_changes'])==1
    row=diagnosis['unexpected_native_fill_changes'][0]
    assert rounded[row['uuid']]==verify(row['before_polygons'],row['after_polygons'])
    assert rounded[row['uuid']]['symmetric_difference_area_mm2']<1e-6
    assert sorted(len(p['holes']) for p in row['before_polygons'])==sorted(len(p['holes']) for p in row['after_polygons'])
    quietpaths=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']
    quietids={u for p in quietpaths for q in json.loads(p.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
    assert all(z0[u]==z1[u] for u in quietids),'quiet field changed'
    supplyids={u for u,z in z0.items() if z['net']!='PWR_AGND'}
    assert len(supplyids)==11
    assert all(z0[u]==z1[u] for u in supplyids),'supply field changed; requires separate current-path review'
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
    transitions=[]
    signal_vias=[v for v in r['vias'] if v['net']!='PWR_AGND']
    assert {(v['net'],tuple(v['position_mm'])) for v in signal_vias}=={(t['net'],tuple(t['position_mm'])) for t in r.get('reference_transitions',[])}
    for t in r.get('reference_transitions',[]):
        refs={path['reference_layer'] for path in r['routes'] if path['net']==t['net'] and any(math.dist(t['position_mm'],pt)<1e-6 for pt in [path['path_mm'][0],path['path_mm'][-1]])}
        assert refs==set(t['reference_layers'])
        if t.get('same_reference_plane'):
            assert len(t['reference_layers'])==1
            transitions.append(dict(t,verified=True));continue
        assert set(t['reference_layers'])=={'In1.Cu','In6.Cu'}
        matches=[o for o in new.values() if o['kind']=='PCB_VIA' and o['net']=='PWR_AGND' and math.dist(o['position_mm'],t['ground_via_mm'])<1e-6]
        assert len(matches)==1;via=matches[0]
        assert via['group']==main
        assert all(fields1[l,main].intersection(shape(via['layers'][l])).area>1e-9 for l in t['reference_layers'])
        d=math.dist(via['position_mm'],t['position_mm'])
        assert abs(d-t['distance_mm'])<1e-6 and d<=r['reference_transition_spacing_limit_mm']==1.5
        transitions.append(dict(t,verified=True,ground_via_uuid=via['uuid']))
    erc=json.loads((OUT/'erc.json').read_text());findings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(findings)==2 and all(v['severity']=='warning' for v in findings)
    assert native['geometry_findings']==native['schematic_parity_findings']==0
    sources=[Path(__file__),diagnosis_path,*paths,*quietpaths,BASE/'netlist.xml',OUT/'netlist.xml',OUT/'erc.json',REPO/'hardware/fabrication/plan_two_board_startup_controls.py',REPO/'hardware/fabrication/verify_native_zone_unfracture.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},zone_capture_fidelity=fidelity,
        generated_pad_identity_aliases=aliases,closed_connections=len(r['joins']),new_opens=native['opens'],
        declared_native_group_merges=r['joins'],all_other_native_groups_preserved=True,
        all_original_objects_placements_and_schematic_nets_preserved=True,quiet_network_fields_preserved=7,
        all_eleven_supply_planes_unchanged=True,
        retained_reference_checks=references,new_reference_checks=newrefs,zone_changes=changes,
        reference_transitions=transitions,original_supply_fill_preserved_despite_native_rounding=rounded,
        unanchored_fragments_preserved=True,geometry_errors=0,parity_errors=0,ERC_errors=0,ERC_warnings=2,
        startup_functionally_verified=False,fabrication_released=False)
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(opens=native['opens'],closed_connections=len(r['joins']),retained_reference_checks=len(references),new_reference_checks=len(newrefs),quiet_networks_preserved=7)))


if __name__=='__main__':run()
