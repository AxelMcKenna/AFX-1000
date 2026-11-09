"""Reconcile previously rejected source nets with current native connectivity."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--capture',required=True)
    ap.add_argument('--audit',required=True)
    args=ap.parse_args();out=STAGING/args.source
    assert Path(args.audit).name==args.audit and args.audit.endswith('.json')
    cp=STAGING/args.capture/'capture.json'
    first=STAGING/'two-board-power-routed-native-01/copper-restoration.json'
    clean=STAGING/'two-board-power-routed-native-02/copper-restoration.json'
    cap=json.loads(cp.read_text());trial=json.loads(first.read_text());selected=json.loads(clean.read_text())
    for p,h in cap['source_sha256'].items():assert sha(REPO/p)==h,p
    assert cap['source_sha256'][str(out/'power_protection.kicad_pcb')]==sha(out/'power_protection.kicad_pcb')
    excluded=set(selected['excluded_after_native_DRC']);assert len(excluded)==52
    objects={o['uuid']:o for o in cap['objects']};netgroups=defaultdict(list)
    for key,members in cap['all_groups'].items():
        nets={objects[u]['net'].lstrip('/') for u in members};assert len(nets)==1
        netgroups[next(iter(nets))].append(key)
    pad_lookup=defaultdict(list)
    for o in objects.values():
        if o['kind']=='PAD' and o.get('pin'):pad_lookup[(o['ref'],o['pin'])].append(o)
    rows=[]
    for r in trial['selected_nets']:
        if r['key'] not in excluded:continue
        target=r['target_net'].lstrip('/');groups=netgroups[target];assert groups
        pads=[p for ref,pin in r['terminals'] for p in pad_lookup[(ref,pin)]]
        assert len({(p['ref'],p['pin']) for p in pads})==len({tuple(t) for t in r['terminals']})
        assert all(p['net'].lstrip('/')==target and p['group'] for p in pads)
        terminal_groups={p['group'] for p in pads}
        rows.append(dict(source_key=r['key'],target_net=target,physical_source_terminal_pads=len(pads),
            source_terminal_groups_now=len(terminal_groups),whole_net_native_groups_now=len(groups),
            whole_net_native_opens_now=len(groups)-1,whole_net_connected_now=len(groups)==1))
    assert {r['source_key'] for r in rows}==excluded
    closed=[r['source_key'] for r in rows if r['whole_net_connected_now']]
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),cp,first,clean,out/args.audit]},
        originally_rejected_source_nets=52,now_fully_connected=len(closed),fully_connected_source_keys=closed,
        still_incomplete=52-len(closed),remaining_native_opens_on_these_nets=sum(r['whole_net_native_opens_now'] for r in rows),
        evidence=rows,scope='Native connectivity only; this does not qualify electrical behavior or claim that rejected original copper was restored',
        fabrication_released=False)
    with (out/'rejected-source-net-status.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','evidence']},indent=2))


if __name__=='__main__':run()
