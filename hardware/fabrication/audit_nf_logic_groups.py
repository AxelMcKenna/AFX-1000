"""Audit additive NF logic routing against exact native boards and pad groups."""
import argparse,json,re
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_candidate import geometry_delta,native_evidence_errors,sha
from hardware.fabrication.audit_single_net import open_counts
from hardware.fabrication.route_nf_surface import is_logic_net

ROOT=Path(__file__).resolve().parent
SIGNAL_LAYERS={'F.Cu','In2.Cu','In3.Cu','B.Cu'}

def eligible_logic(net):
    if re.search(r'(?:_CT|_REF|_SS)(?:_|$)|SENSE|TMR|RAMP|GATE|SOURCE|FORCE|_VIN|INTVCC|RMID|HOST5',net):return False
    return is_logic_net(net) or bool(re.fullmatch(r'/N(?:12|19)_OUTPUT_(?:(?:UV|OV)_GOOD|QUALIFIED)',net))

def verify_geometry(before,after):
    delta=geometry_delta(before,after);assert delta['other_root_geometry_exact']
    for tag in ('footprint','zone'):assert not any(delta[tag].values())
    nets=set()
    for tag in ('segment','via'):
        assert not delta[tag]['removed'] and not delta[tag]['changed']
        nodes={first(n,'uuid')[1]:n for n in children(after,tag)}
        for key in delta[tag]['added']:
            n=nodes[key];net=first(n,'net')[-1];assert eligible_logic(net),net;nets.add(net)
            if tag=='segment':assert first(n,'layer')[1] in SIGNAL_LAYERS and float(first(n,'width')[1])>=.16
            else:assert float(first(n,'size')[1])==.6 and float(first(n,'drill')[1])==.3
    assert nets
    return delta,nets

def verify_pads(before,after):
    pads=[{(o['ref'],o['pin']):o for o in c['objects'] if o['kind']=='PAD'} for c in (before,after)];assert pads[0].keys()==pads[1].keys()
    groups={}
    for key,old in pads[0].items():
        new=pads[1][key];assert old['net']==new['net'] and old['position_mm']==new['position_mm']
        groups.setdefault((old['net'],old['group']),[]).append(key)
    for keys in groups.values():assert len({pads[1][key]['group'] for key in keys})==1,keys
    return len(groups)

def verify_counts(old,new,nets):
    for net in old.keys()|new.keys():
        if net in nets:assert new[net]<old[net],net
        else:assert new[net]==old[net],net

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--before',required=True);ap.add_argument('--after',required=True);ap.add_argument('--before-capture',required=True);ap.add_argument('--after-capture',required=True);args=ap.parse_args()
    assert all(s and all(c.isalnum() or c in '-_' for c in s) for s in vars(args).values())
    folders=[ROOT/'staging'/n for n in (args.before,args.after)]
    projects=[p/'negative_startup_physical.kicad_pro' for p in folders];pcbs=[p.with_suffix('.kicad_pcb') for p in projects];reviews=[p/'review.json' for p in folders]
    for p,r in zip(projects,reviews):
        d=json.loads(r.read_text());assert not native_evidence_errors(p,d)
        assert d['status']['counts']['violations']==d['status']['counts']['schematic_parity']==0 and d['status']['counts']['erc']==2
    assert sha(projects[0])==sha(projects[1]) and sha(projects[0].with_suffix('.kicad_sch'))==sha(projects[1].with_suffix('.kicad_sch'))
    trees=[read_sexpr(p.read_text()) for p in pcbs];delta,nets=verify_geometry(*trees)
    cap_paths=[ROOT/'staging'/n/'capture.json' for n in (args.before_capture,args.after_capture)];caps=[json.loads(p.read_text()) for p in cap_paths]
    for p,c in zip(pcbs,caps):assert str(p) in c['source_sha256'] and all(sha(Path(n))==h for n,h in c['source_sha256'].items())
    groups=verify_pads(*caps);drcs=[p/'drc.json' for p in folders];counts=[open_counts(json.loads(p.read_text())) for p in drcs];verify_counts(*counts,nets)
    inputs=[Path(__file__),ROOT/'audit_candidate.py',ROOT/'audit_single_net.py',ROOT/'route_nf_surface.py',*projects,*pcbs,*reviews,*cap_paths,*drcs,*[p.with_suffix('.kicad_sch') for p in projects]]
    output=folders[1]/'logic-group-audit.json';assert not output.exists()
    output.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},delta=delta,added_logic_nets=sorted(nets),all_original_geometry_and_authored_zones_preserved=True,all_previous_pad_connections_preserved=True,prior_pad_partitions=groups,per_net_opens_before=dict(counts[0]),per_net_opens_after=dict(counts[1]),opens_before=sum(counts[0].values()),opens_after=sum(counts[1].values()),physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Audited additive logic groups:',sum(counts[0].values()),'to',sum(counts[1].values()),'opens')

if __name__=='__main__':run()
