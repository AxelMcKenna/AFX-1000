"""Audit the unselected six-layer comparison without approving its stack."""
import copy
import json
from pathlib import Path

from shapely.geometry import Point
from shapely.strtree import STRtree

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_candidate import geometry_delta, native_evidence_errors, sha
from hardware.fabrication.audit_digital_core import verify_export
from hardware.fabrication.audit_digital_signals import check as selected_check
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = ROOT/'staging/digital-six-clean-native-01'


def check():
    selected = selected_check()
    base = ROOT/'staging/digital-distribution-native-02/digital_core.kicad_pcb'
    pcb = OUT/base.name
    rp = OUT/'review.json'
    cp = ROOT/'staging/digital-six-clean-inputs-113/capture.json'
    nr = OUT/'signal-connectivity-review.json'
    review, capture, native = [json.loads(p.read_text()) for p in [rp, cp, nr]]
    assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'), review)
    assert review['status']['counts'] == dict(violations=0, unconnected_items=113,
                                              schematic_parity=0, erc=0)
    assert review['uncapped_open_connections'] == 113
    for r in [capture, native]:
        assert all(sha(Path(p)) == h for p, h in r['source_sha256'].items())
    parts, pins = netlist(OUT/'netlist.xml')
    verify_export(parts, pins)
    before, after = [read_sexpr(p.read_text()) for p in [base, pcb]]
    delta = geometry_delta(before, after)
    for tag in ['footprint', 'segment', 'via', 'zone']:
        assert not delta[tag]['removed'] and not delta[tag]['changed']
    assert not delta['footprint']['added'] and len(delta['zone']['added']) == 1
    assert [r[1] for r in first(after, 'layers')[1:] if r[1].endswith('.Cu')] == [
        'F.Cu', 'In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu', 'B.Cu']
    normalized = copy.deepcopy(after)
    normalized[normalized.index(first(normalized, 'layers'))] = copy.deepcopy(first(before, 'layers'))
    assert geometry_delta(before, normalized)['other_root_geometry_exact']
    new_zone = next(z for z in children(after, 'zone') if first(z, 'layer')[1] == 'In4.Cu')
    old_zone = next(z for z in children(before, 'zone') if first(z, 'layer')[1] == 'In1.Cu')
    def authored_zone(z):
        z = copy.deepcopy(z)
        return [n for n in z if not isinstance(n, list) or n[0] not in
                {'uuid', 'layer', 'filled_polygon', 'filled_areas_thickness'}]
    assert authored_zone(new_zone) == authored_zone(old_zone)
    assert native['preserved_power_ground_pads'] == 201
    assert native['preserved_local_connections'] == 39
    assert native['preserved_thermal_connections'] == 33
    assert native['copper_layer_count'] == 6
    assert all(len(z['polygons']) == 1 for z in native['planes'])
    assert {(z['net'], z['layer']) for z in native['planes']} == {
        ('AGND', 'In1.Cu'), ('5V_DIG', 'In2.Cu'), ('AGND', 'In4.Cu')}
    pads = [o for o in capture['objects'] if o['kind'] == 'PAD'
            and not any(o['drill_mm']) and o['layers']]
    polygons = [shape([p for ps in o['layers'].values() for p in ps]) for o in pads]
    tree = STRtree(polygons)
    old_vias = {first(v, 'uuid')[1] for v in children(before, 'via')}
    drills = []
    for v in children(after, 'via'):
        uid = first(v, 'uuid')[1]
        if uid in old_vias:
            continue
        point = Point(list(map(float, first(v, 'at')[1:3])))
        drill = float(first(v, 'drill')[1])
        index = int(tree.nearest(point))
        gap = point.distance(polygons[index])-drill/2
        assert drill >= .3 and gap >= .15
        drills.append(dict(uuid=uid, hole_edge_to_SMD_copper_mm=gap))
    inputs = [base, pcb, pcb.with_suffix('.kicad_pro'), rp, cp, nr, OUT/'netlist.xml',
              Path(__file__), ROOT/'audit_digital_signals.py', ROOT/'route_nf_surface.py']
    hashes = {str(p.relative_to(REPO)): sha(p) for p in inputs}
    hashes.update(selected['source_sha256'])
    return dict(source_sha256=hashes, selected_four_layer_opens=143,
                trial_six_layer_opens=113, native_geometry_parity_ERC_findings=0,
                geometry_delta=delta, only_root_change_is_two_added_copper_layers=True,
                added_plane_is_authored_AGND_zone_copy=True,
                original_DC03_components_and_copper_preserved=True,
                preserved_power_ground_pads=201, preserved_local_connections=39,
                preserved_thermal_connections=33, new_via_drill_review=drills,
                minimum_new_drill_edge_to_SMD_copper_mm=min(r['hole_edge_to_SMD_copper_mm'] for r in drills),
                open_nets=[r for r in native['nets'] if not r['all_pads_connected']],
                stack_copper_dielectric_impedance_and_process_accepted=False,
                signal_integrity_and_thermal_performance_qualified=False,
                selected=False, fabrication_released=False)


if __name__ == '__main__':
    result = check()
    with (OUT/'comparison-review.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print('Six-layer trial: 113 opens, native-clean, original copper retained; unselected')
