#!/usr/bin/env python3
"""Generate the draft bypass permission sheet; no KiCad installation required.

This emits pin-block symbols with embedded libraries. Native KiCad import/ERC and
PCB footprints remain release gates; --check is a reproducibility check only.
"""
import argparse
import csv
import html
import io
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "hardware/electrical"
NAMESPACE = uuid.UUID("b76a8ea2-1ad7-4e18-a1ba-c768f4b56383")


def uid(name):
    return str(uuid.uuid5(NAMESPACE, name))


def quote(value):
    return json.dumps(str(value), ensure_ascii=False)


def effects(size=1.27, hide=False, justify=""):
    return f'(effects (font (size {size} {size})){" (justify " + justify + ")" if justify else ""}{" hide" if hide else ""})'


def property_text(key, value, x, y, hide=False):
    return f'(property {quote(key)} {quote(value)} (at {x:g} {y:g} 0) {effects(hide=hide)})'


def geometry(part):
    """All external pins are on the right of a labelled component block."""
    count = len(part['pins'])
    half_height = max(3.81, (count + 1) * 1.27)
    return half_height, [(pin, 25.4, (count - 1) * 1.27 - i * 2.54)
                         for i, pin in enumerate(part['pins'])]


def validate(data):
    parts = data['components']
    assert len({p['ref'] for p in parts}) == len(parts), 'Duplicate component reference'
    for p in parts:
        assert len({v['number'] for v in p['pins']}) == len(p['pins']), p['ref']
        assert p['source'], 'Part needs a source or explicit project interface definition'
        for v in p['pins']:
            assert bool(v.get('net')) != bool(v.get('no_connect')), (p['ref'], v)
            assert v['type'] in {'input', 'output', 'bidirectional', 'open_collector', 'passive', 'power_in', 'power_out'}
    proto = json.loads((ROOT / 'hardware/prototype.json').read_text())
    assert data['mcu_gpio'] == {k: proto['pins'][k] for k in data['mcu_gpio']}


def library_symbol(p, external=False):
    """Share exact pin-block definitions between the cache and project library."""
    ref = p['ref']
    name = 'RMX_' + ref
    half, pins = geometry(p)
    physical = 'no' if p.get('virtual') else 'yes'
    out = [f'(symbol {quote(name if external else "RMX:" + name)} (pin_names (offset 1.016)) (in_bom {physical}) (on_board {physical})',
           property_text('Reference', ref.rstrip('0123456789'), 0, half + 5.08),
           property_text('Value', p['value'], 0, half + 2.54),
           property_text('Footprint', p.get('footprint', ''), 0, 0, True),
           property_text('Datasheet', p['source'], 0, 0, True),
           f'(symbol "{name}_0_1" (rectangle (start -20.32 {half:g}) (end 20.32 {-half:g}) (stroke (width 0.254) (type default)) (fill (type background))))',
           f'(symbol "{name}_1_1"']
    for pin, x, y in pins:
        out += [f'(pin {pin["type"]} line (at {x:g} {y:g} 180) (length 5.08)',
                f'(name {quote(pin["name"])} {effects(1.016)}) (number {quote(pin["number"])} {effects(1.016)}))']
    return '\n'.join(out + ['))'])


def schematic(data, assembly=None):
    project = data.get('project', 'bypass-permission')
    # Preserve the original sheet's IDs; independently generated sheets must
    # never reuse root/component UUIDs when opened together in a project.
    scoped_uid = lambda name: uid(name if project == 'bypass-permission' else project + ':' + name)
    root = scoped_uid('root')
    qualification = ('DRAFT - see current native-check.json; PCB and physical qualification pending'
                     if assembly else 'DRAFT - native import/ERC and physical validation pending')
    out = ['(kicad_sch (version 20231120) (generator rmx_generate_bypass)',
           f'(uuid {root}) (paper {quote(data.get("paper", "A2"))})',
           f'(title_block (title {quote(data.get("title", "RMX - bypass permission logic"))}) (date "2026-10-22") (rev {quote(data["revision"])}) (comment 1 {quote(qualification)}))',
           '(lib_symbols']
    for p in data['components']:
        out += [library_symbol(p)]
    out += [')']
    for i, line in enumerate(data['sheet_notes']):
        out += [f'(text {quote(line)} (at 15 {13 + i*4} 0) {effects(1.6, justify="left")} (uuid {scoped_uid("note"+str(i))}))']
    for p in data['components']:
        ref = p['ref']
        x, y = p['at']
        half, pins = geometry(p)
        physical = 'no' if p.get('virtual') else 'yes'
        out += [f'(symbol (lib_id "RMX:RMX_{ref}") (at {x:g} {y:g} 0) (unit 1) (in_bom {physical}) (on_board {physical}) (dnp no) (uuid {scoped_uid(ref)})',
                property_text('Reference', ref, x, y - half - 5.08),
                property_text('Value', p['value'], x, y - half - 2.54),
                property_text('Footprint', p.get('footprint', ''), x, y, True),
                property_text('Datasheet', p['source'], x, y, True),
                property_text('MPN', p.get('mpn', p['value'] if ref.startswith('U') else ''), x, y, True)]
        out += [f'(pin {quote(pin["number"])} (uuid {scoped_uid(ref+":"+pin["number"])}))' for pin, _, _ in pins]
        instance_project = assembly['project'] if assembly else project
        instance_path = assembly['path'] if assembly else '/' + root
        out += [f'(instances (project {quote(instance_project)} (path {quote(instance_path)} (reference "{ref}") (unit 1))))', ')']
        for pin, px, py in pins:
            xx, yy = round(x + px, 5), round(y - py, 5)
            key = ref + ':' + pin['number']
            if pin.get('no_connect'):
                out += [f'(no_connect (at {xx:g} {yy:g}) (uuid {scoped_uid(key+":nc")}))']
            else:
                # Stub then local label; identical net names connect on this root sheet.
                ex = round(xx + 2.54, 5)
                global_net = assembly and pin['net'] in assembly['global_nets']
                label_kind = 'global_label' if global_net else 'label'
                shape = ' (shape bidirectional)' if global_net else ''
                label_effects = effects(1.016, justify='left' if global_net else 'left bottom')
                out += [f'(wire (pts (xy {xx:g} {yy:g}) (xy {ex:g} {yy:g})) (stroke (width 0) (type default)) (uuid {scoped_uid(key+":wire")}))',
                        f'({label_kind} {quote(pin["net"])}{shape} (at {ex:g} {yy:g} 0) {label_effects} (uuid {scoped_uid(key+":label")}))']
    out += ['(sheet_instances (path "/" (page "1")))', ')']
    return '\n'.join(out) + '\n'


def preview(data):
    """SVG uses the same symbol geometry and sheet coordinates as the KiCad file."""
    w, h = {'A2': (594, 420), 'A1': (841, 594), 'A0': (1189, 841)}[data.get('paper', 'A2')]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w*4}" height="{h*4}" viewBox="0 0 {w} {h}">',
           f'<rect width="{w}" height="{h}" fill="white"/>',
           '<g font-family="Arial,sans-serif" fill="#18262f">']
    for i, text in enumerate(data['sheet_notes']):
        out += [f'<text x="15" y="{13 + i*4}" font-size="1.6">{html.escape(text)}</text>']
    for p in data['components']:
        x, y = p['at']
        half, pins = geometry(p)
        out += [f'<rect x="{x-20.32}" y="{y-half}" width="40.64" height="{half*2}" fill="#f4f7f8" stroke="#344c5a" stroke-width=".25"/>',
                f'<text x="{x}" y="{y-half-5.08}" text-anchor="middle" font-size="1.6" font-weight="bold">{html.escape(p["ref"])}</text>',
                f'<text x="{x}" y="{y-half-2.54}" text-anchor="middle" font-size="1.4">{html.escape(p["value"])}</text>']
        for pin, px, py in pins:
            yy, xx = y - py, x + px
            out += [f'<line x1="{x+20.32}" y1="{yy}" x2="{xx}" y2="{yy}" stroke="#226f50" stroke-width=".25"/>',
                    f'<text x="{x+19}" y="{yy+.35}" text-anchor="end" font-size="1.15">{html.escape(pin["name"])}</text>',
                    f'<text x="{xx-2.54}" y="{yy-.4}" text-anchor="middle" font-size=".9">{pin["number"]}</text>']
            if pin.get('no_connect'):
                out += [f'<path d="M {xx-.6},{yy-.6} l 1.2,1.2 m -1.2,0 l 1.2,-1.2" stroke="#b03a3a" stroke-width=".2"/>']
            else:
                out += [f'<line x1="{xx}" y1="{yy}" x2="{xx+2.54}" y2="{yy}" stroke="#226f50" stroke-width=".25"/>',
                        f'<text x="{xx+2.54}" y="{yy-.4}" font-size="1.15" fill="#226f50">{html.escape(pin["net"])}</text>']
    return '\n'.join(out + ['</g></svg>']) + '\n'


def artifacts(data):
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['Reference', 'Value', 'MPN', 'Package', 'Footprint', 'Source', 'Qualification'])
    for p in data['components']:
        if p.get('virtual'):
            continue
        writer.writerow([p['ref'], p['value'], p.get('mpn', p['value'] if p['ref'].startswith('U') else ''), p['package'], p.get('footprint', ''), p['source'], p['qualification']])
    project = data.get('project', 'bypass-permission')
    bom = data.get('bom_file', 'bypass-bom.csv')
    return {project + '.kicad_sch': schematic(data),
            project + '.svg': preview(data), bom: stream.getvalue()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = json.loads((DEST / 'bypass.json').read_text())
    validate(data)
    for name, content in artifacts(data).items():
        path = DEST / name
        if args.check:
            assert path.exists() and path.read_text() == content, f'Stale generated artifact: {name}'
        else:
            path.write_text(content)
    print(f'PASS: {len(data["components"])} components; generated CAD/BOM/preview consistent (not native ERC)')


if __name__ == '__main__':
    main()
