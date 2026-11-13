"""Capture the exact D101 rigid move while retaining cumulative R303/R308."""
import copy
import json
import math
from pathlib import Path
from shapely.geometry import Polygon, box
from hardware.cad.assembly_workflow import workflow as w
from hardware.cad.two_board_installation_06.workflow_adapter import pcb_freshness as bridge
from hardware.cad.assembly_workflow.pcb_updates.r44.build import boxes

H = Path(__file__).resolve().parent
SIGNAL = 'hardware/cad/two_board_sensor_05/signal_dac/native-r125/signal_main.kicad_pcb'


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def physical_signature(physical, rotation=0):
    """Permit child serialization order and exact native absolute-angle transport."""
    physical = copy.deepcopy(physical)
    for child in physical[2:]:
        if isinstance(child, list) and child[0] in ['pad', 'fp_text']:
            at = next(x for x in child if isinstance(x, list) and x[0] == 'at')
            angle = float(at[3]) if len(at) == 4 else 0
            at[3:] = [f'{(angle + rotation) % 360:g}']
    return physical[:2], sorted(json.dumps(x, sort_keys=True) for x in physical[2:])


def run():
    previous = H / 'previous-manifest.json'
    if not previous.exists():
        previous.write_bytes((w.HERE / 'current.json').read_bytes())
    data, parts, checks, _ = w.load_manifest(previous)
    old_board = bridge.snapshot(w.ROOT / data['boards']['signal'])
    new_board = bridge.snapshot(w.ROOT / SIGNAL)
    delta = bridge.compare(old_board, new_board)
    assert [(d.get('ref'), d['field']) for d in delta] == [('A_D101', 'pose'), ('A_D101', 'physical')], delta
    before = old_board['footprints']['A_D101']
    after = new_board['footprints']['A_D101']
    assert before['pose'] == [75., 66., 0, 'B.Cu']
    assert after['pose'] == [75.8, 65.2, 90., 'B.Cu']
    assert physical_signature(before['physical'], 90) == physical_signature(after['physical'])
    parent = w.ROOT / data['mechanical_capture']
    old = json.loads(parent.read_text())
    new = copy.deepcopy(old)
    moved = []
    for field in ['component_envelopes', 'tail_envelopes']:
        for row in new[field]:
            if row[0] != 'A_D101':
                continue
            x0, y0, x1, y1 = row[1]
            corners = [(75.8 + y - 66, 65.2 - (x - 75)) for x in [x0, x1] for y in [y0, y1]]
            row[1] = [round(min(x for x, y in corners), 9), round(min(y for x, y in corners), 9),
                      round(max(x for x, y in corners), 9), round(max(y for x, y in corners), 9)]
            assert math.isclose(row[1][2] - row[1][0], y1 - y0, abs_tol=1e-9)
            assert math.isclose(row[1][3] - row[1][1], x1 - x0, abs_tol=1e-9)
            moved.append(row)
    assert moved == [['A_D101', [74.1, 63.27, 77.5, 67.13], [4.05, 6.95]]]
    for field in ['component_envelopes', 'tail_envelopes']:
        assert [r for r in old[field] if r[0] != 'A_D101'] == [r for r in new[field] if r[0] != 'A_D101']
    for path in list(new['source_sha256']):
        if path.endswith('/signal_main.kicad_pcb'):
            del new['source_sha256'][path]
    for path in [w.ROOT / SIGNAL, parent, Path(__file__)]:
        new['source_sha256'][w.relative(path)] = w.sha(path)
    new['mechanical_update'] = dict(parent_capture=w.relative(parent), parent_mechanical_update=old['mechanical_update'],
        exact_incremental_footprint_difference=delta, rigid_rotation_native_degrees=90,
        before_pose=before['pose'], after_pose=after['pose'], other_physical_fields_and_envelopes_unchanged=True,
        physical_serialization_note='FP child order changes only; pad and user-text absolute angles advance exactly90degrees. All other child data identical.')
    save(H / 'capture.json', new)
    excluded = set(json.loads((w.HERE / 'base.json').read_text())['replaced_allocations'])
    rows = [r for r in new['component_envelopes'] + new['tail_envelopes'] if r[0] not in excluded]
    (H / 'allocations.scad').write_text(boxes('base_component_allocations', rows))
    (H / 'probes.scad').write_text(boxes('r125_moved_body', moved) + boxes('r125_other_allocations', [r for r in rows if r[0] != 'A_D101']))
    bindings = dict(data['_loaded_sources'])
    for path in [H / 'capture.json', H / 'allocations.scad', Path(__file__), previous]:
        w.merge_sources(bindings, {w.relative(path): w.sha(path)})
    parts['base_component_allocations']['source'] = w.relative(H / 'allocations.scad')
    save(H / 'registry.json', dict(schema_version=1, components=list(parts.values()), source_sha256=bindings,
         intentional_contacts=sum((r['intentional_contacts'] for r in data['contracts']), [])))
    selection = json.loads(previous.read_text())
    selection['registries'] = [w.relative(H / 'registry.json')]
    selection['boards']['signal'] = SIGNAL
    selection['mechanical_capture'] = w.relative(H / 'capture.json')
    save(H / 'selection.json', selection)
    save(H / 'probe-registry.json', dict(schema_version=1,
        components=[dict(id=n, source=w.relative(H / 'probes.scad'), module=n, role='receiving') for n in ['r125_moved_body', 'r125_other_allocations']],
        source_sha256={w.relative(H / 'probes.scad'): w.sha(H / 'probes.scad')}))
    candidate = copy.deepcopy(selection)
    candidate['registries'].append(w.relative(H / 'probe-registry.json'))
    external = [n for n in parts if n not in ['base_component_allocations', 'base_main_pcbs']]
    candidate['checks'].append(dict(id='r125_body_other_parts', left=['r125_moved_body'], right=external + ['r125_other_allocations'], expect='empty'))
    save(H / 'candidate.json', candidate)
    fresh = bridge.run(w.ROOT, selection['boards'], selection['mechanical_capture'])
    assert fresh['geometry_fresh'], fresh['errors']
    save(H / 'freshness.json', fresh)
    power = next(b for b in new['boards'] if b['id'] == 'power')
    area = Polygon(power['outline']).intersection(box(*moved[0][1])).area
    assert area == 0
    save(H / 'body-proof.json', dict(exact_delta=delta, body=moved[0], power_board_xy_intersection_mm2=area,
         own_signal_substrate_contact_expected=True, prior_roles=len(parts), prior_checks=len(checks),
         diagnostic_external_roles=external, full_housing_fit_qualified=False, fabrication_released=False))
    print(f'Exact D101 rigid capture; R303/R308 retained; {len(checks)} prior checks plus moved-body check')


if __name__ == '__main__':
    run()
