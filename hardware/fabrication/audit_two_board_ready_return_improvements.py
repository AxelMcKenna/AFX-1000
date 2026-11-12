"""Compare existing control return gaps without waiving terminal clearances.

Plated-pad clearance overlap is diagnostic only: it never makes a failing
full-width reference check pass, and it does not qualify return transitions.
"""
import json
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
from hardware.fabrication.route_nf_surface import shape

BEFORE = STAGING / 'two-board-power-routing-inputs-control-return-planes-01/capture.json'
AFTER = STAGING / 'two-board-power-routing-inputs-ready-return-planes-01/capture.json'
SURVEY = STAGING / 'two-board-control-return-survey-after-03/survey.json'
OUT = STAGING / 'two-board-power-ready-return-planes-native-01'


def run():
    target = OUT / 'ready-return-improvement-review.json'
    assert not target.exists()
    before, after, survey = [json.loads(p.read_text()) for p in [BEFORE, AFTER, SURVEY]]
    captures = [before, after]
    fields, holes, objects = [], [], []
    for c in captures:
        f, _ = anchored_fields(c)
        main = next(o['group'] for o in c['objects'] if o.get('ref') == 'P_C103' and o.get('pin') == '2')
        fields.append({l: p.buffer(.0015) for (l, g), p in f.items() if g == main})
        h = {}
        for o in c['objects']:
            if o['kind'] == 'PCB_VIA':
                h.setdefault(o['net'], []).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
        holes.append({n: unary_union(gs) for n, gs in h.items()})
        objects.append({o['uuid']: o for o in c['objects']})
    tracks = [r['track_uuid'] for n in survey['nets'] for r in n['checks'] if not r['fully_referenced']]
    assert len(tracks) == 7
    rows = []
    for uid in tracks:
        old, new = [os[uid] for os in objects]
        assert {k: v for k, v in old.items() if k != 'group'} == {k: v for k, v in new.items() if k != 'group'}
        layer, = old['layers']
        index = before['copper_layers'].index(layer)
        adjacent = [before['copper_layers'][j] for j in [index-1, index+1] if 0 <= j < len(before['copper_layers'])]
        gaps = []
        for i, obj in enumerate([old, new]):
            band = LineString([obj['position_mm'], obj['end_mm']]).buffer(obj['width_mm']/2).difference(holes[i].get(obj['net'], Polygon()))
            choices = [(band.difference(fields[i][l]), l) for l in adjacent if l in fields[i]]
            missing, reference = min(choices, key=lambda x: x[0].area)
            gaps.append((missing, reference))
        assert gaps[1][0].area <= gaps[0][0].area + 1e-6, (uid, 'Existing gap worsened')
        pad_regions = []
        pad_details = []
        reference = gaps[1][1]
        for obj in after['objects']:
            if obj['kind'] != 'PAD' or obj['net'] != new['net'] or obj.get('npth') or not any(obj.get('drill_mm', [0, 0])):
                continue
            if reference not in obj['layers']:
                continue
            clearance = shape(obj['layers'][reference]).buffer(.215)
            overlap = gaps[1][0].intersection(clearance).area
            if overlap > 1e-9:
                pad_regions.append(clearance)
                pad_details.append(dict(ref=obj['ref'], pin=obj['pin'], overlap_mm2=overlap))
        pad_overlap = gaps[1][0].intersection(unary_union(pad_regions)).area if pad_regions else 0
        rows.append(dict(track_uuid=uid, net=new['net'], layer=layer,
            start_mm=new['position_mm'], end_mm=new['end_mm'],
            reference_layer=reference, before_uncovered_mm2=gaps[0][0].area,
            after_uncovered_mm2=gaps[1][0].area, fully_referenced=gaps[1][0].area < 1e-6,
            diagnostic_same_net_plated_pad_clearance_overlap_mm2=pad_overlap,
            diagnostic_gap_outside_plated_pad_clearance_mm2=gaps[1][0].area-pad_overlap,
            diagnostic_pad_contacts=pad_details))
    sources = [Path(__file__), BEFORE, AFTER, SURVEY, OUT/'ready-return-planes-review.json',
               REPO/'hardware/fabrication/plan_two_board_startup_controls.py', REPO/'hardware/fabrication/route_nf_surface.py']
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
        previous_unreferenced_tracks=7, repaired_tracks=sum(r['fully_referenced'] for r in rows),
        remaining_unreferenced_tracks=sum(not r['fully_referenced'] for r in rows),
        no_existing_gap_worsened=True, tracks=rows,
        scope='Strict adjacent main-ground full-width check, own-via exception unchanged. Plated-pad overlap is diagnosis only, with .215 mm clearance allocation; it grants no qualification or exemption.',
        transitions_and_functional_operation_qualified=False, fabrication_released=False)
    target.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ['previous_unreferenced_tracks', 'repaired_tracks', 'remaining_unreferenced_tracks']}))


if __name__ == '__main__':
    run()
