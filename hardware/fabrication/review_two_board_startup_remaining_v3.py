"""Audit startup reference edits, complete native topology and quiet ownership."""
import json,math
from pathlib import Path
from shapely.geometry import Polygon
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha,read_netlist
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.verify_native_zone_unfracture import verify_capture
from hardware.fabrication.route_two_board_buck_cell import transform_object,position,mechanical_check
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.integrate_two_board_signal import prop
BASE=STAGING/'two-board-power-startup-cells-native-03'
OUT=STAGING/'two-board-power-startup-remaining-native-03'
BEFORE=STAGING/'two-board-power-routing-inputs-2199-startup-cells-03/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2172-startup-remaining-03/capture.json'
FILL=STAGING/'two-board-power-startup-remaining-filled-03/local-plane-fill.json'


def run():
    paths=[BEFORE,AFTER,OUT/'startup-cell-routing.json',OUT/'review.json',FILL]
    before,after,r,native,fill=[json.loads(p.read_text()) for p in paths]
    for path,data in zip(paths,[before,after,r,native,fill]):
        for key in ['source_sha256','artifact_sha256']:
            for name,digest in data.get(key,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else path.parent)/p
                assert sha(p)==digest,(path,name)
    fidelity=verify_capture(after)
    old,new=[{o['uuid']:o for o in cap['objects']} for cap in [before,after]]
    retired=set(r['retired_objects']);tracks={u for route in r['routes'] for u in route['segment_uuids']};vias={v['uuid'] for v in r['vias']};added=tracks|vias
    assert len(retired)==112 and all(old[u]['kind']=='PCB_TRACK' for u in retired) and len(tracks)==r['added_tracks'] and len(vias)==r['added_vias']==20
    physical=lambda o:{k:v for k,v in o.items() if k not in ['uuid','group']}
    aliases={}
    for u in old.keys()-new.keys()-retired:
        assert old[u]['kind']=='PAD'
        matches=[v for v in new.keys()-old.keys()-added if physical(old[u])==physical(new[v])]
        assert len(matches)==1,(u,'unmatched unchanged generated pad')
        aliases[matches[0]]=u
    assert set(aliases)==new.keys()-old.keys()-added
    for o in after['objects']:
        o['uuid']=aliases.get(o['uuid'],o['uuid']);o['group']=aliases.get(o['group'],o['group'])
    after['all_groups']={aliases.get(g,g):[aliases.get(u,u) for u in members] for g,members in after['all_groups'].items()}
    new={o['uuid']:o for o in after['objects']}
    assert old.keys()-retired==new.keys()-added
    assert all(physical(o)==physical(new[u]) for u,o in old.items() if u not in retired and o.get('ref') not in r['moves'])
    b0,b1=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
    strip=lambda b:[n for n in b if not(isinstance(n,list) and n and (n[0]=='zone' or n[0]=='footprint' and prop(n,'Reference')[2] in r['moves'] or n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in retired|added))]
    assert strip(b0)==strip(b1),'Undeclared change to board or component'
    fps0,fps1=[{prop(f,'Reference')[2]:f for f in children(b,'footprint')} for b in [b0,b1]]
    assert set(r['moves'])=={'E_C57','E_C59','E_C67','E_C71','E_C72'}
    placementpath=STAGING/'two-board-placement-05/capture.json';placement=json.loads(placementpath.read_text())
    for row in r['side_reconciliations']:
        rec=next(x for x in placement['parts'] if x['id']==row['ref']);assert rec['side']==row['old_side'];rec['side']=row['current_side']
    mechanical_check(fps1,set(r['moves']),placement)
    for ref,(xy,rot,flip) in r['moves'].items():
        assert not flip and sexpr(rotate_footprint(fps0[ref],xy,rot))==sexpr(fps1[ref])
        for u,o in old.items():
            if o.get('ref')!=ref:continue
            assert len(before['all_groups'][o['group']])==1
            n=new[u];expected=transform_object(o,position(fps0[ref]),xy,rot)
            assert math.dist(n['position_mm'],expected['position_mm'])<1e-6
            for k in ['kind','net','ref','pin','drill_mm','npth']:assert n[k]==o[k]
            assert n['layers'].keys()==expected['layers'].keys()
            for layer in n['layers']:assert shape(n['layers'][layer]).hausdorff_distance(shape(expected['layers'][layer]))<2e-6
    for route in r['routes']:
        assert len(route['segment_uuids'])==len(route['path_mm'])-1
        for uid,(start,end) in zip(route['segment_uuids'],zip(route['path_mm'],route['path_mm'][1:])):
            o=new[uid]
            assert o['kind']=='PCB_TRACK' and list(o['layers'])==[route['layer']] and o['net']==route['net'] and o['width_mm']==route['width_mm']
            assert math.dist(start,o['position_mm'])<1e-6 and math.dist(end,o['end_mm'])<1e-6
    for v in r['vias']:
        o=new[v['uuid']]
        assert o['kind']=='PCB_VIA' and o['net']==v['net'] and o['width_mm']==v['size_mm']==.6 and o['drill_mm']==v['drill_mm']==.3
        assert math.dist(o['position_mm'],v['position_mm'])<1e-6 and o['span']==['F.Cu','B.Cu']
    expected={frozenset(set(g)-retired) for g in before['all_groups'].values()}-{frozenset()}
    actual={frozenset(set(g)-added) for g in after['all_groups'].values()}-{frozenset()}
    def pad(objects,ref,pin):return next(o for o in objects.values() if o.get('ref')==ref and o.get('pin')==pin)
    assert len(r['joins'])==27
    for join in r['joins']:
        p,q=[pad(old,*join[k]) for k in ['left','right']]
        assert p['net']==q['net']==join['net']
        left=next(g for g in expected if p['uuid'] in g);right=next(g for g in expected if q['uuid'] in g)
        assert left!=right
        expected.remove(left);expected.remove(right);expected.add(left|right)
    assert expected==actual and all(new[u].get('group') for u in added)
    assert {cell['chip'] for cell in r['cells']}=={'E_U18','E_U19','E_U20','E_U22','E_U23','E_U24','E_U26','E_U27'}
    for cell in r['cells']:
        chip,cap=cell['chip'],cell['bypass']
        assert pad(new,chip,cell['supply_pin'])['group']==pad(new,cap,'1')['group']
        assert pad(new,chip,cell['ground_pin'])['group']==pad(new,cap,'2')['group']==pad(new,'P_C103','2')['group']
    assert before['native_uncapped_opens']==2199 and after['native_uncapped_opens']==native['opens']==2172
    a0,p0=read_netlist(BASE/'netlist.xml');a1,p1=read_netlist(OUT/'netlist.xml')
    assert a0.keys()==a1.keys() and p0==p1
    assert all(a0[k].findtext(f)==a1[k].findtext(f) for k in a0 for f in ['value','footprint','datasheet'])
    z0,z1=[{z['uuid']:z for z in c['zones']} for c in [before,after]]
    assert z0.keys()==z1.keys() and len(z1)==47
    t0,t1=[{str(first(z,'uuid')[1]):z for z in children(b,'zone')} for b in [b0,b1]]
    edited={z['uuid']:z for z in r['edited_zone_outlines']};refilled=set(r['refilled_existing_zones'])
    assert set(edited)=={'4b63f119-2e71-5d61-96f6-8b78a1f5c6cb'} and len(refilled)==4
    stripzone=lambda z,keys:[n for n in z if not(isinstance(n,list) and n and n[0] in keys)]
    for u,z in z0.items():
        if u not in refilled:assert t0[u]==t1[u] and z==z1[u],u
        else:assert stripzone(t0[u],['filled_polygon']+(['polygon'] if u in edited else []))==stripzone(t1[u],['filled_polygon']+(['polygon'] if u in edited else []))
        if u in edited:assert shape(z1[u]['authored_outline']).hausdorff_distance(Polygon(edited[u]['outer_mm'],edited[u]['holes_mm']))<2e-6
    assert set(fill['unchanged_existing_zone_canonical_polygon_match'])==z0.keys()-refilled
    digital=STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json'
    analog=STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json'
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
    erc=json.loads((OUT/'erc.json').read_text());findings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(findings)==2 and all(v['severity']=='warning' for v in findings)
    assert native['geometry_findings']==native['schematic_parity_findings']==0
    sources=[Path(__file__),*paths,digital,analog,placementpath,REPO/'hardware/fabrication/route_two_board_buck_cell.py',REPO/'hardware/fabrication/repack_two_board_buck_input.py',STAGING/'assembly-layout-04/allocation.json',*[d/n for d in [BASE,OUT] for n in ['power_protection.kicad_pcb','netlist.xml']],OUT/'erc.json',REPO/'hardware/fabrication/verify_native_zone_unfracture.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},zone_capture_fidelity=fidelity,
        generated_pad_identity_aliases=aliases,closed_connections=27,new_opens=2172,declared_native_group_merges=r['joins'],all_other_native_groups_preserved=True,
        all_other_objects_preserved=True,moved_footprints=r['moves'],local_bypass_ground_cells=[cell['chip'] for cell in r['cells']],quiet_returns=quiet,retained_part_count=len(a0),retained_pin_entries=len(p0),
        geometry_errors=0,parity_errors=0,ERC_errors=0,ERC_warnings=2,reference_audit_pending=True,fabrication_released=False)
    with (OUT/'startup-cell-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(opens=2172,declared_joins=27,all_other_native_groups_preserved=True,quiet_networks_preserved=7)))


if __name__=='__main__':run()
