"""TBP10: represent the second, internally common OUT terminal as passive.

Both physical OUT pins remain connected. Pin 23 declares the one power driver;
pin 24 is a parallel terminal of that same driver, not an independent source.
"""
import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def adjust(node):
    count = 0
    if isinstance(node, list):
        if node and node[0] == 'pin' and children(node, 'number') and first(node, 'number')[1] == '24':
            assert first(node, 'name')[1] == 'OUT' and node[1] == 'power_out'
            node[1] = a('passive')
            count += 1
        else:
            for item in node:
                count += adjust(item)
    return count


def build():
    source = STAGING/'two-board-power-integration-09'
    out = STAGING/'two-board-power-integration-10'
    assert not out.exists()
    shutil.copytree(source, out)
    names = ['G_module_input.kicad_sch', 'symbols/RMX_TBP09.kicad_sym',
             'module-cell-timed/module_input.kicad_sch', 'module-cell-timed/RMX_TBP09.kicad_sym']
    for name in names:
        p = out/name
        tree = read_sexpr(p.read_text())
        assert adjust(tree) == 1, name
        p.write_text(sexpr(tree)+'\n')
    p = out/'module-cell-timed/components.json'
    data = json.loads(p.read_text())
    u1 = next(c for c in data if c['ref'] == 'U1')
    pin = next(p for p in u1['pins'] if p['number'] == '24')
    assert pin['kind'] == 'power_out'
    pin['kind'] = 'passive'
    p.write_text(json.dumps(data, indent=2)+'\n')
    p = out/'power_protection.kicad_sch'
    root = read_sexpr(p.read_text())
    first(first(root, 'title_block'), 'rev')[1] = 'TBP10'
    p.write_text(sexpr(root)+'\n')
    record = json.loads((out/'construction.json').read_text())
    record.update(revision='TBP10', correction='Parallel OUT pin 24 passive; pin 23 retains power_out. No connectivity or PCB change.',
        source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),
            STAGING/'two-board-power-native-09/erc.json', *[p for p in source.rglob('*') if p.is_file()]]})
    (out/'construction.json').write_text(json.dumps(record,indent=2)+'\n')
    print('TBP10 prepared; parallel output pin typing corrected')


if __name__ == '__main__':
    build()
