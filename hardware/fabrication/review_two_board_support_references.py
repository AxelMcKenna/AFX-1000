"""Verify support-only route replacements preserve the complete native topology."""
import json
import math
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha,read_netlist
from hardware.fabrication.verify_native_zone_unfracture import verify_capture
BASE=STAGING/'two-board-power-digital-return-native-03'
OUT=STAGING/'two-board-power-support-references-native-01'
BEFORE=STAGING/'two-board-power-routing-inputs-2210-digital-return-03/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2210-support-references-01/capture.json'


def run():
    paths=[BEFORE,AFTER,OUT/'support-reference-routing.json',OUT/'review.json']
    before,after,r,native=[json.loads(p.read_text()) for p in paths]
    for path,data in zip(paths,[before,after,r,native]):
        for key in ['source_sha256','artifact_sha256']:
            for name,digest in data.get(key,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else path.parent)/p
                assert sha(p)==digest,(path,name)
    fidelity=verify_capture(after)
    old,new=[{o['uuid']:o for o in cap['objects']} for cap in [before,after]]
    retired=set(r['retired_objects']);added={u for route in r['routes'] for u in route['segment_uuids']}
    assert len(retired)==6 and len(added)==9
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
    assert all(physical(o)==physical(new[u]) for u,o in old.items() if u not in retired)
    b0,b1=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
    strip=lambda b:[n for n in b if not(isinstance(n,list) and n and n[0]=='segment' and str(first(n,'uuid')[1]) in retired|added)]
    assert strip(b0)==strip(b1),'Undeclared change to board, component, via or zone'
    assert before['zones']==after['zones'] and len(after['zones'])==47
    for route in r['routes']:
        assert len(route['segment_uuids'])==len(route['path_mm'])-1
        for uid,(start,end) in zip(route['segment_uuids'],zip(route['path_mm'],route['path_mm'][1:])):
            o=new[uid]
            assert o['kind']=='PCB_TRACK' and list(o['layers'])==[route['layer']] and o['net']==route['net'] and o['width_mm']==route['width_mm']
            assert math.dist(start,o['position_mm'])<1e-6 and math.dist(end,o['end_mm'])<1e-6
    expected={frozenset(set(g)-retired) for g in before['all_groups'].values()}-{frozenset()}
    actual={frozenset(set(g)-added) for g in after['all_groups'].values()}-{frozenset()}
    assert expected==actual and all(new[u].get('group') for u in added)
    assert before['native_uncapped_opens']==after['native_uncapped_opens']==native['opens']==2210
    a0,p0=read_netlist(BASE/'netlist.xml');a1,p1=read_netlist(OUT/'netlist.xml')
    assert a0.keys()==a1.keys() and p0==p1
    assert all(a0[k].findtext(f)==a1[k].findtext(f) for k in a0 for f in ['value','footprint','datasheet'])
    erc=json.loads((OUT/'erc.json').read_text());findings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(findings)==2 and all(v['severity']=='warning' for v in findings)
    assert native['geometry_findings']==native['schematic_parity_findings']==0
    sources=[Path(__file__),*paths,*[d/n for d in [BASE,OUT] for n in ['power_protection.kicad_pcb','netlist.xml']],OUT/'erc.json',REPO/'hardware/fabrication/verify_native_zone_unfracture.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},zone_capture_fidelity=fidelity,
                generated_pad_identity_aliases=aliases,closed_connections=0,new_opens=2210,
                all_native_groups_preserved=True,all_other_objects_preserved=True,
                all_zones_and_fills_unchanged=True,all_supply_planes_unchanged=True,
                quiet_return_geometry_unchanged=True,retained_part_count=len(a0),retained_pin_entries=len(p0),
                geometry_errors=0,parity_errors=0,ERC_errors=0,ERC_warnings=2,
                reference_audit_pending=True,fabrication_released=False)
    with (OUT/'support-reference-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ['closed_connections','new_opens','all_native_groups_preserved','all_zones_and_fills_unchanged']}))


if __name__=='__main__':run()
