"""Independently verify three additive LED closures and replay their parent."""
import copy
import json
import math
from pathlib import Path

from hardware.electronics.common.sexpr import children, read_sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.audit_digital_xlat_bridge import check as parent_check
from hardware.fabrication.audit_digital_eight_routes import check as route_check
from hardware.fabrication.audit_digital_pot_filter import check as physical_check
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

ROOT = Path(__file__).resolve().parent
PARENT = 'digital-xlat-bridge-native-01'
SOURCE = 'digital-led-sink-native-01'
RECIPE = 'digital-led-sink-checkpoint-01'
CAPTURE = 'digital-led-sink-inputs-34'
EXPECTED = {'/LED/LED_49': (80.0527359368956, 5),
            '/LED/LED_39': (133.67633900276226, 5),
            '/LED/LED_33': (150.67561352442613, 4)}


def check():
    parent, out = [ROOT/'staging'/n for n in (PARENT, SOURCE)]
    pp = parent/'xlat-bridge-review.json'
    assert parent_check() == json.loads(pp.read_text())
    ap, physical = out/'additive-route-review.json', out/'corridor-audit.json'
    additive = route_check(PARENT, SOURCE, RECIPE)
    assert additive == json.loads(ap.read_text())
    assert physical_check(SOURCE, CAPTURE) == json.loads(physical.read_text())
    assert (additive['before_opens'], additive['after_opens']) == (37, 34)
    assert additive['added_tracks'] == 170 and additive['added_vias'] == 14
    assert {r['net'] for r in additive['improved_nets']} == set(EXPECTED)
    paths = [Path(__file__), pp, ap, physical]
    records = []
    for folder in (parent, out):
        cp = folder/'stage-connectivity-review.json'
        records.append(json.loads(cp.read_text()))
        paths.append(cp)
    old, new = [{r['net']: r for r in c['nets']} for c in records]
    assert all(new[n] == r for n, r in old.items() if n not in EXPECTED)
    assert records[1]['open_nets'] == 34
    assert all(new[f'/CONTROLS/CONTROL_{i:02d}']['all_pads_connected'] for i in range(32))
    assert sum(n.startswith('/LED/LED_') and not r['all_pads_connected'] for n, r in new.items()) == 30
    pcb = out/'digital_core.kicad_pcb'
    tree = read_sexpr(pcb.read_text())
    assert len(children(tree, 'segment')) == 3056 and len(children(tree, 'via')) == 501
    cp = ROOT/'staging'/CAPTURE/'capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in cap['source_sha256'].items())
    ids = set(additive['geometry_delta']['segment']['added'] + additive['geometry_delta']['via']['added'])
    added = [o for o in cap['objects'] if o['uuid'] in ids]
    assert len(added) == 184 and {o['net'] for o in added} == set(EXPECTED)
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .01
    faces = surface.SIGNAL_LAYERS = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    screen = DigitalViaScreen(cap, signal_layers=faces)
    for obj in added:
        net = obj['net']
        if obj['kind'] == 'PCB_TRACK':
            assert obj['width_mm'] == .2
            assert screen.legal(net, next(iter(obj['layers'])), [obj['position_mm'], obj['end_mm']])
        else:
            assert obj['kind'] == 'PCB_VIA'
            work = copy.deepcopy(cap)
            work['objects'] = [p for p in cap['objects'] if p['uuid'] != obj['uuid']]
            assert DigitalViaScreen(work, signal_layers=faces).via_legal(net, obj['position_mm'])
    rp = ROOT/'staging'/RECIPE/'construction.json'
    recipe = json.loads(rp.read_text())
    assert len(recipe['routes']) == 3
    for net, (length, via_count) in EXPECTED.items():
        assert not old[net]['all_pads_connected'] and old[net]['planar_copper_length_mm'] == 0
        assert new[net]['all_pads_connected'] and new[net]['via_count'] == via_count
        assert math.isclose(new[net]['planar_copper_length_mm'], length, abs_tol=2e-6)
        route, = [r for r in recipe['routes'] if r['net'] == net]
        assert math.isclose(route['planar_length_mm'], length, abs_tol=2e-6)
        segments = [(f, p, q) for f, path in route['runs'] for p, q in zip(path, path[1:]) if math.dist(p, q) > 1e-7]
        tracks = [o for o in added if o['net'] == net and o['kind'] == 'PCB_TRACK']
        vias = [o for o in added if o['net'] == net and o['kind'] == 'PCB_VIA']
        assert len(segments) == len(tracks)
        assert len(vias) == len(route['new_vias_mm']) == via_count
        assert all(any(f in o['layers'] and math.dist(p, o['position_mm']) < 2e-6 and math.dist(q, o['end_mm']) < 2e-6 for o in tracks) for f, p, q in segments)
        assert all(any(math.dist(v['position_mm'], p) < 2e-6 for v in vias) for p in route['new_vias_mm'])
    for name in ('conditional-assembly-review.json', 'visual-review.json'):
        p = out/name
        receipt = json.loads(p.read_text())
        assert all(sha(Path(k)) == v for k, v in receipt['source_sha256'].items())
        paths.append(p)
    paths += [pcb, cp, rp]+[ROOT/n for n in ('digital_via_spacing_v2.py', 'route_nf_surface.py', 'nf_minimum_logic.py')]
    return dict(source_sha256={str(p): sha(p) for p in paths}, before_opens=37, after_opens=34,
                improved_nets=additive['improved_nets'], added_tracks=170, added_vias=14,
                total_tracks=3056, total_vias=501, remaining_LED_output_nets=30,
                all_other_net_records_exact=True, all_parent_copper_and_component_poses_exact=True,
                all_power_local_thermal_SD_and_plane_checks_preserved=True,
                length_targets_are_not_electrical_acceptance=True,
                current_headroom_coupling_EMC_and_installed_performance_qualified=False,
                electrical_qualified=False, fabrication_released=False)


if __name__ == '__main__':
    result = check()
    with (ROOT/'staging'/SOURCE/'led-sinks-review.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print('Three LED closures verified; 37 -> 34 opens; parent copper and other nets exact')
