"""Source-bound full-shell candidate; does not change selected assembly."""
import copy
import json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w

HERE = Path(__file__).resolve().parent

def run():
    parent = HERE.parent / 'fan-touch-r24-r25/candidate.json'
    data, components, _, _ = w.load_manifest(parent)
    mount_path = w.ROOT / 'hardware/cad/two_board_installation_06/workflow_adapter/touch-mount-registry.json'
    mount = json.loads(mount_path.read_text())
    shell = components['cooling_shell']
    adapter = HERE / 'shell.scad'
    import os
    sources = [shell['source'], mount['required_shell_revision']['source']]
    adapter.write_text('\n'.join('use <' + os.path.relpath(w.ROOT / s, HERE) + '>' for s in sources) +
                       '\nmodule cooling_shell_r26(){difference(){' + shell['module'] + '();panel_touch_nut_cuts_r26();}}\n')
    parts = copy.deepcopy(components)
    parts['cooling_shell'] = dict(shell, source=w.relative(adapter), module='cooling_shell_r26',
                                 uncertainty='Candidate two-pocket revision; exact hardware and physical tolerances remain unqualified')
    bindings = dict(data['_loaded_sources'])
    bindings[w.relative(mount_path)] = w.sha(mount_path)
    for path, expected in mount['source_sha256'].items():
        assert w.sha(w.ROOT / path) == expected, path
        assert path not in bindings or bindings[path] == expected, path
        bindings[path] = expected
    for p in [Path(__file__), adapter]:
        bindings[w.relative(p)] = w.sha(p)
    registry = {'schema_version': 1, 'components': list(parts.values()), 'source_sha256': bindings,
                'intentional_contacts': sum((r['intentional_contacts'] for r in data['contracts']), [])}
    (HERE / 'registry.json').write_text(json.dumps(registry, indent=2) + '\n')
    candidate = json.loads(parent.read_text())
    candidate['registries'] = [w.relative(HERE / 'registry.json')]
    candidate['unresolved'].append('Shell-only r26 diagnostic: original touch head proxies remain; do not promote until exact hardware replacement and full assembly checks complete.')
    (HERE / 'candidate.json').write_text(json.dumps(candidate, indent=2) + '\n')
    w.load_manifest(HERE / 'candidate.json')

if __name__ == '__main__':
    run()
