"""Verify the immutable r26 gate using only this checkout, without rewriting evidence."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
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
        return local_path(self).read_text(*args, **kwargs)

    def write_text(self, data, *args, **kwargs):
        assert self == HERE / 'final-review.json', ('unexpected write', self)
        assert json.loads(data) == json.loads(Path(self).read_text()), 'frozen gate result changed'
        return len(data)

def main():
    frozen = json.loads((HERE / 'final-review.json').read_text())
    for name, digest in frozen['source_sha256'].items():
        assert not Path(name).is_absolute()
        path = local_path(ROOT / name)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, ('stale local source', name)
    source = HERE / 'final_review.py'
    tree = ast.parse(source.read_text(), filename=str(source))
    imports = [node for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == 'pathlib']
    assert len(imports) == 1 and [(a.name, a.asname) for a in imports[0].names] == [('Path', None)]
    tree.body.remove(imports[0])
    exec(compile(tree, str(source), 'exec'), {'Path': LocalPath, '__file__': str(source), '__name__': '__portable_gate__'})
    print('Portable verification passed; frozen evidence unchanged; all dependencies read from', ROOT)

if __name__ == '__main__':
    main()
