"""Independently verify a bounded set of net improvements without regressions."""
import argparse
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import authored,native_evidence_errors,sha
from hardware.fabrication.audit_single_net import open_counts

ROOT=Path(__file__).resolve().parent


def unchanged_outside_nets(before,after,nets):
    def retained(tree):
        result=[]
        for node in tree:
            if isinstance(node,list) and node:
                if node[0] in ('segment','via') and str(first(node,'net')[-1]) in nets:
                    continue
                if node[0]=='zone':
                    result.append(authored(node))
                    continue
            result.append(sexpr(node))
        return result
    return retained(before)==retained(after)


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--before',required=True)
    parser.add_argument('--after',required=True)
    parser.add_argument('--nets',nargs='+',required=True)
    args=parser.parse_args()
    assert all(n and all(c.isalnum() or c in '-_' for c in n) for n in (args.before,args.after))
    old,new=[ROOT/'staging'/n for n in (args.before,args.after)]
    output=new/'net-set-audit.json'
    assert not output.exists()
    projects=[next(f.glob('*.kicad_pro')) for f in (old,new)]
    reviews=[json.loads((f/'review.json').read_text()) for f in (old,new)]
    for p,r in zip(projects,reviews):
        assert not native_evidence_errors(p,r)
        assert r['status']['counts']['violations']==r['status']['counts']['schematic_parity']==0
    assert reviews[0]['status']['counts']['erc']==reviews[1]['status']['counts']['erc']
    assert sha(projects[0])==sha(projects[1])
    pcbs=[p.with_suffix('.kicad_pcb') for p in projects]
    trees=[read_sexpr(p.read_text()) for p in pcbs]
    assert unchanged_outside_nets(*trees,set(args.nets))
    old_parts,old_pins=netlist(old/'netlist.xml')
    new_parts,new_pins=netlist(new/'netlist.xml')
    assert old_pins==new_pins and set(old_parts)==set(new_parts)
    assert all(old_parts[r].findtext(k)==new_parts[r].findtext(k) for r in old_parts for k in ('value','footprint'))
    counts=[open_counts(json.loads((f/'drc.json').read_text())) for f in (old,new)]
    all_nets=counts[0].keys()|counts[1].keys()
    assert all(counts[1][n]<=counts[0][n] for n in all_nets)
    assert all(counts[1][n]<counts[0][n] for n in args.nets)
    assert all(counts[1][n]==counts[0][n] for n in all_nets-set(args.nets))
    inputs=[Path(__file__),ROOT/'audit_single_net.py',ROOT/'audit_candidate.py',*projects,*pcbs,
            *[f/name for f in (old,new) for name in ('review.json','drc.json','erc.json','netlist.xml')]]
    output.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},
        changed_nets=sorted(args.nets),per_net_opens_before=dict(sorted(counts[0].items())),
        per_net_opens_after=dict(sorted(counts[1].items())),all_other_authored_objects_exact=True,
        all_original_parts_pin_nets_values_and_footprint_IDs_exact=True,no_connectivity_regressions=True,
        native_status=reviews[1]['status'],physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Verified',len(args.nets),'net improvements;',sum(counts[0].values()),'to',sum(counts[1].values()),'opens')


if __name__=='__main__':
    run()
