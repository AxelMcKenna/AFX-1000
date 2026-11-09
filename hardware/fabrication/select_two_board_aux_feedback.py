"""Select concrete AUX feedback parts and author their TBP51 candidate lands.

This is a working BOM/land revision, not manufacturing release or lifetime proof.
"""
import copy
import csv
import itertools
import json
import math
import shutil
from pathlib import Path

import numpy as np
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, sha
from hardware.fabrication.assess_two_board_aux_load import circuit, numeric
from hardware.fabrication.route_nf_surface import shape

BASE = STAGING / 'two-board-power-startup-remaining-native-03'
CAP = STAGING / 'two-board-power-routing-inputs-2172-startup-remaining-03/capture.json'
OUT = STAGING / 'two-board-power-aux-feedback-01'
PARTS = REPO / 'hardware/fabrication/parts/aux-feedback-01'
FPID = 'TBP51_AUX:R_0805_Vishay_TNPW_28950'
VISHAY = 'https://www.vishay.com/docs/28758/tnpw_e3.pdf'
SELECTION = [
    dict(ref='P_R108', value='11.7k 0.1% 25ppm', resistance_ohm=11700,
         manufacturer='Vishay', MPN='TNPW080511K7BEEA', datasheet=VISHAY,
         tolerance=.001, TCR_ppm_K=25, installed_allocation=.01,
         catalog='https://www.mouser.ca/en/ProductDetail/Vishay/TNPW080511K7BEEA?qs=sGAEpiMZZMtlubZbdhIBIOfZK%2FXsMeDWlbNCLC%252B7iiE%3D'),
    dict(ref='P_R130', value='49.9 0.01% 5ppm', resistance_ohm=49.9,
         manufacturer='Stackpole Electronics', MPN='RNCF0805TKY49R9',
         datasheet='https://www.seielect.com/catalog/sei-rncf.pdf',
         tolerance=.0001, TCR_ppm_K=5, installed_allocation=.03,
         catalog='https://www.digikey.com/en/products/detail/stackpole-electronics-inc/RNCF0805TKY49R9/4072348'),
    dict(ref='P_R109', value='10k 0.1% 10ppm', resistance_ohm=10000,
         manufacturer='Vishay', MPN='TNPW080510K0BYEA', datasheet=VISHAY,
         tolerance=.001, TCR_ppm_K=10, installed_allocation=.01,
         catalog='https://www.digikey.in/en/products/detail/vishay-dale/TNPW080510K0BYEA/7662246'),
]


def lands(f):
    """Vishay 28950 p1 IPC-based reflow row: G1, Y.9, X1.45, Z2.8."""
    f[1] = FPID
    for pad in children(f, 'pad'):
        assert pad[1] in ['1', '2']
        pad[3] = a('rect')
        first(pad, 'at')[1:3] = [-.95 if pad[1] == '1' else .95, 0]
        first(pad, 'size')[1:] = [.9, 1.45]
        pad[:] = [n for n in pad if not (isinstance(n, list) and n and n[0] == 'roundrect_rratio')]
    for rect in children(f, 'fp_rect'):
        if str(first(rect, 'layer')[1]).endswith('.CrtYd'):
            first(rect, 'start')[1:] = [-1.68, -1.0]
            first(rect, 'end')[1:] = [1.68, 1.0]


def set_property(node, key, value, pcb=False):
    existing = [p for p in children(node, 'property') if p[1] == key]
    assert len(existing) <= 1
    if existing:
        existing[0][2] = value
    else:
        p = copy.deepcopy(prop(node, 'Datasheet'))
        p[1:3] = [key, value]
        p[:] = [n for n in p if not (isinstance(n, list) and n and n[0] == 'uuid')]
        node.append(p)


def voltage_screen(parts):
    scenarios = []
    for name, bounds in [('initial_labels', [p['tolerance'] for p in parts]),
                         ('installed_requirements', [p['installed_allocation'] for p in parts])]:
        cases = []
        for factors, accuracy, ifb in itertools.product(
                itertools.product(*[(1-t, 1+t) for t in bounds]), [.98, 1.02], [-1e-7, 1e-7]):
            r1, r2, rb = [p['resistance_ohm']*f for p, f in zip(parts, factors)]
            vf = 1.193*accuracy
            current = vf/rb-ifb
            vo = vf+current*(r1+r2)
            # Independent nodal solution with ideal FB voltage constraint.
            matrix = np.array([[1/r1+1/r2, -1/r1], [-1/r2, 0.]])
            rhs = np.array([vf/r2, ifb-vf*(1/rb+1/r2)])
            vm, actual = np.linalg.solve(matrix, rhs)
            assert abs(vo-actual) < 1e-11
            cases.append(dict(factors=factors, feedback_V=vf, IFB_out_A=ifb,
                output_V=vo, midpoint_V=float(vm), KCL_output_V=float(actual),
                resistor_power_W=[current*current*r1, current*current*r2, vf*vf/rb]))
        limits = [min(c['output_V'] for c in cases), max(c['output_V'] for c in cases)]
        assert 2.3 < limits[0] < limits[1] < 2.7
        scenarios.append(dict(name=name, bounds=bounds, cases=cases,
            source_voltage_range_V=limits, margin_to_2p7_V=2.7-limits[1],
            distribution_allowance_to_2p3_V=limits[0]-2.3,
            maximum_power_W=[max(c['resistor_power_W'][i] for c in cases) for i in range(3)]))
    return scenarios


def run():
    assert not OUT.exists() and not (PARTS/'selection.json').exists()
    parts, nets, pins = circuit(BASE/'netlist.xml')
    rows = copy.deepcopy(SELECTION)
    for row in rows:
        r = row['ref']
        assert numeric(parts[r].findtext('value')) == row['resistance_ohm']
        row.update(old_value=parts[r].findtext('value'), pins=pins[r],
                   footprint=FPID if r != 'P_R130' else parts[r].findtext('footprint'))
    scenarios = voltage_screen(rows)
    # A screening sum of specified separate tests, not a combined-stress guarantee.
    drift = []
    for row in rows:
        if row['manufacturer'] != 'Vishay':
            continue
        r = row['resistance_ohm']
        terms = dict(initial=.001, temperature_105K=row['TCR_ppm_K']*105e-6,
            solder_heat=.0002+.01/r, endurance_general_8000h=.001+.02/r,
            damp_heat_accelerated=.001+.01/r, temperature_cycles=.001+.01/r,
            bending=.0005+.01/r, vibration=.0005+.01/r, cold=.0005+.01/r)
        combined = math.prod(1+t for t in terms.values())-1
        assert combined < row['installed_allocation']
        drift.append(dict(ref=row['ref'], terms=terms, compounded_upper=combined,
            unallocated_fraction=(1+row['installed_allocation'])/(1+combined)-1,
            combined_stress_or_mission_lifetime_proven=False))
    source_files = [Path(__file__), CAP, BASE/'netlist.xml',
        REPO/'hardware/fabrication/assess_two_board_aux_voltage_budget.py',
        REPO/'hardware/qualification/boards/aux_current_partition/sources/primary/TPS7A16.pdf',
        *sorted((PARTS/'sources').glob('*.pdf'))]
    OUT.mkdir()
    for src in BASE.rglob('*'):
        if not src.is_file():
            continue
        rel = src.relative_to(BASE)
        if rel.parts[0] in ['libraries', 'symbols'] or len(rel.parts) == 1 and (
                src.suffix == '.kicad_sch' or src.name in ['power_protection.kicad_pcb',
                'power_protection.kicad_pro', 'power_protection.kicad_dru', 'fp-lib-table',
                'sym-lib-table', 'expected-circuit.json', 'symbol-paths.json']):
            target = OUT/rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            source_files.append(src)
    bpath = OUT/'power_protection.kicad_pcb'
    board = read_sexpr(bpath.read_text())
    fps = {prop(f, 'Reference')[2]: f for f in children(board, 'footprint')}
    for row in rows:
        f = fps[row['ref']]
        for k, value in [('Value', row['value']), ('MPN', row['MPN']),
                         ('Manufacturer', row['manufacturer']), ('Datasheet', row['datasheet'])]:
            set_property(f, k, value, pcb=True)
        if row['ref'] != 'P_R130':
            lands(f)
    cap = json.loads(CAP.read_text())
    refill = set()
    for obj in cap['objects']:
        if obj.get('ref') not in ['P_R108', 'P_R109']:
            continue
        for layer, polygon in obj['layers'].items():
            for z in cap['zones']:
                if z['layer'] == layer and shape(z['authored_outline']).intersects(shape(polygon).buffer(.8)):
                    refill.add(z['uuid'])
    assert refill == {'bc76c316-2c04-5ecb-85b7-3e5f80b26bf1', 'd0572a8e-b95d-5c59-9a7c-1d3514a507b4'}
    for z in children(board, 'zone'):
        if str(first(z, 'uuid')[1]) in refill:
            z[:] = [n for n in z if not (isinstance(n, list) and n and n[0] == 'filled_polygon')]
    bpath.write_text(sexpr(board)+'\n')
    path = OUT/'P_power_p03.kicad_sch'
    schematic = read_sexpr(path.read_text())
    symbols = {prop(s, 'Reference')[2]: s for s in children(schematic, 'symbol')}
    expected = json.loads((OUT/'expected-circuit.json').read_text())
    for row in rows:
        for key, value in [('Value', row['value']), ('Footprint', row['footprint']),
                           ('MPN', row['MPN']), ('Manufacturer', row['manufacturer']), ('Datasheet', row['datasheet'])]:
            set_property(symbols[row['ref']], key, value)
        expected[row['ref']].update(value=row['value'], footprint=row['footprint'])
    path.write_text(sexpr(schematic)+'\n')
    (OUT/'expected-circuit.json').write_text(json.dumps(expected, indent=2)+'\n')
    root = OUT/'power_protection.kicad_sch'
    sch = read_sexpr(root.read_text())
    first(first(sch, 'title_block'), 'rev')[1] = 'TBP51-CANDIDATE'
    root.write_text(sexpr(sch)+'\n')
    lib = OUT/'libraries/TBP51_AUX.pretty'
    lib.mkdir()
    template = read_sexpr((BASE/'libraries/TB05_P_Resistor_SMD.pretty/R_0805_2012Metric.kicad_mod').read_text())
    lands(template)
    template[1] = FPID.split(':')[1]
    first(template, 'descr')[1] = 'Vishay TNPW0805; 28950 p1 IPC-based reflow lands; G1 Y0.9 X1.45 Z2.8 mm'
    prop(template, 'Value')[2] = template[1]
    (lib/(template[1]+'.kicad_mod')).write_text(sexpr(template)+'\n')
    table = read_sexpr((OUT/'fp-lib-table').read_text())
    table.append([a('lib'), [a('name'), 'TBP51_AUX'], [a('type'), 'KiCad'],
        [a('uri'), '${KIPRJMOD}/libraries/TBP51_AUX.pretty'], [a('options'), ''], [a('descr'), 'AUX feedback resistor lands']])
    (OUT/'fp-lib-table').write_text(sexpr(table)+'\n')
    report = dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in source_files},
        parent_revision='TBP50', candidate_revision='TBP51-CANDIDATE', parts=rows,
        voltage_scenarios=scenarios, TNPW_separate_test_screen=drift,
        refilled_zone_uuids=sorted(refill), nominal_output_V=1.193*(1+11749.9/10000),
        RNCF_current_full_datasheet_review_pending=True, RNCF_generic_lands_retained=True,
        installed_resistor_limits_qualified=False, fabrication_released=False)
    (PARTS/'selection.json').write_text(json.dumps(report, indent=2)+'\n')
    (OUT/'aux-feedback-selection.json').write_text(json.dumps(dict(
        selection_report=str((PARTS/'selection.json').relative_to(REPO)),
        selection_sha256=sha(PARTS/'selection.json'), refilled_zone_uuids=sorted(refill),
        fabrication_released=False), indent=2)+'\n')
    with (PARTS/'bom.csv').open('w') as file:
        keys=['ref','value','manufacturer','MPN','footprint','datasheet','catalog']
        writer=csv.DictWriter(file,fieldnames=keys);writer.writeheader()
        writer.writerows({k:row[k] for k in keys} for row in rows)
    print(json.dumps(dict(candidate=str(OUT), parts=[r['MPN'] for r in rows],
        voltage_range=scenarios[1]['source_voltage_range_V'], refill=sorted(refill))))


if __name__ == '__main__':
    run()
