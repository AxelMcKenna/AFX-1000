"""Integrate the sourced nominal full stacks without dropping selected geometry."""
import copy
import importlib
import json
import re
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
from hardware.electronics.common import sexpr as sx
from hardware.fabrication import assembly_layout as al

H = Path(__file__).resolve().parent
SOURCE = H.parent / 'main-fasteners-r1'


def save(name, value):
    (H / name).write_text(json.dumps(value, indent=2) + '\n')


def run():
    previous = H / 'previous-manifest.json'
    if not previous.exists():
        previous.write_bytes((w.HERE / 'current.json').read_bytes())
    data, parts, checks, _ = w.load_manifest(previous)
    _, hardware, _, _ = w.load_manifest(SOURCE / 'candidate.json')
    budget = json.loads((SOURCE / 'budget.json').read_text())
    contacts = json.loads((SOURCE / 'contact-review.json').read_text())
    for proof in [budget, contacts]:
        w.assert_current({'sources': proof['source_sha256']})
    assert len(contacts['results']) == 2
    assert all(r['all_retained_vertices_on_expected_seat_planes'] and len(r['mounts_with_retained_seat_mesh']) == 22 for r in contacts['results'])
    for role in ['base_main_pcbs', 'cooling_shell']:
        assert w.job('component', parts[role], parts)[0] == w.job('component', hardware[role], hardware)[0], ('Changed own-seat geometry', role)
    old = copy.deepcopy(parts)
    parts['base_board_heads'] = copy.deepcopy(hardware['base_board_heads'])
    parts['base_board_heads']['description'] = 'Sourced nominal22full main-board screw/washer/nut stacks; physical receiving and underhead mating remain unqualified'
    receiving = 'main_fastener_receiving_r1'
    assert receiving not in parts
    parts[receiving] = copy.deepcopy(hardware[receiving])
    assert all(parts[k] == v for k, v in old.items() if k != 'base_board_heads')
    assert w.job('component', parts['base_board_heads'], parts)[0] == w.job('component', hardware['base_board_heads'], hardware)[0]
    # Recompute conductive contact against the exact selected boards, guarding
    # every NPTH exception before the conservative copper screen.
    copper = importlib.import_module('hardware.cad.assembly_workflow.verification.main-fasteners-r1.copper_screen')
    guard = importlib.import_module('hardware.cad.assembly_workflow.verification.main-fasteners-r1.npth_guard')
    captured = w.ROOT / 'hardware/cad/two_board_print_01/captured.scad'
    mounts = json.loads(re.search(r'^mounts = (.*);', captured.read_text(), re.M).group(1))
    mounts = [m for m in mounts if m[0] not in ['D_H2', 'D_H5']]
    ownership, audit = {}, {}
    for board, path in data['boards'].items():
        pcb = w.ROOT / path
        tree, _ = al.outline(pcb)
        ownership[board] = {str(next(q[2] for q in sx.children(f, 'property') if q[1] == 'Reference')) for f in sx.children(tree, 'footprint')}
        selected = [m for m in mounts if m[0] in ownership[board]]
        count = guard.audit(pcb)
        audit[board] = copper.audit(pcb, selected)
        assert not audit[board]['hits'], board
        audit[board]['npth_pads_proved_drill_only'] = count
    assert len(mounts) == 22 and all(sum(m[0] in refs for refs in ownership.values()) == 1 for m in mounts)
    save('copper-review.json', dict(boards=audit, all22mounts_clear=True, physical_insulation_qualified=False,
        source_sha256={w.relative(p): w.sha(p) for p in [Path(copper.__file__), Path(guard.__file__), captured] + [w.ROOT / p for p in data['boards'].values()]}))
    bindings = dict(data['_loaded_sources'])
    for proof in [budget, contacts]:
        w.merge_sources(bindings, proof['source_sha256'])
    for path in [Path(__file__), SOURCE / 'parts.scad', SOURCE / 'budget.json', SOURCE / 'contact-review.json', H / 'copper-review.json']:
        w.merge_sources(bindings, {w.relative(path): w.sha(path)})
    intentional = sum((r['intentional_contacts'] for r in data['contracts']), [])
    intentional += [dict(components=['base_board_heads', 'base_main_pcbs'], reason='22nominal washer bearing planes retained separately; not an empty-contact claim'),
                    dict(components=['base_board_heads', 'cooling_shell'], reason='22nominal nut/pocket-roof planes retained separately; no external collision waiver')]
    save('registry.json', dict(schema_version=1, components=list(parts.values()), source_sha256=bindings, intentional_contacts=intentional,
        unmodeled_installed_items=sum((r['unmodeled_installed_items'] for r in data['contracts']), [])))
    excluded = ['base_board_heads', 'base_main_pcbs', 'cooling_shell']
    external = sorted(k for k in old if k not in excluded)
    extra = [dict(id=f'main_stack_r2_external_{i // 8 + 1}', left=[receiving], right=external[i:i + 8], expect='empty') for i in range(0, len(external), 8)]
    candidate = json.loads(previous.read_text())
    candidate['registries'] = [w.relative(H / 'registry.json')]
    candidate['checks'].extend(extra)
    candidate['unresolved'].append('Full22main-board nominal screw/washer/nut stacks are modeled under explicit receiving requirements. Underhead fillet/washer mating, screw length/tip conformity, washer registration, nut bearing, torque/creep, printed strength, tools and loaded feet clearance remain unqualified. Bare-board H_NEW5 uses12mm; the unselected cradle needs its separate14mm stack.')
    save('candidate.json', candidate)
    save('scope.json', dict(prior_roles=len(old), prior_checks=len(checks), all_prior_checks_unchanged=True,
        sole_replacement='base_board_heads', added_role=receiving, external_roles=external, excluded_own_roles=excluded,
        exclusion_evidence=w.relative(SOURCE / 'contact-review.json'), same_own_seat_geometry=True,
        new_checks=[c['id'] for c in extra], physical_qualified=False))
    _, p, c, _ = w.load_manifest(H / 'candidate.json')
    assert len(p) == len(old) + 1 and len(c) == len(checks) + len(extra)
    print(f'Prepared {len(p)} roles / {len(c)} checks;22mount copper regions clear; own44seat planes retained')


if __name__ == '__main__':
    run()
