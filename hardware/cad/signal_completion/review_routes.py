"""Audit actual native added copper against unchanged connected reference fields."""
import argparse
import hashlib
import json
from pathlib import Path

from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import children, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'hardware/cad/two_board_sensor_05/signal_dac'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shape(polygons):
    return unary_union([Polygon(row['outer'], row['holes']) for row in polygons])


def retained_board_check(before_path, after_path, expected_added):
    def split(path):
        keyed, global_nodes = {}, []
        for node in read_sexpr(path.read_text())[1:]:
            uid = children(node, 'uuid') if isinstance(node, list) else []
            if uid:
                key = uid[0][1]
                assert key not in keyed, 'Duplicate native object UUID'
                keyed[key] = sexpr(node)
            else:
                global_nodes.append(sexpr(node) if isinstance(node, list) else str(node))
        return keyed, global_nodes
    before, globals_before = split(before_path)
    after, globals_after = split(after_path)
    assert globals_before == globals_after, 'Board-global settings changed'
    assert all(after.get(uid) == value for uid, value in before.items()), 'Retained board object or fill changed'
    assert set(after) - set(before) == expected_added, 'Unexpected native additions'


def audit(candidate, native, output):
    candidate, native, output = candidate.resolve(), native.resolve(), output.resolve()
    assert not output.exists(), 'Do not overwrite review evidence'
    source_inputs = Path(__file__).with_name('source-inputs.json')
    for name, expected in json.loads(source_inputs.read_text())['source_sha256'].items():
        assert sha(ROOT / name) == expected, ('stale gate dependency', name)
    manifest = json.loads((candidate / 'routing.json').read_text())
    review_path = native / 'native-review.json'
    native_review = json.loads(review_path.read_text())
    for report in (manifest, native_review):
        for name, expected in report['source_sha256'].items():
            assert sha(ROOT / name) == expected, ('stale source', name)
    assert sha(candidate / 'signal_main.kicad_pcb') == manifest['candidate_sha256']
    assert sha(native / 'signal_main.kicad_pcb') == native_review['pcb_sha256']
    assert not native_review['violations'] and not native_review['erc_findings']
    assert native_review['original_connectivity_preserved']
    assert native_review['native_opens'] == manifest['expected_opens']
    # This additive surface-only batch must leave every saved reference fill
    # bit-for-bit unchanged. No numerical waiver for lost original fields.
    assert native_review['changed_filled_zone_uuids'] == []
    capture = json.loads((BASE / 'capture-r148/capture.json').read_text())
    main = next(o['group'] for o in capture['objects']
                if o.get('ref') == 'D_U1001' and o.get('pin') == '20')
    connected_ground = {}
    fields = {}
    for layer in ('In1.Cu', 'In2.Cu', 'In4.Cu', 'In6.Cu'):
        connected_ground[layer] = unary_union([
            shape(o['layers'][layer]) for o in capture['objects']
            if o['net'] == 'LINK_AGND' and o['group'] == main and o['layers'].get(layer)])
        polygons = [Polygon(p['outer'], p['holes'])
                    for zone in native_review['reference_fields'] if zone['layer'] == layer
                    for p in zone['polygons']]
        # Only directly main-ground-connected filled islands are accepted.
        fields[layer] = unary_union([p for p in polygons
                                     if p.intersection(connected_ground[layer]).area > 1e-8])
    added = {row['uuid']: row for row in native_review['added_copper']}
    expected = {uid for row in manifest['routes'] for uid in row['segment_uuids']}
    assert len(added) == len(native_review['added_copper']), 'Duplicate native added-copper UUID'
    assert set(added) == expected
    retained_board_check(BASE / 'native-r148/signal_main.kicad_pcb', native / 'signal_main.kicad_pcb', expected)
    cases = []
    for route in manifest['routes']:
        copper = unary_union([shape(added[uid]['polygons']) for uid in route['segment_uuids']])
        assert all(added[uid]['net'] == route['net'] and added[uid]['layer'] == route['layer']
                   for uid in route['segment_uuids'])
        old_copper = unary_union([shape(o['layers'][route['layer']]) for o in capture['objects']
                                 if o['net'] == route['net'] and o['layers'].get(route['layer'])])
        introduced = copper.difference(old_copper)
        holes = []
        for obj in capture['objects']:
            if obj['net'] != route['net']:
                continue
            if obj['kind'] == 'PCB_VIA':
                holes.append(Point(obj['position_mm']).buffer(obj['width_mm']/2 + .215))
            elif obj['kind'] == 'PAD' and any(obj['drill_mm']):
                holes.extend(shape(ps).buffer(.215) for ps in obj['layers'].values() if ps)
        transition_copper = introduced.intersection(unary_union(holes))
        reference_required = introduced.difference(unary_union(holes))
        reference_cases = []
        physical_layers = capture['copper_layers']
        index = physical_layers.index(route['layer'])
        adjacent = {physical_layers[j] for j in (index-1, index+1) if 0 <= j < len(physical_layers)}
        assert set(route['reference_layers']) <= adjacent, 'Nonadjacent reference cannot qualify a route'
        field = unary_union([fields[layer] for layer in route['reference_layers']])
        uncovered = reference_required.difference(field.buffer(2e-6))
        reference_cases.append({'adjacent_layers': route['reference_layers'], 'uncovered_mm2': uncovered.area})
        assert uncovered.area < 1e-6, ('unreferenced introduced copper', route['net'], uncovered.area)
        assert introduced.area > 1e-6
        cases.append({'net': route['net'], 'layer': route['layer'], 'native_copper_mm2': copper.area,
                      'introduced_copper_mm2': introduced.area, 'existing_transition_copper_mm2': transition_copper.area, 'references': reference_cases})
    report = {'accepted_routing_checkpoint': True, 'fabrication_released': False,
              'baseline_opens': 162, 'native_opens': native_review['native_opens'],
              'joins': len(manifest['routes']), 'actual_native_reference_cases': cases,
              'all_original_authored_objects_and_connectivity_preserved': True,
              'all_saved_reference_fills_exact': True,
              'scope': 'Additive surface routing only; missing ESS footprint, remaining routing and complete-board qualification are open.',
              'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), source_inputs, review_path,
                  candidate / 'routing.json', BASE / 'capture-r148/capture.json']}}
    output.write_text(json.dumps(report, indent=2) + '\n')
    print('PASS', len(cases), 'native copper/reference cases;', report['native_opens'], 'opens')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('candidate', type=Path)
    parser.add_argument('native', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    audit(args.candidate, args.native, args.output)
