"""Read-only copper-removal comparisons to identify LED_35 rework candidates.

Removed conductors are diagnostic omissions, never authorized disconnections.
Every pad, hole belonging to a retained object, zone and component stays fixed.
A connected result only identifies potential space; all displaced nets would
need simultaneous restoration and independent native verification.
"""
import copy
import json
from pathlib import Path

from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.route_nf_surface as surface

ROOT = Path(__file__).resolve().parent


def run():
    cp = ROOT / 'staging/digital-led-sink-inputs-34/capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in cap['source_sha256'].items())
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .01
    faces = surface.SIGNAL_LAYERS = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    net = '/LED/LED_35'
    pads = [o for o in cap['objects'] if o['kind'] == 'PAD' and o['net'] == net]
    start = next(o for o in pads if o['ref'].startswith('U'))
    end = next(o for o in pads if o['ref'].startswith('J'))
    candidates = ['/LED/LED_33', '/LED/LED_34', '/LED/LED_32',
                  '/PROCESSOR/DAC_DATA', '/PROCESSOR/POT_ADC_05', '/PROCESSOR/MCU_PERMIT']
    cases = [[n] for n in candidates] + [candidates[:3], candidates[3:], candidates]
    results = []
    for nets in cases:
        omitted = [o for o in cap['objects'] if o['kind'] in ('PCB_TRACK', 'PCB_VIA') and o['net'] in nets]
        assert omitted and set(o['net'] for o in omitted) == set(nets)
        ids = {o['uuid'] for o in omitted}
        work = copy.deepcopy(cap)
        work['objects'] = [o for o in work['objects'] if o['uuid'] not in ids]
        assert [o for o in work['objects'] if o['kind'] == 'PAD'] == [o for o in cap['objects'] if o['kind'] == 'PAD']
        screen = DigitalViaScreen(work, signal_layers=faces)
        result = reachability(screen, net, [('F.Cu', start['position_mm'])],
                              [(f, end['position_mm']) for f in faces if end['layers'].get(f)], faces)
        result.update(omitted_nets=nets, omitted_uuids=sorted(ids),
                      omitted_tracks=sum(o['kind'] == 'PCB_TRACK' for o in omitted),
                      omitted_vias=sum(o['kind'] == 'PCB_VIA' for o in omitted))
        results.append(result)
        print(nets, 'potential region connection:', result['connected'], flush=True)
    paths = [cp, Path(__file__)] + [ROOT / n for n in
             ('audit_candidate.py', 'digital_region_reachability.py', 'digital_via_spacing_v2.py',
              'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py', 'nf_minimum_logic.py', 'route_nf_surface.py')]
    receipt = dict(source_sha256={str(p): sha(p) for p in paths}, results=results,
                   all_pads_retained=True, all_zones_retained=True, candidate_emitted=False,
                   restoration_of_every_omitted_net_required=True, native_rules_relaxed=False,
                   planner_track_margin_mm=.01, fabrication_released=False)
    out = ROOT / 'staging/digital-led35-rework-survey-01'
    out.mkdir(exist_ok=False)
    (out / 'diagnosis.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    run()
