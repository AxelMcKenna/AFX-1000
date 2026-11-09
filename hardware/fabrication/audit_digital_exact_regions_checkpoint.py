"""Replay the LED_52 additive checkpoint and its independently checked parent."""
import copy
import json
import math
from pathlib import Path

from hardware.electronics.common.sexpr import children, read_sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.audit_latch_supply_delta import check as parent_check
from hardware.fabrication.audit_digital_eight_routes import check as route_check
from hardware.fabrication.audit_digital_latch_supply import check as physical_check
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v3 as search

ROOT = Path(__file__).resolve().parent
PARENT = 'digital-latch-supply-native-02'
SOURCE = 'digital-exact-regions-native-01'
RECIPE = 'digital-exact-regions-routes-01'
CAPTURE = 'digital-exact-regions-inputs-41'
NET = '/LED/LED_52'


def check():
    parent, out = [ROOT/'staging'/n for n in (PARENT, SOURCE)]
    pp = parent/'latch-supply-review.json'
    assert parent_check() == json.loads(pp.read_text())
    ap, physical = out/'additive-route-review.json', out/'corridor-audit.json'
    additive = route_check(PARENT, SOURCE, RECIPE)
    assert additive == json.loads(ap.read_text())
    assert physical_check(SOURCE, CAPTURE) == json.loads(physical.read_text())
    assert (additive['before_opens'], additive['after_opens']) == (42, 41)
    assert additive['added_tracks'] == 9 and additive['added_vias'] == 1
    assert [r['net'] for r in additive['improved_nets']] == [NET]
    paths = [Path(__file__), pp, ap, physical]
    records = []
    for folder in (parent, out):
        cp = folder/'stage-connectivity-review.json'
        records.append(json.loads(cp.read_text()))
        paths.append(cp)
    old, new = [{r['net']: r for r in c['nets']} for c in records]
    assert all(new[n] == r for n, r in old.items() if n != NET)
    assert new[NET]['all_pads_connected'] and new[NET]['via_count'] == 1
    assert math.isclose(new[NET]['planar_copper_length_mm'], 15.315642253825866, abs_tol=2e-6)
    assert records[1]['open_nets'] == 41
    assert sum(n.startswith('/LED/LED_') and not r['all_pads_connected'] for n, r in new.items()) == 34
    pcb = out/'digital_core.kicad_pcb'
    tree = read_sexpr(pcb.read_text())
    assert len(children(tree, 'segment')) == 2744 and len(children(tree, 'via')) == 476
    cp = ROOT/'staging'/CAPTURE/'capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in cap['source_sha256'].items())
    ids = set(additive['geometry_delta']['segment']['added'] + additive['geometry_delta']['via']['added'])
    added = [o for o in cap['objects'] if o['uuid'] in ids]
    assert len(added) == 10 and all(o['net'] == NET for o in added)
    surface.WIDTH = layers.WIDTH = raster.WIDTH = search.WIDTH = .2
    surface.MARGIN = .01
    faces = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    screen = DigitalViaScreen(cap, signal_layers=faces)
    for o in added:
        if o['kind'] == 'PCB_TRACK':
            assert o['width_mm'] == .2
            assert screen.legal(NET, next(iter(o['layers'])), [o['position_mm'], o['end_mm']])
        else:
            assert o['kind'] == 'PCB_VIA'
            work = copy.deepcopy(cap)
            work['objects'] = [p for p in cap['objects'] if p['uuid'] != o['uuid']]
            assert DigitalViaScreen(work, signal_layers=faces).via_legal(NET, o['position_mm'])
    rp = ROOT/'staging'/RECIPE/'construction.json'
    recipe = json.loads(rp.read_text())
    route, = recipe['routes']
    segments = [(f, p, q) for f, path in route['runs'] for p, q in zip(path, path[1:]) if math.dist(p, q) > 1e-7]
    tracks = [o for o in added if o['kind'] == 'PCB_TRACK']
    vias = [o for o in added if o['kind'] == 'PCB_VIA']
    assert len(segments) == len(tracks) == 9 and len(vias) == len(route['new_vias_mm']) == 1
    assert all(any(f in o['layers'] and math.dist(p, o['position_mm']) < 2e-6 and math.dist(q, o['end_mm']) < 2e-6 for o in tracks) for f, p, q in segments)
    assert math.dist(vias[0]['position_mm'], route['new_vias_mm'][0]) < 2e-6
    for name in ('conditional-assembly-review.json', 'visual-review.json'):
        p = out/name
        receipt = json.loads(p.read_text())
        assert all(sha(Path(k)) == v for k, v in receipt['source_sha256'].items())
        paths.append(p)
    paths += [pcb, cp, rp] + [ROOT/n for n in ('digital_via_spacing_v2.py', 'route_nf_surface.py', 'nf_minimum_logic.py', 'nf_pin_escape_routes.py', 'digital_native_spacing_search_v3.py')]
    return dict(source_sha256={str(p): sha(p) for p in paths}, before_opens=42, after_opens=41,
                improved_net=NET, added_tracks=9, added_vias=1, added_planar_length_mm=route['planar_length_mm'],
                total_tracks=2744, total_vias=476, remaining_LED_output_nets=34,
                all_other_net_records_exact=True, all_parent_copper_and_component_poses_exact=True,
                all_power_local_thermal_SD_and_plane_checks_preserved=True,
                electrical_qualified=False, fabrication_released=False)


if __name__ == '__main__':
    result = check()
    with (ROOT/'staging'/SOURCE/'exact-regions-review.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print('LED_52 checkpoint verified; 42 -> 41 opens; all parent copper and other nets exact')
