"""One assembly registry and content-addressed native clearance workflow."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
from collections import Counter
from datetime import datetime, timezone
import re
import subprocess
import sys
import uuid
from pathlib import Path

from hardware.cad.a12.enclosure_growth.r1_local.linux_runner.openscad import IMAGE, DOCKER, command
from hardware.cad.a12.thermal.enlarged_base.verify import mesh

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CACHE = HERE / 'cache'
SCHEMA = 1


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def relative(path):
    return str(path.resolve().relative_to(ROOT))


def source_closure(path, found=None):
    found = {} if found is None else found
    path = path.resolve()
    key = relative(path)
    if key in found:
        return found
    found[key] = sha(path)
    for dep in re.findall(r'(?:include|use)\s*<([^>]+)>', path.read_text()):
        source_closure(path.parent / dep, found)
    return found


def load_manifest(path=HERE / 'current.json'):
    raw = path.read_bytes()
    data = json.loads(raw)
    loaded_sources = {relative(path): hashlib.sha256(raw).hexdigest()}
    assert data['schema_version'] == SCHEMA
    components = {}
    registries = {}
    public_modules = {}
    contracts = []
    for name in data['registries']:
        p = ROOT / name
        registry_raw = p.read_bytes()
        registry = json.loads(registry_raw)
        registries[name] = hashlib.sha256(registry_raw).hexdigest()
        loaded_sources[name] = registries[name]
        for field in ('source_sha256', 'sources_sha256'):
            for dependency, expected in registry.get(field, {}).items():
                assert sha(ROOT / dependency) == expected, ('Registry source drift', dependency)
                if dependency in loaded_sources:
                    assert loaded_sources[dependency] == expected, ('Conflicting source snapshots', dependency)
                loaded_sources[dependency] = expected
        contracts.append(dict(registry=name, intentional_contacts=registry.get('intentional_contacts', []), unmodeled_installed_items=registry.get('unmodeled_installed_items', [])))
        for item in registry['components']:
            ident = item['id']
            assert re.fullmatch(r'[a-z][a-z0-9_]*', ident), ident
            assert ident not in components, ('duplicate component', ident)
            assert re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', item['module']), item
            assert item['role'] in ('installed', 'motion', 'receiving'), item
            previous = public_modules.setdefault(item['module'], item['source'])
            assert previous == item['source'], ('Duplicate public module name', item['module'])
            source_closure(ROOT / item['source'])
            components[ident] = item
    checks = {}
    for check in data['checks']:
        assert check['id'] not in checks
        assert check['expect'] == 'empty', 'Contacts require a separately scoped geometric check'
        assert check['left'] and check['right']
        assert not set(check['left']) & set(check['right']), check['id']
        assert set(check['left'] + check['right']) <= components.keys(), check['id']
        checks[check['id']] = check
    data = dict(data, contracts=contracts, _loaded_sources=loaded_sources)
    return data, components, checks, registries


def scad(components, left, right=None, source_root=None):
    source_root = ROOT if source_root is None else source_root
    selected = sorted(set(left + (right or [])))
    sources = sorted({components[i]['source'] for i in selected})
    # Includes are resolved from the generated job folder; paths remain local.
    lines = ['$fn=64;', *[f'use <{source_root / s}>' for s in sources]]
    def body(ids):
        return 'union(){' + ''.join(components[i]['module'] + '();' for i in ids) + '}'
    lines.append(body(left) if right is None else 'intersection(){' + body(left) + body(right) + '}')
    return '\n'.join(lines) + '\n'


def job(kind, definition, components):
    ids = [definition['id']] if kind == 'component' else definition['left'] + definition['right']
    inputs = {}
    for ident in ids:
        source_closure(ROOT / components[ident]['source'], inputs)
    # Runtime/mesh logic are part of the cache identity, not merely geometry.
    for module in [Path(__file__), ROOT / 'hardware/cad/a12/enclosure_growth/r1_local/linux_runner/openscad.py',
                   ROOT / 'hardware/cad/a12/thermal/enlarged_base/verify.py']:
        inputs[relative(module)] = sha(module)
    geometry_definition = {k:definition[k] for k in (('id', 'source', 'module') if kind == 'component' else ('id', 'left', 'right', 'expect'))}
    identity = dict(schema=SCHEMA, kind=kind, definition=geometry_definition,
                    components={i:{k:components[i][k] for k in ('source', 'module')} for i in sorted(set(ids))},
                    sources=inputs, image=IMAGE, backend='Manifold', facets=64)
    key = digest(identity)
    return identity, CACHE / kind / key


def cached(identity, folder):
    result = folder / 'result.json'
    if not result.exists():
        if folder.exists():
            raise RuntimeError(f'Incomplete job preserved at {folder}; inspect its running.json/log before retrying')
        return None
    data = json.loads(result.read_text())
    assert data['identity'] == identity, 'Cache identity mismatch'
    for name, expected in data['artifacts'].items():
        assert (folder / name).resolve().is_relative_to(CACHE.resolve()), 'Artifact outside cache'
        assert sha(folder / name) == expected, ('Corrupt cached artifact', folder / name)
    if data['runtime_failure']:
        raise RuntimeError(f'Failed job preserved at {folder}; fix the cause before a new source-keyed run')
    return data


def assert_current(identity):
    drift = [p for p, h in identity["sources"].items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
    if drift:
        raise RuntimeError("Source snapshot changed: " + ", ".join(drift))



def boundary_balance(path):
    """Distinguish open surfaces from closed multi-part contact boundaries."""
    raw = path.read_bytes()
    edges = Counter()
    for i in range(struct.unpack_from('<I', raw, 80)[0]):
        row = struct.unpack_from('<12fH', raw, 84 + 50*i)
        a, b, c = (tuple(row[j:j+3]) for j in (3, 6, 9))
        if a == b or b == c or c == a:
            continue
        for x, y in ((a,b),(b,c),(c,a)):
            edges[x,y] += 1
    return dict(balanced_oriented_boundary=bool(edges) and all(edges[y,x] == count for (x,y),count in edges.items()),
                maximum_edge_multiplicity=max(edges.values(), default=0))


def execute(kind, definition, components, timeout=60, expected=None):
    identity, folder = job(kind, definition, components)
    if expected is not None and identity != expected:
        raise RuntimeError('Source snapshot changed before native job')
    previous = cached(identity, folder)
    if previous is not None:
        assert_current(identity)
        return previous, True
    folder.parent.mkdir(parents=True, exist_ok=True)
    folder.mkdir()  # Exclusive ownership: a concurrent job must not overwrite it.
    name = 'afx-assembly-' + uuid.uuid4().hex[:12]
    (folder / 'running.json').write_text(json.dumps(dict(identity=identity, status='running', pid=os.getpid(), container=name, started=datetime.now(timezone.utc).isoformat()), indent=2))
    source = folder / 'geometry.scad'
    operands = []
    if kind == 'check':
        imported = {}
        direct = {}
        direct_sources = {}
        for ident in sorted(set(definition['left'] + definition['right'])):
            component_identity, component_folder = job('component', components[ident], components)
            operand = cached(component_identity, component_folder)
            assert operand is not None and operand['passed'], ('Missing verified operand', ident)
            assert_current(component_identity)
            if operand['mesh']['closed_oriented_boundary']:
                imported[ident] = component_folder / 'geometry.stl'
                operands.append(imported[ident])
            else:
                # Multi-part assemblies can share balanced contact edges. Never feed
                # those non-manifold STL boundaries back into a Boolean operation.
                direct[ident] = components[ident]
                direct_sources[ident] = component_folder / 'sources' / components[ident]['source']
                operands.append(component_folder / 'geometry.stl')
        def solid(ids):
            return 'union(){' + ''.join(('import(' + json.dumps(str(imported[i])) + ');') if i in imported else direct[i]['module'] + '();' for i in ids) + '}'
        uses = ['$fn=64;'] + [f'use <{p}>' for p in direct_sources.values()]
        source.write_text('\n'.join(uses) + '\nintersection(){' + solid(definition['left']) + solid(definition['right']) + '}\n')
    else:
        for path, expected_hash in identity['sources'].items():
            if not path.endswith('.scad'):
                continue
            raw = (ROOT / path).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == expected_hash, ('Source changed before snapshot', path)
            for dep in re.findall(r'(?:include|use)\s*<([^>]+)>', raw.decode()):
                assert not Path(dep).is_absolute(), 'Snapshot requires repository-relative SCAD dependencies'
            frozen = folder / 'sources' / path
            frozen.parent.mkdir(parents=True, exist_ok=True)
            frozen.write_bytes(raw)
            operands.append(frozen)
        source.write_text(scad(components, [definition['id']], source_root=folder / 'sources'))
    target = folder / 'geometry.stl'
    args = command(['--hardwarnings', '--backend=Manifold', '--export-format=binstl', '-o', str(target), str(source)])
    args[2:2] = ['--name', name, '--memory', '2g', '--cpus', '2']
    failure, timed_out, returncode = False, False, None
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        returncode = proc.returncode
        log = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as error:
        stopped = subprocess.run([DOCKER, 'rm', '-f', name], capture_output=True, text=True, timeout=10)
        log = f'Timeout after {timeout}s; container stop rc={stopped.returncode}\n{stopped.stdout}{stopped.stderr}'
        for value in (error.stdout, error.stderr):
            if value:
                log += value.decode(errors='replace') if isinstance(value, bytes) else value
        failure, timed_out = True, True
    except OSError as error:
        failure = True
        log = 'Native launch failed: ' + repr(error)
    (folder / 'native.log').write_text(log)
    empty = 'Current top level object is empty.' in log
    failure |= returncode not in (0, 1) or any(x in log for x in ('WARNING:', 'ERROR:', 'Segmentation fault', 'Abort trap'))
    failure |= returncode == 1 and not empty
    # Never certify a result generated while its source tree changed.
    drift = [p for p, h in identity['sources'].items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
    failure |= bool(drift)
    shape = None
    if target.exists() and not failure:
        try:
            shape = mesh(target)
            shape.update(boundary_balance(target))
        except (AssertionError, ValueError) as error:
            failure = True
            log += '\nInvalid mesh: ' + str(error)
            (folder / 'native.log').write_text(log)
    passed = not failure and ((empty and shape is None) if kind == 'check' else
                             (not empty and shape is not None and shape['volume_mm3'] > 0 and shape['balanced_oriented_boundary']))
    files = [source, folder / 'native.log'] + ([target] if target.exists() else [])
    data = dict(identity=identity, passed=passed, runtime_failure=bool(failure), timeout=timed_out,
                source_drift=drift, empty=empty, mesh=shape, container=name,
                artifacts={os.path.relpath(p, folder):sha(p) for p in files + operands}, fabrication_released=False)
    (folder / 'result.json').write_text(json.dumps(data, indent=2) + '\n')
    (folder / 'running.json').unlink()
    return data, False


def plan(components, checks):
    rows = []
    for name, check in checks.items():
        ident, folder = job('check', check, components)
        result = cached(ident, folder)
        rows.append(dict(id=name, state='pending' if result is None else ('passed' if result['passed'] else 'interference'),
                         components=sorted(set(check['left'] + check['right'])), cache=relative(folder)))
    return rows


def scene(components, path, reservations=False, motion=False):
    roles = {'installed'} | ({'receiving'} if reservations else set()) | ({'motion'} if motion else set())
    selected = {i:c for i,c in components.items() if c['role'] in roles and (c['role'] != 'installed' or c.get('scene', True))}
    text = ['$fn=64;'] + [f'use <{ROOT / s}>' for s in sorted({c['source'] for c in selected.values()})]
    for ident, c in selected.items():
        alpha = 1 if c['role'] == 'installed' else .25
        color = c.get('color', [.65, .7, .75])
        text += [f'// {ident}: {c["role"]}', f'color({json.dumps(color + [alpha])}) {c["module"]}();']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(text) + '\n')
    return dict(path=str(path), components=list(selected), roles=sorted(roles))




def board_state(manifest):
    from hardware.cad.two_board_installation_06.workflow_adapter import pcb_freshness
    pointer = CACHE / 'boards/latest.json'
    if pointer.exists():
        previous = json.loads(pointer.read_text())
        if previous['selected_pcbs'] == manifest['boards'] and all((ROOT / p).is_file() and sha(ROOT / p) == h for p, h in previous['source_sha256'].items()):
            return previous
    result = pcb_freshness.run(ROOT, manifest['boards'], 'hardware/cad/two_board_print_01/capture.json')
    for path, expected in result['source_sha256'].items():
        assert sha(ROOT / path) == expected, ('PCB source changed during comparison', path)
    folder = CACHE / 'boards'
    folder.mkdir(parents=True, exist_ok=True)
    frozen = folder / (result['freshness_key'] + '.json')
    if frozen.exists():
        assert json.loads(frozen.read_text()) == result, 'Freshness-key collision or altered cache'
    else:
        frozen.write_text(json.dumps(result, indent=2) + '\n')
    temp = folder / ('latest-' + uuid.uuid4().hex + '.json')
    temp.write_text(json.dumps(result, indent=2) + '\n')
    temp.replace(pointer)
    return result


def recover(job_path, reason):
    """Archive a terminal runtime failure after explicit diagnosis; never rerun it."""
    folder = (CACHE / job_path).resolve()
    assert folder.is_relative_to(CACHE.resolve()) and folder.parent.name in ('component', 'check')
    result_path = folder / 'result.json'
    if result_path.exists():
        result = json.loads(result_path.read_text())
        assert result['runtime_failure'], 'A valid geometry result is not a runtime recovery target'
        container = result.get('container')
        assert container, 'Missing container ownership; inspect this job manually'
        probe = subprocess.run([DOCKER, 'inspect', '--format', '{{.State.Running}}', container], capture_output=True, text=True, timeout=10)
        assert (probe.returncode == 0 and probe.stdout.strip() == 'false') or (probe.returncode != 0 and 'No such' in probe.stderr), 'Container termination not established'
    else:
        running = json.loads((folder / 'running.json').read_text())
        pid = running.get('pid')
        assert isinstance(pid, int), 'Unknown process ownership; inspect this job manually'
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise RuntimeError('Owning process is still live; do not archive its job')
        probe = subprocess.run([DOCKER, 'inspect', '--format', '{{.State.Running}}', running['container']], capture_output=True, text=True, timeout=10)
        if probe.returncode == 0:
            assert probe.stdout.strip() == 'false', 'CAD container remains live'
        else:
            assert 'No such' in probe.stderr, 'Cannot establish container termination'
    archive = CACHE / 'failed' / (folder.parent.name + '-' + folder.name + '-' + uuid.uuid4().hex[:8])
    archive.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(folder), str(archive))
    (archive / 'recovery.json').write_text(json.dumps(dict(reason=reason, archived_at=datetime.now(timezone.utc).isoformat(), automatically_retried=False), indent=2) + '\n')
    return dict(archived=relative(archive), reason=reason, automatically_retried=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'plan', 'check', 'export', 'scene', 'recover'])
    parser.add_argument('--only', nargs='+', help='Check IDs, or component IDs for export')
    parser.add_argument('--reservations', action='store_true')
    parser.add_argument('--motion', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--job', help='Failed cache job, e.g. component/<hash>')
    parser.add_argument('--reason', help='Diagnosis recorded when archiving a failed job')
    args = parser.parse_args()
    if args.action == 'recover':
        assert args.job and args.reason
        print(json.dumps(recover(args.job, args.reason), indent=2))
        return
    data, components, checks, registries = load_manifest()
    boards = board_state(data)
    batch_sources = dict(data['_loaded_sources'])
    for path, expected in boards['source_sha256'].items():
        if path in batch_sources and batch_sources[path] != expected:
            raise RuntimeError('Source snapshot changed during board comparison: ' + path)
        batch_sources[path] = expected
    assert_current({'sources': batch_sources})
    if args.action not in ('status', 'plan') and not boards['geometry_fresh']:
        raise RuntimeError('KiCad mechanical changes require updating the assembly capture; run status for differences')
    if args.action == 'scene':
        print(json.dumps(scene(components, args.output or HERE / 'generated/assembly.scad', args.reservations, args.motion), indent=2))
        return
    if args.action in ('status', 'plan'):
        print(json.dumps(dict(components=len(components), checks=plan(components, checks),
                             boards=boards, unresolved=data['unresolved'], contracts=data['contracts'], component_roles={i:c['role'] for i,c in components.items()}, fabrication_released=False), indent=2))
        return
    policy = json.loads((ROOT / 'hardware/validation/board-qualification/NATIVE-CAD-STOP.json').read_text())
    assert policy['isolated_Linux_restart_authorized_by_user'] and policy['allowed_isolated_image'] == IMAGE
    selected = args.only or list(checks if args.action == 'check' else components)
    assert set(selected) <= (checks.keys() if args.action == 'check' else components.keys())
    rows = []
    batch_identities = []
    for ident in selected:
        required = [ident] if args.action == 'export' else sorted(set(checks[ident]['left'] + checks[ident]['right']))
        check_identity = job('check', checks[ident], components)[0] if args.action == 'check' else None
        component_identities = {c:job('component', components[c], components)[0] for c in required}
        if check_identity is not None:
            assert_current(check_identity)
            batch_identities.append(check_identity)
        for component in required:
            result, reused = execute('component', components[component], components, expected=component_identities[component])
            batch_identities.append(component_identities[component])
            if not result['passed']:
                raise RuntimeError(f'Component {component} is empty/invalid; inspect {job("component", components[component], components)[1]}')
            print(f'component {component}: ' + ('cached' if reused else 'exported'), flush=True)
        if args.action == 'check':
            for component_identity in component_identities.values():
                assert_current(component_identity)
            result, reused = execute('check', checks[ident], components, expected=check_identity)
            rows.append(dict(check=ident, passed=result['passed'], cached=reused))
            print(f'check {ident}: ' + ('PASS' if result['passed'] else 'FAIL') + (' cached' if reused else ''), flush=True)
            if result['runtime_failure']:
                raise RuntimeError(f'Native job failed for {ident}; no automatic retry')
    for identity in batch_identities:
        assert_current(identity)
    assert_current({'sources': batch_sources})
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        assert not args.output.exists(), 'Fresh evidence output required'
        args.output.write_text(json.dumps(dict(results=rows, registries=registries, snapshot_sha256=batch_sources, board_freshness_key=boards['freshness_key'], fabrication_released=False), indent=2) + '\n')
    if any(not row['passed'] for row in rows):
        raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, RuntimeError, FileNotFoundError, ValueError) as error:
        print('Assembly workflow stopped: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
