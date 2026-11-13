"""Verify the immutable r83 gate using only this checkout, without rewriting evidence."""
import argparse
import copy
import traceback
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
TRANSITION_OVERRIDE = None
RECORDED_ROOT = Path('/private/tmp/rmx-lever-sensor-20261112')

def local_path(value):
    path = Path(value)
    if path.is_absolute() and path.is_relative_to(RECORDED_ROOT):
        path = ROOT / path.relative_to(RECORDED_ROOT)
    if path.is_absolute() and not path.resolve().is_relative_to(ROOT):
        raise AssertionError(('external dependency rejected', str(path)))
    return path

class LocalPath(type(Path())):
    def __init__(self, *args):
        path = Path(*args)
        if path.is_absolute() and path.is_relative_to(RECORDED_ROOT):
            path = ROOT / path.relative_to(RECORDED_ROOT)
        super().__init__(path)

    def read_bytes(self):
        return local_path(self).read_bytes()

    def read_text(self, *args, **kwargs):
        if TRANSITION_OVERRIDE is not None and self == HERE / 'transitions-r83.json':
            return json.dumps(TRANSITION_OVERRIDE)
        return local_path(self).read_text(*args, **kwargs)

    def write_text(self, data, *args, **kwargs):
        assert TRANSITION_OVERRIDE is None, 'mutation unexpectedly reached output'
        assert self in [HERE / 'final-review-r83.json', HERE / 'reference-review-r83.json', HERE / 'replacement-audit-r83.json'], ('unexpected write', self)
        assert json.loads(data) == json.loads(Path(self).read_text()), 'frozen gate result changed'
        return len(data)

def execute(source):
    tree = ast.parse(source.read_text(), filename=str(source))
    imports = [node for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == 'pathlib']
    assert len(imports) == 1 and [(a.name, a.asname) for a in imports[0].names] == [('Path', None)]
    tree.body.remove(imports[0])
    exec(compile(tree, str(source), 'exec'), {'Path': LocalPath, '__file__': str(source), '__name__': '__portable_gate__'})

def regression_checks():
    global TRANSITION_OVERRIDE
    original = json.loads((HERE / 'transitions-r83.json').read_text())
    routing = json.loads((HERE / 'candidate-r83/routing.json').read_text())
    uid = routing['vias'][-1]['uuid']
    bridge_uid=next(v['uuid']for v in routing['vias']if v.get('role')=='intermediate_layer_transition')
    for case, uid, expected_line in [('missing',uid,'unverified excluded transition'),('wrong-net',uid,"v['signal_net']==o['net']"),('missing-bridge',bridge_uid,'unverified excluded transition')]:
        data = copy.deepcopy(original)
        if case.startswith('missing'):
            data['transitions'] = [row for row in data['transitions'] if row['signal_uuid'] != uid]
        else:
            next(row for row in data['transitions'] if row['signal_uuid'] == uid)['signal_net'] = '/wrong-net'
        TRANSITION_OVERRIDE = data
        try:
            execute(HERE / 'review_r83.py')
        except AssertionError as error:
            final = traceback.extract_tb(error.__traceback__)[-1]
            assert Path(final.filename) == HERE / 'review_r83.py'
            line = (HERE / 'review_r83.py').read_text().splitlines()[final.lineno - 1]
            assert expected_line in line, ('failure occurred before intended identity check', case, line)
        else:
            raise AssertionError(('identity mutation accepted', case))
        finally:
            TRANSITION_OVERRIDE = None
    print('Three portable transition identity regressions passed at the intended assertions')

def main(reference=False, regressions=False):
    frozen = json.loads((HERE / 'final-review-r83.json').read_text())
    for name, digest in frozen['source_sha256'].items():
        assert not Path(name).is_absolute()
        path = local_path(ROOT / name)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, ('stale local source', name)
    execute(HERE / 'replacement_audit_r83.py')
    execute(HERE / 'final_review_r83.py')
    if reference:
        execute(HERE / 'review_r83.py')
    if regressions:
        regression_checks()
    print('Portable verification passed; frozen evidence unchanged; all dependencies read from', ROOT)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', action='store_true', help='Recompute the full frozen reference audit')
    parser.add_argument('--regressions', action='store_true', help='Run exact-point fail-closed identity regressions')
    args = parser.parse_args()
    main(args.reference, args.regressions)
