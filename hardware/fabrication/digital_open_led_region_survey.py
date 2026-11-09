"""Classify retained-copper access for remaining LED outputs at 33 opens."""
import json
from pathlib import Path

from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

ROOT = Path(__file__).resolve().parent


def run():
    cp = ROOT/'staging/digital-led35-dac-pot-inputs-33/capture.json'
    wp = ROOT/'staging/digital-led35-dac-pot-native-01/stage-connectivity-review.json'
    cap, witness = [json.loads(p.read_text()) for p in (cp, wp)]
    for r in (cap, witness):
        assert all(sha(Path(p)) == h for p,h in r['source_sha256'].items())
    nets = [r['net'] for r in witness['nets'] if r['net'].startswith('/LED/LED_') and not r['all_pads_connected']]
    assert len(nets) == 29 and witness['open_nets'] == 33
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .01
    faces = surface.SIGNAL_LAYERS = ('F.Cu','In3.Cu','In5.Cu','B.Cu')
    screen = DigitalViaScreen(cap, signal_layers=faces)
    results = []
    for net in nets:
        pads = [o for o in cap['objects'] if o['kind'] == 'PAD' and o['net'] == net]
        assert len(pads) == 2
        start = next(o for o in pads if o['ref'].startswith('U'))
        end = next(o for o in pads if o['ref'].startswith('J'))
        crossings = [(o['position_mm'], [f for f in faces if o['layers'].get(f)])
                     for o in cap['objects'] if o['kind'] == 'PCB_VIA' and o['net'] == net]
        result = reachability(screen, net, [('F.Cu',start['position_mm'])],
                              [(f,end['position_mm']) for f in faces if end['layers'].get(f)], faces,
                              existing_crossings=crossings)
        result.update(net=net, existing_via_crossings=len(crossings))
        results.append(result)
        print(net, 'potential retained-copper access:', result['connected'], flush=True)
    paths = [cp, wp, Path(__file__)]+[ROOT/n for n in
             ('audit_candidate.py','digital_region_reachability.py','digital_via_spacing_v2.py',
              'nf_softstart_joint_screen.py','nf_softstart_cell_routes.py','nf_minimum_logic.py','route_nf_surface.py')]
    report = dict(source_sha256={str(p):sha(p) for p in paths}, results=results,
                  connected_nets=[r['net'] for r in results if r['connected']],
                  disconnected_nets=[r['net'] for r in results if not r['connected']],
                  no_copper_omitted=True, planner_track_margin_mm=.01, native_rules_relaxed=False,
                  connected_regions_do_not_prove_joint_via_spacing_or_acceptable_routing=True,
                  candidate_emitted=False, fabrication_released=False)
    out = ROOT/'staging/digital-open-led-regions-33-01'
    out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Remaining LED region survey complete:', len(report['connected_nets']), 'potentially connected')


if __name__ == '__main__':
    run()
