"""Screen remaining AUX capacitor returns to existing main-ground contacts.

The previous pass searched for new vias. This pass reuses existing main-ground
pads/vias, without changing planes or crossing a quiet-ground boundary.
Native validation is required before any route becomes an accepted PCB.
"""
import json
import math
from pathlib import Path

from shapely.geometry import LineString
from shapely.ops import unary_union
from shapely.prepared import prep

from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
from hardware.fabrication.route_two_board_power_local_v2 import MountScreen
import hardware.fabrication.route_nf_surface as routing

BASE = STAGING / 'two-board-power-aux-cap-ground-native-01'
CAP = STAGING / 'two-board-power-routing-inputs-aux-cap-ground-01/capture.json'
SURVEY = STAGING / 'two-board-aux-cap-ground-survey-02/survey.json'
OUT = STAGING / 'two-board-aux-ground-reuse-plan-01'


def run():
    assert not OUT.exists()
    capture, survey = [json.loads(p.read_text()) for p in (CAP, SURVEY)]
    for data in (capture, survey):
        for name, expected in data['source_sha256'].items():
            path = Path(name)
            assert sha(path if path.is_absolute() else REPO / path) == expected, name
    fields, excluded = anchored_fields(capture)
    main = next(o['group'] for o in capture['objects']
                if o.get('ref') == 'P_C103' and o.get('pin') == '2')
    quiet_paths = [STAGING / 'two-board-power-digital-startup-native-02/digital-startup-routing.json',
                   STAGING / 'two-board-power-analog-cells-native-03/analog-cell-routing.json']
    quiet_ids = {u for p in quiet_paths for q in json.loads(p.read_text())['quiet_ground_islands']
                 for u in q['zone_uuids']}
    quiet = {layer: prep(unary_union([
        routing.shape(z['authored_outline']).buffer(.165) for z in capture['zones']
        if z['uuid'] in quiet_ids and z['layer'] == layer
    ])) for layer in ('F.Cu', 'B.Cu')}
    routing.SIGNAL_LAYERS = ('F.Cu', 'B.Cu')
    routing.WIDTH = .3
    screen = MountScreen(dict(capture, zones=[z for z in capture['zones'] if z['keepout']]))
    contacts = [o for o in capture['objects'] if o['net'] == 'PWR_AGND'
                and o['group'] == main and o['kind'] in ('PAD', 'PCB_VIA')]
    routes, deferred = [], []
    for row in survey['rows']:
        layer, start = row['layer'], row['position_mm']
        reference = fields[row['reference_layer'], main].buffer(.0015)
        isolated = prep(unary_union([
            routing.shape(o['layers'][layer]).buffer(.165) for o in capture['objects']
            if o['net'] == 'PWR_AGND' and o['group'] not in (main, row['group']) and layer in o['layers']
        ]))
        options = sorted((math.dist(start, o['position_mm']), o['uuid'], o['position_mm'])
                         for o in contacts if layer in o['layers']
                         and 0 < math.dist(start, o['position_mm']) <= 8)
        best = None
        for distance, target, end in options:
            for path in routing.candidate_paths(start, end):
                path = [p for i, p in enumerate(path) if not i or p != path[i-1]]
                if len(path) < 2:
                    continue
                line = LineString(path)
                if line.length > min(12, distance * 1.8 + 3) or best and line.length >= best[0]:
                    continue
                if not reference.covers(line.buffer(.15)) or quiet[layer].intersects(line) or isolated.intersects(line):
                    continue
                if screen.legal('PWR_AGND', layer, path):
                    best = (line.length, target, path)
        if best:
            length, target, path = best
            routes.append(dict(pad_ref=row['ref'], pad_pin=row['pin'], source_group=row['group'],
                               target_uuid=target, net='PWR_AGND', layer=layer, width_mm=.3,
                               path_mm=path, length_mm=length, reference_layer=row['reference_layer']))
            screen.added.append(('PWR_AGND', layer, LineString(path)))
        else:
            deferred.append(dict(ref=row['ref'], pin=row['pin'], existing_contacts_in_radius=len(options),
                                 reason='No direct referenced route to an existing main-ground contact within the screened limits'))
    allowed = {main, *[r['source_group'] for r in routes]}
    assert len(allowed) == len(routes) + 1
    sources = [Path(__file__), CAP, SURVEY, BASE / 'final-review.json', *quiet_paths,
               *[REPO / 'hardware/fabrication' / name for name in
                 ('plan_two_board_startup_controls.py', 'route_two_board_power_local_v2.py',
                  'route_two_board_power_local.py', 'route_nf_surface.py')]]
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                  routes=routes, vias=[], deferred=deferred, old_main_ground_group=main,
                  allowed_ground_groups={g: [dict(ref=o['ref'], pin=o['pin']) for o in capture['objects']
                                            if o['kind'] == 'PAD' and o['group'] == g] for g in sorted(allowed)},
                  edited_zone_outlines=[], previous_opens=capture['native_uncapped_opens'],
                  expected_closed_connections=len(routes), maximum_endpoint_distance_mm=8,
                  maximum_route_length_mm=12, excluded_unanchored_fragments=excluded,
                  native_validation_pending=True, fabrication_released=False)
    OUT.mkdir()
    (OUT / 'plan.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(routes=len(routes), deferred=len(deferred), new_vias=0)))


if __name__ == '__main__':
    run()
