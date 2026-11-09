"""Independently check boot-return net partition and unchanged native geometry."""
import json
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha, read_netlist
from hardware.fabrication.audit_two_board_power_delta import geometry

BASE=STAGING/'two-board-power-buck-local-native-01'
OUT=STAGING/'two-board-power-boot-return-native-01'
BEFORE=STAGING/'two-board-power-routing-inputs-2535-buck-local/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2533-boot-return/capture.json'


def run():
    report=json.loads((OUT/'boot-return-change.json').read_text())
    before,after=[json.loads(p.read_text()) for p in [BEFORE,AFTER]]
    for record in [report,before,after]:
        for name,h in record['source_sha256'].items():assert sha(REPO/name)==h,name
    trees=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
    assert geometry(trees[0])==geometry(trees[1]),'Undeclared physical change'
    oldparts,oldpins=read_netlist(BASE/'netlist.xml');parts,pins=read_netlist(OUT/'netlist.xml')
    assert oldparts.keys()==parts.keys() and len(parts)==1088
    for ref in parts:
        for field in ['value','footprint']:assert parts[ref].findtext(field)==oldparts[ref].findtext(field)
    expected={('P_U20','13'):'P03_D_BOOT_RETURN',('P_C201','2'):'P03_D_BOOT_RETURN',
              ('P_U23','13'):'P03_A_BOOT_RETURN',('P_C221','2'):'P03_A_BOOT_RETURN'}
    assert oldpins.keys()==pins.keys()
    assert {p for p in pins if pins[p]!=oldpins[p]}==set(expected)
    for pair,name in expected.items():assert pins[pair]=='P_power_supply/'+name
    def collapsed(name):return name.replace('P03_A_BOOT_RETURN','P03_A_SW').replace('P03_D_BOOT_RETURN','P03_D_SW')
    assert {p:collapsed(n) for p,n in pins.items()}==oldpins
    for u,c in [('P_U20','P_C201'),('P_U23','P_C221')]:
        assert {p for p,n in pins.items() if n==pins[(u,'13')]}=={(u,'13'),(c,'2')}
        assert pins[(u,'10')]!=pins[(u,'13')]
    old,new=[{o['uuid']:o for o in d['objects']} for d in [before,after]]
    def physical(o):return {k:v for k,v in o.items() if k not in ['uuid','group','net']}
    aliases={}
    for uid in old.keys()-new.keys():
        assert old[uid]['kind']=='PAD'
        hits=[v for v in new.keys()-old.keys() if physical(old[uid])==physical(new[v])]
        assert len(hits)==1;aliases[uid]=hits[0]
    assert len(aliases)==len(set(aliases.values()))
    assert {aliases.get(u,u) for u in old}==new.keys()
    changed=[]
    for uid,o in old.items():
        n=new[aliases.get(uid,uid)];assert physical(o)==physical(n),uid
        assert collapsed(n['net'])==o['net'],uid
        if n['net']!=o['net']:changed.append(uid)
    assert set(changed)==set(report['retargeted_tracks'])|{u for u,o in old.items() if (o.get('ref'),o.get('pin')) in expected}
    groups={u:set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        mapped={aliases.get(u,u) for u in g};assert mapped==groups[next(iter(mapped))]
    native=json.loads((OUT/'review.json').read_text())
    assert native['opens']==after['native_uncapped_opens']==after['independent_sum_of_pad_cluster_gaps']==2533
    assert native['geometry_findings']==native['schematic_parity_findings']==0
    erc=json.loads((OUT/'erc.json').read_text());warnings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(warnings)==2 and all(v['severity']=='warning' and v['type']=='ground_pin_not_ground' for v in warnings)
    paths=[Path(__file__),BEFORE,AFTER,*[OUT/n for n in ['boot-return-change.json','power_protection.kicad_pcb','netlist.xml','review.json','erc.json','drc.json']]]
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        all_board_geometry_unchanged=True,all_native_objects_preserved=len(old),all_prior_physical_groups_preserved=len(before['all_groups']),
        electrical_components=1088,schematic_pin_entries=len(pins),declared_pin_net_changes=4,retargeted_tracks=2,
        complete_pin_partition_restored_by_declared_internal_bridges=True,
        native_opens=2533,previous_opens=2535,physical_connections_added=0,
        open_reduction_is_internal_pin_model_correction=True,
        geometry_findings=0,parity_findings=0,erc_errors=0,erc_warnings=2,
        prior_geometry_clearance_and_visual_evidence_remains_applicable=True,
        power_stage_qualified=False,fabrication_released=False)
    with (OUT/'boot-return-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}))

if __name__=='__main__':run()
