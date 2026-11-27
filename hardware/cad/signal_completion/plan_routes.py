"""Plan additive, fully referenced routes from the frozen r148 native capture.

This does not approve a board. Native refill/DRC, exact connectivity and
retained-reference audits must accept each generated candidate separately.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import uuid

from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.prepared import prep

from hardware.electronics.common.sexpr import a, read_sexpr, sexpr
import hardware.fabrication.route_nf_surface as routing

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'hardware/cad/two_board_sensor_05/signal_dac'
LAYERS = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
REFERENCES = {'F.Cu': ('In1.Cu',), 'In3.Cu': ('In2.Cu', 'In4.Cu'),
              'In5.Cu': ('In4.Cu', 'In6.Cu'), 'B.Cu': ('In6.Cu',)}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output, grid_budget=0):
    assert not output.exists(), 'Use a fresh evidence directory'
    capture_path = BASE / 'capture-r148/capture.json'
    board_path = BASE / 'native-r148/signal_main.kicad_pcb'
    capture = json.loads(capture_path.read_text())
    routing.SIGNAL_LAYERS = LAYERS
    screen = routing.Screen(capture)
    # Only physically connected main-ground islands can serve as references.
    objects = {row['uuid']: row for row in capture['objects']}
    ground = next(row['group'] for row in objects.values()
                  if row.get('ref') == 'D_U1001' and row.get('pin') == '20')
    ground_geometry = {layer: unary_union([
        routing.shape(row['layers'][layer]) for row in objects.values()
        if row['net'] == 'LINK_AGND' and row['group'] == ground and row['layers'].get(layer)
    ]) for layer in ('In1.Cu', 'In2.Cu', 'In4.Cu', 'In6.Cu')}
    fields = {}
    for layer in ground_geometry:
        zones = [routing.shape(z['polygons']) for z in capture['zones']
                 if not z['keepout'] and z['net'] == 'LINK_AGND' and z['layer'] == layer]
        # Ignore disconnected islands, even if their zone has the right net name.
        connected = []
        for zone in zones:
            for part in list(zone.geoms) if hasattr(zone, 'geoms') else [zone]:
                if part.intersection(ground_geometry[layer]).area > 1e-8:
                    connected.append(part)
        fields[layer] = unary_union(connected)
    allowances = {}
    base_legal = screen.legal

    def legal(net, layer, path):
        if not base_legal(net, layer, path):
            return False
        key = (net, layer)
        if key not in allowances:
            field = fields[REFERENCES[layer][0]]
            for reference in REFERENCES[layer][1:]:
                field = field.union(fields[reference])
            # Old same-net copper is existing geometry, not a new unreferenced
            # trace. This initial batch introduces neither holes nor exclusions.
            existing = unary_union([routing.shape(o['layers'][layer]) for o in objects.values()
                                    if o['net'] == net and o['layers'].get(layer)])
            # Match the established r148 transition-hole policy: only immutable
            # baseline same-net holes, with no new vias or changed drills.
            holes = []
            for obj in objects.values():
                if obj['net'] != net:
                    continue
                if obj['kind'] == 'PCB_VIA':
                    holes.append(Point(obj['position_mm']).buffer(obj['width_mm']/2 + .215))
                elif obj['kind'] == 'PAD' and any(obj['drill_mm']):
                    holes.extend(routing.shape(ps).buffer(.215) for ps in obj['layers'].values() if ps)
            allowances[key] = prep(field.buffer(2e-6).union(existing).union(unary_union(holes)).buffer(-.100001))
        return allowances[key].covers(LineString(path))

    screen.legal = legal
    groups = capture['groups']
    by_net, contacts = {}, {}
    for key, identifiers in groups.items():
        net = objects[key]['net']
        by_net.setdefault(net, []).append(key)
        points = set()
        for uid in identifiers:
            obj = objects[uid]
            for layer in LAYERS:
                if obj['layers'].get(layer):
                    for point in [obj['position_mm']] + ([obj['end_mm']] if 'end_mm' in obj else []):
                        points.add((layer, tuple(point)))
        contacts[key] = points
    tasks = []
    for net, keys in by_net.items():
        for left, right in itertools.combinations(keys, 2):
            choices = sorted((math.dist(p, q), layer, p, q)
                             for layer, p in contacts[left] for other_layer, q in contacts[right]
                             if layer == other_layer and 1e-6 < math.dist(p, q) <= 80)
            if choices:
                tasks.append((choices[0][0], net, left, right, choices[:80]))
    parent = {key: key for key in contacts}

    def root(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    routes = []
    blocked = []
    for _, net, left, right, choices in sorted(tasks):
        if root(left) == root(right):
            continue
        accepted = None
        for _, layer, start, end in choices:
            for path in routing.candidate_paths(start, end):
                path = [p for i, p in enumerate(path) if i == 0 or p != path[i-1]]
                if legal(net, layer, path):
                    accepted = (layer, path)
                    break
            if accepted:
                break
        if not accepted and grid_budget:
            for _, layer, start, end in choices[:2]:
                path = screen.grid_path(net, layer, start, end, budget=grid_budget)
                if path:
                    accepted = layer, path
                    break
        if not accepted:
            blocked.append({'net': net, 'groups': [left, right], 'nearest_mm': choices[0][0]})
            continue
        layer, path = accepted
        line = LineString(path)
        screen.added.append((net, layer, line))
        parent[root(right)] = root(left)
        routes.append({'net': net, 'layer': layer, 'path_mm': path, 'width_mm': .2,
                       'groups': [left, right], 'reference_layers': REFERENCES[layer],
                       'length_mm': line.length})
        print('Planned', net, layer, round(line.length, 3), flush=True)
    tree = read_sexpr(board_path.read_text())
    for route_index, row in enumerate(routes):
        row['segment_uuids'] = []
        for index, (start, end) in enumerate(zip(row['path_mm'], row['path_mm'][1:])):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:signal-completion:completion01:{route_index}:{index}'))
            row['segment_uuids'].append(uid)
            tree.append([a('segment'), [a('start'), *start], [a('end'), *end], [a('width'), .2],
                         [a('layer'), row['layer']], [a('net'), row['net']], [a('uuid'), uid]])
    output.mkdir()
    (output / 'signal_main.kicad_pcb').write_text(sexpr(tree) + '\n')
    sources = [Path(__file__), capture_path, board_path, ROOT / 'hardware/fabrication/route_nf_surface.py']
    report = {'baseline_opens': 162, 'expected_opens': 162-len(routes), 'routes': routes,
              'blocked_pairs': blocked, 'new_vias': [], 'fabrication_released': False,
              'native_acceptance_pending': True, 'existing_transition_holes_policy': 'Frozen r148 same-net holes only; radius or captured pad plus 0.215 mm, per r148 reference policy',
              'source_sha256': {str(p.relative_to(ROOT)): digest(p) for p in sources},
              'candidate_sha256': digest(output / 'signal_main.kicad_pcb')}
    (output / 'routing.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Planned', len(routes), 'joins; expected opens', report['expected_opens'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--grid-budget', type=int, default=0)
    args = parser.parse_args()
    run(args.output, args.grid_budget)
