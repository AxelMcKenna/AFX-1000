"""Partition the failed full union without dropping any role or changing geometry."""
import json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
HERE = Path(__file__).resolve().parent

def run():
    path = HERE / 'hardware-candidate.json'
    data = json.loads(path.read_text())
    original = [q for q in data['checks'] if q['id'] in ['panel_touch_hardware_r26_assembly', 'touch_upper_probe_r26_assembly']]
    assert len(original) == 2
    data['checks'] = [q for q in data['checks'] if q not in original]
    coverage = []
    for check in original:
        groups = [check['right'][i:i+8] for i in range(0,len(check['right']),8)]
        assert sum(groups, []) == check['right']
        ids = []
        for number, group in enumerate(groups):
            ident = check['id'] + '_group_' + str(number+1)
            data['checks'].append(dict(check, id=ident, right=group))
            ids.append(ident)
        coverage.append(dict(original=check, replacement_checks=ids, exact_operand_partition=True))
    (HERE / 'hardware-split-candidate.json').write_text(json.dumps(data,indent=2)+'\n')
    (HERE / 'split-coverage.json').write_text(json.dumps(dict(coverage=coverage,
        source_sha256={w.relative(path):w.sha(path),w.relative(Path(__file__)):w.sha(Path(__file__))},
        reason='Full union native process failed with empty native log; exit code was not retained by that runner. Original failure preserved. Limit each union to eight roles without reducing comparison coverage.'),indent=2)+'\n')
    w.load_manifest(HERE / 'hardware-split-candidate.json')
    print(' '.join(i for c in coverage for i in c['replacement_checks']))
if __name__ == '__main__':run()
