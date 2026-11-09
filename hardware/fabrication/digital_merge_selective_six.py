"""Replace mutable signal routing while retaining exact declared protected geometry."""
import argparse
import json
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta

ROOT=Path(__file__).resolve().parent

def run():
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',required=True);args=parser.parse_args()
    assert args.workspace and all(c.isalnum() or c in '-_' for c in args.workspace)
    work=ROOT/'staging'/args.workspace;rp=work/'raw-import.json';record=json.loads(rp.read_text())
    assert all(sha(Path(p))==h for p,h in record['source_sha256'].items())
    assert sha(work/'raw-import.kicad_pcb')==record['raw_PCB_sha256']
    original=read_sexpr((work/'input.kicad_pcb').read_text())
    fixed=set(json.loads((work/'export.json').read_text())['protected_source_UUIDs'])
    old=[n for n in original if not(isinstance(n,list) and n and n[0] in ['segment','via']) or first(n,'uuid')[1] in fixed]
    assert {first(n,'uuid')[1] for tag in ['segment','via'] for n in children(old,tag)}==fixed
    new=read_sexpr((work/'raw-import.kicad_pcb').read_text())
    def net_names(tree):return {str(n[1]):str(n[2]) for n in children(tree,'net') if len(n)>2}
    names=net_names(new);oldnames=net_names(old)
    def net(n,mapping):
        token=str(first(n,'net')[1]);return mapping.get(token,token)
    paths={};oldvias=[];oldids={first(n,'uuid')[1] for tag in ['segment','via'] for n in children(old,tag)}
    for n in children(old,'segment'):
        key=(net(n,oldnames),first(n,'layer')[1]);line=LineString([list(map(float,first(n,t)[1:3])) for t in ['start','end']])
        paths.setdefault(key,[]).append(line.buffer(float(first(n,'width')[1])/2+.002,quad_segs=16))
    covered={key:unary_union(rows) for key,rows in paths.items()}
    for n in children(old,'via'):oldvias.append((net(n,oldnames),Point(list(map(float,first(n,'at')[1:3]))),float(first(n,'size')[1]),float(first(n,'drill')[1])))
    manual=set(json.loads((work/'export.json').read_text())['manual_net_names'])
    kept=[];discarded=[];raised=[]
    for tag in ['segment','via']:
        for n in children(new,tag):
            name=net(n,names);ident=first(n,'uuid')[1];reason=None
            if tag=='segment':
                face=first(n,'layer')[1];width=float(first(n,'width')[1]);assert face in ['F.Cu','In3.Cu','B.Cu']
                line=LineString([list(map(float,first(n,t)[1:3])) for t in ['start','end']])
                if (name,face) in covered and covered[(name,face)].covers(line.buffer(max(width/2-.002,.001),quad_segs=8)):reason='source copper representation'
                if not reason and width<.2:
                    assert width in [.1,.12,.15];first(n,'width')[1]=.2;raised.append(dict(uuid=ident,before_mm=width,after_mm=.2))
            else:
                point=Point(list(map(float,first(n,'at')[1:3])));size=float(first(n,'size')[1]);drill=float(first(n,'drill')[1])
                assert drill>=.3
                if any(name==other and point.distance(q)<.001 and abs(size-d)<1e-6 and abs(drill-h)<1e-6 for other,q,d,h in oldvias):reason='source via representation'
            if name in manual:reason='manual or unused net'
            if ident in oldids:reason='original UUID retained exactly'
            if reason:discarded.append(dict(uuid=ident,reason=reason));continue
            first(n,'net')[1]=name
            kept.append(n)
    assert kept
    candidate=old+kept;delta=geometry_delta(old,candidate)
    assert delta['other_root_geometry_exact']
    assert all(not delta[t]['removed'] and not delta[t]['changed'] for t in ['footprint','segment','via','zone'])
    assert not delta['footprint']['added'] and not delta['zone']['added']
    dest=work/'accepted-signals.kicad_pcb';assert not dest.exists();dest.write_text(sexpr(candidate)+'\n')
    inputs=[work/'input.kicad_pcb',work/'raw-import.kicad_pcb',rp,work/'export.json',Path(__file__)]
    (work/'adoption.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),
        geometry_delta=delta,discarded_import_objects=discarded,raised_fanout_tracks=raised,
        added_segments=len(delta['segment']['added']),added_vias=len(delta['via']['added']),
        protected_copper_and_components_exact=True,mutable_signal_copper_replaced=True,delta_from_routed_parent=geometry_delta(original,candidate),native_checks_pending=True,fabrication_released=False),indent=2)+'\n')
    print('Merged',len(delta['segment']['added']),'tracks',len(delta['via']['added']),'vias; original geometry exact')

if __name__=='__main__':run()
