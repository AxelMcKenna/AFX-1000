"""Survey the current remaining pad pairs in continuous multilayer free space."""
import argparse
import json
import time
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_serial1_joint_repair import ROOT, FACES
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_region_reachability import reachability
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--capture',default='digital-costed-shortening-inputs-30')
    parser.add_argument('--source',default='digital-costed-shortening-native-01')
    parser.add_argument('--label',default='digital-remaining-region-survey-30-01')
    args=parser.parse_args()
    assert all(all(c.isalnum() or c in '-_' for c in s) for s in (args.capture,args.source,args.label))
    cp=ROOT/'staging'/args.capture/'capture.json'
    wp=ROOT/'staging'/args.source/'stage-connectivity-review.json'
    cap,witness=[json.loads(p.read_text()) for p in (cp,wp)]
    for record in (cap,witness):
        assert all(sha(Path(p))==h for p,h in record['source_sha256'].items())
    assert cap['native_uncapped_opens']==witness['uncapped_open_connections']
    pads={(o['ref'],o['pin']):o for o in cap['objects'] if o['kind']=='PAD' and o.get('pin')}
    surface.WIDTH=layers.WIDTH=.2
    surface.MARGIN=.001
    surface.SIGNAL_LAYERS=FACES
    screen=CloseMarginViaScreen(cap,signal_layers=FACES)
    results=[]
    for row in witness['nets']:
        if row['all_pads_connected']:
            continue
        assert len(row['pad_groups'])==2 and all(len(g)==1 for g in row['pad_groups'])
        pair=[pads[tuple(g[0])] for g in row['pad_groups']]
        pair.sort(key=lambda o: (any(o['drill_mm']),o['ref'],o['pin']))
        net=row['net']
        assert all(o['net']==net for o in pair)
        starts=[(f,pair[0]['position_mm']) for f in FACES if pair[0]['layers'].get(f)]
        ends=[(f,pair[1]['position_mm']) for f in FACES if pair[1]['layers'].get(f)]
        crossings=[(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in cap['objects'] if o['net']==net and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]
        started=time.monotonic()
        result=reachability(screen,net,starts,ends,FACES,existing_crossings=crossings)
        portal_count=len(result.pop('conventional_via_pair_regions'))
        result.update(net=net,terminals=[dict(ref=o['ref'],pin=o['pin'],position_mm=o['position_mm']) for o in pair],
                      starts=starts,ends=ends,conventional_via_pair_region_count=portal_count,
                      elapsed_seconds=time.monotonic()-started,retained_planar_copper_mm=row['planar_copper_length_mm'])
        results.append(result)
        print(net,'free-space connected',result['connected'],'transitions',len(result['component_witness']),flush=True)
        screen._obstacle_cache.clear()
    assert len(results)==witness['open_nets']
    paths=[cp,wp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_region_reachability.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging'/args.label
    out.mkdir(exist_ok=False)
    report=dict(source_sha256={str(p):sha(p) for p in paths},native_opens=cap['native_uncapped_opens'],results=results,
                individually_connected_nets=[r['net'] for r in results if r['connected']],
                candidate_emitted=False,joint_routing_or_mutual_new_via_spacing_proven=False,
                native_rules_relaxed=False,electrical_performance_qualified=False,fabrication_released=False)
    (out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Survey complete:',len(report['individually_connected_nets']),'of',len(results),'individually connected',flush=True)


if __name__=='__main__':
    run()
