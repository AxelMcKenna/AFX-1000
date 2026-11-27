"""Adopt the ground-chain terminal assignment without changing panel circuitry."""
import csv
import hashlib
import json
import shutil
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
BASE = HERE.parent / 'panel_electrical'
GROUND = REPO / 'hardware/cad/two_board_installation_06/r12_ground/ground-routes.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    output = HERE / 'assembly'
    assert not output.exists()
    ground = json.loads(GROUND.read_text())
    assert all(sha(REPO / p) == h for p, h in ground['source_sha256'].items())
    manifest = json.loads((BASE / 'assembly-manifest.json').read_text())
    mapping = {c['note'].split(';')[0]: c['ref'] for c in manifest['components'] if c['part'] == 'B3F-1000'}
    assert len(mapping) == 29
    contacts = {}
    for edge in ground['edges']:
        for own, other in ((edge['from'], edge['to']), (edge['to'], edge['from'])):
            assert own not in contacts
            contacts[own] = other
    def label(endpoint):
        name, pin = endpoint.split(':')
        return mapping[name.removeprefix('button_')] + '.' + pin if name.startswith('button_') else endpoint
    rows = []
    for name, reference in mapping.items():
        endpoint = 'button_' + name
        incoming = contacts[endpoint + ':3']
        outgoing = contacts.get(endpoint + ':4')
        rows.append(dict(reference=reference, control=name, signal_terminal='1',
                         unused_signal_duplicate='2', ground_in_terminal='3',
                         ground_in_from=label(incoming), ground_out_terminal='4',
                         ground_out_to=label(outgoing) if outgoing else 'UNWIRED'))
    assert sum(r['ground_out_to'] == 'UNWIRED' for r in rows) == 4
    shutil.copytree(BASE / 'assembly', output)
    switch_path = output / 'switches/panel.kicad_sch'
    sch = read_sexpr(switch_path.read_text())
    note, = children(sch, 'text')
    assert str(note[1]).endswith('wire1 and3 only')
    first(note, 'at')[2] = 24
    note[1] = 'GROUND AMENDMENT: 1=signal; 2=unwired; 3=ground in; 4=chain out where noted. Internal 1-2 and 3-4 pairs; press bridges pairs. Routes are not fabrication released.'
    symbols = {next(p[2] for p in children(s, 'property') if p[1] == 'Reference'): s
               for s in children(sch, 'symbol')}
    annotations = {}
    for row in rows:
        symbol = symbols[row['reference']]
        x, y = map(float, first(symbol, 'at')[1:3])
        text = f"{row['reference']}: 3 <- {row['ground_in_from']}; 4 -> {row['ground_out_to']}"
        ident = str(uuid.uuid5(uuid.NAMESPACE_URL, 'AFX:panel-ground-amendment:' + row['reference']))
        sch.append([a('text'), text, [a('at'), x - 23, y + 18, 0],
                    [a('effects'), [a('font'), [a('size'), 1, 1]], [a('justify'), a('left')]],
                    [a('uuid'), ident]])
        annotations[ident] = text
    switch_path.write_text(sexpr(sch) + '\n')
    with (HERE / 'terminal-schedule.csv').open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    sources = [Path(__file__), GROUND, BASE / 'assembly-manifest.json',
               BASE / 'assembly-native-r3/netlist.xml', *sorted((BASE / 'assembly').rglob('*'))]
    sources = [p for p in sources if p.is_file()]
    record = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                  artifact_sha256={str(p.relative_to(HERE)): sha(p) for p in output.rglob('*') if p.is_file()},
                  annotations=annotations, terminal_schedule=rows,
                  circuit_change=False, physical_route_adopted=False,
                  supersedes='Only the panel electrical drawing instruction to leave every terminal 4 unwired',
                  native_validation_pending=True, fabrication_released=False)
    record['artifact_sha256']['terminal-schedule.csv'] = sha(HERE / 'terminal-schedule.csv')
    (HERE / 'amendment.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Annotated 29 switches; 25 outgoing ground contacts and four unwired chain ends')


if __name__ == '__main__':
    run()
