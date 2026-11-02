"""Audit the explicit two-IC swap, retained geometry and original pad relationships."""
import argparse,copy,json,math
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_candidate import geometry_delta,native_evidence_errors,sha
from hardware.fabrication.audit_single_net import open_counts

ROOT=Path(__file__).resolve().parent
PAIR=('U38','U41')

def removed_nodes():
    paths=[ROOT/'staging'/n/'construction.json' for n in ['nf-logic-swap-prepared-01','nf-logic-swap-leaves-01']]
    rows=[]
    for p in paths:
        d=json.loads(p.read_text());assert all(sha(Path(n))==h for n,h in d['source_sha256'].items());rows+=d['removed_objects']
    assert len(rows)==203 and len({first(n,'uuid')[1] for n in rows})==203
    return rows,paths

def verify_geometry(before,after,removed,allowed):
    expected=copy.deepcopy(before)
    fps={next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(expected,'footprint')}
    poses={r:copy.deepcopy(first(fps[r],'at')[1:]) for r in PAIR}
    for here,other in [PAIR,PAIR[::-1]]:first(fps[here],'at')[1:]=copy.deepcopy(poses[other])
    for n in removed:
        assert first(n,'net')[-1] in allowed and n in expected;expected.remove(n)
    delta=geometry_delta(expected,after);assert delta['other_root_geometry_exact']
    for tag in ['footprint','zone']:assert not any(delta[tag].values())
    for tag in ['segment','via']:
        assert not delta[tag]['removed'] and not delta[tag]['changed']
        nodes={first(n,'uuid')[1]:n for n in children(after,tag)}
        for uid in delta[tag]['added']:
            node=nodes[uid];assert first(node,'net')[-1] in allowed
            if tag=='segment':assert first(node,'layer')[1] in {'F.Cu','In2.Cu','In3.Cu','B.Cu'} and float(first(node,'width')[1])>=.16
            else:assert float(first(node,'size')[1])==.6 and float(first(node,'drill')[1])==.3
    return geometry_delta(before,after)

def pad_review(before,after):
    pads=[{(o['ref'],o['pin']):o for o in c['objects'] if o['kind']=='PAD'} for c in (before,after)];assert pads[0].keys()==pads[1].keys();groups={}
    for key,old in pads[0].items():
        new=pads[1][key];assert old['net']==new['net']
        physical_key=(PAIR[1] if key[0]==PAIR[0] else PAIR[0],key[1]) if key[0] in PAIR else key
        assert math.dist(new['position_mm'],pads[0][physical_key]['position_mm'])<.000002,key
        groups.setdefault((old['net'],old['group']),[]).append(key)
    lost=[]
    for (net,group),keys in groups.items():
        buckets={}
        for key in keys:buckets.setdefault(str(pads[1][key]['group']),[]).append(key)
        if len(buckets)>1:lost.append(dict(net=net,old_group=group,split_pad_groups=list(buckets.values())))
    return lost

def track_lengths(tree):
    totals={}
    for n in children(tree,'segment'):
        net=first(n,'net')[-1];pts=[[float(v) for v in first(n,k)[1:3]] for k in ['start','end']];totals[net]=totals.get(net,0)+math.dist(*pts)
    return totals

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--after',required=True);ap.add_argument('--capture',required=True);ap.add_argument('--allow-incomplete',action='store_true');args=ap.parse_args()
    assert all(v and all(c.isalnum() or c in '-_' for c in v) for v in [args.after,args.capture])
    old=ROOT/'staging/nf-u37-multilayer-native-02';new=ROOT/'staging'/args.after;pcbs=[p/'negative_startup_physical.kicad_pcb' for p in [old,new]];reviews=[p/'review.json' for p in [old,new]]
    for p,r in zip(pcbs,reviews):
        d=json.loads(r.read_text());assert not native_evidence_errors(p.with_suffix('.kicad_pro'),d)
        assert d['status']['counts']['violations']==d['status']['counts']['schematic_parity']==0 and d['status']['counts']['erc']==2
    assert sha(pcbs[0].with_suffix('.kicad_sch'))==sha(pcbs[1].with_suffix('.kicad_sch')) and sha(pcbs[0].with_suffix('.kicad_pro'))==sha(pcbs[1].with_suffix('.kicad_pro'))
    removed,proofs=removed_nodes();allowed=set(json.loads(proofs[0].read_text())['affected_nets']);trees=[read_sexpr(p.read_text()) for p in pcbs];delta=verify_geometry(*trees,removed,allowed)
    cps=[ROOT/'staging/nf-u37-multilayer-inputs-149/capture.json',ROOT/'staging'/args.capture/'capture.json'];caps=[json.loads(p.read_text()) for p in cps]
    for p,c in zip(pcbs,caps):assert str(p) in c['source_sha256'] and all(sha(Path(n))==h for n,h in c['source_sha256'].items())
    lost=pad_review(*caps);drcs=[p/'drc.json' for p in [old,new]];counts=[open_counts(json.loads(p.read_text())) for p in drcs];allnets=counts[0].keys()|counts[1].keys();regressed={n:[counts[0][n],counts[1][n]] for n in allnets if counts[1][n]>counts[0][n]}
    assert all(counts[0][n]==counts[1][n] for n in allnets-allowed)
    if not args.allow_incomplete:assert not lost and not regressed,(lost,regressed)
    lengths=[track_lengths(t) for t in trees]
    inputs=[Path(__file__),ROOT/'audit_candidate.py',ROOT/'audit_single_net.py',*pcbs,*reviews,*cps,*drcs,*proofs,*[p.with_suffix(s) for p in pcbs for s in ['.kicad_sch','.kicad_pro']]]
    output=new/'logic-swap-audit.json';assert not output.exists()
    output.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},delta=delta,explicitly_removed_original_objects=len(removed),changed_component_poses=list(PAIR),all_other_authored_geometry_exact=True,all_original_parts_pin_nets_and_values_unchanged=True,lost_original_pad_partitions=lost,all_original_pad_connections_preserved=not lost,regressed_net_open_counts=regressed,per_net_opens_before=dict(counts[0]),per_net_opens_after=dict(counts[1]),opens_before=sum(counts[0].values()),opens_after=sum(counts[1].values()),affected_net_track_length_mm={n:dict(before=lengths[0].get(n,0),after=lengths[1].get(n,0)) for n in sorted(allowed)},incomplete_trial=bool(lost or regressed),physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Swap audit opens',sum(counts[0].values()),'to',sum(counts[1].values()),'split prior pad partitions',len(lost),'regressed nets',len(regressed))

if __name__=='__main__':run()
