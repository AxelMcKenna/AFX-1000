"""Inventory disconnected logic ground pins against native main-ground fields.

Coverage below an SMD pad is not an electrical connection. This survey selects
no copper, makes no current-rating claim, and does not waive later native checks.
"""
import argparse
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from shapely.geometry import Point
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields


def run():
    parser = argparse.ArgumentParser()
    for name in ['capture', 'candidate', 'output']:
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    assert all(all(x.isalnum() or x in '-_' for x in v) for v in vars(args).values())
    cp = STAGING / args.capture / 'capture.json'
    netlist = STAGING / args.candidate / 'netlist.xml'
    checkpoint = STAGING / args.candidate / 'final-review.json'
    out = STAGING / args.output
    assert not out.exists()
    capture = json.loads(cp.read_text())
    for data in [capture, json.loads(checkpoint.read_text())]:
        for name, digest in data['source_sha256'].items():
            path = Path(name)
            assert sha(path if path.is_absolute() else REPO / path) == digest, name
    tree = ET.parse(netlist)
    parts = {p.attrib['ref']: p.findtext('value') for p in tree.findall('./components/comp')}
    ground_nodes = [p.attrib for n in tree.findall('./nets/net')
                    if n.attrib['name'] == 'PWR_AGND' for p in n.findall('node')]
    selected = [n for n in ground_nodes if parts[n['ref']].startswith('SN74')
                and n.get('pintype') == 'power_in' and n.get('pinfunction', '').startswith('GND')]
    pads = {(o['ref'], o['pin']): o for o in capture['objects'] if o['kind'] == 'PAD'}
    main = pads['P_C103', '2']['group']
    fields, excluded = anchored_fields(capture)
    main_fields = {l: p for (l, g), p in fields.items() if g == main}
    ground_vias = [o for o in capture['objects']
                   if o['kind'] == 'PCB_VIA' and o['net'] == 'PWR_AGND' and o['group'] == main]
    rows = []
    for node in selected:
        pad = pads[node['ref'], node['pin']]
        assert pad['net'] == 'PWR_AGND'
        if pad['group'] == main:
            continue
        assert len(pad['layers']) == 1
        layer, = pad['layers']
        reference = {'F.Cu': 'In1.Cu', 'B.Cu': 'In6.Cu'}[layer]
        point = Point(pad['position_mm'])
        field = main_fields[reference]
        nearest = min(ground_vias, key=lambda o: math.dist(o['position_mm'], pad['position_mm']))
        rows.append(dict(ref=pad['ref'], pin=pad['pin'], value=parts[pad['ref']],
                         pinfunction=node['pinfunction'], group=pad['group'], layer=layer,
                         position_mm=pad['position_mm'], reference_layer=reference,
                         main_reference_covers_pad_center_band=field.buffer(.0015).covers(point.buffer(.1)),
                         distance_to_adjacent_main_ground_mm=field.distance(point),
                         nearest_main_ground_via_uuid=nearest['uuid'],
                         nearest_main_ground_via_mm=math.dist(nearest['position_mm'], pad['position_mm'])))
    rows.sort(key=lambda r: (not r['main_reference_covers_pad_center_band'], r['ref'], r['pin']))
    sources = [Path(__file__), cp, netlist, checkpoint,
               REPO / 'hardware/fabrication/plan_two_board_startup_controls.py']
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                  selection='SN74-family IC power_in pins named GND on PWR_AGND, outside the native main-ground group',
                  selected_ground_pins=len(selected), disconnected_logic_ground_pins=len(rows),
                  disconnected_groups=len({r['group'] for r in rows}),
                  pins_with_adjacent_main_reference=sum(r['main_reference_covers_pad_center_band'] for r in rows),
                  by_subsystem=dict(Counter(r['ref'].split('_')[0] for r in rows)),
                  rows=rows, excluded_unanchored_fragments=excluded,
                  scope='Routing-access inventory only; main reference coverage is not pad connectivity. Via legality, return ownership, supply current, decoupling and functional qualification remain required.',
                  fabrication_released=False)
    out.mkdir()
    (out / 'survey.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['selected_ground_pins', 'disconnected_logic_ground_pins',
                                             'disconnected_groups', 'pins_with_adjacent_main_reference', 'by_subsystem']}))


if __name__ == '__main__':
    run()
