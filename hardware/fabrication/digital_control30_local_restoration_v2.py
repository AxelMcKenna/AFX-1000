"""Restore the compact CONTROL30 branch around the shortened SERIAL_1 route."""
import copy
import json
import math
import time
import uuid
from pathlib import Path
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha, geometry_delta
from hardware.fabrication.digital_serial1_joint_repair import ROOT, FACES, SERIAL
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_polygon_path import route as polygon_route
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

CONTROL = '/CONTROLS/CONTROL_30'
REPLACE = {'0350a0fb-3e7b-5b9d-b3c0-3cd88afeda49', 'b6609b81-ac87-5baf-b63d-5d9e5c0084c7', '52ce26ee-337e-54d6-9fe1-c65205968188'}


def run():
    cp = ROOT/'staging/digital-serial1-closed-inputs-30/capture.json'
    op = ROOT/'staging/digital-serial1-source-preparation-inputs-31-02/capture.json'
    sp = ROOT/'staging/digital-serial1-costed-restoration-03/construction.json'
    rp = ROOT/'staging/digital-combined-costed-routes-01/construction.json'
    cap, old, serial_source, joint = [json.loads(p.read_text()) for p in (cp, op, sp, rp)]
    for record in (cap, old, serial_source, joint):
        assert all(sha(Path(p)) == h for p, h in record['source_sha256'].items())
    serial = next(r for r in joint['routes'] if r['net'] == SERIAL)
    pcb = next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    old_pcb = next(Path(p) for p in old['source_sha256'] if p.endswith('.kicad_pcb'))
    before, previous = [read_sexpr(p.read_text()) for p in (pcb, old_pcb)]
    removed = set(serial_source['removed_uuids']) | {o['uuid'] for o in cap['objects'] if o['net'] == CONTROL and o['kind'] in ('PCB_TRACK', 'PCB_VIA')}
    restored = [copy.deepcopy(o) for o in old['objects'] if o['net'] == CONTROL and o['kind'] in ('PCB_TRACK', 'PCB_VIA') and o['uuid'] not in REPLACE]
    old_vias = {first(v, 'uuid')[1]: v for v in children(previous, 'via')}
    for o in restored:
        if o['kind'] == 'PCB_VIA':
            d = float(first(old_vias[o['uuid']], 'drill')[1])
            o['drill_mm'] = [d, d]
    work = copy.deepcopy(cap)
    work['objects'] = [o for o in cap['objects'] if o['uuid'] not in removed] + restored
    assert len({o['uuid'] for o in work['objects']}) == len(work['objects'])
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .001
    surface.SIGNAL_LAYERS = FACES
    screen = CloseMarginViaScreen(work, signal_layers=FACES)
    conflict = dict(failed_serial_run_indices=[i for i, (face, path) in enumerate(serial['runs']) if not screen.legal(SERIAL, face, path)],
                    failed_serial_vias=[p for p in serial['new_vias_mm'] if not screen.via_legal(SERIAL, p)])
    routes, selected = [], None
    if not any(conflict.values()):
        routes.append(add(screen, SERIAL, dict(runs=serial['runs'], vias=serial['new_vias_mm'])))
        frozen = PlannedRegionScreen(screen, CONTROL)
        free = frozen.outline.difference(unary_union([g.buffer(d+.0005, quad_segs=32) for n, g, d in frozen.geometry['F.Cu'] if n != CONTROL]))
        path = polygon_route(frozen, CONTROL, 'F.Cu', (81.9,11.1), (83.4,16.), free, time.monotonic()+30)
        if path:
            selected = add(screen, CONTROL, dict(runs=[('F.Cu',path)], vias=[]))
            assert selected['planar_length_mm'] < 20, 'Local restoration must not add another long detour'
            routes.append(selected)
    paths = [cp, op, sp, rp, pcb, old_pcb, Path(__file__)] + [ROOT/n for n in ('audit_candidate.py', 'digital_serial1_joint_repair.py', 'digital_via_spacing_close_margin.py', 'digital_via_spacing_v2.py', 'digital_xlat_escape_repair.py', 'digital_planned_region_screen.py', 'digital_polygon_path.py', 'digital_region_reachability.py', 'route_nf_surface.py', 'nf_minimum_logic.py', 'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py')] + [ROOT.parent/'electronics/common/sexpr.py']
    out = ROOT/'staging/digital-control30-local-restoration-02'
    out.mkdir(exist_ok=False)
    result = dict(source_sha256={str(p): sha(p) for p in paths}, candidate_emitted=bool(selected),
        serial_conflict_with_restored_control=conflict, mutation_removed_uuids=sorted(removed),
        original_control_replaced_uuids=sorted(REPLACE), routes=routes,
        retained_serial_object_uuids=serial_source['kept_serial_object_uuids'],
        native_rules_relaxed=False, fabrication_released=False)
    if selected:
        board = copy.deepcopy(before)
        for tag in ('segment', 'via'):
            for n in list(children(board, tag)):
                if first(n, 'uuid')[1] in removed:
                    board.remove(n)
        restored_nodes = [copy.deepcopy(n) for tag in ('segment', 'via') for n in children(previous, tag) if first(n, 'net')[1] == CONTROL and first(n, 'uuid')[1] not in REPLACE]
        assert {first(n, 'uuid')[1] for n in restored_nodes} == {o['uuid'] for o in restored}
        board.extend(restored_nodes)
        for r in routes:
            for face, path in r['runs']:
                for p, q in zip(path, path[1:]):
                    if math.dist(p, q) < 1e-7:
                        continue
                    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:CONTROL30-LOCAL-02:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                    board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), .2], [a('layer'), face], [a('net'), r['net']], [a('uuid'), uid]])
            for p in r['new_vias_mm']:
                uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:CONTROL30-LOCAL-02-VIA:{sha(cp)}:{r["net"]}:{p}'))
                board.append([a('via'), [a('at'), *p], [a('size'), .6], [a('drill'), .3], [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), r['net']], [a('uuid'), uid]])
        dest = out/pcb.name
        dest.write_text(sexpr(board)+'\n')
        result.update(candidate_PCB_sha256=sha(dest), geometry_delta=geometry_delta(before, board),
                      restored_control_objects=restored_nodes, native_checks_pending=True)
    (out/'construction.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Local CONTROL30 restoration:', bool(selected), 'serial conflicts', conflict, 'local length', selected['planar_length_mm'] if selected else None, flush=True)


if __name__ == '__main__':
    run()
