"""Select the independently verified relocated startup-logic checkpoint."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha

def run():
 power=STAGING/'two-board-power-startup-logic-native-02'
 previous=STAGING/'two-board-fabrication-status-40/status.json'
 cp=STAGING/'two-board-power-routing-inputs-2294-startup-logic-02/capture.json'
 reports=[previous,cp,STAGING/'two-board-startup-logic-plan-02/manifest.json',STAGING/'two-board-power-startup-logic-filled-02/local-plane-fill.json',STAGING/'two-board-signal-routed-native-03/review.json',*[power/n for n in ['review.json','startup-logic-routing.json','startup-logic-review.json','startup-logic-reference-review.json','rejected-source-net-status.json','plots/native-plots.json','plots/preview-render.json','plots/logic-render.json','plots/visual-review.json']]]
 count=0
 for p in reports:
  d=json.loads(p.read_text())
  for field in ['source_sha256','artifact_sha256']:
   for name,h in d.get(field,{}).items():
    q=Path(name)
    if not q.is_absolute():q=(REPO if name.startswith(('hardware/','tests/')) else p.parent)/q
    assert sha(q)==h,(p,name);count+=1
 audit=json.loads((power/'startup-logic-review.json').read_text())
 refs=json.loads((power/'startup-logic-reference-review.json').read_text())
 route=json.loads((power/'startup-logic-routing.json').read_text());cap=json.loads(cp.read_text())
 assert audit['new_opens']==2294 and audit['closed_connections']==16 and audit['all_other_native_groups_preserved']
 assert audit['moved_pad_count']==20 and audit['retained_part_count']==1086 and audit['retained_pin_entries']==3420
 assert len(audit['prior_reference_coverage'])==299 and len(audit['own_quiet_reference_preservation'])==22 and len(audit['quiet_returns'])==4
 assert audit['source_plane_contacts_preserved']==20 and audit['new_logic_fully_referenced_sections']==2 and len(audit['new_logic_reference'])==32
 assert refs['retained_support_fully_referenced_sections']==24 and len(refs['retained_support_reference'])==28 and len(refs['fast_OV_reference'])==33
 assert len(cap['objects'])==6742 and len(cap['all_groups'])==3032 and cap['footprints_captured']==1101
 assert sum(o['kind']=='PCB_TRACK' for o in cap['objects'])==2683 and sum(o['kind']=='PCB_VIA' for o in cap['objects'])==338 and len(cap['zones'])==36
 assert route['added_tracks']==83 and route['added_vias']==22 and len(route['moves'])==4 and len(route['edited_zone_outlines'])==1 and len(route['refilled_existing_zones'])==7
 status=json.loads(previous.read_text())
 status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},previous_status=str(previous.relative_to(REPO)),previous_status_scope='TBP40 evidence remains applicable except the four declared logic/capacitor poses, two retired U29 terminal tracks and In5 return extension. TBP41 independently verifies exactly sixteen joins and preservation of all prior connections and complete reference cases.',verified_direct_source_and_artifact_bindings=count,
  power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2294,power_copper_segments=2683,power_copper_vias=338,power_filled_zones=36,power_native_connection_groups=3032,power_connections_closed_this_pass=16,power_added_tracks_this_pass=83,power_retired_tracks_this_pass=2,power_retired_vias_this_pass=0,power_added_vias_this_pass=22,power_added_zones_this_pass=0,
  power_previous_native_connection_groups_preserved=3048,power_moved_footprints_this_pass=4,power_changed_pad_instances_this_pass=20,power_complete_footprints_unchanged=1097,power_complete_footprint_geometries_unchanged=1097,power_changed_component_values_this_pass=0,power_schematic_pin_net_changes_this_pass=0,power_unchanged_existing_zone_fills=29,power_changed_existing_zone_fills=7,power_edited_existing_zone_outlines=1,power_existing_zone_layer_changes=0,power_native_group_merges=audit['declared_native_joins'],power_previous_full_width_adjacent_ground_reference_cases_preserved=299,power_fast_OV_current_reference_coverage=refs['fast_OV_reference'],
  power_digital_startup_review=str((power/'startup-logic-review.json').relative_to(REPO)),power_digital_reference_review=str((power/'startup-logic-reference-review.json').relative_to(REPO)),power_digital_source_layer='In4.Cu',power_digital_source_previous_layer='In4.Cu',power_digital_source_plane_contacts_preserved=20,power_digital_eFuse_quiet_islands=audit['quiet_returns'],power_digital_reference_complete_route_sections=24,power_digital_reference_screened_route_sections=28,power_digital_reference_residuals=[r for r in refs['retained_support_reference'] if min(r['adjacent_uncovered_mm2'].values())>=1e-6],power_digital_own_quiet_reference_screen=audit['own_quiet_reference_preservation'],power_digital_cell_full_new_route_reference_complete=False,power_digital_cell_current_thermal_transient_qualified=False,
  power_startup_fully_referenced_sections=2,power_startup_reference_screened_sections=32,power_startup_reference_scope='TBP41 relocated U29/U40 logic fanout, interconnects and AUX branches; adjacent-ground projection only. Complete startup chain and current/timing/noise qualification remain unfinished.',power_startup_full_reference_complete=False,power_startup_complete=False,power_startup_reference_details=audit['new_logic_reference'],power_retained_TBP40_startup_reference_complete_sections=refs['new_startup_fully_referenced_sections'],power_retained_TBP40_startup_reference_screened_sections=len(refs['new_startup_reference']),
  power_digital_source_plane_area_mm2=refs['source_plane_area_mm2'],power_digital_source_In5_reference_uncovered_mm2=refs['source_In5_uncovered_mm2'],power_digital_source_In5_reference_covered_fraction=1-refs['source_In5_uncovered_mm2']/refs['source_In5_screen_area_mm2'],power_digital_source_reference_full_area_coverage=refs['source_In5_uncovered_mm2']<1e-6,power_visual_evidence_scope='Eleven current TBP41 views directly inspected: front/back overview, six-inner overview and all eight startup-logic detail layers.',power_inlet_resistance_model_scope='TBP35 historical conditional screen; TBP36–TBP41 copper/refills/layer changes and current sharing are not modeled.',fabrication_released=False,goal_complete=False)
 status['next_required_design_work']=['Complete new logic and retained PG/EN ground-reference coverage while preserving all quiet-return owners','Complete U29 ALL_RAILS_ALLOW and U30/U34/U41 supplies/bypass, remaining gate/receiver paths and PG pull-up AUX ends','Complete digital eFuse protected outputs/thermal copper, analog regulator outputs, remaining module supplies, force/quiet returns and signal routing','Establish actual load/startup/fault states, effective capacitance, current sharing, accepted stack/plating and thermal limits','Resolve ESS package inputs, final interfaces, complete housing/fastener/cooling/harness fit, exact BOM and manufacturing deliverables','Prepare the reviewed prototype bring-up plan and complete applicable release checks']
 out=STAGING/'two-board-fabrication-status-41';out.mkdir(exist_ok=False)
 (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
 print(json.dumps(dict(bindings=count,power_opens=2294,signal_opens=251,closed_connections=16,new_logic_fully_referenced_sections=2,fabrication_released=False)))

if __name__=='__main__':run()
