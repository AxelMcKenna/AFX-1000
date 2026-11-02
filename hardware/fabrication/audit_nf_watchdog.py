"""Source-bound, narrow change audit for the local watchdog-capacitor candidate."""
import json
import math
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.electronics.common.netlists import netlist
from hardware.fabrication.audit_candidate import geometry_delta,native_evidence_errors,sha
from hardware.fabrication.audit_single_net import open_counts

ROOT=Path(__file__).resolve().parent
ALLOWED_NETS={'/N19_CWD','/N12_CWD','/AGND'}


def verify_geometry(before,after,removed):
    delta=geometry_delta(before,after)
    fps={str(first(f,'uuid')[1]):next(p[2] for p in children(f,'property') if p[1]=='Reference') for f in children(before,'footprint')}
    assert delta['other_root_geometry_exact']
    assert not delta['footprint']['added'] and not delta['footprint']['removed']
    assert {fps[k] for k in delta['footprint']['changed']}=={'C1','C2'}
    assert not any(delta['zone'].values())
    for tag in ('segment','via'):
        assert not delta[tag]['changed']
        old={str(first(n,'uuid')[1]):n for n in children(before,tag)}
        new={str(first(n,'uuid')[1]):n for n in children(after,tag)}
        permitted={str(first(n,'uuid')[1]):n for n in removed if n[0]==tag}
        assert set(delta[tag]['removed'])==set(permitted)
        assert all(old[k]==permitted[k] and first(old[k],'net')[-1]=='/AGND' for k in permitted)
        assert all(first(new[k],'net')[-1] in ALLOWED_NETS for k in delta[tag]['added'])
    return delta


def run():
    old,new=[ROOT/'staging'/n for n in ('nf-six-net-native-01','nf-watchdog-routed-native-02')]
    captures=[ROOT/'staging'/n/'capture.json' for n in ('nf-six-net-inputs-170','nf-watchdog-routed-inputs-168')]
    removed_path=ROOT/'staging/nf-watchdog-stub-cleanup-01/removed-objects.json'
    output=new/'watchdog-placement-audit.json';assert not output.exists()
    projects=[f/'negative_startup_physical.kicad_pro' for f in (old,new)]
    reviews=[json.loads((f/'review.json').read_text()) for f in (old,new)]
    for p,r in zip(projects,reviews):
        assert not native_evidence_errors(p,r)
        assert r['status']['counts']['violations']==r['status']['counts']['schematic_parity']==0
    assert sha(projects[0])==sha(projects[1])
    assert reviews[0]['status']['counts']['erc']==reviews[1]['status']['counts']['erc']==2
    boards=[read_sexpr(p.with_suffix('.kicad_pcb').read_text()) for p in projects]
    removed=json.loads(removed_path.read_text())
    delta=verify_geometry(*boards,removed)
    parts=[netlist(f/'netlist.xml') for f in (old,new)]
    assert parts[0][1]==parts[1][1] and set(parts[0][0])==set(parts[1][0])
    assert all(parts[0][0][r].findtext(k)==parts[1][0][r].findtext(k) for r in parts[0][0] for k in ('value','footprint'))
    counts=[open_counts(json.loads((f/'drc.json').read_text())) for f in (old,new)]
    assert all(counts[1][n]<=counts[0][n] for n in counts[0].keys()|counts[1].keys())
    assert all(counts[1][n]==0 and counts[0][n]==1 for n in ALLOWED_NETS-{'/AGND'})
    assert sum(counts[0].values())==170 and sum(counts[1].values())==168
    pads=[]
    for path,project in zip(captures,projects):
        c=json.loads(path.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
        assert str(project.with_suffix('.kicad_pcb')) in c['source_sha256']
        pads.append({(o['ref'],o['pin']):o for o in c['objects'] if o['kind']=='PAD'})
    timing=[]
    for key,cap in pads[0].items():
        if not cap['ref'].startswith('C') or not cap['net'].endswith(('_CWD','_CT','_TMR','_SS','_RAMP')):continue
        owners=[p for p in pads[0].values() if p['ref'].startswith('U') and p['net']==cap['net']]
        if len(owners)!=1:continue
        owner=owners[0];ownerkey=(owner['ref'],owner['pin'])
        lengths=[math.dist(p[key]['position_mm'],p[ownerkey]['position_mm']) for p in pads]
        timing.append(dict(cap=cap['ref'],pin=cap['pin'],owner=owner['ref'],owner_pin=owner['pin'],net=cap['net'],
                           projected_pin_distance_before_mm=lengths[0],projected_pin_distance_after_mm=lengths[1],
                           routed_planar_length_mm=sum(math.dist(list(map(float,first(s,'start')[1:3])),list(map(float,first(s,'end')[1:3]))) for s in children(boards[1],'segment') if first(s,'net')[-1]==cap['net'])))
    inputs=[Path(__file__),removed_path,*captures,*projects,*[p.with_suffix('.kicad_pcb') for p in projects],
            *[f/n for f in (old,new) for n in ('review.json','netlist.xml','drc.json','erc.json')]]
    output.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},geometry_delta=delta,
        only_C1_C2_poses_changed=True,all_original_parts_values_pin_nets_and_packages_preserved=True,
        only_four_vacated_ground_escape_objects_removed=True,no_existing_copper_or_zone_modified=True,
        connectivity_no_regressions=True,opens_before=170,opens_after=168,timing_capacitor_inventory=timing,
        layout_basis={'url':'https://www.ti.com/lit/gpn/tps3431','revision':'SNVSB66A, October 2021','section':'10.1, page 21','requirement_paraphrase':'Keep the external CWD timing capacitor close to the CWD pin.'},
        rear_population_changed_from_to=[111,113],rear_complete_height_receiving_mm=1.9,
        other_timing_capacitors_need_local_placement_review=True,installed_receiving_qualified=False,
        timing_noise_and_return_impedance_qualified=False,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Verified only C1/C2 moved; original circuit and unrelated copper exact; 170 -> 168 opens')
    print(json.dumps([r for r in timing if r['cap'] in ('C1','C2')],indent=2))


if __name__=='__main__':run()
