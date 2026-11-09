"""Shorten CONTROL30 from its through-hole source, retaining the receiving escape."""
import copy
import json
import math
import time
import uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha, geometry_delta
from hardware.fabrication.digital_costed_region_route_v3 import route
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_joint_repair import ROOT, FACES
SERIAL = '/CONTROLS/CONTROL_30'
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers


def run():
    cp = ROOT/'staging/digital-serial1-closed-inputs-30/capture.json'
    op = ROOT/'staging/digital-serial1-source-preparation-inputs-31-02/capture.json'
    cap, old = [json.loads(p.read_text()) for p in (cp, op)]
    for record in (cap, old):
        assert all(sha(Path(p)) == h for p, h in record['source_sha256'].items())
    pcb = next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    original_pcb = next(Path(p) for p in old['source_sha256'] if p.endswith('.kicad_pcb'))
    before, previous = [read_sexpr(p.read_text()) for p in (pcb, original_pcb)]
    control = '/CONTROLS/CONTROL_30'
    source = (67.62, 7.)
    target = (87.5, 39.7)
    keep = set()
    for o in cap['objects']:
        if o['net'] != SERIAL:
            continue
        if o['kind'] == 'PCB_VIA' and any(math.dist(o['position_mm'], p) < 1e-7 for p in (source, target)):
            keep.add(o['uuid'])
        if o['kind'] == 'PCB_TRACK' and o['layers'].get('B.Cu') and all(87.4 <= p[0] <= 89 and 39.6 <= p[1] <= 40 for p in (o['position_mm'], o['end_mm'])):
            keep.add(o['uuid'])
    assert len(keep) == 3
    source_pad=next(o for o in cap['objects'] if o.get('ref')=='J2003' and o.get('pin')=='4')
    assert source_pad['net']==SERIAL and source_pad['position_mm']==list(source) and source_pad['drill_mm']==[1.,1.]
    removed = {o['uuid'] for o in cap['objects'] if o['kind'] in ('PCB_TRACK', 'PCB_VIA') and (o['net'] == SERIAL and o['uuid'] not in keep)}
    restored = []
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
    seeds=[o['position_mm'] for record in (cap,old) for o in record['objects'] if o['kind']=='PCB_VIA' and o['net']==SERIAL]
    search = route(screen, SERIAL, [(f, source) for f in FACES], [(f, target) for f in FACES], time.monotonic()+420, via_candidates=seeds)
    proposal = search['route']
    selected = add(screen, SERIAL, proposal) if proposal else None
    old_length = sum(math.dist(o['position_mm'], o['end_mm']) for o in cap['objects'] if o['uuid'] in removed and o['kind'] == 'PCB_TRACK' and o['net'] == SERIAL)
    emitted = bool(selected and selected['planar_length_mm'] < old_length-1e-5)
    paths = [cp, op, pcb, original_pcb, Path(__file__)] + [ROOT/n for n in ('audit_candidate.py', 'digital_costed_region_route.py', 'digital_costed_region_route_v2.py', 'digital_costed_region_route_v3.py', 'digital_polygon_path.py', 'digital_region_reachability.py', 'digital_planned_region_screen.py', 'digital_via_spacing_close_margin.py', 'digital_via_spacing_v2.py', 'digital_xlat_escape_repair.py', 'digital_serial1_joint_repair.py', 'route_nf_surface.py', 'nf_minimum_logic.py', 'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py')] + [ROOT.parents[1]/'tests/tooling/test_digital_costed_region_route.py', ROOT.parents[1]/'tests/tooling/test_digital_costed_region_incumbents.py', ROOT.parents[1]/'tests/tooling/test_digital_costed_region_seeds.py', ROOT.parent/'electronics/common/sexpr.py']
    out = ROOT/'staging/digital-control30-costed-restoration-02'
    out.mkdir(exist_ok=False)
    result = dict(source_sha256={str(p): sha(p) for p in paths}, candidate_emitted=emitted, SERIAL1_current_native_copper_preserved=True,
        search=search, kept_control30_object_uuids=sorted(keep), removed_uuids=sorted(removed),
        restored_control_uuids=[o['uuid'] for o in restored], before_control30_trunk_length_mm=old_length,
        proposal=selected, native_rules_relaxed=False, electrical_performance_qualified=False, fabrication_released=False)
    if emitted:
        board = copy.deepcopy(before)
        retired = [n for tag in ('segment', 'via') for n in children(board, tag) if first(n, 'uuid')[1] in removed]
        assert len(retired) == len(removed)
        for n in retired:
            board.remove(n)
        restored_nodes = []
        assert {first(n, 'uuid')[1] for n in restored_nodes} == {o['uuid'] for o in restored}
        board.extend(restored_nodes)
        for face, path in selected['runs']:
            for p, q in zip(path, path[1:]):
                if math.dist(p, q) < 1e-7:
                    continue
                uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:CONTROL30-COSTED-02:{sha(cp)}:{face}:{p}:{q}'))
                board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), .2], [a('layer'), face], [a('net'), SERIAL], [a('uuid'), uid]])
        for p in selected['new_vias_mm']:
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:CONTROL30-COSTED-02-VIA:{sha(cp)}:{p}'))
            board.append([a('via'), [a('at'), *p], [a('size'), .6], [a('drill'), .3], [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), SERIAL], [a('uuid'), uid]])
        dest = out/pcb.name
        dest.write_text(sexpr(board)+'\n')
        result.update(candidate_PCB_sha256=sha(dest), geometry_delta=geometry_delta(before, board),
                      removed_objects=retired, restored_control_objects=restored_nodes, native_checks_pending=True)
    (out/'construction.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Costed restoration emitted:', emitted, 'CONTROL30 trunk', old_length, '->', selected['planar_length_mm'] if selected else None, flush=True)


if __name__ == '__main__':
    run()
