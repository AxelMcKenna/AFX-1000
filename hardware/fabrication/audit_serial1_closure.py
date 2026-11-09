"""Independent SERIAL_1 closure, declared translation and native-copper audit."""
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
NETS={SERIAL,'/LED/CLOCK_5V','/LED/LED_48','/LED/LED_50','/CONTROLS/CONTROL_30','/LED/DATA_5V_SRC','/LED/DATA_5V'}
RETIRED={'1e976130-3b9b-551a-a663-b1e2e6cd0739', '6a538cec-4500-5fb6-a3db-da27fe13a423', 'f1ea2e26-acf3-46e4-a518-bdb380e99c7e', 'd18a7b56-cee4-57a0-8d51-5ad1af942110', 'ef5a8750-045b-547b-ac65-4c13865eedce', 'a17a4834-5809-5f1c-93d1-7004ae4f3aae', 'b6609b81-ac87-5baf-b63d-5d9e5c0084c7', '897ee0ba-b96d-5bdd-a199-4c5d409bb86b', '487dbfb3-629b-4cb9-98cf-eaddc01789ec', '58cf2d4c-093c-5144-9c31-d1c45ff36946', 'bb5eb11d-5d1b-51c1-8fa3-5f2abaafb6b5', 'bdd4f9b7-9e3e-5cb1-9a15-349777c74f6f', '2fcca3a5-039e-5097-b13d-23077a574782', 'c20db915-15cb-5838-a6ad-d77fec29c030', '0350a0fb-3e7b-5b9d-b3c0-3cd88afeda49', 'e14ad693-05ac-5156-ae2a-5bfef8567353', '373cac0f-3aca-532a-b4a4-7a085aed19c4', '47c159cf-a3f8-5e69-b4d2-76cf8791b4d4', '98acf862-6dce-5306-8e7c-ee6c724b77de', '52ce26ee-337e-54d6-9fe1-c65205968188', '5f9bb711-0036-5d18-8d8a-65654893fb44', 'b90e09cc-4179-5d1c-8ca6-8733c88c906e', 'bab55e59-71f4-58c3-b764-3f358c5309ea', '7e838d49-2971-54d2-a5cf-ea8cc48b8ea7', 'e6e7ad4f-fc7e-5522-8b60-9e7e4e644f80', '3757c47e-9abe-583c-b6a7-01507c25a8ef', '0bfeb1bf-84a3-590b-9019-259953c84d26', '223863e5-2a5a-58dd-8eba-824f8a4aa7e8', '51d93778-52bd-57c6-a7bc-d4c2251c448d', '93545be2-620a-5e46-a342-b65362d8ddbd', '941893f2-7280-46d5-8c1a-ff7c521fad41', '2130b0f5-f764-5f0c-8a21-9f768ff13cd9', 'db2c1191-c948-5f0f-92eb-7ebce8a80417', '7bd45892-726f-5cbc-813a-98e5bbf0ffd8'}

def xy(v):return tuple(round(float(x),6) for x in v)

def verify_delta(before,after,recipe):
    delta=geometry_delta(before,after)
    assert delta==recipe['geometry_delta'] and delta['other_root_geometry_exact']
    assert delta['zone']==dict(added=[],removed=[],changed=[])
    def resistor(tree):return next(f for f in children(tree,'footprint') if any(p[1:3]==['Reference','R3015'] for p in children(f,'property')))
    original=resistor(before);moved=resistor(after)
    assert delta['footprint']==dict(added=[],removed=[],changed=[first(original,'uuid')[1]])
    assert xy(first(original,'at')[1:3])==(75.,21.) and xy(first(moved,'at')[1:3])==(75.25,21.)
    restored=copy.deepcopy(moved);restored[restored.index(first(restored,'at'))]=copy.deepcopy(first(original,'at'))
    assert restored==original and first(moved,'layer')[1]=='B.Cu'
    assert moved==read_sexpr(sexpr(recipe['component_move']['footprint']))
    assert not delta['segment']['changed'] and not delta['via']['changed']
    assert set(delta['segment']['removed']+delta['via']['removed'])==RETIRED==set(recipe['removed_uuids'])
    assert len(delta['segment']['added'])==94 and len(delta['via']['added'])==11
    old={first(n,'uuid')[1]:n for tag in ('segment','via') for n in children(before,tag)}
    new={first(n,'uuid')[1]:n for tag in ('segment','via') for n in children(after,tag)}
    assert {first(n,'uuid')[1] for n in recipe['removed_objects']}==RETIRED
    assert all(n==old[first(n,'uuid')[1]] for n in recipe['removed_objects'])
    assert all(first(old[u],'net')[1] in NETS for u in RETIRED)
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
    parent=ROOT/'staging/digital-serial1-source-preparation-native-01';out=ROOT/'staging/digital-serial1-closed-native-03'
    rd=ROOT/'staging/digital-serial1-combined-restoration-08';rp=rd/'construction.json';recipe=json.loads(rp.read_text())
    assert all(sha(Path(p))==h for p,h in recipe['source_sha256'].items())
    candidate=rd/'digital_core.kicad_pcb';assert sha(candidate)==recipe['candidate_PCB_sha256']
    before,after=[read_sexpr((p/'digital_core.kicad_pcb').read_text()) for p in (parent,out)]
    delta=verify_delta(before,after,recipe)
    nd=geometry_delta(read_sexpr(candidate.read_text()),after)
    assert nd['other_root_geometry_exact'] and all(nd[t]==dict(added=[],removed=[],changed=[]) for t in ('footprint','segment','via','zone'))
    paths=[rp,candidate,Path(__file__)];witnesses=[]
    for folder in (parent,out):
        p=folder/'review.json';r=json.loads(p.read_text());assert not native_evidence_errors(folder/'digital_core.kicad_pro',r)
        assert r['status']['counts']==dict(violations=0,unconnected_items=31 if folder==parent else 30,schematic_parity=0,erc=0)
        w=folder/'stage-connectivity-review.json';v=json.loads(w.read_text());assert all(sha(Path(p))==h for p,h in v['source_sha256'].items())
        witnesses.append(v);paths += [p,w,folder/'digital_core.kicad_pcb']
    old,new=[{r['net']:r for r in v['nets']} for v in witnesses]
    assert old.keys()==new.keys()
    def groups(r):return {frozenset(map(tuple,g)) for g in r['pad_groups']}
    for net in old:
        if net==SERIAL:
            assert not old[net]['all_pads_connected'] and new[net]['all_pads_connected']
            assert set().union(*groups(old[net]))==set().union(*groups(new[net]))
        else:assert groups(old[net])==groups(new[net]),net
        if net not in NETS:assert old[net]==new[net],net
    assert all(new[n]['all_pads_connected'] for n in NETS)
    assert all(v['preserved_power_ground_pads']==201 and v['preserved_local_connections']==39 and v['preserved_thermal_connections']==33 for v in witnesses)
    assert [v['open_nets'] for v in witnesses]==[31,30]
    assert all(new[f'/CONTROLS/CONTROL_{i:02d}']['all_pads_connected'] for i in range(32))
    assert sum(n.startswith('/LED/LED_') and not r['all_pads_connected'] for n,r in new.items())==29
    physical=out/'corridor-audit.json';p=json.loads(physical.read_text());assert all(sha(Path(k))==h for k,h in p['source_sha256'].items())
    assert p['conditional_courtyard_THT_and_mount_clearances_pass'] and p['retained_EP_process_hold_vias']==21
    assert len(p['planes'])==4 and all(r['actual_copper_components_including_pads_tracks_and_vias']==1 for r in p['planes'])
    assert p['minimum_drill_to_nonexempt_SMD_gap_mm']>=.15 and p['SD_planar_spread_mm']<=6.000001
    cp=ROOT/'staging/digital-serial1-closed-inputs-30/capture.json';cap=json.loads(cp.read_text());assert all(sha(Path(k))==h for k,h in cap['source_sha256'].items())
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
        changes[net]=dict(before=old[net],after=new[net])
    paths += [physical,cp]+[ROOT/n for n in ('audit_candidate.py','digital_copper_clearance.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_serial1_joint_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    return dict(source_sha256={str(p):sha(p) for p in paths},geometry_delta=delta,native_refill_authored_geometry_exact=True,
        before_opens=31,after_opens=30,all_previous_pad_connections_preserved=True,regressed_pad_groups=[],all_other_net_records_exact=True,
        preserved_power_ground_pads=201,preserved_local_connections=39,preserved_thermal_connections=33,preserved_front_controls=32,
        actual_added_track_clearance=clearance,new_vias_rechecked_against_native_capture=True,net_before_after=changes,
        full_serial_route_complete=True,only_newly_closed_net=SERIAL,declared_R3015_translation_mm=[.25,0.],
        electrical_timing_thermal_EMC_and_installed_performance_qualified=False,fabrication_released=False)

if __name__=='__main__':
    result=check()
    with (ROOT/'staging/digital-serial1-closed-native-03/serial1-closure-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('SERIAL_1 closure audit passed: 31 to 30 opens; all prior connections preserved')
