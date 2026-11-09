"""Verify the exact clock-repack delta against its 75-open routed parent."""
import copy,json,math
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta
ROOT=Path(__file__).resolve().parent

def check():
    source=ROOT/'staging/digital-interface-clean-native-02';out=ROOT/'staging/digital-clock-series-clean-native-01'
    before=read_sexpr((source/'digital_core.kicad_pcb').read_text());after=read_sexpr((out/'digital_core.kicad_pcb').read_text())
    recipe_path=ROOT/'staging/digital-clock-series-repack-01/construction.json';cleanup_path=ROOT/'staging/digital-clock-series-clean-01/construction.json'
    recipe=json.loads(recipe_path.read_text());cleanup=json.loads(cleanup_path.read_text())
    paths=[source/'digital_core.kicad_pcb',out/'digital_core.kicad_pcb',recipe_path,cleanup_path,Path(__file__)]
    for record in [recipe,cleanup]:assert all(sha(Path(p))==h for p,h in record['source_sha256'].items())
    def refs(tree):return {next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(tree,'footprint')}
    old,new=refs(before),refs(after);assert set(old)==set(new)
    assert all(sexpr(f)==sexpr(new[r]) for r,f in old.items() if r!='R3016')
    normalized=copy.deepcopy(new['R3016']);assert list(map(float,first(normalized,'at')[1:3]))==[69.,23.]
    normalized[normalized.index(first(normalized,'at'))]=copy.deepcopy(first(old['R3016'],'at'));assert sexpr(normalized)==sexpr(old['R3016'])
    delta=geometry_delta(before,after);assert delta['other_root_geometry_exact'] and delta['zone']==dict(added=[],removed=[],changed=[])
    removed={first(n,'uuid')[1] for n in recipe['removed_objects']+cleanup['removed_objects']}
    assert set(delta['segment']['removed'])==removed and not delta['segment']['changed']
    assert len(delta['segment']['added'])==11 and len(delta['segment']['removed'])==8
    assert len(delta['via']['added'])==1 and not delta['via']['removed'] and not delta['via']['changed']
    oldtracks={first(n,'uuid')[1]:n for n in children(before,'segment')};newtracks={first(n,'uuid')[1]:n for n in children(after,'segment')}
    assert {first(oldtracks[u],'net')[1] for u in removed}=={'V3V3_IO','/LED/CLOCK_5V'}
    assert {first(newtracks[u],'net')[1] for u in delta['segment']['added']}=={'V3V3_IO','/LED/CLOCK_5V','/LED/CLOCK_5V_SRC'}
    added_supply=[newtracks[u] for u in delta['segment']['added'] if first(newtracks[u],'net')[1]=='V3V3_IO']
    assert all(float(first(n,'width')[1])==.3 and first(n,'layer')[1]=='B.Cu' for n in added_supply)
    def length(n):return math.dist(list(map(float,first(n,'start')[1:3])),list(map(float,first(n,'end')[1:3])))
    old_supply=next(n for u,n in oldtracks.items() if u in removed and first(n,'net')[1]=='V3V3_IO')
    native=[]
    for p in [source/'stage-connectivity-review.json',out/'stage-connectivity-review.json']:
        d=json.loads(p.read_text());assert all(sha(Path(s))==h for s,h in d['source_sha256'].items());native.append(d);paths.append(p)
    nets=[{r['net']:r for r in d['nets']} for d in native]
    closed=[{n for n,r in d.items() if r['all_pads_connected']} for d in nets]
    assert not closed[0]-closed[1] and closed[1]-closed[0]=={'/LED/CLOCK_5V_SRC'}
    assert native[0]['uncapped_open_connections']==75 and native[1]['uncapped_open_connections']==74
    assert native[1]['preserved_power_ground_pads']==201 and native[1]['preserved_local_connections']==39 and native[1]['preserved_thermal_connections']==33
    clock=nets[1]['/LED/CLOCK_5V_SRC'];assert clock['via_count']==1 and math.isclose(clock['planar_copper_length_mm'],4.479764365647604,abs_tol=1e-6)
    return dict(source_sha256={str(p):sha(p) for p in paths},geometry_delta=delta,newly_connected_nets=sorted(closed[1]-closed[0]),regressed_connected_nets=[],clock_source=clock,supply_branch_before_mm=length(old_supply),supply_branch_after_mm=sum(length(n) for n in added_supply),supply_branch_width_mm=.3,signal_power_and_thermal_qualified=False,fabrication_released=False)

if __name__=='__main__':
    result=check();p=ROOT/'staging/digital-clock-series-clean-native-01/clock-repack-review.json'
    with p.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('Exact clock-repack delta verified; one newly closed net and no lost connected nets')
