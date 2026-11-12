"""Check simultaneous addon fit using pinned native geometry and frozen hashes."""
import hashlib
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path

from hardware.cad.a12.enclosure_growth.r1_local.linux_runner.openscad import command, IMAGE, DOCKER
from hardware.cad.a12.thermal.enlarged_base.verify import mesh

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
CASES = ['sensor_selectors', 'lever_selectors', 'display_selectors',
         'new_controls_cooling', 'sensor_revised_lid', 'spring_new_controls', 'spring_cooling', 'population_latest_controls', 'population_cooling_r7']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tag = sys.argv[1]
    assert re.fullmatch(r'[a-zA-Z0-9_-]+', tag)
    out = ROOT / tag
    assert not out.exists()
    policy = json.loads((REPO / 'hardware/validation/board-qualification/NATIVE-CAD-STOP.json').read_text())
    assert policy['isolated_Linux_restart_authorized_by_user'] and policy['allowed_isolated_image'] == IMAGE
    assert not (ROOT / 'NATIVE-FAILED.json').exists()
    sources = {}

    def bind(path):
        path = path.resolve()
        key = str(path.relative_to(REPO))
        if key in sources:
            return
        sources[key] = digest(path)
        for dependency in re.findall(r'(?:include|use)\s*<([^>]+)>', path.read_text()):
            bind(path.parent / dependency)

    bind(ROOT / 'assembly_population.scad')
    sources[str(Path(__file__).relative_to(REPO))] = digest(Path(__file__))
    out.mkdir()
    rows = []
    for case in CASES:
        folder = out / case
        folder.mkdir()
        target = folder / (case + '.stl')
        args = command(['--hardwarnings', '--backend=Manifold', '--export-format=binstl',
                        '-D', 'part=' + json.dumps(case), '-o', str(target), str(ROOT / 'assembly_population.scad')])
        name = 'afx-tbh07-' + uuid.uuid4().hex[:12]
        args[2:2] = ['--name', name, '--memory', '2g', '--cpus', '2']
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            subprocess.run([DOCKER, 'rm', '-f', name], capture_output=True, timeout=10)
            (ROOT / 'NATIVE-FAILED.json').write_text(json.dumps(dict(case=case, reason='timeout')))
            raise
        log = proc.stdout + proc.stderr
        (folder / 'native.log').write_text(log)
        empty = 'Current top level object is empty.' in log
        fatal = (proc.returncode not in (0, 1) or
                 any(t in log for t in ['WARNING:', 'ERROR:', 'Segmentation fault', 'Abort trap']) or
                 (proc.returncode == 1 and not empty))
        row = dict(case=case, empty=empty, returncode=proc.returncode, runtime_failure=fatal,
                   mesh=mesh(target) if target.exists() else None)
        (folder / 'result.json').write_text(json.dumps(row, indent=2) + '\n')
        rows.append(row)
        if fatal:
            (ROOT / 'NATIVE-FAILED.json').write_text(json.dumps(row, indent=2))
            raise RuntimeError(log)
        print(case, 'empty' if empty else 'INTERFERENCE', flush=True)
    for path, expected in sources.items():
        assert digest(REPO / path) == expected, ('Source changed during check', path)
    result = dict(source_sha256=sources, image=IMAGE, cases=rows,
                  all_empty=all(r['empty'] and r['mesh'] is None for r in rows),
                  scope='Simultaneous candidate addon geometry including cooling r7 and spring sweep; includes populated sensor PCB envelopes; excludes complete harness, LED carriers and thermal/electrical qualification.',
                  complete_installed_fit=False, fabrication_released=False)
    (out / 'review.json').write_text(json.dumps(result, indent=2) + '\n')
    assert result['all_empty'], 'Inspect recorded interference meshes before integration'


if __name__ == '__main__':
    main()
