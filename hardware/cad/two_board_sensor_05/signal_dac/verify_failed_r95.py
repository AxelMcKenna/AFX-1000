"""Verify the immutable r95 gate using only this checkout, without rewriting evidence."""
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
        if TRANSITION_OVERRIDE is not None and self == HERE / 'transitions-r95.json':
            return json.dumps(TRANSITION_OVERRIDE)
        return local_path(self).read_text(*args, **kwargs)

    def write_text(self, data, *args, **kwargs):
        assert TRANSITION_OVERRIDE is None, 'mutation unexpectedly reached output'
        assert self in [HERE / 'failed-checkpoint-r95.json', HERE / 'reference-review-r95.json', HERE / 'replacement-audit-r95.json'], ('unexpected write', self)
        assert json.loads(data) == json.loads(Path(self).read_text()), 'frozen gate result changed'
        return len(data)

def execute(source):
    tree = ast.parse(source.read_text(), filename=str(source))
    imports = [node for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == 'pathlib']
    assert len(imports) == 1 and [(a.name, a.asname) for a in imports[0].names] == [('Path', None)]
    tree.body.remove(imports[0])
    exec(compile(tree, str(source), 'exec'), {'Path': LocalPath, '__file__': str(source), '__name__': '__portable_gate__'})

def main(reference=False):
 frozen=json.loads((HERE/'failed-checkpoint-r95.json').read_text())
 assert frozen['accepted'] is False and frozen['selected_checkpoint_remains']=='r89'
 for name,digest in frozen['source_sha256'].items():
  assert not Path(name).is_absolute()
  assert hashlib.sha256(local_path(ROOT/name).read_bytes()).hexdigest()==digest,('stale source',name)
 execute(HERE/'replacement_audit_r95.py');execute(HERE/'failure_review_r95.py')
 if reference:
  try:execute(HERE/'review_r95.py')
  except AssertionError as error:
   final=traceback.extract_tb(error.__traceback__)[-1];assert Path(final.filename)==HERE/'review_r95.py'
   line=(HERE/'review_r95.py').read_text().splitlines()[final.lineno-1];assert "all(v['unexplained_uncovered_mm2']<1e-6 for v in newrefs)"in line
  else:raise AssertionError('rejected reference candidate unexpectedly accepted')
 print('Rejected checkpoint verified locally; no evidence rewritten; r89 remains selected')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--reference',action='store_true');args=parser.parse_args();main(args.reference)
