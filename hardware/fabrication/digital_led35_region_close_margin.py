"""Bind the LED_35 retained-copper region connectivity diagnosis to native data."""
import json
from pathlib import Path

from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_region_reachability import reachability
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

ROOT = Path(__file__).resolve().parent


def run():
    cp = ROOT/'staging/digital-led-sink-inputs-34/capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in cap['source_sha256'].items())
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .001
    faces = surface.SIGNAL_LAYERS = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    screen = DigitalViaScreen(cap, signal_layers=faces)
    net = '/LED/LED_35'
    pads = [o for o in cap['objects'] if o['kind'] == 'PAD' and o['net'] == net]
    assert len(pads) == 2
    start = next(o for o in pads if o['ref'].startswith('U'))
    end = next(o for o in pads if o['ref'].startswith('J'))
    result = reachability(screen, net, [('F.Cu', start['position_mm'])],
                          [(f, end['position_mm']) for f in faces if end['layers'].get(f)], faces)
    paths = [cp, Path(__file__)]+[ROOT/n for n in
             ('audit_candidate.py', 'digital_region_reachability.py', 'digital_via_spacing_v2.py',
              'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py', 'nf_minimum_logic.py', 'route_nf_surface.py')]
    result.update(source_sha256={str(p): sha(p) for p in paths}, net=net, retained_all_current_geometry=True, planner_track_margin_mm=.001,
                  native_rules_relaxed=False, fabrication_released=False)
    out = ROOT/'staging/digital-led35-region-close-margin-01'
    out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(result, indent=2)+'\n')
    print('LED_35 polygon-region connection:', result['connected'], 'components:', result['component_counts'])


if __name__ == '__main__':
    run()
