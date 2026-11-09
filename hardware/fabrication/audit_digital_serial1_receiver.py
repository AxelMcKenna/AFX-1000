"""Physical audit including the declared 0.25 mm R3015 receiving-area translation."""
import argparse
import copy
import json
import math
from pathlib import Path

from shapely.geometry import Point, Polygon, box
from shapely import make_valid
from shapely.ops import unary_union

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.audit_candidate import geometry_delta, native_evidence_errors, sha
from hardware.fabrication.audit_digital_core import verify_export
from hardware.fabrication.digital_core_layout import pad_box
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent


def check(label, capture_label='digital-coordinated-six-clean-inputs-117'):
    out = ROOT/'staging'/label
    pcb = out/'digital_core.kicad_pcb'
    rp = out/'review.json'
    review = json.loads(rp.read_text())
    assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'), review)
    assert review['status']['counts']['schematic_parity'] == review['status']['counts']['erc'] == 0
    drc = json.loads((out/'drc.json').read_text())
    assert all(v['severity'] == 'warning' and v['type'] == 'via_dangling' for v in drc['violations'])
    parts, pins = netlist(out/'netlist.xml')
    verify_export(parts, pins)
    board = read_sexpr(pcb.read_text())
    base = ROOT/'staging/digital-distribution-native-02/digital_core.kicad_pcb'
    original = read_sexpr(base.read_text())
    delta = geometry_delta(original, board)
    normalized = copy.deepcopy(board)
    normalized[normalized.index(first(normalized, 'layers'))] = copy.deepcopy(first(original, 'layers'))
    assert geometry_delta(original, normalized)['other_root_geometry_exact']
    assert len(delta['zone']['added']) == 2 and not delta['zone']['removed'] and not delta['zone']['changed']
    assert [n[1] for n in first(board, 'layers')[1:] if n[1].endswith('.Cu')] == ['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','In5.Cu','In6.Cu','B.Cu']
    ground = next(z for z in children(board, 'zone') if first(z, 'layer')[1] == 'In4.Cu')
    reference = next(z for z in children(original, 'zone') if first(z, 'layer')[1] == 'In1.Cu')
    def authored(z):
        return [n for n in z if not isinstance(n, list) or n[0] not in ('uuid','layer','filled_polygon','filled_areas_thickness')]
    assert authored(ground) == authored(reference)
    added_ground = next(z for z in children(board, 'zone') if first(z, 'layer')[1] == 'In6.Cu')
    assert authored(added_ground) == authored(reference)
    assert not delta['footprint']['added'] and not delta['footprint']['removed']
    def refs(tree):
        return {next(p[2] for p in children(f, 'property') if p[1] == 'Reference'): f
                for f in children(tree, 'footprint')}
    fps, old_fps = refs(board), refs(original)
    changed = sorted(r for r in fps if sexpr(fps[r]) != sexpr(old_fps[r]))
    expected = {f'R{n}' for n in (1010,1011,1012,1013,1015,1016,1017,1018,1019,1020,1039,3019,3020,3021)} | {'J1001','R3016','R3015','R1005','R1003','R2002','R2003','R3010','R3017','R1040'}
    assert set(changed) == expected
    pot_path=ROOT/'staging/digital-pot-filter-repack-04/construction.json'
    pot=json.loads(pot_path.read_text())
    assert all(sha(Path(p))==h for p,h in pot['source_sha256'].items())
    pot_templates=ROOT/'staging/digital-pot-filter-templates-01/templates.json'
    pts=json.loads(pot_templates.read_text())
    assert all(sha(Path(p))==h for p,h in pts['source_sha256'].items())
    pot_template=pot_templates.parent/pot['component_move']['template_file']
    assert next(t['sha256'] for t in pts['templates'] if t['file']==pot_template.name)==sha(pot_template)
    native_pot=read_sexpr(pot_template.read_text());moved=copy.deepcopy(fps['R1040'])
    assert pot['component_move']['after_mm']==[40.5,35.5] and pot['component_move']['side']=='B' and pot['component_move']['angle']==90
    assert list(map(float,first(moved,'at')[1:3]))==[40.5,35.5]
    moved[moved.index(first(moved,'at'))]=copy.deepcopy(first(native_pot,'at'))
    assert sexpr(moved)==sexpr(native_pot)
    armed=copy.deepcopy(fps['R1005'])
    assert list(map(float,first(armed,'at')[1:3]))==[27.5,29.5]
    armed[armed.index(first(armed,'at'))]=copy.deepcopy(first(old_fps['R1005'],'at'))
    assert sexpr(armed)==sexpr(old_fps['R1005'])
    moves_path=ROOT/'staging/digital-control-pulldowns-repack-05/construction.json'
    moves=json.loads(moves_path.read_text())
    assert all(sha(Path(p))==h for p,h in moves['source_sha256'].items())
    for row in moves['component_moves']:
        ref=row['ref'];assert ref in {'R1003','R2002','R2003'}
        moved=copy.deepcopy(fps[ref]);assert list(map(float,first(moved,'at')[1:3]))==row['after_mm']
        moved[moved.index(first(moved,'at'))]=copy.deepcopy(first(old_fps[ref],'at'))
        assert sexpr(moved)==sexpr(old_fps[ref])
    blank_path=ROOT/'staging/digital-blank-pullup-repack-01/construction.json'
    blank=json.loads(blank_path.read_text())
    assert all(sha(Path(p))==h for p,h in blank['source_sha256'].items())
    moved=copy.deepcopy(fps['R3010'])
    assert blank['component_move']['ref']=='R3010'
    assert list(map(float,first(moved,'at')[1:3]))==blank['component_move']['after_mm']
    moved[moved.index(first(moved,'at'))]=copy.deepcopy(first(old_fps['R3010'],'at'))
    assert sexpr(moved)==sexpr(old_fps['R3010'])
    latch_path=ROOT/'staging/digital-latch-supply-repack-01/construction.json'
    latch=json.loads(latch_path.read_text())
    assert all(sha(Path(p))==h for p,h in latch['source_sha256'].items())
    moved=copy.deepcopy(fps['R3017'])
    assert latch['component_move']['ref']=='R3017' and latch['component_move']['after_mm']==[68.,25.]
    assert list(map(float,first(moved,'at')[1:3]))==[68.,25.]
    moved[moved.index(first(moved,'at'))]=copy.deepcopy(first(old_fps['R3017'],'at'))
    assert sexpr(moved)==sexpr(old_fps['R3017'])
    template_path=ROOT/'staging/digital-data-series-templates-01/R3015-B-0.kicad_mod'
    templates_path=template_path.parent/'templates.json'
    template=read_sexpr(template_path.read_text())
    templates=json.loads(templates_path.read_text())
    assert all(sha(Path(p))==h for p,h in templates['source_sha256'].items())
    assert next(r['sha256'] for r in templates['templates'] if r['file']==template_path.name)==sha(template_path)
    data_series=copy.deepcopy(fps['R3015'])
    assert list(map(float,first(data_series,'at')[1:3]))==[75.25,21.]
    serial_path=ROOT/'staging/digital-serial1-combined-restoration-08/construction.json'
    serial=json.loads(serial_path.read_text())
    assert all(sha(Path(p))==h for p,h in serial['source_sha256'].items())
    assert serial['component_move']['position_mm']==[75.25,21.] and serial['component_move']['angle']==0 and serial['component_move']['side']=='B'
    assert data_series==read_sexpr(sexpr(serial['component_move']['footprint']))
    assert first(data_series,'layer')[1]=='B.Cu'
    data_series[data_series.index(first(data_series,'at'))]=copy.deepcopy(first(template,'at'))
    assert sexpr(data_series)==sexpr(template)
    series = copy.deepcopy(fps['R3016'])
    assert list(map(float,first(series,'at')[1:3])) == [69.0,23.0]
    series[series.index(first(series,'at'))] = copy.deepcopy(first(old_fps['R3016'],'at'))
    assert sexpr(series)==sexpr(old_fps['R3016'])
    shifted = copy.deepcopy(fps['J1001'])
    assert list(map(float, first(shifted, 'at')[1:])) == [31.2, 14.0]
    assert first(shifted, 'layer')[1] == 'F.Cu'
    shifted[shifted.index(first(shifted, 'at'))] = copy.deepcopy(first(old_fps['J1001'], 'at'))
    assert sexpr(shifted) == sexpr(old_fps['J1001'])
    shift_source = ROOT/'staging/digital-coordinated-interface-native-01/digital_core.kicad_pcb'
    shift_result = ROOT/'staging/digital-input-shift-native-01/digital_core.kicad_pcb'
    before_shift = read_sexpr(shift_source.read_text())
    after_shift = read_sexpr(shift_result.read_text())
    shift_delta = geometry_delta(before_shift, after_shift)
    assert shift_delta['other_root_geometry_exact']
    assert shift_delta['footprint'] == dict(added=[], removed=[], changed=[first(fps['J1001'], 'uuid')[1]])
    expected_tracks = ['0f17361b-836d-54a5-958a-0322dbb84109', '315da06e-7073-5520-939e-6c630b774fff']
    assert shift_delta['segment'] == dict(added=[], removed=[], changed=expected_tracks)
    for category in ['via', 'zone']:
        assert shift_delta[category] == dict(added=[], removed=[], changed=[])
    old_tracks = {first(t, 'uuid')[1]: t for t in children(before_shift, 'segment')}
    new_tracks = {first(t, 'uuid')[1]: t for t in children(after_shift, 'segment')}
    final_tracks = {first(t, 'uuid')[1]: t for t in children(board, 'segment')}
    for uid in expected_tracks:
        track = copy.deepcopy(new_tracks[uid])
        assert list(map(float, first(track, 'end')[1:])) == [31.2, 14.0]
        track[track.index(first(track, 'end'))] = copy.deepcopy(first(old_tracks[uid], 'end'))
        assert sexpr(track) == sexpr(old_tracks[uid])
        assert sexpr(final_tracks[uid]) == sexpr(new_tracks[uid])
    profile = Polygon([(0,0),(64,0),(64,3),(104,3),(104,9),(114,9),(114,60),(0,60)])
    sides = {r: first(f, 'layer')[1][0] for r, f in fps.items()}
    courts = {r: box(*courtyard(f, sides[r]+'.CrtYd')) for r, f in fps.items()}
    through = {r: [box(*pad_box(f, p, .5)) for p in children(f, 'pad') if p[2] == 'thru_hole']
               for r, f in fps.items()}
    for ref in parts:
        assert profile.covers(courts[ref]) and courts[ref].distance(profile.boundary) >= .5-1e-8
        for other in parts:
            if ref == other:
                continue
            if sides[ref] == sides[other]:
                assert courts[ref].distance(courts[other]) >= .3-1e-8, (ref, other)
            else:
                assert not any(courts[ref].intersection(p).area > 1e-10 for p in through[other]), (ref, other)
        for x, y in [(4,4),(66,13),(110,25),(4,36),(110,44)]:
            assert courts[ref].distance(box(x-3.6,y-3.6,x+3.6,y+3.6)) >= .15-1e-8
    cp = ROOT/'staging/digital-signal-corridor-inputs/capture.json'
    capture = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in capture['source_sha256'].items())
    captured_pcb = next(Path(p) for p in capture['source_sha256'] if p.endswith('.kicad_pcb'))
    assert all(sexpr(fps[r]) == sexpr(f) for r, f in refs(read_sexpr(captured_pcb.read_text())).items() if r not in {'J1001','R3016','R3015','R1005','R1003','R2002','R2003','R3010','R3017','R1040'})
    current_cp=ROOT/'staging'/capture_label/'capture.json'
    current_capture=json.loads(current_cp.read_text())
    assert current_capture['source_sha256'][str(pcb)]==sha(pcb)
    assert all(sha(Path(p))==h for p,h in current_capture['source_sha256'].items())
    smd_objects=[o for o in capture['objects'] if o.get('ref') not in {'R3016','R3015','R1005','R1003','R2002','R2003','R3010','R3017','R1040'}]+[o for o in current_capture['objects'] if o.get('ref') in {'R3016','R3015','R1005','R1003','R2002','R2003','R3010','R3017','R1040'}]
    smd = [(o, shape(ps)) for o in smd_objects if o['kind'] == 'PAD' and not any(o['drill_mm'])
           for layer, ps in o['layers'].items() if layer in ('F.Cu', 'B.Cu') and ps]
    thermal_path = ROOT/'staging/digital-thermal-vias-01/construction.json'
    thermal = json.loads(thermal_path.read_text())
    special = {r['via_uuid']: r['ref'] for r in thermal['thermal_vias']}
    old_vias = {first(v, 'uuid')[1]: v for v in children(original, 'via')}
    drills = []
    for v in children(board, 'via'):
        uid = first(v, 'uuid')[1]
        xy = list(map(float, first(v, 'at')[1:3]))
        drill, size = float(first(v, 'drill')[1]), float(first(v, 'size')[1])
        assert drill >= .3 and (size-drill)/2 >= .15-1e-9
        exempt = special.get(uid)
        if exempt:
            assert sexpr(v) == sexpr(old_vias[uid])
            assert sexpr(fps[exempt]) == sexpr(old_fps[exempt])
        gap = min(Point(xy).distance(g)-drill/2 for o, g in smd
                  if not (o['ref'] == exempt and o['pin'] == '33'))
        assert gap >= .15-1e-6, (uid, gap)
        drills.append(dict(uuid=uid, xy_mm=xy, hole_edge_to_SMD_copper_mm=gap,
                           retained_mask_covered_EP_ref=exempt))
    assert sum(r['retained_mask_covered_EP_ref'] is not None for r in drills) == 21
    nr = out/'stage-connectivity-review.json'
    native = json.loads(nr.read_text())
    assert all(sha(Path(p)) == h for p, h in native['source_sha256'].items())
    assert native['copper_layer_count'] == 8
    assert {(z['net'],z['layer']) for z in native['planes']} == {('AGND','In1.Cu'),('5V_DIG','In2.Cu'),('AGND','In4.Cu'),('AGND','In6.Cu')}
    plane_cp = ROOT/'staging'/capture_label/'capture.json'
    plane_capture = json.loads(plane_cp.read_text())
    assert plane_capture['source_sha256'][str(pcb)] == sha(pcb)
    assert all(sha(Path(p)) == h for p, h in plane_capture['source_sha256'].items())
    planes = []
    for zone in native['planes']:
        layer, net = zone['layer'], zone['net']
        # Filled-zone contours alone omit thermal pad copper. The small
        # J1007 ground lobe joins the main fill through its actual THT pad.
        # Require one physical same-net copper component, including every
        # captured pad, via and track on the layer; do not waive a split.
        shapes = [make_valid(shape(zone['polygons']))]
        shapes += [make_valid(shape(o['layers'][layer])) for o in plane_capture['objects']
                   if o['net'] == net and o['layers'].get(layer)]
        copper = unary_union(shapes)
        assert copper.geom_type == 'Polygon' and copper.is_valid, (layer, copper.geom_type)
        planes.append(dict(layer=layer, net=net, filled_zone_regions=len(zone['polygons']),
                           actual_copper_components_including_pads_tracks_and_vias=1,
                           actual_copper_area_mm2=copper.area))
    assert native['preserved_power_ground_pads'] == 201
    assert native['preserved_local_connections'] == 39 and native['preserved_thermal_connections'] == 33
    assert native['uncapped_open_connections'] == review['uncapped_open_connections']
    sd_path = ROOT/'staging/digital-sd-matched-routes-01/construction.json'
    sd_recipe = json.loads(sd_path.read_text())
    by_net = {r['net']: r for r in native['nets']}
    sd = []
    for row in sd_recipe['carrier_path_totals']:
        nets = [by_net['/PROCESSOR/SDMMC_'+row['signal']+suffix] for suffix in ('', '_SRC')]
        assert all(r['all_pads_connected'] for r in nets)
        length = sum(r['planar_copper_length_mm'] for r in nets)
        assert math.isclose(length, row['carrier_planar_mm'], abs_tol=1e-5)
        assert sum(r['via_count'] for r in nets) == 1
        sd.append(dict(signal=row['signal'], carrier_planar_mm=length, via_count=1))
    inputs = [Path(__file__), pcb, pcb.with_suffix('.kicad_pro'), rp, out/'drc.json', out/'netlist.xml',
              base, cp, captured_pcb, plane_cp, thermal_path, nr, sd_path, shift_source, shift_result,
              ROOT/'digital_core_layout.py', ROOT/'route_nf_surface.py',template_path,templates_path,moves_path,blank_path,latch_path,pot_path,pot_templates,pot_template,serial_path]
    return dict(source_sha256={str(p): sha(p) for p in inputs},
                changed_component_refs=changed, declared_R3015_position_mm=[75.25,21.], connector_shift_delta=shift_delta, conditional_courtyard_THT_and_mount_clearances_pass=True,
                geometry_delta_from_DC03=delta, drill_review=drills, planes=planes,
                minimum_drill_to_nonexempt_SMD_gap_mm=min(r['hole_edge_to_SMD_copper_mm'] for r in drills),
                retained_EP_process_hold_vias=21, SD_carrier_paths=sd,
                SD_planar_spread_mm=max(r['carrier_planar_mm'] for r in sd)-min(r['carrier_planar_mm'] for r in sd),
                SD_Seed_socket_card_loading_impedance_timing_qualified=False,
                uncapped_open_connections=native['uncapped_open_connections'],
                retained_native_warnings=len(drc['violations']),
                physical_eight_layer_stack_accepted=False,
                complete_assembly_and_fabrication_qualified=False, fabrication_released=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--capture', default='digital-coordinated-six-clean-inputs-117')
    args = parser.parse_args()
    assert all(c.isalnum() or c in '-_' for c in args.source)
    assert all(c.isalnum() or c in '-_' for c in args.capture)
    result = check(args.source, args.capture)
    with (ROOT/'staging'/args.source/'corridor-audit.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print('Placement/drill/SD audit passed;', result['uncapped_open_connections'], 'opens;',
          round(result['SD_planar_spread_mm'], 3), 'mm SD spread')
