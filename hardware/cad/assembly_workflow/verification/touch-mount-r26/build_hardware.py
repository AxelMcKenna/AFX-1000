"""Integrate candidate touch fasteners without dropping main-board head reservations."""
import copy
import json
import os
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w

HERE = Path(__file__).resolve().parent

def run():
    data, parts, _, _ = w.load_manifest(HERE / 'candidate.json')
    parts = copy.deepcopy(parts)
    base = w.ROOT / parts['base_board_heads']['source']
    text = base.read_text()
    old = ' for(m=touch_mounts)translate([m[0],m[1],21.6])cylinder(d=4.5,h=2.5);'
    assert text.count(old) == 1
    text = text.replace(old, '').replace('module base_board_heads()', 'module base_main_board_heads_r26()')
    for relative in ['../two_board_print_01/captured.scad', '../two_board_print_01/housing.scad']:
        text = text.replace('<' + relative + '>', '<' + os.path.relpath(base.parent / relative, HERE) + '>')
    adapter = HERE / 'main-heads.scad'
    adapter.write_text(text)
    parts['base_board_heads'].update(source=w.relative(adapter), module='base_main_board_heads_r26')
    mount_path = w.ROOT / 'hardware/cad/two_board_installation_06/workflow_adapter/touch-mount-registry.json'
    mount = json.loads(mount_path.read_text())
    for part in mount['components']:
        assert part['id'] not in parts
        parts[part['id']] = part
    probe = mount['additional_clearance_probe']
    parts['touch_upper_probe_r26'] = dict(id='touch_upper_probe_r26', source=probe['source'], module=probe['module'],
                                        role='receiving', description='Diagnostic only enlarged upper fastener envelope')
    bindings = dict(data['_loaded_sources'])
    for p in [Path(__file__), adapter, base, mount_path]:
        bindings[w.relative(p)] = w.sha(p)
    registry = {'schema_version': 1, 'components': list(parts.values()), 'source_sha256': bindings,
                'intentional_contacts': sum((r['intentional_contacts'] for r in data['contracts']), [])}
    (HERE / 'hardware-registry.json').write_text(json.dumps(registry, indent=2) + '\n')
    candidate = json.loads((HERE / 'candidate.json').read_text())
    candidate['registries'] = [w.relative(HERE / 'hardware-registry.json')]
    others = sorted(set(parts) - {'cooling_shell', 'panel_touch_c3_r25', 'panel_touch_hardware_r26', 'touch_upper_probe_r26'})
    for role in ['panel_touch_hardware_r26', 'touch_upper_probe_r26']:
        candidate['checks'].append(dict(id=role + '_assembly', left=[role], right=others, expect='empty'))
    candidate['unresolved'] = [x for x in candidate['unresolved'] if not x.startswith('Shell-only r26 diagnostic:')]
    candidate['unresolved'].append('Unselected r26 hardware candidate: full shell/touch seating witnesses, physical fastener/print/assembly qualification remain required. Upper probe is diagnostic, not installed material.')
    (HERE / 'hardware-candidate.json').write_text(json.dumps(candidate, indent=2) + '\n')
    w.load_manifest(HERE / 'hardware-candidate.json')

if __name__ == '__main__':
    run()
