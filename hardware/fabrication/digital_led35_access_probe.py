"""Recheck two discovered LED_35 escapes against complete current native copper."""
import json
from pathlib import Path

from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

ROOT = Path(__file__).resolve().parent


def run():
    cp = ROOT/'staging/digital-led-sink-inputs-34/capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in cap['source_sha256'].items())
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .01
    surface.SIGNAL_LAYERS = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    screen = DigitalViaScreen(cap, signal_layers=surface.SIGNAL_LAYERS)
    pad = next(o for o in cap['objects'] if o.get('ref') == 'U3002' and o.get('pin') == '16')
    assert pad['net'] == '/LED/LED_35'
    power = next(o for o in cap['objects'] if o['uuid'] == 'aed69f03-b0cd-5897-804d-23e6631f3816')
    assert power['net'] == '5V_DIG' and power['width_mm'] == 1.
    results = []
    for point in ((33.505560, 22.123882), (33.444941, 22.040900)):
        path = [pad['position_mm'], point]
        results.append(dict(point_mm=point, runs=[('F.Cu', path)],
                            via_legal=screen.via_legal(pad['net'], point),
                            lead_legal=screen.legal(pad['net'], 'F.Cu', path)))
    paths = [cp, Path(__file__)]+[ROOT/n for n in
             ('audit_candidate.py', 'digital_via_spacing_v2.py', 'nf_softstart_joint_screen.py',
              'nf_softstart_cell_routes.py', 'nf_minimum_logic.py', 'route_nf_surface.py')]
    report = dict(source_sha256={str(p): sha(p) for p in paths}, results=results,
                  all_current_copper_pads_holes_and_keepouts_retained=True,
                  power_spur_retained_width_mm=1., PCB_emitted=False,
                  global_connection_proven=False, physical_or_electrical_qualified=False,
                  fabrication_released=False)
    out = ROOT/'staging/digital-led35-access-probe-01'
    out.mkdir(exist_ok=False)
    (out/'probe.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Current-copper LED_35 escape checks:', results)


if __name__ == '__main__':
    run()
