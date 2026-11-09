"""Remove a redundant source-via loop and a newly unused CONTROL30 branch.

All edits are made to S-expressions before native loading. The 16-track,
three-via CONTROL30 branch ends at the preserved (87.5,39.7) receiving via;
native pad-group verification must subsequently prove no lost connection.
"""
import copy
import json
import math
import uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha, geometry_delta
from hardware.fabrication.digital_serial1_joint_repair import ROOT, FACES, SERIAL
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

CONTROL_BRANCH = {
    '52ce26ee-337e-54d6-9fe1-c65205968188', '897ee0ba-b96d-5bdd-a199-4c5d409bb86b',
    'db2c1191-c948-5f0f-92eb-7ebce8a80417', 'bab55e59-71f4-58c3-b764-3f358c5309ea',
    '7e838d49-2971-54d2-a5cf-ea8cc48b8ea7', 'a17a4834-5809-5f1c-93d1-7004ae4f3aae',
    'd18a7b56-cee4-57a0-8d51-5ad1af942110', '58cf2d4c-093c-5144-9c31-d1c45ff36946',
    '223863e5-2a5a-58dd-8eba-824f8a4aa7e8', '51d93778-52bd-57c6-a7bc-d4c2251c448d',
    '2fcca3a5-039e-5097-b13d-23077a574782', 'e14ad693-05ac-5156-ae2a-5bfef8567353',
    'bdd4f9b7-9e3e-5cb1-9a15-349777c74f6f', '93545be2-620a-5e46-a342-b65362d8ddbd',
    'bb5eb11d-5d1b-51c1-8fa3-5f2abaafb6b5', '5f9bb711-0036-5d18-8d8a-65654893fb44',
    '373cac0f-3aca-532a-b4a4-7a085aed19c4', '47c159cf-a3f8-5e69-b4d2-76cf8791b4d4',
    'c20db915-15cb-5838-a6ad-d77fec29c030',
}


def run():
    rp = ROOT/'staging/digital-serial1-combined-restoration-07/construction.json'
    cp = ROOT/'staging/digital-serial1-source-preparation-inputs-31-02/capture.json'
    native = ROOT/'staging/digital-serial1-closed-native-02'
    recipe, cap = [json.loads(p.read_text()) for p in (rp, cp)]
    for record in (recipe, cap):
        assert all(sha(Path(p)) == h for p, h in record['source_sha256'].items())
    drc = json.loads((native/'drc.json').read_text())
    assert sorted(v['type'] for v in drc['violations']) == ['track_dangling', 'track_not_centered_on_via', 'track_not_centered_on_via']
    assert len(drc['unconnected_items']) == 30
    routes = copy.deepcopy(recipe['routes'])
    serial = next(r for r in routes if r['net'] == SERIAL and len(r['new_vias_mm']) == 1 and math.dist(r['new_vias_mm'][0], (44.1,14.65)) < 1e-7)
    redundant = serial['new_vias_mm'][0]
    # F.Cu continues to the second via at (44.64637,14.504573). The
    # first via adds no required transition and intersects the return path.
    serial['new_vias_mm'] = []
    removed = set(recipe['removed_uuids']) | CONTROL_BRANCH
    work = copy.deepcopy(cap)
    work['objects'] = [o for o in cap['objects'] if o['uuid'] not in removed and o.get('ref') != 'R3015'] + copy.deepcopy(recipe['component_move']['pads'])
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .001
    surface.SIGNAL_LAYERS = FACES
    screen = CloseMarginViaScreen(work, signal_layers=FACES)
    routes = [add(screen, r['net'], dict(runs=r['runs'], vias=r['new_vias_mm'])) for r in routes]
    parent = ROOT/'staging/digital-serial1-source-preparation-native-01/digital_core.kicad_pcb'
    before = read_sexpr(parent.read_text())
    board = copy.deepcopy(before)
    retired = [n for tag in ('segment', 'via') for n in children(board, tag) if first(n, 'uuid')[1] in removed]
    assert len(retired) == len(removed) == 34
    assert all(first(n, 'net')[1] == '/CONTROLS/CONTROL_30' for n in retired if first(n, 'uuid')[1] in CONTROL_BRANCH)
    assert sum(n[0] == 'via' for n in retired if first(n, 'uuid')[1] in CONTROL_BRANCH) == 3
    for n in retired:
        board.remove(n)
    fp = next(f for f in children(board, 'footprint') if any(p[1:3] == ['Reference', 'R3015'] for p in children(f, 'property')))
    first(fp, 'at')[1:3] = [75.25, 21.]
    assert fp == recipe['component_move']['footprint']
    for r in routes:
        for face, path in r['runs']:
            for p, q in zip(path, path[1:]):
                if math.dist(p, q) < 1e-7:
                    continue
                uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:SERIAL1-CLEAN:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), .2], [a('layer'), face], [a('net'), r['net']], [a('uuid'), uid]])
        for p in r['new_vias_mm']:
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:SERIAL1-CLEAN-VIA:{sha(cp)}:{r["net"]}:{p}'))
            board.append([a('via'), [a('at'), *p], [a('size'), .6], [a('drill'), .3], [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), r['net']], [a('uuid'), uid]])
    out = ROOT/'staging/digital-serial1-combined-restoration-08'
    out.mkdir(exist_ok=False)
    dest = out/parent.name
    dest.write_text(sexpr(board)+'\n')
    paths = [rp, cp, parent, native/'drc.json', native/'review.json', native/'digital_core.kicad_pcb', Path(__file__)] + [ROOT/n for n in ('audit_candidate.py', 'digital_serial1_joint_repair.py', 'digital_via_spacing_close_margin.py', 'digital_via_spacing_v2.py', 'digital_xlat_escape_repair.py', 'route_nf_surface.py', 'nf_minimum_logic.py', 'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py')] + [ROOT.parent/'electronics/common/sexpr.py']
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p): sha(p) for p in paths},
        candidate_PCB_sha256=sha(dest), candidate_emitted=True, component_move=recipe['component_move'],
        removed_uuids=sorted(removed), removed_objects=retired, routes=routes, geometry_delta=geometry_delta(before, board),
        removed_unused_control_branch=sorted(CONTROL_BRANCH), redundant_source_via_removed=redundant,
        native_checks_pending=True, expected_opens=30, native_rules_relaxed=False,
        electrical_performance_qualified=False, fabrication_released=False), indent=2)+'\n')
    print('Screened source-loop and unused-branch cleanup; native verification pending')


if __name__ == '__main__':
    run()
