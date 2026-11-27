"""Inventory source-bound delivery files without staging unrelated workspace data."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / 'hardware/fabrication/staging'
OUT = STAGING / 'two-board-delivery-closure-01'


def main():
    assert not OUT.exists()
    candidate = STAGING / 'two-board-power-aux-cap-ground-native-01'
    pending = list(candidate.rglob('*')) + [Path(__file__)]
    seen, missing, mismatches = {}, [], []

    def local(value):
        if not isinstance(value, str):
            return None
        if value.startswith('hardware/'):
            return ROOT / value
        if '/hardware/' in value and value.startswith('/'):
            return ROOT / ('hardware/' + value.split('/hardware/', 1)[1])
        return None

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                p = local(key)
                if p and isinstance(item, str) and len(item) == 64 and all(c in '0123456789abcdef' for c in item):
                    if not p.is_file():
                        missing.append(str(p.relative_to(ROOT)))
                    else:
                        actual = hashlib.sha256(p.read_bytes()).hexdigest()
                        if actual != item:
                            mismatches.append(dict(path=str(p.relative_to(ROOT)), expected=item, actual=actual))
                        pending.append(p)
                walk(key)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str):
            p = local(value)
            if p and p.is_file():
                pending.append(p)

    while pending:
        path = pending.pop().resolve()
        if not path.is_file() or path in seen:
            continue
        raw = path.read_bytes()
        seen[path] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        if path.suffix == '.json':
            try:
                walk(json.loads(raw))
            except ValueError:
                pass
        elif path.suffix == '.py':
            for node in ast.walk(ast.parse(raw)):
                names = []
                if isinstance(node, ast.Import):
                    names = [n.name for n in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    names = [node.module]
                for name in names:
                    if name.startswith('hardware.'):
                        p = ROOT / (name.replace('.', '/') + '.py')
                        if p.is_file():
                            pending.append(p)
    tracked = set(subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines())
    rows = {str(p.relative_to(ROOT)): dict(v, tracked=str(p.relative_to(ROOT)) in tracked) for p, v in sorted(seen.items())}
    result = dict(candidate=str(candidate.relative_to(ROOT)), files=rows,
                  missing_bound_files=sorted(set(missing)), hash_mismatches=mismatches,
                  file_count=len(rows), total_bytes=sum(v['bytes'] for v in rows.values()),
                  untracked_count=sum(not v['tracked'] for v in rows.values()),
                  scope='Recursive SHA-bound evidence, explicit hardware file references and static absolute Python imports. Dynamic imports, external tools and full fresh-checkout execution remain separate checks.',
                  complete_reproducibility_verified=False)
    OUT.mkdir()
    (OUT / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'files'}, indent=2))


if __name__ == '__main__':
    main()
