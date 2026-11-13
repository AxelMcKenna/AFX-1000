"""Screen the removable assembly tool against every other selected role."""
import copy
import json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w

HERE = Path(__file__).resolve().parent
TOOLS = w.ROOT / 'hardware/cad/two_board_installation_06/r30_touch_mount_tools'

def run():
    previous = HERE / 'previous-manifest.json'
    if not previous.exists():
        previous.write_bytes((w.HERE / 'current.json').read_bytes())
    data, parts, _, registries = w.load_manifest(previous)
    evidence = json.loads((TOOLS / 'verification.json').read_text())
    w.assert_current({'sources': evidence['source_sha256']})
    parts = copy.deepcopy(parts)
    original = sorted(parts)
    # The worst-case tip reaches 3.55; its corresponding nut bottom is 3.55.
    # Nominal nuts instead start at3.2. Mixing these two poses creates a false
    # overlap. The separately verified nominal tool/hardware pair is retained.
    excluded = ['panel_touch_hardware_r26']
    assert all(name in parts for name in excluded)
    parts['touch_nut_tool_access_r30'] = dict(
        id='touch_nut_tool_access_r30', source=w.relative(TOOLS / 'tools.scad'),
        module='touch_nut_tool_access', role='motion', scene=False,
        description='Removable nut insertion tool receiving sweep; not installed hardware')
    bindings = dict(data['_loaded_sources'])
    for p in [Path(__file__), TOOLS / 'tools.scad', TOOLS / 'verification.json']:
        w.merge_sources(bindings, {w.relative(p): w.sha(p)})
    registry = dict(schema_version=1, components=list(parts.values()), source_sha256=bindings,
                    intentional_contacts=sum((r['intentional_contacts'] for r in data['contracts']), []))
    (HERE / 'registry.json').write_text(json.dumps(registry, indent=2)+'\n')
    others = [name for name in original if name not in excluded]
    assert len(others) == 76 and len(set(others)) == len(others)
    checks = [dict(id=f'touch_tool_external_{i//8+1}', left=['touch_nut_tool_access_r30'],
                   right=others[i:i+8], expect='empty') for i in range(0,len(others),8)]
    candidate = {k:v for k,v in data.items() if not k.startswith('_') and k != 'contracts'}
    candidate.update(registries=[w.relative(HERE/'registry.json')], checks=checks)
    (HERE/'candidate.json').write_text(json.dumps(candidate,indent=2)+'\n')
    (HERE/'scope.json').write_text(json.dumps(dict(original_roles=original,screened_roles=others,
        excluded_nominal_own_hardware=excluded,installed_selection_changed=False,
        underside_fixture_clearance_required_mm=40,hand_access_qualified=False,
        tolerance_bearing_contact_qualified=False),indent=2)+'\n')
    print(f'Prepared {len(checks)} checks covering {len(others)} external roles')

if __name__ == '__main__':
    run()
