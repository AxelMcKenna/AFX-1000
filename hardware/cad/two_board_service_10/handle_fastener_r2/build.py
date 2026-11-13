"""Unselected flat-seat service handle with explicit receiving bounds."""
import json, math
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
H=Path(__file__).resolve().parent

def run():
    previous=H/'previous-manifest.json'
    if not previous.exists():previous.write_bytes((w.HERE/'current.json').read_bytes())
    data,parts,_,_=w.load_manifest(previous)
    roles={'cap_handle_body_r2':'installed','cap_handle_r2':'installed','cap_handle_screw_r2':'receiving',
           'cap_handle_withdrawal_r2':'motion','cap_handle_driver_r2':'receiving',
           'cap_handle_local_lift_r2':'motion','cap_handle_motion_r2':'motion'}
    for name,role in roles.items():
        assert name not in parts
        parts[name]=dict(id=name,source=w.relative(H/'parts.scad'),module=name,role=role,
                         description='Unselected removable-handle diagnostic; physical assembly and thread strength unqualified')
    bindings=dict(data['_loaded_sources'])
    for p in [Path(__file__),H/'parts.scad',*sorted((H/'sources').glob('*.pdf'))]:bindings[w.relative(p)]=w.sha(p)
    registry=dict(schema_version=1,components=list(parts.values()),source_sha256=bindings,
                  intentional_contacts=sum((r['intentional_contacts'] for r in data['contracts']),[]))
    manifest=json.loads(previous.read_text());manifest['registries']=[w.relative(H/'registry.json')];manifest['checks']=[]
    # Original lever and its swept envelope are replaced in this diagnostic.
    # Other selected roles remain opponents; the screw is removed for service.
    opponents=sorted(set(parts)-set(roles)-{'sensor_lever_nominal','sensor_lever_motion'})
    coverage={}
    for left in ['cap_handle_r2','cap_handle_withdrawal_r2','cap_handle_driver_r2','cap_handle_motion_r2']:
        groups=[opponents[i:i+8] for i in range(0,len(opponents),8)]
        assert sum(groups,[])==opponents
        coverage[left]=groups
        for i,group in enumerate(groups):manifest['checks'].append(dict(id=left+'_group_'+str(i+1),left=[left],right=group,expect='empty'))
    manifest['checks'].append(dict(id='cap_handle_local_lift',left=['cap_handle_local_lift_r2'],right=['cap_handle_body_r2'],expect='empty'))
    manifest['unresolved'].append('Handle r2 diagnostic only: original lever remains selected; candidate raises handle top1.2mm, uses sourced cap screw and project-only receiving tolerances. Printed threads, tool/hand space, torque, service wiring and retention remain unqualified.')
    (H/'candidate.json').write_text(json.dumps(manifest,indent=2)+'\n')
    budget=dict(tip_min=56.4-6.3,tip_max=56.6-5.7,tip_to_pilot_bottom_min=(56.4-6.3)-49.7,
                engagement_min=55.5-(56.6-5.7),full_thread_allocation_min=55.5-(56.6-5.7)-.4-.2,
                head_recess_min=58.7-(56.6+2),bearing_roof_min=56.4-55.7,
                radial_head_clearance_min=4.1/2*math.cos(math.pi/64)-3.8/2-.1,
                radial_shank_clearance_min=2.35/2*math.cos(math.pi/64)-1-.1,
                chord_error_max=28.5*(1-math.cos(math.radians(.5))))
    assert min(budget.values())>0
    contract=dict(screw='SSCF-M2-6-A2',supplier_pdf=w.relative(H/'sources/SSCF-M2-6-A2.pdf'),
      supplier_bounds=dict(head_diameter=[3.62,3.8],head_height=[1.86,2.0],length_nominal=6,thread_pitch=.4,hex_size=1.5,full_thread=True),
      receiving_requirements_not_supplier_guarantees=dict(length=[5.7,6.3],head_seat_z=[56.4,56.6],stem_seat_z=[55.5,55.7],
      pilot_bottom_z=[49.5,49.7],handle_top_z=[58.7,58.9],counterbore_diameter=[4.1,4.3],shank_bore_diameter=[2.35,2.45],registration_max=.1,
      incomplete_tip_allowance=.4,thread_entry_allowance=.2,underhead_fillet_envelope='coneD2to2.6/H0.2'),
      nominal_original_handle_top=57.6,nominal_candidate_top=58.8,budget_mm=budget,exact_opponent_groups=coverage,
      original_selected_lever_unchanged=True,physical_qualified=False,fabrication_released=False,source_sha256=bindings)
    (H/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    bindings[w.relative(H/'contract.json')]=w.sha(H/'contract.json')
    (H/'registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    w.load_manifest(H/'candidate.json')
    print(budget)
if __name__=='__main__':run()
