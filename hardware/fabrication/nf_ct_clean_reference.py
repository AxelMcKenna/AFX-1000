"""Remove only the remaining vacated reference leaves from the CT candidate."""
import json
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.route_nf_surface import sha
from hardware.fabrication.nf_ct_leaf_cleanup import prune_leaf_returns


def run():
    root=Path(__file__).resolve().parent
    capture_path=root/'staging/nf-ct-routed-inputs-166/capture.json';c=json.loads(capture_path.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'))
    _,removed=prune_leaf_returns(c);ids={o['uuid'] for o in removed}
    board=read_sexpr(source.read_text());nodes=[]
    for n in list(children(board,'segment')+children(board,'via')):
        if first(n,'uuid')[1] in ids:nodes.append(n);board.remove(n)
    assert len(nodes)==len(ids)==6
    output=root/'staging/nf-ct-clean-reference-01';output.mkdir(exist_ok=False)
    (output/source.name).write_text(sexpr(board)+'\n')
    (output/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [source,capture_path,Path(__file__),root/'nf_ct_leaf_cleanup.py']},removed_leaf_objects=nodes,
        native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Removed six unused reference branch objects; no via or supply-route movement')


if __name__=='__main__':run()
