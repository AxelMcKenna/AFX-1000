"""Remove only four documented route sets that conflict in the combined trial."""
import json
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,native_evidence_errors


def run():
    root=Path(__file__).resolve().parent;folder=root/'staging/nf-eight-rebased-native-01'
    project=folder/'negative_startup_physical.kicad_pro';source=project.with_suffix('.kicad_pcb')
    assert not native_evidence_errors(project,json.loads((folder/'review.json').read_text()))
    board=read_sexpr(source.read_text())
    paths=[root/'staging'/n/'construction.json' for n in ['nf-softstart-cell-routes-01','nf-softstart-fault-finish-04','nf-eight-sense-finish-01']]
    records=[json.loads(p.read_text()) for p in paths]
    routes=[r for r in records[0]['routes'] if r['task']['name'] in {'C53:return','C54:return'}]
    routes += [dict(net=records[1]['net'],runs=records[1]['runs'],new_vias_mm=records[1]['new_vias_mm']),records[2]]
    assert len(routes)==4
    removed=[]
    def xy(values):return tuple(round(float(x),6) for x in values)
    for route in routes:
        net=route.get('net',route.get('task',{}).get('net'))
        assert net in {'/N12_P03_SRC','/NF_NO_FAULT','/N12_BIAS_SENSE'}
        for layer,points in route['runs']:
            for start,end in zip(points,points[1:]):
                matches=[n for n in children(board,'segment') if first(n,'net')[-1]==net and first(n,'layer')[1]==layer and xy(first(n,'start')[1:3])==xy(start) and xy(first(n,'end')[1:3])==xy(end)]
                assert len(matches)==1,(net,layer,start,end)
                removed.append(matches[0]);board.remove(matches[0])
        for point in route['new_vias_mm']:
            matches=[n for n in children(board,'via') if first(n,'net')[-1]==net and xy(first(n,'at')[1:3])==xy(point)]
            assert len(matches)==1,(net,point)
            removed.append(matches[0]);board.remove(matches[0])
    output=root/'staging/nf-eight-conflict-prepared-01';output.mkdir(exist_ok=False)
    pcb=output/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,project,Path(__file__),*paths]
    (output/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},removed_route_objects=removed,
        preserved_all_CT_SS_TMR_signal_routes=True,reroute_nets=['/N12_P03_SRC','/NF_NO_FAULT','/N12_BIAS_SENSE'],
        native_checks_pending=True,fabrication_released=False),indent=2)+'\n')
    print('Removed',len(removed),'objects in four documented conflicting route sets')


if __name__=='__main__':run()
