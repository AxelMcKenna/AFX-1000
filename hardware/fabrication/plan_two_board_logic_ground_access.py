"""Screen local SN74 GND escapes against the verified TBP64 board.

Only existing main-ground fields are used. No supply fields, quiet islands,
component placements or ground-zone outlines are changed by this plan.
"""
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

BASE = STAGING / 'two-board-power-watchdog-fast-native-01'
CAP = STAGING / 'two-board-power-routing-inputs-watchdog-fast-01/capture.json'
SURVEY = STAGING / 'two-board-logic-ground-access-survey-02/survey.json'
OUT = STAGING / 'two-board-logic-ground-access-plan-01'


def run():
    assert not OUT.exists()
    c, survey = [json.loads(p.read_text()) for p in [CAP, SURVEY]]
    for data in [c, survey]:
        for name, digest in data['source_sha256'].items():
            p = Path(name)
            assert sha(p if p.is_absolute() else REPO / p) == digest, name
    fields, excluded = anchored_fields(c)
    main = next(o['group'] for o in c['objects'] if o.get('ref') == 'P_C103' and o.get('pin') == '2')
    reference = {l: fields[l, main].buffer(.0015) for l in ['In1.Cu', 'In6.Cu']}
    via_field = prep(fields['In1.Cu', main].intersection(fields['In6.Cu', main]).buffer(-.31))
    quiet_paths = [STAGING / 'two-board-power-digital-startup-native-02/digital-startup-routing.json',
                   STAGING / 'two-board-power-analog-cells-native-03/analog-cell-routing.json']
    quiet_ids = {u for p in quiet_paths for q in json.loads(p.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
    forbidden = prep(unary_union([
        routing.shape(z['authored_outline']).buffer(.55) for z in c['zones'] if z['uuid'] in quiet_ids
    ] + [routing.shape(z['polygons']).buffer(.55) for z in c['zones'] if z['net'] != 'PWR_AGND']))
    routing.SIGNAL_LAYERS = tuple(c['copper_layers'])
    routing.WIDTH = .2
    screen = ViaScreen(dict(c, zones=[]))
    isolated = [o for o in c['objects'] if o['net'] == 'PWR_AGND' and o['group'] != main]
    routes, vias, deferred = [], [], []
    for row in survey['rows']:
        if not row['main_reference_covers_pad_center_band']:
            deferred.append(dict(ref=row['ref'], pin=row['pin'], reason='Adjacent main reference needs separate repair'))
            continue
        layer, xy = row['layer'], row['position_mm']
        other = [o for o in isolated if o['group'] != row['group']]
        via_obstacles = prep(unary_union([routing.shape(g) for o in other for g in o['layers'].values()]).buffer(.315))
        route_obstacles = prep(unary_union([routing.shape(o['layers'][layer]) for o in other if layer in o['layers']]).buffer(.115))
        sites = sorted((math.dist(xy, [ix/4, iy/4]), [ix/4, iy/4])
                       for ix in range(math.floor((xy[0]-3.5)*4), math.ceil((xy[0]+3.5)*4)+1)
                       for iy in range(math.floor((xy[1]-3.5)*4), math.ceil((xy[1]+3.5)*4)+1))
        chosen = None
        for distance, site in sites:
            if distance > 3.5:
                break
            point = Point(site)
            if not via_field.covers(point) or forbidden.intersects(point) or via_obstacles.intersects(point):
                continue
            if not screen.via_legal('PWR_AGND', site):
                continue
            path = screen.simple('PWR_AGND', layer, xy, site, 5.5)
            if not path:
                continue
            line = LineString(path[1])
            if route_obstacles.intersects(line) or not reference[row['reference_layer']].covers(line.buffer(.1)):
                continue
            chosen = (path, site)
            break
        if chosen is None:
            deferred.append(dict(ref=row['ref'], pin=row['pin'], reason='No screened local escape within 3.5 mm; placement or return-field work required'))
            print('Deferred', row['ref'], row['pin'], flush=True)
            continue
        (length, path), site = chosen
        routes.append(dict(net='PWR_AGND', layer=layer, reference_layer=row['reference_layer'], width_mm=.2,
                           path_mm=path, length_mm=length, pad_ref=row['ref'], pad_pin=row['pin'], source_group=row['group']))
        vias.append(dict(net='PWR_AGND', position_mm=site, size_mm=.6, drill_mm=.3,
                         role='Local logic ground: ' + row['ref'] + '.' + row['pin']))
        screen.added.append(('PWR_AGND', layer, LineString(path)))
        screen.vias.append(('PWR_AGND', site))
        for l in c['copper_layers']:
            screen.added.append(('PWR_AGND', l, Point(site).buffer(.2)))
        print('Planned', row['ref'], row['pin'], round(length, 3), flush=True)
    allowed = {main, *[r['source_group'] for r in routes]}
    group_pads = {g: [dict(ref=o['ref'], pin=o['pin']) for o in c['objects']
                     if o['kind'] == 'PAD' and o['group'] == g] for g in sorted(allowed)}
    sources = [Path(__file__), CAP, SURVEY, BASE / 'final-review.json', *quiet_paths,
               *[REPO / 'hardware/fabrication' / n for n in ['plan_two_board_startup_controls.py',
                  'route_two_board_power_layer_detours.py', 'route_two_board_power_local_v2.py', 'route_nf_surface.py']]]
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                  routes=routes, vias=vias, deferred=deferred, edited_zone_outlines=[], target_reference_pads=[],
                  allowed_ground_groups=group_pads, old_main_ground_group=main,
                  previous_opens=c['native_uncapped_opens'], expected_closed_connections=len(allowed)-1,
                  excluded_unanchored_fragments=excluded,
                  scope='Local logic GND escapes only, with existing In1/In6 main references. Supply, decoupling, loading and functional behavior remain unqualified.',
                  native_validation_pending=True, fabrication_released=False)
    assert routes and len(routes) == len(allowed)-1
    OUT.mkdir()
    (OUT / 'plan.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(planned_ground_joins=len(routes), vias=len(vias), deferred=len(deferred))))


if __name__ == '__main__':
    run()
