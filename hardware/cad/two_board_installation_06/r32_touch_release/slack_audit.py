"""Necessary length bounds for prescribed cradle removal; not a flex proof."""
import hashlib
import json
import math
from pathlib import Path

H = Path(__file__).resolve().parent
R = H.parents[3]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def length(segment):
    return sum(math.dist(p['start'], p['end']) if p['kind'] == 'line' else
               p['radius_mm'] * math.radians(p['angle_degrees'])
               for p in segment['primitives'])

def bounds(segment, side, waypoints):
    """Euclidean endpoint distance is convex on each translation interval.

    Therefore its maximum occurs at one of the piecewise-linear motion's
    waypoints. This proves only a necessary length bound, not curvature,
    endpoint tangency, collision freedom or existence of a deformation.
    """
    a, b = segment['points_mm'][0], segment['points_mm'][-1]
    distances = []
    for delta in waypoints:
        moved_a = a if side == 0 else [x+d for x, d in zip(a, delta)]
        moved_b = b if side == 1 else [x+d for x, d in zip(b, delta)]
        distances.append(math.dist(moved_a, moved_b))
    return length(segment) - max(distances)

c = json.loads((H.parent/'r29_touch_inline/route-draft.json').read_text())
assert c['connector_box_mm'] == [[172.,113.5,21.5],[183.,136.5,32.5]]
motions = {'r1': [[0,0,0],[0,24,0]], 'r2': [[0,0,0],[0,0,3],[0,24,3]]}
rows = []
for e in c['edges']:
    first = e['segments'][1]['primitives'][0]
    assert first['kind'] == 'line'
    start, end = first['start'], first['end']
    assert end[0] == start[0] and end[2] == start[2] and end[1] > start[1]
    for side, segment in enumerate(e['segments']):
        margins = {revision: bounds(segment, side, points) for revision, points in motions.items()}
        assert min(margins.values()) > 0
        rows.append({'id': e['id'], 'side': 'host_to_inline' if side == 0 else 'inline_to_trill',
                     'fixed_endpoint': e['host'] if side == 0 else 'C3_J1:'+e['trill_pin'],
                     'constant_wire_length_mm': length(segment),
                     'necessary_euclidean_length_margin_mm': margins})
# A deliberately too-short wire must fail the necessary bound.
import copy
short = copy.deepcopy(c['edges'][0]['segments'][0])
short['primitives'] = [{'kind': 'line', 'start': [0,0,0], 'end': [1,0,0]}]
assert bounds(short, 0, motions['r2']) < 0
sources = [Path(__file__), H/'service.scad', H/'rejected-r1/service.scad',
           H.parent/'r29_touch_inline/route-draft.json', H.parent/'r29_touch_inline/route-draft.scad']
r = {'status': 'CRADLE_REMOVAL_AND_WIRE_DEFORMATION_UNQUALIFIED',
     'prescribed_full_cradle_removal': motions,
     'travel_basis': '24 mm exceeds the full 23 mm reserved box length by 1 mm; entire mated box moves as one rigid object after strap release.',
     'actual_connector_unmating_travel_mm': None,
     'actual_unmating_not_established': 'Neither 21.35 mm reference mated length nor reserved box length establishes engagement, latch motion, mating axis or unmating travel.',
     'rows': rows,
     'necessary_length_test': 'All eight halves have sufficient endpoint-distance length; this is not a sufficient bend/slack feasibility test.',
     'short_wire_mutation_rejected': True,
     'naive_shortening_invalid': '24 mm shortening changes physical length and crosses the first bend of TH1, TH2 and TH4 outgoing halves; shortening does not store slack.',
     'rigid_wire_translation_invalid': 'Moves the fixed host or C3 solder endpoint.',
     'full_service_motion_verified': False,
     'constant_length_bend_deformation_verified': False,
     'completed_touch_wires': 0,
     'source_sha256': {str(p.relative_to(R)): sha(p) for p in sources}}
(H/'slack-audit.json').write_text(json.dumps(r, indent=2)+'\n')
print(json.dumps({'status': r['status'], 'wire_halves': len(rows), 'min_necessary_length_margin_mm': min(v for row in rows for v in row['necessary_euclidean_length_margin_mm'].values())}))
