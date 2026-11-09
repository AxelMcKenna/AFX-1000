"""Compare region access for four remaining interfaces without moving copper."""
import json
from pathlib import Path

from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

ROOT = Path(__file__).resolve().parent


def run():
    cp = ROOT/'staging/digital-led35-dac-pot-inputs-33/capture.json'
    wp = ROOT/'staging/digital-led35-dac-pot-native-01/stage-connectivity-review.json'
    cap, witness = [json.loads(p.read_text()) for p in (cp,wp)]
    for r in (cap,witness):
        assert all(sha(Path(p)) == h for p,h in r['source_sha256'].items())
    nets = [r for r in witness['nets'] if not r['all_pads_connected'] and not r['net'].startswith('/LED/LED_')]
    assert len(nets) == 4
    surface.WIDTH = layers.WIDTH = .2
    faces = surface.SIGNAL_LAYERS = ('F.Cu','In3.Cu','In5.Cu','B.Cu')
    results = []
    for margin, cls in ((.01,DigitalViaScreen),(.001,CloseMarginViaScreen)):
        surface.MARGIN = margin
        screen = cls(cap, signal_layers=faces)
        for row in nets:
            net = row['net']
            groups = sorted(row['pad_groups'], key=len)
            assert len(groups) == 2 and len(groups[0]) == 1
            pads = [o for o in cap['objects'] if o['kind'] == 'PAD' and o['net'] == net]
            source = next(o for o in pads if [o['ref'],o['pin']] in groups[0])
            targets = [o for o in pads if [o['ref'],o['pin']] in groups[1]]
            starts = [(f,source['position_mm']) for f in faces if source['layers'].get(f)]
            ends = [(f,o['position_mm']) for o in targets for f in faces if o['layers'].get(f)]
            crossings = [(o['position_mm'], [f for f in faces if o['layers'].get(f)])
                         for o in cap['objects'] if o['net'] == net and
                         (o['kind'] == 'PCB_VIA' or o['kind'] == 'PAD' and any(o.get('drill_mm',[0,0])))]
            result = reachability(screen, net, starts, ends, faces, existing_crossings=crossings)
            result.update(net=net, planner_track_margin_mm=margin, close_margin_via_field=margin == .001,
                          source_pad=[source['ref'],source['pin']], target_pads=groups[1],
                          existing_conductive_crossings=len(crossings))
            results.append(result)
            print(net, 'margin', margin, 'potential access:', result['connected'], flush=True)
    paths = [cp,wp,Path(__file__)]+[ROOT/n for n in
             ('audit_candidate.py','digital_region_reachability.py','digital_via_spacing_v2.py',
              'digital_via_spacing_close_margin.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py',
              'nf_minimum_logic.py','route_nf_surface.py')]
    report = dict(source_sha256={str(p):sha(p) for p in paths}, results=results,
                  no_copper_omitted=True,native_rules_relaxed=False,candidate_emitted=False,
                  region_connection_is_not_a_complete_route_or_electrical_acceptance=True,fabrication_released=False)
    out = ROOT/'staging/digital-interface-regions-33-01'
    out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    run()
