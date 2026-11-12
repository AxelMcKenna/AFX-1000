#!/usr/bin/env python3
"""Host-only, fail-closed PCB mechanical comparison against the frozen CAD inputs."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from hardware.electronics.common import sexpr as sx
from hardware.fabrication import assembly_layout
from shapely.geometry import Polygon


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(node):
    # UUIDs and net assignments cannot change a physical footprint. Everything
    # else is retained, including unknown future fields (conservative failure).
    if isinstance(node, list):
        return [canonical(x) for x in node if not (
            isinstance(x, list) and x and x[0] in
            {'uuid', 'tstamp', 'net', 'pinfunction', 'pintype', 'path'})]
    return str(node)


def snapshot(path):
    tree, poly = assembly_layout.outline(path)
    footprints = {}
    holes = []
    for fp in sx.children(tree, 'footprint'):
        props = {str(p[1]): str(p[2]) for p in sx.children(fp, 'property')}
        ref = props.get('Reference')
        if not ref or ref in footprints:
            raise ValueError('Missing or duplicate footprint reference: ' + str(ref))
        at = sx.first(fp, 'at')
        pose = [float(at[1]), float(at[2]), float(at[3]) % 360 if len(at) > 3 else 0,
                str(sx.first(fp, 'layer')[1])]
        physical = [fp[0], fp[1]]
        for child in fp[2:]:
            if isinstance(child, list) and child[0] in {'property', 'at', 'layer', 'uuid', 'tstamp', 'path'}:
                continue
            physical.append(child)
        pads = sx.children(fp, 'pad')
        if pads and all(p[2] == 'np_thru_hole' for p in pads):
            for pad in pads:
                pa = sx.first(pad, 'at')
                x, y = map(float, pa[1:3])
                a = math.radians(pose[2])
                drill = sx.first(pad, 'drill')
                if len(drill) != 2:
                    raise ValueError('Unsupported noncircular mounting hole: ' + ref)
                holes.append([round(pose[0]+x*math.cos(a)+y*math.sin(a), 9),
                              round(pose[1]-x*math.sin(a)+y*math.cos(a), 9), float(drill[1])])
        footprints[ref] = {'pose': pose, 'library': str(fp[1]),
                           'physical': canonical(physical),
                           'properties': {k: v for k, v in props.items() if k != 'Reference'}}
    return {'outline': list(map(list, poly.exterior.coords)),
            'thickness': float(sx.first(sx.first(tree, 'general'), 'thickness')[1]),
            'holes': sorted(holes), 'footprints': footprints}


def compare(old, new):
    differences = []
    if not Polygon(old['outline']).equals(Polygon(new['outline'])):
        differences.append({'field': 'outline', 'before': old['outline'], 'after': new['outline']})
    for field in ('thickness', 'holes'):
        if old[field] != new[field]:
            differences.append({'field': field, 'before': old[field], 'after': new[field]})
    for ref in sorted(set(old['footprints']) | set(new['footprints'])):
        a, b = old['footprints'].get(ref), new['footprints'].get(ref)
        if a is None or b is None:
            differences.append({'ref': ref, 'field': 'presence', 'before': a, 'after': b})
            continue
        for field in a:
            if a[field] != b[field]:
                differences.append({'ref': ref, 'field': field, 'before': a[field], 'after': b[field]})
    return differences


def run(repo, selected, capture_path):
    capture = json.loads((repo / capture_path).read_text())
    sources = {capture_path: sha(repo / capture_path)}
    # Bind the actual executing code, even when reading another isolated checkout.
    for path in (Path(__file__), Path(sx.__file__), Path(assembly_layout.__file__)):
        sources[str(path.relative_to(REPO))] = sha(path)
    result = {'schema': 1, 'selected_pcbs': selected, 'source_sha256': sources,
              'boards': {}, 'errors': [], 'geometry_fresh': False,
              'qualification': 'Receiving envelopes only; not exact STEP or supplier-approved heights.',
              'height_uncertainty': {'supplier_approved': capture.get('heights_supplier_approved', False),
                                     'new_height_assumptions': capture.get('new_height_assumptions'),
                                     'value_or_part_change_requires_height_review': True},
              'scope': 'Outlines, nominal thickness, mounting holes, footprint presence/pose/side, all footprint physical fields (including courtyards, models and pad/drill geometry), and part properties. Tracks, zones and vias are excluded; this is not electrical or fabrication approval.'}
    for board, path in selected.items():
        sources[path] = sha(repo / path)
        candidates = [p for p in capture['source_sha256'] if p.endswith('/' + Path(path).name)]
        if len(candidates) != 1:
            result['errors'].append(board + ': ambiguous or missing captured PCB source')
            continue
        baseline = candidates[0]
        sources[baseline] = sha(repo / baseline)
        if sources[baseline] != capture['source_sha256'][baseline]:
            result['errors'].append(board + ': captured PCB source hash mismatch')
            continue
        try:
            old, new = snapshot(repo / baseline), snapshot(repo / path)
            captured = next(b for b in capture['boards'] if b['id'] == board)
            if not Polygon(old['outline']).equals(Polygon(captured['outline'])) or old['thickness'] != captured['thickness'] or old['holes'] != sorted(captured['holes']):
                result['errors'].append(board + ': original PCB disagrees with captured outline/thickness/holes')
            result['boards'][board] = {'baseline': baseline, 'footprints': len(new['footprints']),
                                      'differences': compare(old, new)}
        except (AssertionError, ValueError, IndexError, KeyError, StopIteration) as error:
            result['errors'].append(board + ': unsupported or invalid geometry: ' + repr(error))
    result['geometry_fresh'] = not result['errors'] and len(result['boards']) == 2 and not any(b['differences'] for b in result['boards'].values())
    result['freshness_key'] = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=REPO)
    parser.add_argument('--capture', default='hardware/cad/two_board_print_01/capture.json')
    parser.add_argument('--power', required=True)
    parser.add_argument('--signal', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.repo_root.resolve(), {'power': args.power, 'signal': args.signal}, args.capture)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'geometry_fresh': result['geometry_fresh'], 'errors': result['errors'],
                      'differences': {k: len(v['differences']) for k, v in result['boards'].items()},
                      'freshness_key': result['freshness_key']}))
    return 0 if result['geometry_fresh'] else 1


if __name__ == '__main__':
    sys.exit(main())
