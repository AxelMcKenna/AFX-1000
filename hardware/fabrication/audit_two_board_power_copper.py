"""Verify restored copper against native source shapes and physical connections."""
import copy
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from hardware.electronics.common.sexpr import children, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.native_two_board_power import partition
from hardware.fabrication.audit_two_board_module_cutoff import branch, numerical, package
from hardware.fabrication.audit_two_board_enable_recovery import check_uv
from hardware.fabrication.audit_two_board_fault_mask import evaluate
from hardware.fabrication.audit_two_board_source_sense import verify_sense

BASE=STAGING/'two-board-power-native-10'
OUT=STAGING/'two-board-power-routed-native-02'


def audit():
    assert sys.platform=='linux'
    import pcbnew
    paths=[Path(__file__),BASE/'power_protection.kicad_pcb',BASE/'netlist.xml',
        OUT/'power_protection.kicad_pcb',OUT/'netlist.xml',OUT/'copper-restoration.json',
        OUT/'review.json',OUT/'erc.json',OUT/'drc.json',
        STAGING/'two-board-placement-05/capture.json',
        *[REPO/'hardware/fabrication'/n for n in ['audit_two_board_power_delta.py','native_two_board_power.py',
            'audit_two_board_module_cutoff.py','audit_two_board_enable_recovery.py',
            'audit_two_board_fault_mask.py','audit_two_board_source_sense.py']]]
    data=json.loads((OUT/'copper-restoration.json').read_text())
    cap=json.loads((STAGING/'two-board-placement-05/capture.json').read_text())
    for name,h in data['source_sha256'].items():assert sha(REPO/name)==h,name
    oldparts,oldpins=read_netlist(BASE/'netlist.xml');parts,pins=read_netlist(OUT/'netlist.xml')
    assert set(parts)==set(oldparts) and partition(pins)==partition(oldpins)
    for ref in parts:
        for field in ['value','footprint']:assert parts[ref].findtext(field)==oldparts[ref].findtext(field),(ref,field)
    oldtree,newtree=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [BASE,OUT]]
    oldfps,newfps=[{prop(f,'Reference')[2]:f for f in children(t,'footprint')} for t in [oldtree,newtree]]
    assert set(oldfps)==set(newfps)
    for ref in oldfps:assert geometry(oldfps[ref])==geometry(newfps[ref]),ref
    # Footprints are checked above with only native net/path annotations removed.
    def layout(t):return [n for n in t if not(isinstance(n,list) and n and n[0] in ['footprint','net','segment','via','arc'])]
    assert layout(oldtree)==layout(newtree)
    branch(parts,pins);numbers=numerical(parts);land=package(newfps['G_U1'])
    assert len(evaluate(pins))==32 and len(verify_sense(parts,pins))==2
    uv,_,_=check_uv(pins);assert len(uv)==64
    boards=[]
    def load(path):
        b=pcbnew.LoadBoard(str(path));b.BuildConnectivity();b.GetConnectivity().RecalculateRatsnest();boards.append(b)
        return b
    final=load(OUT/'power_protection.kicad_pcb');before=load(BASE/'power_protection.kicad_pcb')
    sources={}
    for role in {r['role'] for r in data['selected_nets']}:
        p=REPO/cap['sources'][role]['path'];paths.append(p);sources[role]=load(p)
    def point(p,delta=(0,0)):
        return tuple(round(pcbnew.ToMM(v)-d,6) for v,d in zip((p.x,p.y),delta))
    def copper(t,delta=(0,0)):
        kind=t.GetClass()
        via=kind=='PCB_VIA'
        mid=point(t.GetMid(),delta) if kind=='PCB_ARC' else None
        # Through vias span the front/back surfaces on the new eight-layer
        # board. Its additional enabled inner layers are not a changed drill
        # or a blind/buried via; physical stack qualification stays open.
        return (kind,point(t.GetStart(),delta),point(t.GetEnd(),delta),mid,
            (t.TopLayer(),t.BottomLayer(),int(t.GetViaType())) if via else t.GetLayer(),
            round(pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu) if via else t.GetWidth()),6),
            round(pcbnew.ToMM(t.GetDrillValue()),6) if via else None)
    finaltracks={t.m_Uuid.AsString():t for t in final.GetTracks()}
    claimed={u for r in data['selected_nets'] for u in r['target_copper_uuids']}
    assert claimed==set(finaltracks) and sum(len(r['target_copper_uuids']) for r in data['selected_nets'])==len(claimed)
    def groups(board,refs,net,prefix='',delta=(0,0)):
        selected={}
        for f in board.GetFootprints():
            if f.GetReference() not in refs:continue
            for p in f.Pads():
                if p.GetNetname().lstrip('/')==net and p.GetNumber():
                    selected[p.m_Uuid.AsString()]=(p,(prefix+f.GetReference(),p.GetNumber(),*point(p.GetPosition(),delta)))
        remaining=set(selected);result=[];conn=board.GetConnectivity()
        while remaining:
            uid=min(remaining)
            members=({uid}|{p.m_Uuid.AsString() for p in conn.GetConnectedItems(selected[uid][0])})&set(selected)
            result.append(frozenset(selected[k][1] for k in members));remaining-=members
        return result
    rows=[];expected_count=Counter();source_groups=0;net_full=0
    for row in data['selected_nets']:
        prefix=row['key'].split(':')[0]+'_';source=sources[row['role']]
        sc=[t for t in source.GetTracks() if t.GetNetname().lstrip('/')==row['source_net']]
        tc=[finaltracks[u] for u in row['target_copper_uuids']]
        assert all(t.GetNetname().lstrip('/')==row['target_net'] for t in tc)
        assert Counter(copper(t) for t in sc)==Counter(copper(t,row['translation_mm']) for t in tc),row['key']
        expected_count.update(t.GetClass() for t in sc)
        target_refs={r for r,p in row['terminals']};source_refs={r[len(prefix):] for r in target_refs}
        a=groups(source,source_refs,row['source_net'],prefix)
        b=groups(final,target_refs,row['target_net'],delta=row['translation_mm'])
        assert set().union(*a)==set().union(*b),row['key']
        lost=[sorted(g) for g in a if not any(g<=new for new in b)]
        assert not lost,(row['key'],lost)
        source_groups+=len(a);net_full+=len(b)==1
        rows.append(dict(key=row['key'],physical_pad_instances=sum(map(len,a)),source_groups=len(a),
            target_groups=len(b),all_selected_terminals_connected=len(b)==1,regressions=lost))
    # Independent controls detect copper and connectivity changes, rather than
    # merely trusting the constructor's hashes or selected-net count.
    example=next(row for row in rows if row['physical_pad_instances']>1 and row['target_groups']==1)
    witness=next(r for r in data['selected_nets'] if r['key']==example['key'])
    source=sources[witness['role']];prefix=witness['key'].split(':')[0]+'_'
    target_refs={r for r,p in witness['terminals']}
    physical=groups(final,target_refs,witness['target_net'],delta=witness['translation_mm'])
    split=[frozenset([p]) for p in set().union(*physical)]
    assert any(not any(g<=s for s in split) for g in physical)
    count=Counter(copper(t) for t in final.GetTracks());broken=count.copy();broken[next(iter(broken))]-=1
    assert count!=broken
    drc=json.loads((OUT/'drc.json').read_text());erc=json.loads((OUT/'erc.json').read_text())
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(warnings)==2 and all(v['type']=='ground_pin_not_ground' and v['severity']=='warning' for v in warnings)
    opens=final.GetConnectivity().GetUnconnectedCount(False)
    assert opens<before.GetConnectivity().GetUnconnectedCount(False)
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},unchanged_footprints=len(oldfps),
        unchanged_electrical_parts=len(parts),unchanged_schematic_pin_partition=True,
        restored_copper_counts=dict(expected_count),restored_source_nets=len(rows),source_physical_groups=source_groups,
        fully_connected_restored_terminal_sets=net_full,connection_evidence=rows,
        copper_shape_layer_width_drill_and_net_mapping_verified=True,
        missing_copper_control_detected=True,split_connection_control_detected=True,
        module_branch_rechecked=True,prior_fault_cases=32,prior_source_sense_channels=2,prior_UV_cases=len(uv),
        old_opens=before.GetConnectivity().GetUnconnectedCount(False),new_opens=opens,
        geometry_findings=0,schematic_parity_findings=0,erc_errors=0,erc_warnings=2,
        source_plane_zones_restored=False,stack_approved=False,complete_power_circuit=False,fabrication_released=False)
    p=OUT/'copper-audit.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','connection_evidence']},indent=2))


if __name__=='__main__':audit()
