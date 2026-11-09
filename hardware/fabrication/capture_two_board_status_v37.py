"""Select reviewed digital source distribution without claiming fabrication readiness."""
import json
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape


def run():
    power=STAGING/'two-board-power-digital-distribution-native-02'
    previous=STAGING/'two-board-fabrication-status-36/status.json'
    cp=STAGING/'two-board-power-routing-inputs-2340-digital-distribution-02/capture.json'
    reports=[previous,cp,STAGING/'two-board-power-digital-distribution-filled-02/local-plane-fill.json',
             STAGING/'two-board-signal-routed-native-03/review.json',*[power/n for n in [
             'review.json','digital-distribution-routing.json','digital-distribution-review.json','rejected-source-net-status.json',
             'plots/native-plots.json','plots/preview-render.json','plots/digital-render.json','plots/digital-source-render.json','plots/visual-review.json']]]
    count=0
    for p in reports:
        d=json.loads(p.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in d.get(field,{}).items():
                q=Path(name)
                if not q.is_absolute():q=(REPO if name.startswith(('hardware/','tests/')) else p.parent)/q
                assert sha(q)==h,(p,name);count+=1
    audit=json.loads((power/'digital-distribution-review.json').read_text())
    assert audit['new_opens']==2340 and audit['all_prior_groups_preserved']==3107
    assert audit['all_footprints_unchanged']==1101 and audit['previous_full_width_adjacent_ground_cases_preserved']==229
    assert len(audit['quiet_ground_islands'])==4 and audit['all_vias_screened']==300
    cap=json.loads(cp.read_text());objects={o['uuid']:o for o in cap['objects']}
    zones=[z for z in cap['zones'] if z['net']=='PWR_AGND']
    route_sources=[STAGING/'two-board-power-input-tvs-native-01'/n for n in ['fast-ov-routing.json','fast-ov-return-routing.json']]
    routes=[]
    for p in route_sources:routes.extend(r for r in json.loads(p.read_text())['routes'] if all(u in objects for u in r['segment_uuids']))
    assert len(routes)==33
    coverage=[];layers=cap['copper_layers']
    for r in routes:
        g=LineString(r['path_mm']).buffer(r['width_mm']/2)
        for o in objects.values():
            if o['kind']=='PCB_VIA' and o['net']==r['net'] and o['net']!='PWR_AGND':g=g.difference(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
        i=layers.index(r['layer']);adjacent=[layers[j] for j in [i-1,i+1] if 0<=j<len(layers)]
        areas={l:g.difference(unary_union([shape(z['polygons']) for z in zones if z['layer']==l]).buffer(.0015)).area for l in adjacent}
        assert min(areas.values())<1e-6,(r['label'],areas)
        coverage.append(dict(label=r['label'],adjacent_reference_uncovered_mm2=areas))
    status=json.loads(previous.read_text())
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,*route_sources,power/'README.md',REPO/'hardware/fabrication/route_nf_surface.py']},
        previous_status=str(previous.relative_to(REPO)),
        previous_status_scope='TBP36 feed/return and earlier circuit evidence retained; TBP37 direct reports describe current digital distribution and inlet refills.',
        verified_direct_source_and_artifact_bindings=count,power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2340,power_copper_segments=2491,power_copper_vias=300,power_filled_zones=30,
        power_connections_closed_this_pass=29,power_added_tracks_this_pass=47,power_added_vias_this_pass=38,power_added_zones_this_pass=6,
        power_previous_native_connection_groups_preserved=3107,power_complete_footprints_unchanged=1101,
        power_complete_footprint_geometries_unchanged=1101,power_changed_component_values_this_pass=0,
        power_unchanged_existing_zone_fills=20,power_changed_existing_zone_fills=4,power_edited_existing_zone_outlines=2,
        power_native_group_merges=audit['native_group_merges'],power_all_vias_screened=300,
        power_minimum_all_via_drill_to_SMD_mm=audit['minimum_all_via_drill_to_SMD_mm'],
        power_previous_full_width_adjacent_ground_reference_cases_preserved=229,power_fast_OV_current_reference_coverage=coverage,
        power_digital_distribution_review=str((power/'digital-distribution-review.json').relative_to(REPO)),
        power_digital_eFuse_inputs_and_four_input_capacitors_connected=True,
        power_digital_eFuse_quiet_islands=audit['quiet_ground_islands'],power_digital_complete_source_net_connected=False,
        power_digital_source_In5_reference_uncovered_mm2=audit['source_In5_reference_uncovered_mm2'],
        power_digital_source_In5_reference_covered_fraction=1-audit['source_In5_reference_uncovered_mm2']/audit['source_In5_reference_screen_area_mm2'],
        power_digital_source_reference_full_area_coverage=False,power_digital_cell_current_thermal_transient_qualified=False,
        power_visual_evidence_scope='Current TBP37 front/back, six-inner overview, five eFuse details and four U20-source details inspected.',
        power_inlet_resistance_model_scope='TBP35 historical conditional screen; TBP36/TBP37 distribution and inlet refills are not modeled.',
        fabrication_released=False,goal_complete=False)
    status['next_required_design_work']=[
        'Complete digital eFuse output and support routing, local bypass placement/effective capacitance, thermal copper and load/startup current-sharing review',
        'Qualify U20 output transition, new digital plane and input escapes against accepted stack/plating and twice-full-load sizing',
        'Complete remaining digital source loads, analog regulator output, module input and force/quiet return distribution',
        *status['next_required_design_work']]
    out=STAGING/'two-board-fabrication-status-37';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(bindings=count,power_opens=2340,signal_opens=251,closed_connections=29,fast_OV_references=len(coverage),fabrication_released=False)))

if __name__=='__main__':run()
