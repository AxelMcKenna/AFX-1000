"""Independently verify the R3015 relocation and exact pre/post-series net transfer."""
import copy,json,math
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta,native_evidence_errors
from hardware.fabrication.audit_digital_data_series import check as physical_check
from hardware.fabrication.audit_digital_eight_escape_checkpoint import check as parent_check
ROOT=Path(__file__).resolve().parent
SRC='/LED/DATA_5V_SRC';DATA='/LED/DATA_5V'

def refs(tree):return {next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(tree,'footprint')}
def copper(tree):return {first(n,'uuid')[1]:n for tag in ('segment','via') for n in children(tree,tag)}

def verify_board_delta(before,after,recipe,template):
    old,new=refs(before),refs(after);assert old.keys()==new.keys()
    assert all(sexpr(f)==sexpr(new[r]) for r,f in old.items() if r!='R3015')
    moved=copy.deepcopy(new['R3015']);assert first(moved,'layer')[1]=='B.Cu'
    assert list(map(float,first(moved,'at')[1:3]))==[75.,21.]
    moved[moved.index(first(moved,'at'))]=copy.deepcopy(first(template,'at'));assert sexpr(moved)==sexpr(template)
    delta=geometry_delta(before,after);assert delta==recipe['geometry_delta']
    assert delta['other_root_geometry_exact'] and delta['zone']==dict(added=[],removed=[],changed=[])
    assert delta['footprint']==dict(added=[],removed=[],changed=[first(old['R3015'],'uuid')[1]])
    assert len(delta['segment']['added'])==23 and len(delta['segment']['changed'])==17
    assert delta['segment']['removed']==['a35ab001-7b4f-53c4-8dda-68c074214151']
    assert len(delta['via']['added'])==2 and len(delta['via']['changed'])==1 and not delta['via']['removed']
    olds,news=copper(before),copper(after);transferred=set(delta['segment']['changed']+delta['via']['changed'])
    assert transferred==set(recipe['reassigned_uuids']) and len(transferred)==18
    assert {first(n,'uuid')[1] for n in recipe['reassigned_objects_before']}==transferred
    for ident in transferred:
        assert first(olds[ident],'net')[1]==SRC and first(news[ident],'net')[1]==DATA
        restored=copy.deepcopy(news[ident]);first(restored,'net')[1]=SRC
        assert sexpr(restored)==sexpr(olds[ident]),ident
    for recorded in recipe['reassigned_objects_before']:
        assert recorded==olds[first(recorded,'uuid')[1]]
    # JSON receipts preserve token values but not the parser's quoted-atom type.
    removed=recipe['removed_objects'];assert len(removed)==1 and removed[0]==olds[delta['segment']['removed'][0]]
    for ident in ('d34b4002-d43f-5361-bc02-56efb6390b56','3b693fe4-d5a4-55d2-ba57-cafd41d1ad62'):assert sexpr(olds[ident])==sexpr(news[ident])
    for tag in ('segment','via'):
        for ident in delta[tag]['added']:
            n=news[ident];assert first(n,'net')[1] in (SRC,DATA)
            if tag=='segment':assert float(first(n,'width')[1])==.2 and first(n,'layer')[1] in ('F.Cu','B.Cu','In5.Cu')
            else:assert float(first(n,'size')[1])==.6 and float(first(n,'drill')[1])==.3
    return delta


def check():
    parent=ROOT/'staging/digital-eight-serial-native-01';out=ROOT/'staging/digital-data-series-native-01';recipe_dir=ROOT/'staging/digital-data-series-repack-01'
    recipe_path=recipe_dir/'construction.json';recipe=json.loads(recipe_path.read_text());assert all(sha(Path(p))==h for p,h in recipe['source_sha256'].items())
    candidate=recipe_dir/'digital_core.kicad_pcb';assert sha(candidate)==recipe['candidate_PCB_sha256']
    template_path=ROOT/'staging/digital-data-series-templates-01/R3015-B-0.kicad_mod';template=read_sexpr(template_path.read_text())
    pcbpaths=[p/'digital_core.kicad_pcb' for p in (parent,out)];before,after=[read_sexpr(p.read_text()) for p in pcbpaths]
    delta=verify_board_delta(before,after,recipe,template)
    native_delta=geometry_delta(read_sexpr(candidate.read_text()),after);assert native_delta['other_root_geometry_exact']
    assert all(native_delta[tag]==dict(added=[],removed=[],changed=[]) for tag in ('footprint','segment','via','zone'))
    pp=parent/'checkpoint-review.json';assert parent_check()==json.loads(pp.read_text())
    physical=out/'corridor-audit.json';assert physical_check(out.name,'digital-data-series-inputs-49')==json.loads(physical.read_text())
    paths=[Path(__file__),recipe_path,candidate,template_path,pp,physical,*pcbpaths];records=[]
    for folder in (parent,out):
        rp=folder/'review.json';r=json.loads(rp.read_text());assert not native_evidence_errors(folder/'digital_core.kicad_pro',r)
        assert r['status']['counts']==dict(violations=0,unconnected_items=49,schematic_parity=0,erc=0)
        cp=folder/'stage-connectivity-review.json';c=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items());records.append(c);paths += [rp,cp]
    oldnets,newnets=[{r['net']:r for r in c['nets']} for c in records];assert oldnets.keys()==newnets.keys()
    for net,old in oldnets.items():
        a=[set(map(tuple,g)) for g in old['pad_groups']];b=[set(map(tuple,g)) for g in newnets[net]['pad_groups']]
        assert set.union(*a)==set.union(*b) and all(any(g<=h for h in b) for g in a),net
    assert all(newnets[n]['all_pads_connected'] for n in (SRC,DATA))
    assert newnets[SRC]['planar_copper_length_mm']<18<oldnets[SRC]['planar_copper_length_mm'] and newnets[SRC]['via_count']==oldnets[SRC]['via_count']==2
    assert newnets['LED_SCK']==oldnets['LED_SCK']
    for name in ('conditional-assembly-review.json','visual-review.json'):
        path=out/name;r=json.loads(path.read_text());assert all(sha(Path(p))==h for p,h in r['source_sha256'].items());paths.append(path)
    before_total=sum(oldnets[n]['planar_copper_length_mm'] for n in (SRC,DATA));after_total=sum(newnets[n]['planar_copper_length_mm'] for n in (SRC,DATA))
    return dict(source_sha256={str(p):sha(p) for p in paths},geometry_delta=delta,
                component_move=recipe['component_move'],unchanged_open_connections=49,regressed_pad_groups=[],
                pre_series_before=oldnets[SRC],pre_series_after=newnets[SRC],post_series_before=oldnets[DATA],post_series_after=newnets[DATA],
                combined_planar_before_mm=before_total,combined_planar_after_mm=after_total,
                pre_series_reduction_mm=oldnets[SRC]['planar_copper_length_mm']-newnets[SRC]['planar_copper_length_mm'],
                increased_total_copper_mm=after_total-before_total,
                all_other_component_poses_and_copper_exact=True,clock_SD_power_local_thermal_and_planes_preserved=True,
                signal_integrity_source_damping_timing_stack_and_installed_unit_qualified=False,fabrication_released=False)
if __name__=='__main__':
    result=check()
    with (ROOT/'staging/digital-data-series-native-01/data-series-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('Exact R3015/net-transfer audit passed; pre-series',round(result['pre_series_after']['planar_copper_length_mm'],3),'mm; total increase',round(result['increased_total_copper_mm'],3),'mm; 49 opens')
