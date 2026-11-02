"""Independent audit of the four-layer partial signal-routing checkpoint."""
import json
from collections import Counter
from pathlib import Path

from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree
from shapely import make_valid
from shapely.validation import explain_validity

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_candidate import geometry_delta, native_evidence_errors, sha
from hardware.fabrication.audit_digital_core import verify_export
from hardware.fabrication.audit_digital_distribution import OUT as PREVIOUS, check as previous_check
from hardware.fabrication.route_nf_surface import shape

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO/'hardware/fabrication'
OUT = ROOT/'staging/digital-four-clean-native-03'


def check():
    old = previous_check()
    assert old == json.loads((PREVIOUS/'handoff.json').read_text())
    pcb = OUT/'digital_core.kicad_pcb'
    rp = OUT/'review.json'
    review = json.loads(rp.read_text())
    assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'), review)
    assert review['status']['counts'] == dict(violations=0, unconnected_items=143,
                                              schematic_parity=0, erc=0)
    assert review['uncapped_open_connections'] == 143
    for name, h in review['captured_hierarchy_sha256'].items():
        assert sha(OUT/name) == h
    parts, pins = netlist(OUT/'netlist.xml')
    verify_export(parts, pins)
    before = read_sexpr((PREVIOUS/pcb.name).read_text())
    after = read_sexpr(pcb.read_text())
    delta = geometry_delta(before, after)
    assert delta['other_root_geometry_exact']
    for tag, count in [('footprint', 0), ('segment', 1007), ('via', 107), ('zone', 0)]:
        assert len(delta[tag]['added']) == count
        assert not delta[tag]['removed'] and not delta[tag]['changed']
    cp = ROOT/'staging/digital-four-clean-inputs-143/capture.json'
    nr = OUT/'signal-connectivity-review.json'
    capture, native = [json.loads(p.read_text()) for p in [cp, nr]]
    for record in [capture, native]:
        assert all(sha(Path(p)) == h for p, h in record['source_sha256'].items())
    assert native['uncapped_open_connections'] == 143
    assert native['preserved_power_ground_pads'] == 201
    assert native['preserved_local_connections'] == 39
    assert native['preserved_thermal_connections'] == 33
    assert native['copper_layer_count'] == 4
    for name, h in native['plots_sha256'].items():
        assert sha(OUT/'plots'/name) == h
    planes = []
    for z in native['planes']:
        assert len(z['polygons']) == 1
        polygon = Polygon(z['polygons'][0]['outer'], z['polygons'][0]['holes'])
        validity = explain_validity(polygon)
        normalized = make_valid(polygon)
        pieces = list(normalized.geoms) if hasattr(normalized, 'geoms') else [normalized]
        copper = [p for p in pieces if p.geom_type == 'Polygon']
        # KiCad filled contours may touch at zero-area ring slits. Accept
        # normalization only when it preserves area and one copper component.
        assert len(copper) == 1 and copper[0].is_valid
        assert all(p.geom_type in {'Polygon', 'LineString', 'MultiLineString'} for p in pieces)
        assert abs(normalized.area-polygon.area) < 1e-6
        planes.append(dict(net=z['net'], layer=z['layer'], connected_fill_regions=1,
                           area_mm2=polygon.area, exported_contour_validity=validity,
                           normalized_single_copper_component=True,
                           normalization_area_delta_mm2=normalized.area-polygon.area))
    assert {(p['net'], p['layer']) for p in planes} == {('AGND', 'In1.Cu'), ('5V_DIG', 'In2.Cu')}
    pads = [o for o in capture['objects'] if o['kind'] == 'PAD'
            and not any(o['drill_mm']) and o['layers']]
    polygons = [shape([p for ps in o['layers'].values() for p in ps]) for o in pads]
    tree = STRtree(polygons)
    old_vias = {first(v, 'uuid')[1] for v in children(before, 'via')}
    drills = []
    for v in children(after, 'via'):
        ident = first(v, 'uuid')[1]
        if ident in old_vias:
            continue
        xy = list(map(float, first(v, 'at')[1:3]))
        point = Point(xy)
        drill = float(first(v, 'drill')[1])
        assert drill >= .3 and (float(first(v, 'size')[1])-drill)/2 >= .15
        index = int(tree.nearest(point))
        gap = point.distance(polygons[index])-drill/2
        assert gap >= .15
        drills.append(dict(uuid=ident, xy_mm=xy, drill_mm=drill,
                           nearest_SMD=[pads[index]['ref'], pads[index]['pin']],
                           hole_edge_to_SMD_copper_mm=gap))
    assert len(drills) == 107
    by_net = {r['net']: r for r in native['nets']}
    sd = []
    for name in ['CLK', 'CMD', 'D0', 'D1', 'D2', 'D3']:
        a, b = [by_net['/PROCESSOR/SDMMC_'+name+suffix] for suffix in ['', '_SRC']]
        assert a['all_pads_connected'] and b['all_pads_connected']
        sd.append(dict(signal=name, carrier_planar_copper_mm=a['planar_copper_length_mm']+b['planar_copper_length_mm'],
                       via_count=a['via_count']+b['via_count']))
    for name in ['ADC_DATA', 'DAC_DATA', 'DAC_DATA_SRC', 'BCLK', 'WS']:
        assert by_net['/PROCESSOR/'+name]['all_pads_connected']
    open_nets = [r for r in native['nets'] if not r['all_pads_connected']]
    assert sum(len(r['pad_groups'])-1 for r in open_nets) == 143
    hashes = dict(old['source_sha256'])
    inputs = [pcb, pcb.with_suffix('.kicad_pro'), rp, OUT/'netlist.xml', nr, cp,
              PREVIOUS/'handoff.json', Path(__file__), ROOT/'route_nf_surface.py']
    inputs += [OUT/n for n in review['captured_hierarchy_sha256']]
    for record in [capture, native]:
        hashes.update({str(Path(p).relative_to(REPO)): h for p, h in record['source_sha256'].items()})
    hashes.update({str(p.relative_to(REPO)): sha(p) for p in inputs})
    return dict(revision='DC04', source_sha256=hashes, electrical_parts=138,
        exported_physical_terminals=sum(map(len, pins.values())), uncapped_open_connections=143,
        native_geometry_findings=0, native_schematic_parity_findings=0, native_ERC_findings=0,
        geometry_delta=delta, all_previous_footprints_copper_and_root_geometry_exact=True,
        local_connections_native_verified=39, power_ground_pads_native_verified=201,
        thermal_connections_native_verified=33, planes=planes,
        total_tracks=len(children(after, 'segment')), total_vias=len(children(after, 'via')),
        new_via_drill_review=drills, minimum_new_drill_edge_to_SMD_copper_mm=min(r['hole_edge_to_SMD_copper_mm'] for r in drills),
        prior_mask_covered_EP_vias_preserved=21, open_nets=open_nets,
        open_net_categories=dict(Counter('LED outputs' if r['net'].startswith('/LED/LED_') else
                                         'controls' if r['net'].startswith('/CONTROLS/') else 'other' for r in open_nets)),
        SD_carrier_lengths=sd, SD_planar_length_spread_mm=max(r['carrier_planar_copper_mm'] for r in sd)-min(r['carrier_planar_copper_mm'] for r in sd),
        SD_lengths_exclude_Seed_internal_socket_resistor_and_offboard_path=True,
        SD_timing_impedance_and_return_paths_qualified=False,
        complete_mechanical_receiving_qualified=False,
        current_capacity_voltage_noise_and_thermal_performance_qualified=False,
        mask_registration_tenting_plating_and_stack_accepted=False,
        routed=False, fabrication_released=False)


if __name__ == '__main__':
    result = check()
    with (OUT/'handoff.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print('DC04: 143 opens; zero native findings; 107 new drills screened; SD timing remains open')
