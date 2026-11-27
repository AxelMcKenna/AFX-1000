"""Export frozen installation roles and recursive hashes for the unified workflow."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
BASE=HERE.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def build():
    sources={}
    def bind(p):
        p=p.resolve();key=str(p.relative_to(REPO))
        if key in sources:return
        sources[key]=sha(p)
        if p.suffix=='.scad':
            for n in re.findall(r'(?:use|include)\s*<([^>]+)>',p.read_text()):bind(p.parent/n)
    bind(HERE/'parts.scad')
    rows=[
      ('cooling_shell','installed','housing_replacement','r9/cooling_candidate.scad','tbh09_shell_variant','Shell with current fan ports, exhaust and lead bay bores. Replaces baseline shell; never add both.','Printed tolerance and actual part receiving remain open.'),
      ('cooling_installed','installed','cooling_structure','r9/cooling_candidate.scad','tbh09_installed','Complete r9 pods, guards, mesh, fastener allocations and r8 internal supports.','Mixed manufactured/printed receiving geometry; physical retention and torque unqualified.'),
      ('cooling_fans','receiving','fan_body_envelope','r9/cooling_candidate.scad','tbh09_fans','Two fan body reservations with mounting holes.','Actual factory lead emergence remains undimensioned; fan motion/airflow is not represented.'),
      ('cooling_internal_harness','receiving','wire_envelope','r8/terminal_harness.scad','tbh08_harness','Internal bundle paths and six individual terminal transitions.','Inflated nominal path; receiving OD, formation and service acceptance required.'),
      ('cooling_external_harness','receiving','wire_envelope','r9/cooling_candidate.scad','tbh09_external_leads','External datum-to-port fan lead routes.','Excludes undimensioned factory exit to first datum; not a finished cut length.'),
      ('cooling_tie_path','receiving','loose_strap_envelope','r9/cooling_candidate.scad','tbh09_tie_paths','Loose strap routing reservation through lead-bay bridge.','Uncompressed installation path, not final tightened strap shape or pull-strength evidence.'),
      ('cooling_tie_head','receiving','tie_head_envelope','r9/cooling_candidate.scad','tbh09_tie_head_reservations','Two project maximum tie-head receiving boxes.','Project limit, not supplier-certified dimensions.'),
      ('panel_mates','receiving','connector_envelope','r10_interfaces/panel_mates.scad','tbh10_panel_mates','Six dual-row panel mating reservations with negative-Y latch orientation.','Conditional seated stack and retention/polarization; cable exits are not represented.'),
    ]
    components=[]
    for ident,role,category,src,module,desc,uncertain in rows:
        assert re.search(r'\bmodule\s+'+module+r'\s*\(\s*\)',(BASE/src).read_text()),module
        components.append(dict(id=ident,source=str((HERE/'parts.scad').relative_to(REPO)),module=ident,role=role,category=category,description=desc,uncertainty=uncertain,source_definition=str((BASE/src).relative_to(REPO)),source_module=module,parameters={},coordinate_frame='installed housing mm',geometry_parameters='Frozen upstream; no adapter overrides'))
    artifacts=['r9/verification.json','r9/external-path.json','r9/length-budget.json','r8/verification.json','r10_interfaces/mate-envelopes.json','r10_interfaces/verification.json','r11_distribution/anode-topology.json','r11_distribution/ground-topology.json','r11_distribution/verification.json','r11_distribution/ground-verification.json']
    for name in artifacts:bind(BASE/name)
    bind(Path(__file__))
    registry=dict(schema_version=1,owner='installation',components=components,source_sha256=sources,
      intentional_contacts=[dict(components=['cooling_shell','cooling_installed'],reason='Only r8 support plates seat on shell at X2.8, Y118.5/171.5. Existing source excludes a0.02mm seating slab; this is not a waiver for the whole assembly pair.',evidence='hardware/cad/two_board_installation_06/r8/supports.scad:2239',blanket_pair_exclusion=False,contact_mask_contract={'x_mm':[2.79,2.81],'y_centres_mm':[118.5,171.5],'y_half_extent_mm':4.01,'z_mm':[20.99,42.01]},required_policy='Any other nonempty intersection must fail or receive separate exact contact evidence.')],
      external_contacts=[dict(component='cooling_internal_harness',baseline_references=['F_J202','F_J203'],reason='Each terminal set intentionally enters its own XHP-3 receiving connector; source-specific obstacle lists exclude only the matching connector.',evidence='hardware/cad/two_board_installation_06/r8/terminal_harness.scad:22',blanket_pair_exclusion=False),dict(component='cooling_installed',baseline_role='lid',reason='Root trial10 classified inherited pod/lid seating as identical zero-volume coincidence. Do not waive any positive-volume collision.',evidence='hardware/cad/two_board_integrated_07/trial10-support-contacts/review.json',blanket_pair_exclusion=False)],
      parameter_contracts=dict(units='mm',frame='Original housing world coordinates; no translation/rotation/scaling',shell_replaces='two_board_print_01 housing shell',overall_modeled_envelope_mm=[363.6,192.4,45.6],envelope_excludes=['feet','external plugs'],panel_mate_top_z_mm=26.44,panel_mate_latch_direction='negative Y',panel_mate_cable_exits_included=False,tie_head_receiving_box_mm=[5.5,5.5,3.4],internal_wire_max_OD_mm=1.9,internal_terminal_native_radius_mm=.97,external_bundle_native_radius_mm=2.57,external_bundle_nominal_radius_mm=2.5,external_bend_radius_mm=10,caller_tessellation='Preserve caller resolution in cache key; source explicit facet settings remain authoritative'),
      electrical_topology=dict(anode='hardware/cad/two_board_installation_06/r11_distribution/anode-topology.json',ground='hardware/cad/two_board_installation_06/r11_distribution/ground-topology.json',anode_splices=34,ground_splices=26,wires=129,physically_routed=False,cad_roles=[],proposed_daisy_chain_revision_implemented=False),
      runtime_contract=dict(native_macos_allowed=False,separate_harness_parts_required=True,reason='Combined internal+external native union timed out in root trial12; preserve separate checks.',isolated_image='openscad/openscad@sha256:ad0426f9f16f73211765c0ad2a269af8603bcb5954e35564c126ed1555140dc2',per_process_timeout_seconds=60),fabrication_released=False)
    (HERE/'registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    print(len(components),'roles;',len(sources),'dependencies')
if __name__=='__main__':build()
