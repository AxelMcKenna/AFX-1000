"""Survey compact TPS543620 cells against the current board, without moving it.

The old size-first packing separated electrical neighbours. This survey restores
source-relative placement, with explicit small courtyard-spacing corrections.
It is a placement screen, not approval of the source circuit or power layout.
"""
import json
import math
from pathlib import Path

import numpy as np
from shapely.affinity import translate
from shapely.geometry import Point, Polygon, box
from shapely.strtree import STRtree

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.two_board_placement import offset, overlap
from hardware.fabrication.route_nf_surface import shape

BASE = STAGING / 'two-board-power-routed-native-08'
CAP = STAGING / 'two-board-power-routing-inputs-2554-via-repair/capture.json'
PLACEMENT = STAGING / 'two-board-placement-05/capture.json'
SOURCE = REPO / 'hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter/generated/native-closed-transmitter/power_p03.kicad_pcb'
OUT = STAGING / 'two-board-buck-cell-survey-01'
CELLS = {
    'U20': ['U20', 'C200', 'C201', 'C202', 'C203', 'C210', 'C211', 'L20', 'R201', 'R206'],
    'U23': ['U23', 'C220', 'C221', 'C222', 'C223', 'C230', 'C231', 'L23', 'R220', 'R221'],
}
ADJUST = {'C202': (1, 4.4), 'C203': (1, -4.4), 'C210': (.75, 2.5), 'C211': (.75, -2.5),
          'C222': (1, 4.4), 'C223': (1, -4.4), 'C230': (.75, 2.5), 'C231': (.75, -2.5),
          'L23': (9.1, 0), 'R201': (-4, -.8), 'R221': (4.8, 5.6)}


def footprints(path):
    return {next(p[2] for p in children(f, 'property') if p[1] == 'Reference'): f
            for f in children(read_sexpr(path.read_text()), 'footprint')}


def xy(f):
    return [float(v) for v in first(f, 'at')[1:3]]


def run():
    assert not OUT.exists()
    cap = json.loads(CAP.read_text()); placement = json.loads(PLACEMENT.read_text())
    for name, h in cap['source_sha256'].items():
        assert sha(REPO / name) == h, name
    assert cap['native_uncapped_opens'] == 2554 and not cap['zones']
    current = footprints(BASE / 'power_protection.kicad_pcb'); source = footprints(SOURCE)
    records = {r['id']: r for r in placement['parts']}
    objects = {o['uuid']: o for o in cap['objects']}
    envelopes = []
    for ref, f in current.items():
        x, y = xy(f)
        for side in ['F', 'B']:
            try:
                envelopes.append((ref, side, courtyard(f, side + '.CrtYd'), 'courtyard'))
            except AssertionError:
                pass
        if ref in records:
            r = records[ref]
            assert (float(first(f, 'at')[3]) if len(first(f, 'at')) > 3 else 0) == r['angle'], ref
            envelopes.append((ref, r['side'], offset(r['body_relative_xy'], x, y), 'body'))
            for b in r['tails_relative_xy']:
                assert r['side'] == 'F'
                envelopes.append((ref, 'B', offset(b, x, y), 'tail'))
            for extra in r.get('additional_planar_reserves', []):
                envelopes.append((ref, extra['side'], offset(extra['bounds'], x, y), extra['kind']))
    mounts = [(o['ref'], o['position_mm'], max(3.6, max(o['drill_mm']) / 2 + .5))
              for o in cap['objects'] if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    assert len(mounts) == 15
    for ref, p, radius in mounts:
        envelopes.append((ref, 'F', [p[0]-radius, p[1]-radius, p[0]+radius, p[1]+radius], 'mount'))
    contexts = [q for q in placement['context'] if not q['id'].startswith('inlet_')]
    allocation_path = STAGING / 'assembly-layout-04/allocation.json'
    for name, x, y, z, dx, dy, t, *_ in json.loads(allocation_path.read_text())['additional_panel_PCBS']:
        contexts.append(dict(id=name, xy=[x, y, x+dx, y+dy], z=[z, z+t]))
    outline = shape(cap['outline']).buffer(-.5)
    grid_x, grid_y = np.meshgrid(np.arange(8, 328.01, .5), np.arange(108.5, 182.51, .5))
    xx, yy = grid_x.ravel(), grid_y.ravel()
    results = []
    for regulator, refs0 in CELLS.items():
        refs = {'P_'+r for r in refs0}; origin = xy(source[regulator]); template = []; distances = []
        for r0 in refs0:
            ref = 'P_'+r0; old = xy(current[ref]); src = xy(source[r0])
            delta = ADJUST.get(r0, (src[0]-origin[0], src[1]-origin[1]))
            assert first(current[ref], 'layer')[1] == first(source[r0], 'layer')[1] == 'F.Cu'
            assert list(first(current[ref], 'at')[3:]) == list(first(source[r0], 'at')[3:])
            rel = offset(courtyard(current[ref], 'F.CrtYd'), -old[0]+delta[0], -old[1]+delta[1])
            template.append(dict(ref=ref, delta_mm=delta, courtyard_relative_to_anchor_mm=rel))
            distances.append(dict(ref=ref, source_centre_distance_mm=math.dist(src, origin),
                                  current_centre_distance_mm=math.dist(old, xy(current['P_'+regulator])),
                                  proposed_centre_distance_mm=math.hypot(*delta)))
            for o in objects.values():
                if o.get('ref') == ref and o.get('group'):
                    assert all(objects[u].get('ref') == ref for u in cap['all_groups'][o['group']]), (ref, o['pin'])
        for i, a in enumerate(template):
            for b in template[:i]:
                assert not overlap(a['courtyard_relative_to_anchor_mm'], b['courtyard_relative_to_anchor_mm'], .3), (a, b)
        obstacles = [(ref, b, kind) for ref, side, b, kind in envelopes if side == 'F' and ref not in refs]
        # Count distinct blocking owners, so duplicate body/courtyard envelopes
        # cannot inflate the ranking. This screen uses rectangles conservatively.
        owners = {}
        for ref, b, kind in obstacles:
            owners.setdefault(ref, []).append(b)
        counts = np.zeros(len(xx), dtype=np.int32)
        for ref, boxes in owners.items():
            hit = np.zeros(len(xx), dtype=bool)
            for a in template:
                b = a['courtyard_relative_to_anchor_mm']
                for q in boxes:
                    hit |= ((xx+b[0] < q[2]+.3-1e-8) & (xx+b[2] > q[0]-.3+1e-8) &
                            (yy+b[1] < q[3]+.3-1e-8) & (yy+b[3] > q[1]-.3+1e-8))
            counts += hit
        legal_context = np.ones(len(xx), dtype=bool)
        for a in template:
            r = records[a['ref']]; b = a['courtyard_relative_to_anchor_mm']
            z = [placement['power_Z']-.2+1.44, placement['power_Z']+.2+1.76+r['height_mm']]
            assert z[0] >= 3.05 and z[1] <= 43.35
            for q in contexts:
                if min(z[1]+.25, q['z'][1]) <= max(z[0]-.25, q['z'][0]):
                    continue
                c = q['xy']
                legal_context &= ~((xx+b[0] < c[2]+.25) & (xx+b[2] > c[0]-.25) &
                                   (yy+b[1] < c[3]+.25) & (yy+b[3] > c[1]-.25))
        # Search the whole lower C-board arm; individual exact polygon checks
        # reject edge/cutout candidates after the vectorized broad phase.
        target = xy(current['P_'+regulator]); distance = (xx-target[0])**2+(yy-target[1])**2
        candidates = []; exact_zero = 0
        for index in np.lexsort((distance, counts)):
            if not legal_context[index]:
                continue
            anchor = [float(xx[index]), float(yy[index])]
            if not all(outline.covers(box(*offset(a['courtyard_relative_to_anchor_mm'], *anchor))) for a in template):
                continue
            blocking = sorted(ref for ref, boxes in owners.items() if any(
                overlap(offset(a['courtyard_relative_to_anchor_mm'], *anchor), q, .3) for a in template for q in boxes))
            assert len(blocking) == int(counts[index])
            candidates.append(dict(anchor_mm=anchor, blocking_owners=blocking,
                                   regulator_displacement_mm=math.sqrt(float(distance[index]))))
            exact_zero += not blocking
            if len(candidates) >= 24:
                break
        result = dict(regulator='P_'+regulator, members=template, distances=distances,
                      all_member_pad_groups_have_no_external_copper=True, grid_points=len(xx),
                      search_step_mm=.5, best_candidates=candidates,
                      checked_zero_blocker_candidates=exact_zero,
                      copper_clearance_not_yet_checked=True)
        results.append(result)
        print(regulator, 'best:', candidates[:3], flush=True)
    paths = [Path(__file__), CAP, PLACEMENT, SOURCE, BASE/'power_protection.kicad_pcb',
             BASE/'via-repair-audit.json', allocation_path,
             REPO/'hardware/electronics/output_stage/check_placement.py',
             REPO/'hardware/fabrication/two_board_placement.py', REPO/'hardware/fabrication/route_nf_surface.py']
    data = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths}, cells=results,
                primary_layout_reference='https://www.ti.com/lit/ds/symlink/tps543620.pdf',
                reference_revision='SLUSDR5C, June 2021, sections 9 and 10.1',
                scope='Placement-only fixed-obstacle survey. No circuit, footprint or copper edited.',
                diagnosis='Independent size-first packing separated local regulator bypass and feedback components.',
                candidate_board_written=False, complete_fit_verified=False, fabrication_released=False)
    OUT.mkdir(); (OUT/'survey.json').write_text(json.dumps(data, indent=2)+'\n')


if __name__ == '__main__':
    run()
