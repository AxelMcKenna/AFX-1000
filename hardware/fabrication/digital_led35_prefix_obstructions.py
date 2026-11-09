"""Identify which proposed LED_35 phase closes the DAC_DATA corridor."""
import copy
import json
from pathlib import Path

from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

ROOT = Path(__file__).resolve().parent


def run():
    cp = ROOT/'staging/digital-led-sink-inputs-34/capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in cap['source_sha256'].items())
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .01
    faces = surface.SIGNAL_LAYERS = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    lp = ROOT/'staging/digital-led35-dac-continuous-repair-01/construction.json'
    led_receipt = json.loads(lp.read_text())
    assert all(sha(Path(p)) == h for p,h in led_receipt['source_sha256'].items())
    led = led_receipt['attempts'][0]['routes'][0]['proposed_route']
    net = '/PROCESSOR/DAC_DATA'
    work = copy.deepcopy(cap)
    work['objects'] = [o for o in work['objects'] if not (o['net'] == net and o['kind'] in ('PCB_TRACK','PCB_VIA'))]
    pads = [o for o in work['objects'] if o['net'] == net and o['kind'] == 'PAD']
    start = next(o for o in pads if o['ref'] == 'R1014')
    end = next(o for o in pads if o['ref'] == 'J1005')
    results = []
    for count in range(4):
        screen = DigitalViaScreen(work, signal_layers=faces)
        runs = led['runs'][:count]
        vias = [r[1][-1] for r in runs]
        if count:
            add(screen, '/LED/LED_35', dict(runs=runs, vias=vias))
        frozen = PlannedRegionScreen(screen, net)
        result = reachability(frozen, net, [('F.Cu', start['position_mm'])], [(f,end['position_mm']) for f in faces], faces)
        result.update(LED_prefix_runs=count, LED_runs=runs, LED_vias=vias)
        results.append(result)
        print('DAC connected after', count, 'LED prefix runs:', result['connected'], flush=True)
    paths = [cp, lp, Path(__file__)]+[ROOT/n for n in
             ('digital_xlat_escape_repair.py', 'digital_planned_region_screen.py', 'audit_candidate.py', 'digital_region_reachability.py', 'digital_via_spacing_v2.py',
              'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py', 'nf_minimum_logic.py', 'route_nf_surface.py')]
    result = dict(source_sha256={str(p):sha(p) for p in paths}, results=results, candidate_emitted=False, native_rules_relaxed=False, fabrication_released=False)
    out = ROOT/'staging/digital-led35-prefix-obstructions-01'
    out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Completed prefix diagnosis', flush=True)


if __name__ == '__main__':
    run()
