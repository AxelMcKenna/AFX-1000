"""Select the independently reviewed digital support-cell checkpoint."""
import json
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape


def run():
 power=STAGING/'two-board-power-digital-cells-native-03';previous=STAGING/'two-board-fabrication-status-37/status.json'
 cp=STAGING/'two-board-power-routing-inputs-2320-digital-cells-03/capture.json'
 reports=[previous,cp,STAGING/'two-board-power-digital-cells-filled-03/local-plane-fill.json',STAGING/'two-board-signal-routed-native-03/review.json',*[power/n for n in ['review.json','digital-cell-routing.json','digital-cell-review.json','rejected-source-net-status.json','plots/native-plots.json','plots/preview-render.json','plots/cells-render.json','plots/visual-review.json']]]
 count=0
 for p in reports:
  d=json.loads(p.read_text())
  for field in ['source_sha256','artifact_sha256']:
   for name,h in d.get(field,{}).items():
    q=Path(name)
    if not q.is_absolute():q=(REPO if name.startswith(('hardware/','tests/')) else p.parent)/q
    assert sha(q)==h,(p,name);count+=1
 audit=json.loads((power/'digital-cell-review.json').read_text());construction=json.loads((power/'digital-cell-routing.json').read_text())
 assert audit['new_opens']==2320 and audit['closed_connections']==20 and audit['all_prior_connection_groups_preserved']==3078
 assert audit['moved_footprints']==15 and audit['unchanged_complete_footprints']==1086 and audit['previous_full_width_reference_cases_preserved']==233
 assert len(audit['quiet_returns'])==4 and audit['all_vias_screened']==308 and not audit['full_new_route_reference_complete']
 cap=json.loads(cp.read_text());objects={o['uuid']:o for o in cap['objects']};zones=[z for z in cap['zones'] if z['net']=='PWR_AGND']
 assert sum(o['kind']=='PCB_TRACK' for o in objects.values())==2567
 route_sources=[STAGING/'two-board-power-input-tvs-native-01'/n for n in ['fast-ov-routing.json','fast-ov-return-routing.json']];routes=[]
 for p in route_sources:routes.extend(r for r in json.loads(p.read_text())['routes'] if all(u in objects for u in r['segment_uuids']))
 assert len(routes)==33
 coverage=[];layers=cap['copper_layers']
 for r in routes:
  g=LineString(r['path_mm']).buffer(r['width_mm']/2)
  for o in objects.values():
   if o['kind']=='PCB_VIA' and o['net']==r['net'] and o['net']!='PWR_AGND':g=g.difference(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
  i=layers.index(r['layer']);adjacent=[layers[j] for j in [i-1,i+1] if 0<=j<len(layers)]
  areas={l:g.difference(unary_union([shape(z['polygons']) for z in zones if z['layer']==l]).buffer(.0015)).area for l in adjacent}
  assert min(areas.values())<1e-6,(r['label'],areas);coverage.append(dict(label=r['label'],adjacent_reference_uncovered_mm2=areas))
 status=json.loads(previous.read_text())
 status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,*route_sources,power/'README.md',REPO/'hardware/fabrication/route_nf_surface.py']},previous_status=str(previous.relative_to(REPO)),previous_status_scope='TBP37 source/circuit evidence retained; current TBP38 reports cover the moved passives, replacement routing and changed fields.',verified_direct_source_and_artifact_bindings=count,
  power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2320,power_copper_segments=2567,power_copper_vias=308,power_filled_zones=30,power_connections_closed_this_pass=20,power_added_tracks_this_pass=95,power_retired_tracks_this_pass=19,power_retired_vias_this_pass=16,power_added_vias_this_pass=24,power_added_zones_this_pass=0,
  power_previous_native_connection_groups_preserved=3078,power_moved_footprints_this_pass=15,power_changed_pad_instances_this_pass=30,power_complete_footprints_unchanged=1086,power_complete_footprint_geometries_unchanged=1086,power_changed_component_values_this_pass=0,power_unchanged_existing_zone_fills=20,power_changed_existing_zone_fills=10,power_edited_existing_zone_outlines=6,power_native_group_merges=audit['native_group_merges'],power_all_vias_screened=308,power_minimum_all_via_drill_to_SMD_mm=audit['minimum_all_via_drill_to_SMD_mm'],power_previous_full_width_adjacent_ground_reference_cases_preserved=233,power_fast_OV_current_reference_coverage=coverage,
  power_digital_cell_review=str((power/'digital-cell-review.json').relative_to(REPO)),power_digital_eFuse_support_signal_nets_connected=12,power_digital_eFuse_support_returns_connected=8,power_digital_eFuse_quiet_islands=audit['quiet_returns'],power_digital_cell_full_new_route_reference_complete=False,power_digital_eFuse_outputs_complete=False,power_digital_cell_current_thermal_transient_qualified=False,
  power_digital_source_In5_reference_uncovered_mm2=audit['source_In5_reference_uncovered_mm2'],power_digital_source_In5_reference_covered_fraction=1-audit['source_In5_reference_uncovered_mm2']/audit['source_In5_reference_screen_area_mm2'],power_digital_source_reference_full_area_coverage=audit['source_In5_reference_uncovered_mm2']<1e-6,power_moved_component_mechanical_screen_findings=construction['mechanical_screen_findings'],power_visual_evidence_scope='Current TBP38 front/back, six-inner overview and five digital-cell detail views inspected.',power_inlet_resistance_model_scope='TBP35 historical conditional screen; TBP36–TBP38 copper/refills and current sharing are not modeled.',fabrication_released=False,goal_complete=False)
 status['next_required_design_work']=[
  'Complete new support-route reference/parasitic review; shorten or qualify longer quiet-return paths',
  'Route digital eFuse protected outputs, thermal copper, PG/follower controls and remaining source loads',
  'Complete analog regulator outputs, remaining module supplies, force/quiet returns and signal routing',
  'Establish actual load/startup states, effective capacitance, current sharing, accepted stack/plating and thermal/fault limits',
  'Resolve ESS package inputs, final interfaces, complete housing/fastener/cooling/harness fit, exact BOM and manufacturing deliverables',
  'Prepare the reviewed prototype bring-up plan and complete applicable release checks']
 out=STAGING/'two-board-fabrication-status-38';out.mkdir(exist_ok=False);(out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
 print(json.dumps(dict(bindings=count,power_opens=2320,signal_opens=251,closed_connections=20,fast_OV_references=len(coverage),fabrication_released=False)))
if __name__=='__main__':run()
