"""Eight-layer comparison with an extra ground-referenced signal layer.

Retain the 71-open candidate except its documented long LED_SCK addition.
Reopen that one connection for a shorter route on the new signal layer.
"""
import copy,json,uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta,native_evidence_errors
ROOT=Path(__file__).resolve().parent

def run():
    source=ROOT/'staging/digital-native-spacing-native-01/digital_core.kicad_pcb'
    review_path=source.parent/'review.json';review=json.loads(review_path.read_text())
    assert not native_evidence_errors(source.with_suffix('.kicad_pro'),review)
    assert review['uncapped_open_connections']==71 and review['status']['counts']['violations']==0
    route_path=source.parent/'additive-route-review.json';route=json.loads(route_path.read_text())
    assert all(sha(Path(p))==h for p,h in route['source_sha256'].items())
    board=read_sexpr(source.read_text());original=copy.deepcopy(board)
    removed=[]
    for tag in ('segment','via'):
        added=set(route['geometry_delta'][tag]['added'])
        for node in list(children(board,tag)):
            if first(node,'uuid')[1] in added and first(node,'net')[1]=='LED_SCK':
                removed.append(node);board.remove(node)
    assert sum(n[0]=='via' for n in removed)==9
    layers=first(board,'layers');back=next(n for n in layers[1:] if n[1]=='B.Cu');index=layers.index(back)
    layers[index:index]=[[a(12),'In5.Cu',a('signal')],[a(14),'In6.Cu',a('power')]]
    zone=copy.deepcopy(next(z for z in children(board,'zone') if first(z,'layer')[1]=='In4.Cu'))
    zone=[n for n in zone if not isinstance(n,list) or n[0] not in ('filled_polygon','filled_areas_thickness')]
    first(zone,'layer')[1]='In6.Cu';first(zone,'uuid')[1]=str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:DC:eight-layer:'+sha(source)))
    board.append(zone)
    delta=geometry_delta(original,board)
    assert delta['footprint']==dict(added=[],removed=[],changed=[])
    assert len(delta['zone']['added'])==1 and not delta['zone']['removed'] and not delta['zone']['changed']
    normalized=copy.deepcopy(board);normalized[normalized.index(first(normalized,'layers'))]=copy.deepcopy(first(original,'layers'))
    assert geometry_delta(original,normalized)['other_root_geometry_exact']
    out=ROOT/'staging/digital-eight-layer-01';out.mkdir(exist_ok=False);dest=out/source.name;dest.write_text(sexpr(board)+'\n')
    with (out/'construction.json').open('x') as f:
        json.dump(dict(source_sha256={str(p):sha(p) for p in (source,review_path,route_path,Path(__file__))},candidate_PCB_sha256=sha(dest),
            geometry_delta=delta,removed_clock_objects=removed,new_signal_layer='In5.Cu',new_ground_layer='In6.Cu',
            signal_layers=['F.Cu','In3.Cu','In5.Cu','B.Cu'],reopened_net='LED_SCK',expected_opens=72,
            all_other_parent_copper_exact=True,physical_stack_accepted=False,native_checks_pending=True,fabrication_released=False),f,indent=2);f.write('\n')
    print('Added ground-referenced signal layer; removed',len(removed),'long-clock objects; native review pending')

if __name__=='__main__':run()
