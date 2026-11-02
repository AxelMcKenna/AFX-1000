"""E13 3.3 V distribution trial on In2; keep In1 ground copper unchanged.

Other In2 pours are refilled by native KiCad around added power tracks. Geometry,
connectivity and power integrity require new review; this is not a release.
"""
import argparse
import copy
import itertools
import json
import math
import uuid
from pathlib import Path

from shapely.strtree import STRtree

from hardware.electronics.common.sexpr import a, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import Screen, candidate_paths

ROOT = Path(__file__).resolve().parent


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert all(x and all(c.isalnum() or c in '-_' for c in x) for x in (args.capture,args.label))
    capture_path = ROOT/'staging'/args.capture/'capture.json'
    capture = json.loads(capture_path.read_text())
    assert all(sha(Path(p)) == h for p, h in capture['source_sha256'].items())
    source = next(Path(p) for p in capture['source_sha256'] if p.endswith('.kicad_pcb'))
    board = read_sexpr(source.read_text())
    original, count = sexpr(board), len(board)
    planning = copy.deepcopy(capture)
    planning['zones'] = [z for z in planning['zones'] if z['keepout']]
    screen = Screen(planning)
    layer, net = 'In2.Cu', '/V3V3_IO'
    # Screen's default trace is 0.2 mm; enlarge all obstacle distances for 0.4 mm.
    screen.geometry[layer] = [(n, g, d+.1) for n, g, d in screen.geometry[layer]]
    screen.trees[layer] = STRtree([g for _, g, _ in screen.geometry[layer]])
    screen.outline = screen.outline.buffer(-.1)
    objects = {o['uuid']: o for o in capture['objects']}
    endpoints = {}
    for group, ids in capture['groups'].items():
        if objects[ids[0]]['net'] != net:
            continue
        endpoints[group] = sorted({tuple(objects[i]['position_mm']) for i in ids if layer in objects[i]['layers']})
    parent = {g:g for g in endpoints}
    def root(g):
        while parent[g] != g:
            g = parent[g]
        return g
    tasks = []
    for left, right in itertools.combinations(endpoints, 2):
        options = sorted((math.dist(p, q), p, q) for p in endpoints[left] for q in endpoints[right])
        if options:
            tasks.append((options[0][0], left, right, options[:4]))
    routes = []
    for _, left, right, options in sorted(tasks):
        if root(left) == root(right):
            continue
        chosen = None
        for _, start, end in options:
            for path in candidate_paths(start, end):
                path = [p for i,p in enumerate(path) if not i or p != path[i-1]]
                if screen.legal(net, layer, path):
                    chosen = path
                    break
            if chosen:
                break
        if chosen is None:
            for _, start, end in options:
                chosen = screen.grid_path(net, layer, start, end, budget=15000)
                if chosen:
                    break
        if chosen is None:
            continue
        simple = [chosen[0]]
        index = 0
        while index < len(chosen)-1:
            next_index = index+1
            for j in range(index+2,len(chosen)):
                if screen.legal(net,layer,[chosen[index],chosen[j]]):
                    next_index = j
            simple.append(chosen[next_index])
            index = next_index
        chosen = simple
        for start,end in zip(chosen,chosen[1:]):
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:E13:power-tree:{sha(source)}:{start}:{end}'))
            board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),.4],
                          [a('layer'),layer],[a('net'),net],[a('uuid'),ident]])
        parent[root(right)] = root(left)
        routes.append(dict(groups=[left,right],points_mm=chosen))
    assert sexpr(board[:count]) == original
    output = ROOT/'staging'/args.label
    output.mkdir(exist_ok=False)
    pcb = output/source.name
    pcb.write_text(sexpr(board)+'\n')
    (output/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p):sha(p) for p in (source,capture_path,Path(__file__),ROOT/'route_nf_surface.py')},
        candidate_PCB_sha256=sha(pcb),routes=routes,unreached_groups=[g for g in endpoints if not endpoints[g]],
        original_authored_geometry_exact=True,distribution_layer=layer,net=net,width_mm=.4,
        native_refill_and_checks_required=True,PDN_noise_review_required=True,fabrication_released=False),indent=2)+'\n')
    print('Planned',len(routes),'inner-layer power connections;',len({root(g) for g in endpoints}),'groups remain')


if __name__ == '__main__':
    run()
