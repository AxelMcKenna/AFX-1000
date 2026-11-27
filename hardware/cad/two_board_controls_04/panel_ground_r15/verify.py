"""Native panel parity and independent ground terminal-amendment checks."""
import argparse
import copy
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from .build import HERE, REPO, BASE, GROUND, sha


def validate(rows, ground, manifest):
    controls = {c['ref']: c['note'].split(';')[0] for c in manifest['components'] if c['part'] == 'B3F-1000'}
    assert len(rows) == len(controls) == 29
    assert {r['reference'] for r in rows} == set(controls)
    outgoing = {}
    for r in rows:
        assert r['control'] == controls[r['reference']]
        direction = next(x for x in ground['button_order_and_contact_directions'] if x['button'] == r['control'])
        assert (r['signal_terminal'], r['unused_signal_duplicate']) == ('1', '2')
        assert r['ground_in_terminal'] == direction['incoming_terminal']
        assert r['ground_out_terminal'] == str(7 - int(r['ground_in_terminal']))
        for own, target in ((r['reference'] + '.' + r['ground_in_terminal'], r['ground_in_from']), (r['reference'] + '.' + r['ground_out_terminal'], r['ground_out_to'])):
            if target != 'UNWIRED':
                outgoing[own] = target
    def endpoint(p):
        name, pin = p.split(':')
        if name.startswith('button_'):
            ref, = [ref for ref, control in controls.items() if control == name[7:]]
            return ref + '.' + pin
        return p
    expected = {}
    for edge in ground['external_wires']:
        for a, b in ((edge['from'], edge['to']), (edge['to'], edge['from'])):
            if a.startswith('button_'):
                expected[endpoint(a)] = endpoint(b)
    assert outgoing == expected, 'Drawing terminals differ from the harness topology'


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--strict-native', action='store_true')
    args = parser.parse_args()
    out = HERE / ('native' if args.native else 'native-strict')
    if args.native or args.strict_native:
        assert sys.platform == 'linux' and not out.exists()
        out.mkdir()
        sch = HERE / 'assembly/panel.kicad_sch'
        if args.strict_native:
            shutil.copytree(HERE / 'assembly', out / 'assembly')
            sch = out / 'assembly/panel.kicad_sch'
            project = sch.with_suffix('.kicad_pro')
            settings = json.loads(project.read_text())
            rules = settings.setdefault('erc', {}).setdefault('rule_severities', {})
            for key in ('single_global_label', 'four_way_junction', 'simulation_model_issue', 'footprint_filter'):
                rules[key] = 'error'
            project.write_text(json.dumps(settings, indent=2) + '\n')
            # The deeper isolated review copy must retain its original libraries.
            table_path = sch.parent / 'fp-lib-table'
            table = read_sexpr(table_path.read_text())
            for lib in children(table, 'lib'):
                uri = first(lib, 'uri')
                path = (HERE / 'assembly' / str(uri[1]).removeprefix('${KIPRJMOD}/')).resolve()
                uri[1] = '${KIPRJMOD}/' + os.path.relpath(path, sch.parent)
            table_path.write_text(sexpr(table) + '\n')
        commands = [('erc', ['erc', '--severity-all', '--format', 'json', '--exit-code-violations', '-o', str(out / 'erc.json'), str(sch)]),
                    ('netlist', ['export', 'netlist', '--format', 'kicadxml', '-o', str(out / 'netlist.xml'), str(sch)])]
        for name, command in commands:
            p = subprocess.run(['kicad-cli', 'sch', *command], capture_output=True, text=True, timeout=120)
            (out / (name + '.log')).write_text(p.stdout + p.stderr)
            assert p.returncode == 0, (name, p.stdout, p.stderr)
        return
    record = json.loads((HERE / 'amendment.json').read_text())
    for field, base in (('source_sha256', REPO), ('artifact_sha256', HERE)):
        assert all(sha(base / p) == h for p, h in record[field].items())
    manifest = json.loads((BASE / 'assembly-manifest.json').read_text())
    ground = json.loads(GROUND.read_text())
    assert all(sha(REPO / p) == h for p, h in ground['source_sha256'].items())
    validate(record['terminal_schedule'], ground, manifest)
    with (HERE / 'wire-schedule.csv').open(newline='') as f:
        assert list(csv.DictReader(f)) == ground['external_wires']
    with (HERE / 'terminal-schedule.csv').open(newline='') as f:
        assert list(csv.DictReader(f)) == record['terminal_schedule']
    bad = copy.deepcopy(record['terminal_schedule'])
    bad[0]['ground_out_to'] = 'UNWIRED' if bad[0]['ground_out_to'] != 'UNWIRED' else 'SW900.3'
    try:
        validate(bad, ground, manifest)
    except AssertionError:
        mutation = 'rejected'
    else:
        raise AssertionError('Incorrect outgoing terminal accepted')
    reversed_direction = copy.deepcopy(record['terminal_schedule'])
    reversed_direction[0]['ground_in_terminal'] = '4'
    reversed_direction[0]['ground_out_terminal'] = '3'
    try:
        validate(reversed_direction, ground, manifest)
    except AssertionError:
        direction_mutation = 'rejected'
    else:
        raise AssertionError('Incorrect terminal direction accepted')
    old = read_sexpr((BASE / 'assembly/switches/panel.kicad_sch').read_text())
    new = read_sexpr((HERE / 'assembly/switches/panel.kicad_sch').read_text())
    strip = lambda t: [n for n in t if not (isinstance(n, list) and n and n[0] == 'text')]
    assert strip(old) == strip(new)
    assert len(children(old, 'text')) == 1 and len(children(new, 'text')) == 30
    notes = {str(first(n, 'uuid')[1]): str(n[1]) for n in children(new, 'text')}
    assert all(notes[u] == text for u, text in record['annotations'].items())
    for path in (BASE / 'assembly').rglob('*'):
        if path.is_file() and path.relative_to(BASE / 'assembly').as_posix() != 'switches/panel.kicad_sch':
            assert path.read_bytes() == (HERE / 'assembly' / path.relative_to(BASE / 'assembly')).read_bytes()
    parts0, pins0 = netlist(BASE / 'assembly-native-r3/netlist.xml')
    parts1, pins1 = netlist(out / 'netlist.xml')
    assert pins0 == pins1 and parts0.keys() == parts1.keys()
    for ref in parts0:
        assert all(parts0[ref].findtext(k) == parts1[ref].findtext(k) for k in ('value', 'footprint', 'datasheet'))
    erc = json.loads((out / 'erc.json').read_text())
    assert not erc['ignored_checks'] and not any(s.get('violations') for s in erc['sheets'])
    sources = [Path(__file__), HERE / 'build.py', HERE / 'amendment.json', GROUND,
               BASE / 'assembly-native-r3/netlist.xml', out / 'netlist.xml', out / 'erc.json']
    sources.extend(p for p in (out / 'assembly').rglob('*') if p.is_file())
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                  components=len(parts1), erc_errors=0, erc_warnings=0,
                  native_panel_pin_nets_unchanged=True, annotation_only_schematic_change=True,
                  all_native_erc_checks_enabled=True,
                  switches_amended=29, outgoing_ground_contacts=28, unwired_ground_contact_count=1,
                  wrong_outgoing_terminal_mutation=mutation, wrong_terminal_direction_mutation=direction_mutation,
                  full_wire_schedule_matches_32_ground_paths=True,
                  ground_topology_adopted=True, physical_route_qualified=False, fabrication_released=False)
    target = HERE / 'verification.json'
    assert not target.exists()
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}))


if __name__ == '__main__':
    run()
