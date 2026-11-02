"""Independent boundary and pad-connectivity audit for the U44 escape work."""
import argparse,json
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_candidate import geometry_delta,native_evidence_errors,sha
from hardware.fabrication.audit_single_net import open_counts

ROOT=Path(__file__).resolve().parent
LOGIC={'/N12_OUTPUT_UV_GOOD','/E28_NOT_FAULT','/NOT_NF_FAULT_REQUEST','/N19_OUTPUT_QUALIFIED','/N19_COMPLETE','/N12_OUTPUT_QUALIFIED','/N12_COMPLETE'}

def verify_geometry(before,after,removed=()):
    expected=list(before)
    for n in removed:
        assert n in expected and n[0] in {'segment','via'} and first(n,'net')[-1]=='/AGND'
        expected.remove(n)
    delta=geometry_delta(expected,after)
    assert delta['other_root_geometry_exact']
    for tag in ('footprint','zone'):assert not any(delta[tag].values())
    for tag in ('segment','via'):
        assert not delta[tag]['removed'] and not delta[tag]['changed']
        nodes={first(n,'uuid')[1]:n for n in children(after,tag)}
        for key in delta[tag]['added']:
            n=nodes[key];net=first(n,'net')[-1]
            assert net in LOGIC or (removed and net=='/AGND')
            if tag=='segment':
                assert float(first(n,'width')[1])>=(.2 if net=='/AGND' else .16)
                assert first(n,'layer')[1] in {'F.Cu','In2.Cu','In3.Cu','B.Cu'}
            else:assert float(first(n,'size')[1])==.6 and float(first(n,'drill')[1])==.3
    return geometry_delta(before,after)

def verify_pad_connections(before,after,pins=()):
    pads=[{(o['ref'],o['pin']):o for o in c['objects'] if o['kind']=='PAD'} for c in (before,after)]
    assert pads[0].keys()==pads[1].keys()
    partitions={}
    for key,old in pads[0].items():
        new=pads[1][key]
        assert old['net']==new['net'] and old['position_mm']==new['position_mm']
        partitions.setdefault((old['net'],old['group']),[]).append(key)
    for keys in partitions.values():assert len({pads[1][k]['group'] for k in keys})==1,keys
    for pin in pins:
        key=('U44',pin);old,new=pads[0][key],pads[1][key]
        assert old['net'] in LOGIC
        assert any(p['net']==old['net'] and p['group']!=old['group'] and pads[1][k]['group']==new['group'] for k,p in pads[0].items()),pin
    return len(partitions)

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--after',required=True);ap.add_argument('--capture',required=True);ap.add_argument('--repack',action='store_true');ap.add_argument('--pins',required=True);args=ap.parse_args()
    assert all(n and all(c.isalnum() or c in '-_' for c in n) for n in (args.after,args.capture))
    old=ROOT/'staging/nf-softstart-cell-native-02';new=ROOT/'staging'/args.after
    pcbs=[p/'negative_startup_physical.kicad_pcb' for p in (old,new)]
    projects=[p.with_suffix('.kicad_pro') for p in pcbs]
    reviews=[p/'review.json' for p in (old,new)]
    for p,r in zip(projects,reviews):
        d=json.loads(r.read_text());assert not native_evidence_errors(p,d)
        assert d['status']['counts']['violations']==d['status']['counts']['schematic_parity']==0 and d['status']['counts']['erc']==2
    assert sha(projects[0])==sha(projects[1])
    assert sha(pcbs[0].with_suffix('.kicad_sch'))==sha(pcbs[1].with_suffix('.kicad_sch'))
    trees=[read_sexpr(p.read_text()) for p in pcbs];removed=[];inputs=[*pcbs,*projects,*reviews,Path(__file__),ROOT/'audit_candidate.py',ROOT/'audit_single_net.py']
    if args.repack:
        proof=ROOT/'staging/nf-u44-ground-repack-01/construction.json';proof_data=json.loads(proof.read_text())
        assert all(sha(Path(p))==h for p,h in proof_data['source_sha256'].items())
        removed=proof_data['removed_objects'];assert len(removed)==4
        inputs.append(proof)
    delta=verify_geometry(*trees,removed)
    capture_paths=[ROOT/'staging/nf-softstart-cell-inputs-163/capture.json',ROOT/'staging'/args.capture/'capture.json']
    captures=[json.loads(p.read_text()) for p in capture_paths]
    for c,p in zip(captures,pcbs):
        assert str(p) in c['source_sha256'] and all(sha(Path(n))==h for n,h in c['source_sha256'].items())
    partitions=verify_pad_connections(*captures,args.pins.split(','))
    drcs=[p/'drc.json' for p in (old,new)];counts=[open_counts(json.loads(p.read_text())) for p in drcs]
    for net in counts[0].keys()|counts[1].keys():
        assert counts[1][net]<=counts[0][net]
        if net not in LOGIC:assert counts[1][net]==counts[0][net]
    inputs+=capture_paths+drcs+[p.with_suffix('.kicad_sch') for p in pcbs]
    out=new/'pin-escape-audit.json';assert not out.exists()
    out.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},delta=delta,previous_pad_partitions_preserved=partitions,all_original_pad_connections_preserved=True,new_U44_group_joins=args.pins.split(','),per_net_opens_before=dict(counts[0]),per_net_opens_after=dict(counts[1]),opens_before=sum(counts[0].values()),opens_after=sum(counts[1].values()),no_connectivity_regressions=True,all_component_poses_and_authored_zones_exact=True,explicit_removed_ground_objects=removed,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Verified all prior pad connections;',sum(counts[0].values()),'to',sum(counts[1].values()),'opens')

if __name__=='__main__':run()
