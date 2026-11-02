"""Prune unused trial escape branches using captured native copper polygons."""
import argparse
import json
from pathlib import Path

from shapely.geometry import Point, LineString
from shapely.strtree import STRtree

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    for name in [args.capture, args.label]:
        assert name and all(c.isalnum() or c in '-_' for c in name)
    cp = ROOT/'staging'/args.capture/'capture.json'
    c = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in c['source_sha256'].items())
    pcb = next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'))
    drc_path = pcb.parent/'drc.json'
    drc = json.loads(drc_path.read_text())
    assert all(v['severity'] == 'warning' and v['type'] in
               {'via_dangling', 'track_dangling'} for v in drc['violations'])
    base = ROOT/'staging/digital-distribution-native-02/digital_core.kicad_pcb'
    original = read_sexpr(base.read_text())
    protected = {first(n, 'uuid')[1] for tag in ['segment', 'via']
                 for n in children(original, tag)}
    removed = {i['uuid'] for v in drc['violations'] for i in v['items']}
    assert not removed & protected
    geometry = []
    for o in c['objects']:
        for layer, polygons in o['layers'].items():
            if polygons:
                geometry.append((o['uuid'], o['net'], layer,
                                 LineString([o['position_mm'], o['end_mm']])
                                 if o['kind'] == 'PCB_TRACK' else shape(polygons)))
    for z in c['zones']:
        if not z['keepout'] and z['polygons']:
            geometry.append((z['uuid'], z['net'], z['layer'], shape(z['polygons'])))
    tree = STRtree([g[3] for g in geometry])
    tracks = [o for o in c['objects'] if o['kind'] == 'PCB_TRACK'
              and o['uuid'] not in protected]
    pruned = []
    while True:
        changed = False
        for o in tracks:
            if o['uuid'] in removed:
                continue
            layer = next(l for l, ps in o['layers'].items() if ps)
            for endpoint in [o['position_mm'], o['end_mm']]:
                point = Point(endpoint)
                # Track centerline or pad contact, with rounding tolerance.
                radius = .002
                neighbors = [geometry[int(i)] for i in tree.query(point.buffer(radius))]
                connected = any(uid != o['uuid'] and uid not in removed
                                and net == o['net'] and face == layer
                                and point.distance(g) <= radius
                                for uid, net, face, g in neighbors)
                if not connected:
                    removed.add(o['uuid'])
                    pruned.append(dict(uuid=o['uuid'], net=o['net'],
                                       unsupported_endpoint_mm=endpoint))
                    changed = True
                    break
        if not changed:
            break
    board = read_sexpr(pcb.read_text())
    nodes = [n for tag in ['segment', 'via'] for n in children(board, tag)
             if first(n, 'uuid')[1] in removed]
    assert len(nodes) == len(removed) and not removed & protected
    for n in nodes:
        board.remove(n)
    out = ROOT/'staging'/args.label
    out.mkdir(exist_ok=False)
    dest = out/pcb.name
    dest.write_text(sexpr(board)+'\n')
    inputs = [cp, pcb, drc_path, base, Path(__file__), ROOT/'route_nf_surface.py']
    (out/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p): sha(p) for p in inputs},
        candidate_PCB_sha256=sha(dest), removed_objects=nodes,
        pruned_leaf_tracks=pruned, original_DC03_copper_preserved=True,
        native_checks_pending=True, fabrication_released=False), indent=2)+'\n')
    print('Pruned', len(nodes), 'objects including', len(pruned), 'leaf tracks')


if __name__ == '__main__':
    run()
