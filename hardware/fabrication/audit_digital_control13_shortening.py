"""Independent full-net CONTROL13 shortening audit with exact prior connectivity preservation."""
import copy,json,math
from collections import Counter
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta,native_evidence_errors
from hardware.fabrication.digital_copper_clearance import verify_added_track_clearance
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_joint_repair import FACES,SERIAL,PERMIT
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

ROOT=Path(__file__).resolve().parent
NETS={'/CONTROLS/CONTROL_13'}

def xy(v):return tuple(round(float(x),6) for x in v)

def verify_delta(before,after,recipe):
    delta=geometry_delta(before,after)
    assert delta==recipe['geometry_delta'] and delta['other_root_geometry_exact']
    for tag in ('zone','footprint'):assert delta[tag]==dict(added=[],removed=[],changed=[])
    assert not delta['segment']['changed'] and not delta['via']['changed']
    old={first(n,'uuid')[1]:n for tag in ('segment','via') for n in children(before,tag)}
    new={first(n,'uuid')[1]:n for tag in ('segment','via') for n in children(after,tag)}
    retired={u for u,n in old.items() if first(n,'net')[1] in NETS}
    assert set(delta['segment']['removed']+delta['via']['removed'])==retired==set(recipe['removed_uuids'])
    assert len(delta['segment']['added'])==15 and len(delta['via']['added'])==1
    assert len(delta['segment']['removed'])==39
    assert len(delta['via']['removed'])==6
    assert {first(n,'uuid')[1] for n in recipe['removed_objects']}==retired
    assert all(n==old[first(n,'uuid')[1]] for n in recipe['removed_objects'])
    expected_tracks=Counter();expected_vias=Counter()
    assert {r['net'] for r in recipe['routes']}==NETS
    for r in recipe['routes']:
        for face,path in r['runs']:
            for p,q in zip(path,path[1:]):
                if math.dist(p,q)>=1e-7:expected_tracks[r['net'],face,xy(p),xy(q)]+=1
        for p in r['new_vias_mm']:expected_vias[r['net'],xy(p)]+=1
    actual_tracks=Counter();actual_vias=Counter()
    for uid in delta['segment']['added']:
        n=new[uid];assert float(first(n,'width')[1])==.2 and first(n,'layer')[1] in FACES
        actual_tracks[first(n,'net')[1],first(n,'layer')[1],xy(first(n,'start')[1:]),xy(first(n,'end')[1:])]+=1
    for uid in delta['via']['added']:
        n=new[uid];assert float(first(n,'size')[1])==.6 and float(first(n,'drill')[1])==.3
        assert first(n,'layers')[1:]==['F.Cu','B.Cu']
        actual_vias[first(n,'net')[1],xy(first(n,'at')[1:])]+=1
    assert actual_tracks==expected_tracks and actual_vias==expected_vias
    return delta

def check():
    parent=ROOT/'staging/digital-led10-closed-native-01';out=ROOT/'staging/digital-control13-shortened-native-01'
    rd=ROOT/'staging/digital-control13-full-shortening-01';rp=rd/'construction.json';recipe=json.loads(rp.read_text())
    assert all(sha(Path(p))==h for p,h in recipe['source_sha256'].items())
    candidate=rd/'digital_core.kicad_pcb';assert sha(candidate)==recipe['candidate_PCB_sha256']
    before,after=[read_sexpr((p/'digital_core.kicad_pcb').read_text()) for p in (parent,out)]
    delta=verify_delta(before,after,recipe)
    nd=geometry_delta(read_sexpr(candidate.read_text()),after)
    assert nd['other_root_geometry_exact'] and all(nd[t]==dict(added=[],removed=[],changed=[]) for t in ('footprint','segment','via','zone'))
    paths=[rp,candidate,Path(__file__)];witnesses=[]
    for folder in (parent,out):
        p=folder/'review.json';r=json.loads(p.read_text());assert not native_evidence_errors(folder/'digital_core.kicad_pro',r)
        assert r['status']['counts']==dict(violations=0,unconnected_items=28,schematic_parity=0,erc=0)
        w=folder/'stage-connectivity-review.json';v=json.loads(w.read_text());assert all(sha(Path(p))==h for p,h in v['source_sha256'].items())
        witnesses.append(v);paths += [p,w,folder/'digital_core.kicad_pcb']
    old,new=[{r['net']:r for r in v['nets']} for v in witnesses]
    assert old.keys()==new.keys()
    def groups(r):return {frozenset(map(tuple,g)) for g in r['pad_groups']}
    for net in old:
        assert groups(old[net])==groups(new[net]),net
        if net not in NETS:assert old[net]==new[net],net
    assert all(new[n]['all_pads_connected'] for n in NETS)
    assert all(v['preserved_power_ground_pads']==201 and v['preserved_local_connections']==39 and v['preserved_thermal_connections']==33 for v in witnesses)
    assert [v['open_nets'] for v in witnesses]==[28,28]
    assert all(new[f'/CONTROLS/CONTROL_{i:02d}']['all_pads_connected'] for i in range(32))
    assert sum(n.startswith('/LED/LED_') and not r['all_pads_connected'] for n,r in new.items())==27
    physical=out/'corridor-audit.json';p=json.loads(physical.read_text());assert all(sha(Path(k))==h for k,h in p['source_sha256'].items())
    assert p['conditional_courtyard_THT_and_mount_clearances_pass'] and p['retained_EP_process_hold_vias']==21
    assert len(p['planes'])==4 and all(r['actual_copper_components_including_pads_tracks_and_vias']==1 for r in p['planes'])
    assert p['minimum_drill_to_nonexempt_SMD_gap_mm']>=.15 and p['SD_planar_spread_mm']<=6.000001
    cp=ROOT/'staging/digital-control13-shortened-inputs-28/capture.json';cap=json.loads(cp.read_text());assert all(sha(Path(k))==h for k,h in cap['source_sha256'].items())
    clearance=verify_added_track_clearance(cap,delta['segment']['added'])
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    for o in cap['objects']:
        if o['uuid'] not in delta['via']['added']:continue
        work=copy.deepcopy(cap);work['objects']=[v for v in cap['objects'] if v['uuid']!=o['uuid']]
        assert CloseMarginViaScreen(work,signal_layers=FACES).via_legal(o['net'],o['position_mm'])
    changes={}
    for net in NETS:
        retired=[n for n in recipe['removed_objects'] if first(n,'net')[1]==net]
        removed_length=sum(math.dist(xy(first(n,'start')[1:]),xy(first(n,'end')[1:])) for n in retired if n[0]=='segment')
        assert math.isclose(new[net]['planar_copper_length_mm'],old[net]['planar_copper_length_mm']-removed_length+sum(r['planar_length_mm'] for r in recipe['routes'] if r['net']==net),abs_tol=1e-5)
        assert new[net]['via_count']==old[net]['via_count']-sum(n[0]=='via' for n in retired)+sum(len(r['new_vias_mm']) for r in recipe['routes'] if r['net']==net)
        assert new[net]['planar_copper_length_mm'] < old[net]['planar_copper_length_mm']
        assert new[net]['via_count']==1 and old[net]['via_count']==6
        changes[net]=dict(before=old[net],after=new[net])
    paths += [physical,cp]+[ROOT/n for n in ('audit_candidate.py','digital_copper_clearance.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_serial1_joint_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    return dict(source_sha256={str(p):sha(p) for p in paths},geometry_delta=delta,native_refill_authored_geometry_exact=True,
        before_opens=28,after_opens=28,all_previous_pad_connections_preserved=True,regressed_pad_groups=[],all_other_net_records_exact=True,
        preserved_power_ground_pads=201,preserved_local_connections=39,preserved_thermal_connections=33,preserved_front_controls=32,
        actual_added_track_clearance=clearance,new_vias_rechecked_against_native_capture=True,net_before_after=changes,
        CONTROL13_shortened=True,no_pad_groups_changed=True,all_component_poses_and_authored_zones_exact=True,
        electrical_timing_thermal_EMC_and_installed_performance_qualified=False,fabrication_released=False)

if __name__=='__main__':
    result=check()
    with (ROOT/'staging/digital-control13-shortened-native-01/shortening-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('CONTROL13 shortening audit passed: 28 opens; all pad groups preserved')
