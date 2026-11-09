"""Select the independently checked digital quiet-reference checkpoint."""
import json
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape


def run():
 power=STAGING/'two-board-power-digital-reference-native-02';previous=STAGING/'two-board-fabrication-status-38/status.json'
 cp=STAGING/'two-board-power-routing-inputs-2320-digital-reference-02/capture.json'
 reports=[previous,cp,*[STAGING/f'two-board-power-digital-reference-filled-{i:02d}/local-plane-fill.json' for i in [2,3]],STAGING/'two-board-signal-routed-native-03/review.json',*[power/n for n in ['review.json','digital-reference-routing.json','digital-reference-track-routing.json','digital-reference-review.json','rejected-source-net-status.json','plots/native-plots.json','plots/preview-render.json','plots/reference-render.json','plots/visual-review.json']]]
 count=0
 for p in reports:
  d=json.loads(p.read_text())
  for field in ['source_sha256','artifact_sha256']:
   for name,h in d.get(field,{}).items():
    q=Path(name)
    if not q.is_absolute():q=(REPO if name.startswith(('hardware/','tests/')) else p.parent)/q
    assert sha(q)==h,(p,name);count+=1
 audit=json.loads((power/'digital-reference-review.json').read_text())
 assert audit['new_opens']==2320 and audit['closed_connections']==0 and audit['unchanged_native_connection_groups']==3058
 assert audit['unchanged_complete_footprints']==1101 and audit['unchanged_physical_objects']==6590 and audit['previous_full_width_reference_cases_preserved']==234
 assert audit['source_plane_contacts_preserved']==20 and len(audit['quiet_returns'])==4 and audit['replacement_own_quiet_reference_uncovered_mm2']<1e-6
 assert audit['retired_tracks']==audit['added_tracks']==6 and not audit['full_new_route_reference_complete']
 cap=json.loads(cp.read_text());objects={o['uuid']:o for o in cap['objects']};zones=[z for z in cap['zones'] if z['net']=='PWR_AGND']
 assert sum(o['kind']=='PCB_TRACK' for o in objects.values())==2567 and sum(o['kind']=='PCB_VIA' for o in objects.values())==308 and len(cap['zones'])==36
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
 complete=sum(min(r['adjacent_uncovered_mm2'].values())<1e-6 for r in audit['new_route_reference_screen']);assert complete==24
 status=json.loads(previous.read_text())
 status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,*route_sources,power/'README.md',REPO/'hardware/fabrication/route_nf_surface.py']},previous_status=str(previous.relative_to(REPO)),previous_status_scope='TBP38 circuit/placement evidence retained. TBP39 changes source layer and reference planes, and replaces six DVDT segments; current audits verify those changes and retained geometry.',verified_direct_source_and_artifact_bindings=count,
  power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2320,power_copper_segments=2567,power_copper_vias=308,power_filled_zones=36,power_connections_closed_this_pass=0,power_added_tracks_this_pass=6,power_retired_tracks_this_pass=6,power_retired_vias_this_pass=0,power_added_vias_this_pass=0,power_added_zones_this_pass=6,
  power_previous_native_connection_groups_preserved=3058,power_moved_footprints_this_pass=0,power_changed_pad_instances_this_pass=0,power_complete_footprints_unchanged=1101,power_complete_footprint_geometries_unchanged=1101,power_changed_component_values_this_pass=0,power_unchanged_existing_zone_fills=24,power_changed_existing_zone_fills=6,power_edited_existing_zone_outlines=5,power_existing_zone_layer_changes=1,power_native_group_merges=[],power_previous_full_width_adjacent_ground_reference_cases_preserved=234,power_fast_OV_current_reference_coverage=coverage,
  power_digital_reference_review=str((power/'digital-reference-review.json').relative_to(REPO)),power_digital_source_layer='In4.Cu',power_digital_source_previous_layer='In6.Cu',power_digital_source_plane_contacts_preserved=20,power_digital_eFuse_quiet_islands=audit['quiet_returns'],power_digital_reference_complete_route_sections=complete,power_digital_reference_screened_route_sections=28,power_digital_reference_residuals=audit['remaining_via_edge_reference_gaps'],power_digital_own_quiet_reference_screen=audit['own_quiet_reference_screen'],power_digital_cell_full_new_route_reference_complete=False,power_digital_cell_current_thermal_transient_qualified=False,
  power_digital_source_In5_reference_uncovered_mm2=audit['source_In5_reference_uncovered_mm2'],power_digital_source_In5_reference_covered_fraction=1-audit['source_In5_reference_uncovered_mm2']/audit['source_In5_reference_screen_area_mm2'],power_digital_source_reference_full_area_coverage=audit['source_In5_reference_uncovered_mm2']<1e-6,power_visual_evidence_scope='Current TBP39 front/back, six-inner overview and six digital-cell source/reference detail views inspected.',power_inlet_resistance_model_scope='TBP35 historical conditional screen; TBP36–TBP39 copper/refills/layer changes and current sharing are not modeled.',fabrication_released=False,goal_complete=False)
 status['next_required_design_work']=['Shorten or qualify quiet returns and establish actual support-node parasitics, via-edge reference behavior and local bypass loops','Route digital eFuse protected outputs, thermal copper, PG/follower controls and remaining source loads','Complete analog regulator outputs, remaining module supplies, force/quiet returns and signal routing','Establish actual load/startup states, effective capacitance, current sharing, accepted stack/plating and thermal/fault limits','Resolve ESS package inputs, final interfaces, complete housing/fastener/cooling/harness fit, exact BOM and manufacturing deliverables','Prepare the reviewed prototype bring-up plan and complete applicable release checks']
 out=STAGING/'two-board-fabrication-status-39';out.mkdir(exist_ok=False);(out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
 print(json.dumps(dict(bindings=count,power_opens=2320,signal_opens=251,fully_referenced_sections=complete,fast_OV_references=len(coverage),fabrication_released=False)))
if __name__=='__main__':run()
