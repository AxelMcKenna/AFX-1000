"""Retire the internal inlet cable pair and regroup the second buck locally."""
import copy
import json
import math
import shutil
from pathlib import Path

from shapely.affinity import rotate, translate
from shapely.geometry import Point
from shapely.strtree import STRtree

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.survey_two_board_buck_cells import BASE, CAP, footprints, xy
from hardware.fabrication.route_nf_surface import shape

SURVEY = STAGING/'two-board-buck-cell-survey-02/survey.json'
OUT = STAGING/'two-board-power-buck-cell-01'
RETIRED = {'I_J2', 'P_J101'}


def rotate_footprint(f, target, angle):
    f = copy.deepcopy(f)
    at = first(f, 'at'); old_angle = float(at[3]) if len(at)>3 else 0
    at[1:] = [*target, (old_angle+angle)%360]
    for node in f:
        if isinstance(node, list) and node and node[0] in ['pad', 'property', 'fp_text']:
            for at in children(node, 'at'):
                old_angle = float(at[3]) if len(at)>3 else 0
                at[3:] = [(old_angle+angle)%360]
    return f


def remove_port(sheet, ref, wanted):
    symbol = next(s for s in children(sheet, 'symbol') if prop(s, 'Reference')[2] == ref)
    assert first(symbol, 'at')[3] == '0'
    x, y = map(float, first(symbol, 'at')[1:3])
    lib = next(s for s in children(first(sheet, 'lib_symbols'), 'symbol') if s[1] == first(symbol, 'lib_id')[1])
    removed = [symbol]
    for unit in children(lib, 'symbol'):
        for pin in children(unit, 'pin'):
            number = str(first(pin, 'number')[1]); px, py = map(float, first(pin, 'at')[1:3])
            point = [x+px, y-py]
            wires = [w for w in children(sheet, 'wire') if any(math.dist(point, list(map(float, p[1:3])))<1e-6 for p in children(first(w, 'pts'), 'xy'))]
            assert len(wires) == 1
            wire = wires[0]; ends = [list(map(float, p[1:3])) for p in children(first(wire, 'pts'), 'xy')]
            other = next(p for p in ends if math.dist(point, p)>1e-6)
            labels = [l for l in children(sheet, 'global_label') if math.dist(other, list(map(float, first(l, 'at')[1:3])))<1e-6]
            assert len(labels) == 1 and labels[0][1] == wanted[number]
            # Port-local wires terminate at exactly one global label and have
            # no junction or branch. Native pin-partition verification follows.
            assert not any(math.dist(other, list(map(float, first(j, 'at')[1:3])))<1e-6 for j in children(sheet, 'junction'))
            assert sum(any(math.dist(other, list(map(float, p[1:3])))<1e-6 for p in children(first(w, 'pts'), 'xy')) for w in children(sheet, 'wire')) == 1
            removed.extend([wire, labels[0]])
    assert len(removed) == 5
    for node in removed:
        sheet.remove(node)
    return removed


def run():
    assert not OUT.exists()
    survey = json.loads(SURVEY.read_text()); cap = json.loads(CAP.read_text())
    for record in [survey, cap]:
        for name, h in record['source_sha256'].items():
            assert sha(REPO/name) == h, name
    parts, pins = read_netlist(BASE/'netlist.xml')
    assert all(pins[(r, p)] == n for r in RETIRED for p,n in [('1','PWR_DC_IN'),('2','PWR_AGND')])
    assert pins[('I_F1','2')] == pins[('P_Q101','1')] == 'PWR_DC_IN'
    assert pins[('I_J1','1')] != 'PWR_DC_IN', 'Keep the upstream inlet/fuse protection boundary'
    obj = {o['uuid']: o for o in cap['objects']}; prune = set()
    for o in obj.values():
        if o.get('ref') not in RETIRED or not o.get('group'):
            continue
        group = [obj[u] for u in cap['all_groups'][o['group']]]
        if o['ref'] == 'I_J2' and o['pin'] == '1':
            assert {(p['ref'],p['pin']) for p in group if p['kind']=='PAD'} == {('I_J2','1'),('I_F1','2')}
            assert all(p['kind'] in ['PAD','PCB_TRACK'] for p in group)
            prune.update(p['uuid'] for p in group if p['kind']=='PCB_TRACK')
        else:
            assert len(group) == 1
    assert len(prune) == 3
    current = footprints(BASE/'power_protection.kicad_pcb')
    cell = next(c for c in survey['cells'] if c['regulator']=='P_U23' and c['rotation_degrees']==90)
    moving = {r['ref'] for r in cell['members']}; angle = cell['rotation_degrees']
    stationary = [(o, layer, shape(ps)) for o in obj.values() if o.get('ref') not in moving|RETIRED and o['uuid'] not in prune
                  for layer,ps in o['layers'].items() if ps]
    trees = {}
    for layer in cap['copper_layers']:
        rows = [(o,g) for o,l,g in stationary if l==layer]
        trees[layer] = (rows, STRtree([g for o,g in rows]))
    holes = [(o['position_mm'], (max(o['drill_mm']) if isinstance(o['drill_mm'],list) else o['drill_mm'])/2)
             for o in obj.values() if o.get('ref') not in RETIRED and o.get('drill_mm') and
             (any(o['drill_mm']) if isinstance(o['drill_mm'],list) else o['drill_mm']>0)]
    chosen = None; failures = []
    for candidate in cell['best_candidates']:
        if set(candidate['blocking_owners']) - RETIRED:
            continue
        anchor = candidate['anchor_mm']; poses = {m['ref']: [round(anchor[i]+m['delta_mm'][i],6) for i in [0,1]] for m in cell['members']}
        issues = []; moved_polys = []
        for o in obj.values():
            if o.get('ref') not in moving:
                continue
            old = xy(current[o['ref']]); target = poses[o['ref']]
            for layer, ps in o['layers'].items():
                if not ps: continue
                g = translate(rotate(shape(ps), -angle, origin=old), target[0]-old[0], target[1]-old[1])
                rows, tree = trees[layer]
                for i in tree.query(g.buffer(.211)):
                    other, geom = rows[int(i)]
                    if other['net'] != o['net'] and g.distance(geom) < .21-1e-7:
                        issues.append(['foreign_copper',o['ref'],o['pin'],other['uuid']])
                if not shape(cap['outline']).buffer(-.5).covers(g):
                    issues.append(['edge',o['ref'],o['pin']])
                if any(g.distance(Point(p))-r < .15 for p,r in holes):
                    issues.append(['drill_to_SMD',o['ref'],o['pin']])
                moved_polys.append((o, layer, g))
        for i,(o,l,g) in enumerate(moved_polys):
            for p,m,h in moved_polys[:i]:
                if l==m and o['ref']!=p['ref'] and o['net']!=p['net'] and g.distance(h)<.21-1e-7:
                    issues.append(['internal_foreign_copper',o['ref'],p['ref']])
        if not issues:
            chosen = (candidate, poses); break
        failures.append(dict(candidate=candidate,issues=issues))
    assert chosen is not None, failures
    candidate, poses = chosen
    tree = read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    tree[:] = [n for n in tree if not (isinstance(n,list) and n and
              ((n[0]=='footprint' and prop(n,'Reference')[2] in RETIRED) or
               (n[0]=='segment' and first(n,'uuid')[1] in prune)))]
    for i,f in enumerate(tree):
        if isinstance(f,list) and f and f[0]=='footprint' and prop(f,'Reference')[2] in moving:
            tree[i] = rotate_footprint(f, poses[prop(f,'Reference')[2]], angle)
    source = STAGING/'two-board-power-integration-10'
    shutil.copytree(source, OUT)
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(tree)+'\n')
    deleted = {}
    for name,ref in [('I_rear_inlet.kicad_sch','I_J2'),('P_power_p03.kicad_sch','P_J101')]:
        path = OUT/name; sheet = read_sexpr(path.read_text())
        deleted[ref] = remove_port(sheet,ref,{'1':'PWR_DC_IN','2':'PWR_AGND'})
        path.write_text(sexpr(sheet)+'\n')
    for name in ['expected-circuit.json','symbol-paths.json']:
        path = OUT/name; data = json.loads(path.read_text())
        for ref in RETIRED: del data[ref]
        path.write_text(json.dumps(data,indent=2)+'\n')
    path = OUT/'power_protection.kicad_sch'; root = read_sexpr(path.read_text())
    first(first(root,'title_block'),'rev')[1] = 'TBP11'
    for text in children(root,'text'):
        if 'original power/protection components and connectors remain' in text[1]:
            text[1] = 'TBP11: inlet and source share copper; retired internal cable connectors I_J2/P_J101.'
    path.write_text(sexpr(root)+'\n')
    paths = [Path(__file__),SURVEY,CAP,BASE/'power_protection.kicad_pcb',BASE/'netlist.xml',
             STAGING/'two-board-power-interface-audit-01/interface-review.json',
             REPO/'hardware/fabrication/survey_two_board_buck_cells.py',
             REPO/'hardware/fabrication/route_nf_surface.py',
             *[p for p in source.rglob('*') if p.is_file()]]
    record = dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        retired_connector_refs=sorted(RETIRED), retired_stub_segment_uuids=sorted(prune),
        retired_schematic_nodes=deleted, retained_fuse_output='I_F1.2', retained_supply_input='P_Q101.1',
        removed_only_parallel_internal_cable_terminals=True, unchanged_remaining_schematic_nets_pending_native_check=True,
        selected_candidate=candidate, cell_rotation_degrees=angle,
        poses=[dict(ref=r,old_xy=xy(current[r]),new_xy=poses[r],rotation_added_degrees=angle) for r in sorted(moving)],
        rejected_candidates=failures, predicted_opens=2551,
        open_count_reduction_is_terminal_retirement_not_new_routes=True,
        existing_copper_unchanged_except_retired_inlet_stub=True, new_copper_added=False,
        native_validation_pending=True, full_regulator_power_loop_qualified=False,
        first_buck_and_other_critical_cells_still_require_regrouping=True, fabrication_released=False)
    (OUT/'buck-cell-change.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(candidate=candidate,moved=len(moving),retired=sorted(RETIRED),pruned=len(prune))))


if __name__ == '__main__':
    run()
