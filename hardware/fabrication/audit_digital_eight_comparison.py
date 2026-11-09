"""Compare the eight-layer routed trial with the retained 71-open six-layer PCB."""
import argparse,copy,json
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta,native_evidence_errors
ROOT=Path(__file__).resolve().parent

def check(label):
    parent=ROOT/'staging/digital-native-spacing-native-01';out=ROOT/'staging'/label
    prep_path=ROOT/'staging/digital-eight-layer-01/construction.json'
    routes_path=ROOT/'staging/digital-eight-layer-routes-01/construction.json'
    prep,routes=[json.loads(p.read_text()) for p in (prep_path,routes_path)]
    for record in (prep,routes):assert all(sha(Path(p))==h for p,h in record['source_sha256'].items())
    old,new=[read_sexpr((p/'digital_core.kicad_pcb').read_text()) for p in (parent,out)]
    delta=geometry_delta(old,new)
    normalized=copy.deepcopy(new);normalized[normalized.index(first(normalized,'layers'))]=copy.deepcopy(first(old,'layers'))
    assert geometry_delta(old,normalized)['other_root_geometry_exact']
    assert delta['footprint']==dict(added=[],removed=[],changed=[])
    assert delta['zone']['added']==prep['geometry_delta']['zone']['added'] and not delta['zone']['changed'] and not delta['zone']['removed']
    for tag in ('segment','via'):
        assert delta[tag]['removed']==prep['geometry_delta'][tag]['removed'] and not delta[tag]['changed']
    assert len(delta['segment']['added'])==routes['added_segments'] and len(delta['via']['added'])==routes['added_vias']
    assert len(delta['segment']['removed'])==46 and len(delta['via']['removed'])==9
    assert {first(n,'net')[1] for n in prep['removed_clock_objects']}=={'LED_SCK'}
    records=[];paths=[Path(__file__),prep_path,routes_path]
    for directory in (parent,out):
        review_path=directory/'review.json';review=json.loads(review_path.read_text())
        assert not native_evidence_errors(directory/'digital_core.kicad_pro',review)
        assert all(review['status']['counts'][k]==0 for k in ('violations','schematic_parity','erc'))
        path=directory/'stage-connectivity-review.json';record=json.loads(path.read_text())
        assert all(sha(Path(p))==h for p,h in record['source_sha256'].items())
        records.append(record);paths += [directory/'digital_core.kicad_pcb',review_path,path]
    before,after=[{r['net']:r for r in record['nets']} for record in records]
    assert before.keys()==after.keys()
    for net,old_net in before.items():
        old_groups=[set(map(tuple,g)) for g in old_net['pad_groups']]
        new_groups=[set(map(tuple,g)) for g in after[net]['pad_groups']]
        assert set.union(*old_groups)==set.union(*new_groups)
        assert all(any(group<=merged for merged in new_groups) for group in old_groups),net
    clock_before,clock_after=before['LED_SCK'],after['LED_SCK']
    assert clock_before['all_pads_connected'] and clock_after['all_pads_connected']
    assert clock_after['planar_copper_length_mm']<60<clock_before['planar_copper_length_mm']
    assert clock_after['via_count']==2<clock_before['via_count']==9
    assert records[0]['uncapped_open_connections']==71
    assert records[1]['uncapped_open_connections']==72-len(routes['routes'])<71
    assert records[1]['copper_layer_count']==8
    for key,n in [('preserved_power_ground_pads',201),('preserved_local_connections',39),('preserved_thermal_connections',33)]:assert records[1][key]==n
    improved=[dict(net=n,before_groups=len(before[n]['pad_groups']),after_groups=len(r['pad_groups']),all_pads_connected=r['all_pads_connected'])
              for n,r in after.items() if len(r['pad_groups'])<len(before[n]['pad_groups'])]
    return dict(source_sha256={str(p):sha(p) for p in paths},geometry_delta=delta,
        before_opens=71,after_opens=records[1]['uncapped_open_connections'],improved_nets=improved,regressed_pad_groups=[],
        clock_before=clock_before,clock_after=clock_after,clock_planar_reduction_mm=clock_before['planar_copper_length_mm']-clock_after['planar_copper_length_mm'],
        only_removed_parent_copper_is_the_documented_long_clock_route=True,
        additional_signal_layer='In5.Cu',additional_ground_layer='In6.Cu',
        physical_stack_cost_and_manufacturing_process_accepted=False,
        signal_integrity_power_thermal_and_installed_unit_qualified=False,fabrication_released=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);args=parser.parse_args()
    assert args.source and all(c.isalnum() or c in '-_' for c in args.source)
    result=check(args.source)
    with (ROOT/'staging'/args.source/'eight-layer-comparison.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('Eight-layer comparison verified:',result['after_opens'],'opens; shorter two-via clock; no parent pad-group regressions')
