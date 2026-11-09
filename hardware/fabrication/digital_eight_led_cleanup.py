"""Remove only the three unused, source-bound LED trial escapes."""
import json
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta,native_evidence_errors
ROOT=Path(__file__).resolve().parent

def run():
    base=ROOT/'staging/digital-eight-routed-native-01'
    source=ROOT/'staging/digital-eight-led-inner-native-01'
    fanout=ROOT/'staging/digital-eight-led-fanouts-01'
    routed=ROOT/'staging/digital-eight-led-inner-routes-01'
    out=ROOT/'staging/digital-eight-led-clean-01'
    paths=[Path(__file__)]
    for directory in (fanout,routed):
        p=directory/'construction.json';r=json.loads(p.read_text())
        assert all(sha(Path(f))==h for f,h in r['source_sha256'].items())
        assert sha(directory/'digital_core.kicad_pcb')==r['candidate_PCB_sha256']
        paths += [p,directory/'digital_core.kicad_pcb']
    fan=json.loads((fanout/'construction.json').read_text());routes=json.loads((routed/'construction.json').read_text())
    unused={r['net'] for r in fan['selected_escapes']}-{r['net'] for r in routes['routes']}
    assert unused=={'/LED/LED_35','/LED/LED_41','/LED/LED_46'}
    rp=source/'review.json';review=json.loads(rp.read_text())
    assert not native_evidence_errors(source/'digital_core.kicad_pro',review)
    assert review['status']['counts']==dict(violations=3,unconnected_items=52,schematic_parity=0,erc=0)
    drc=json.loads((source/'drc.json').read_text());assert all(v['type']=='via_dangling' and v['severity']=='warning' for v in drc['violations'])
    parent,escape,board=[read_sexpr((p/'digital_core.kicad_pcb').read_text()) for p in (base,fanout,source)]
    delta=geometry_delta(parent,escape)
    ids=set(delta['segment']['added']+delta['via']['added'])
    removed=[n for tag in ('segment','via') for n in children(board,tag) if first(n,'uuid')[1] in ids and first(n,'net')[1] in unused]
    assert len(removed)==9
    assert {first(n,'uuid')[1] for n in removed if n[0]=='via'}=={i['uuid'] for v in drc['violations'] for i in v['items']}
    for n in removed:board.remove(n)
    finaldelta=geometry_delta(parent,board)
    assert finaldelta['other_root_geometry_exact']
    for tag in ('footprint','zone'):assert finaldelta[tag]==dict(added=[],removed=[],changed=[])
    for tag in ('segment','via'):assert not finaldelta[tag]['removed'] and not finaldelta[tag]['changed']
    out.mkdir(exist_ok=False);dest=out/'digital_core.kicad_pcb';dest.write_text(sexpr(board)+'\n')
    paths += [base/'digital_core.kicad_pcb',source/'digital_core.kicad_pcb',rp,source/'drc.json']
    with (out/'construction.json').open('x') as f:json.dump(dict(source_sha256={str(p):sha(p) for p in paths},candidate_PCB_sha256=sha(dest),removed_objects=removed,unused_escape_nets=sorted(unused),geometry_delta_from_56_open_parent=finaldelta,native_checks_pending=True,fabrication_released=False),f,indent=2);f.write('\n')
    print('Removed only six new unused LED escape segments and three dangling vias')
if __name__=='__main__':run()
