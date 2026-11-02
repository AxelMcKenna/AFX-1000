"""Prepare/import DC01 signal routing with explicit power-plane preservation."""
import argparse,json,re,shlex,shutil,sys
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_signal_router import manual
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'staging/digital-core-placement-03'
OLD=ROOT/'staging/digital-signal-routing-02'
WORK=ROOT/'staging/digital-signal-routing-03'

def prepare():
    record=json.loads((OLD/'export.json').read_text())
    assert all(sha(Path(p))==h for p,h in record['source_sha256'].items())
    assert sha(OLD/'native-input.dsn')==record['native_DSN_sha256']
    assert sha(SOURCE/'digital_core.kicad_pcb')==record['source_PCB_sha256']
    WORK.mkdir(exist_ok=False)
    for name in ['input.kicad_pcb','native-input.dsn']:shutil.copyfile(OLD/name,WORK/name)
    text=(WORK/'native-input.dsn').read_text()
    text=text.replace('(clearance 50 (type smd_smd))','(clearance 200 (type smd_smd))')
    match=re.search(r'    \(class kicad_default ([\s\S]*?)(      \(circuit[\s\S]*?\n    \))',text)
    assert match
    names=set(shlex.split(match.group(1)))
    excluded={n for n in names if manual(n)};included=names-excluded
    assert included and excluded and all(not n.startswith('unconnected-') for n in included)
    rules=match.group(2).replace('(circuit','(circuit\n        (use_layer F.Cu B.Cu)',1)
    classes='\n'.join('    (class '+label+' '+' '.join(json.dumps(n) for n in sorted(nets))+'\n'+rules
                       for label,nets in [('AFX_DIGITAL_SIGNALS',included),('AFX_MANUAL',excluded)])
    text=text[:match.start()]+classes+text[match.end():]
    assert text.count('(use_layer F.Cu B.Cu)')==2
    (WORK/'routing-view.dsn').write_text(text)
    (WORK/'config').mkdir();shutil.copyfile(OLD/'config/freerouting.json',WORK/'config/freerouting.json')
    inputs=[Path(__file__),ROOT/'digital_signal_router.py',OLD/'export.json',OLD/'native-input.dsn',SOURCE/'digital_core.kicad_pcb',WORK/'config/freerouting.json']
    record.update(source_sha256={str(p):sha(p) for p in inputs},
        routed_net_names=sorted(included),manual_net_names=sorted(excluded),
        routing_DSN_sha256=sha(WORK/'routing-view.dsn'),native_DSN_sha256=sha(WORK/'native-input.dsn'),
        explicit_outer_layer_use_rule=True,cli_layer_constraints_required=True,
        previous_trial_rejected_for_inner_layer_signal_tracks=True)
    (WORK/'export.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Prepared outer-only trial;',len(included),'signal nets;',len(excluded),'manual/unused nets')

def adopt():
    assert sys.platform=='linux'
    from hardware.fabrication.placement_router import import_routes
    import_routes(WORK)
    tree=read_sexpr((WORK/'merged.kicad_pcb').read_text())
    original=read_sexpr((WORK/'input.kicad_pcb').read_text())
    numeric={str(n[1]):str(n[2]) for n in children(tree,'net') if len(n)>2}
    kept=[];discarded=[]
    for tag in ['segment','via']:
        for node in children(tree,tag):
            token=str(first(node,'net')[1]);net=numeric.get(token,token)
            (discarded if manual(net) else kept).append(node)
    assert kept
    for node in kept:
        if node[0]=='segment':assert first(node,'layer')[1] in ['F.Cu','B.Cu']
    candidate=WORK/'accepted-signals.kicad_pcb';assert not candidate.exists()
    candidate.write_text(sexpr(original+kept)+'\n')
    inputs=[Path(__file__),ROOT/'digital_signal_router.py',WORK/'import.json',WORK/'export.json',WORK/'router-command.json',WORK/'merged.kicad_pcb',WORK/'input.kicad_pcb']
    result=dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(candidate),
        kept_signal_segments=sum(n[0]=='segment' for n in kept),kept_signal_vias=sum(n[0]=='via' for n in kept),
        discarded_manual_fanout_objects=len(discarded),original_authored_geometry_exact=True,
        reserved_inner_planes_have_no_signal_tracks=True,native_checks_pending=True,fabrication_released=False)
    (WORK/'adoption.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Adopted signal copper:',len(kept),'discarded manual fanout:',len(discarded))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','adopt']);args=ap.parse_args()
    (prepare if args.action=='prepare' else adopt)()
