"""Independent component, copper and native pad-connectivity audit of the CT revision."""
import json
import math
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.electronics.common.netlists import netlist
from hardware.fabrication.audit_candidate import geometry_delta,native_evidence_errors,sha
from hardware.fabrication.audit_single_net import open_counts

ROOT=Path(__file__).resolve().parent
MOVED={'C8','C10','C35','C37'}
ALLOWED={'/N19_BIAS_CT','/N19_VIN_VALID_CT','/N12_P03_SRC','/N19_P03_SRC','/N12_COMPLETE'}


def verify_geometry(before,after,removed):
    delta=geometry_delta(before,after)
    refs={first(f,'uuid')[1]:next(p[2] for p in children(f,'property') if p[1]=='Reference') for f in children(before,'footprint')}
    assert delta['other_root_geometry_exact'] and not any(delta['zone'].values())
    assert not delta['footprint']['added'] and not delta['footprint']['removed']
    assert {refs[k] for k in delta['footprint']['changed']}==MOVED
    for tag in ['segment','via']:
        old={first(n,'uuid')[1]:n for n in children(before,tag)}
        new={first(n,'uuid')[1]:n for n in children(after,tag)}
        permit={first(n,'uuid')[1]:n for n in removed if n[0]==tag}
        assert not delta[tag]['changed'] and set(delta[tag]['removed'])==set(permit)
        assert all(old[k]==n and first(n,'net')[-1] in {'/N12_P03_SRC','/N19_P03_SRC','/N12_COMPLETE'} for k,n in permit.items())
        assert all(first(new[k],'net')[-1] in ALLOWED for k in delta[tag]['added'])
    return delta


def verify_pad_connectivity(before_capture,after_capture):
    pads=[{(o['ref'],o['pin']):o for o in c['objects'] if o['kind']=='PAD'} for c in [before_capture,after_capture]]
    assert set(pads[0])==set(pads[1])
    partitions={}
    for key,pad in pads[0].items():
        assert pad['net']==pads[1][key]['net']
        if key[0] in MOVED:continue
        partitions.setdefault((pad['net'],pad['group']),[]).append(key)
    for keys in partitions.values():
        assert len({pads[1][key]['group'] for key in keys})==1,keys
    for cap,owner in [('C8','U21'),('C10','U20'),('C35','U26'),('C37','U25')]:
        a,b=pads[1][cap,'2'],pads[1][owner,'2']
        assert a['net']==b['net'] and a['net'] in {'/N12_P03_SRC','/N19_P03_SRC'} and a['group']==b['group']
    return pads


def run():
    old,new=[ROOT/'staging'/n for n in ['nf-watchdog-routed-native-02','nf-ct-local-native-01']]
    output=new/'ct-placement-audit.json';assert not output.exists()
    projects=[f/'negative_startup_physical.kicad_pro' for f in [old,new]]
    reviews=[json.loads((f/'review.json').read_text()) for f in [old,new]]
    for p,r in zip(projects,reviews):
        assert not native_evidence_errors(p,r)
        assert r['status']['counts']['violations']==r['status']['counts']['schematic_parity']==0
        assert r['status']['counts']['erc']==2
    assert sha(projects[0])==sha(projects[1])
    boards=[read_sexpr(p.with_suffix('.kicad_pcb').read_text()) for p in projects]
    constructions=[ROOT/'staging'/n/'construction.json' for n in ['nf-ct-routes-01','nf-ct-finish-01','nf-ct-clean-reference-01']]
    removed=[n for p in constructions for n in json.loads(p.read_text())['removed_leaf_objects']]
    removed.append(next(n for n in children(boards[0],'segment') if first(n,'uuid')[1]=='ec29140f-e434-4f05-8433-92fc43c4fb2a'))
    delta=verify_geometry(*boards,removed)
    parts=[netlist(f/'netlist.xml') for f in [old,new]]
    assert parts[0][1]==parts[1][1] and set(parts[0][0])==set(parts[1][0])
    assert all(parts[0][0][r].findtext(k)==parts[1][0][r].findtext(k) for r in parts[0][0] for k in ['value','footprint'])
    counts=[open_counts(json.loads((f/'drc.json').read_text())) for f in [old,new]]
    assert all(counts[1][n]<=counts[0][n] for n in counts[0].keys()|counts[1].keys())
    assert (sum(counts[0].values()),sum(counts[1].values()))==(168,166)
    capture_paths=[ROOT/'staging'/n/'capture.json' for n in ['nf-watchdog-routed-inputs-168','nf-ct-local-inputs-166']]
    captures=[json.loads(p.read_text()) for p in capture_paths]
    for c,project in zip(captures,projects):
        assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
        assert str(project.with_suffix('.kicad_pcb')) in c['source_sha256']
    pads=verify_pad_connectivity(*captures);timing=[]
    for cap,owner in [('C8','U21'),('C10','U20'),('C35','U26'),('C37','U25')]:
        distance=[math.dist(p[cap,'1']['position_mm'],p[owner,'5']['position_mm']) for p in pads]
        net=pads[1][cap,'1']['net']
        timing.append(dict(cap=cap,owner=owner,net=net,distance_before_mm=distance[0],distance_after_mm=distance[1],timing_connection_complete=counts[1][net]==0,
                           local_reference=pads[1][cap,'2']['net'],return_native_connected_to_owner=True))
    inputs=[Path(__file__),ROOT/'audit_candidate.py',ROOT/'audit_single_net.py',*projects,*[p.with_suffix('.kicad_pcb') for p in projects],*capture_paths,*constructions,
            *[f/n for f in [old,new] for n in ['review.json','netlist.xml','drc.json','erc.json']]]
    output.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},geometry_delta=delta,only_four_CT_capacitors_moved=True,
        original_circuit_parts_values_pin_nets_and_packages_preserved=True,all_unmoved_pad_connections_preserved=True,
        local_reference_returns_not_shorted_to_AGND=True,existing_supply_vias_and_retained_copper_exact=True,
        opens_before=168,opens_after=166,no_per_net_connectivity_regressions=True,timing_cells=timing,
        all_four_cells_routed=False,remaining_local_CT_connections=['C35.1-U26.5','C37.1-U25.5'],
        original_rear_population=113,new_rear_population=117,rear_complete_height_proposal_mm=1.9,
        installed_receiving_qualified=False,timing_noise_and_PDN_qualified=False,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Verified four local CT placements, all four reference returns, two CT closures; 168 -> 166 opens')


if __name__=='__main__':run()
