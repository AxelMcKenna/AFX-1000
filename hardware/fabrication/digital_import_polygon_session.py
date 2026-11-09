"""Restore native circular via padstacks in a conservative polygon routing session."""
import argparse, copy, json, re, sys
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.bypass_import import identity
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT=Path(__file__).resolve().parent

def run():
    assert sys.platform=='linux', 'Mac CAD remains disabled'
    import pcbnew
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',required=True);args=parser.parse_args()
    assert args.workspace and all(c.isalnum() or c in '-_' for c in args.workspace)
    work=ROOT/'staging'/args.workspace
    export=json.loads((work/'export.json').read_text());command=json.loads((work/'router-command.json').read_text())
    assert command['returncode']==0 and sha(work/'routed.ses')==command['session_sha256']
    assert sha(work/'input.kicad_pcb')==export['source_PCB_sha256']
    tree=read_sexpr((work/'routed.ses').read_text());original=copy.deepcopy(tree)
    routes=first(tree,'routes');resolution=first(routes,'resolution')
    assert resolution[1]=='um' and float(resolution[2])==10
    native=read_sexpr((work/'native-input.dsn').read_text().replace('(string_quote ")','(string_quote QUOTE)'))
    native_stacks={p[1]:p for p in children(first(native,'library'),'padstack')}
    restored=[]
    for stack in children(first(routes,'library_out'),'padstack'):
        name=stack[1];match=re.fullmatch(r'Via\[0-5\]_(600|650):300_um',str(name));assert match,name
        source=native_stacks[name];shapes=children(stack,'shape');old=children(source,'shape')
        assert len(shapes)==len(old)==6
        for target,reference in zip(shapes,old):
            assert reference[1][0]=='circle' and target[1][0]=='polygon'
            assert target[1][1]==reference[1][1]
            diameter=float(reference[1][2]);assert diameter==float(match[1])
            target[1]=[a('circle'),reference[1][1],diameter*10]
        restored.append(name)
    # Only the library representations change; every session wire/via placement is exact.
    normalized=copy.deepcopy(tree)
    first(normalized,'routes')[first(normalized,'routes').index(first(first(normalized,'routes'),'library_out'))]=copy.deepcopy(first(first(original,'routes'),'library_out'))
    assert sexpr(normalized)==sexpr(original)
    session=work/'native-vias.ses';assert not session.exists();session.write_text(sexpr(tree)+'\n')
    board=pcbnew.LoadBoard(str(work/'input.kicad_pcb'));before=identity(board)
    assert pcbnew.ImportSpecctraSES(board,str(session))
    after=identity(board)
    for ref,p in before.items():
        q=after[ref];assert p[:3]==q[:3] and p[5:]==q[5:]
        assert max(abs(p[3]-q[3]),abs(p[4]-q[4]))<=500
    network=first(routes,'network_out')
    expected_vias=sum(len(children(net,'via')) for net in children(network,'net'))
    actual_vias=sum(t.GetClass()=='PCB_VIA' for t in board.GetTracks())
    assert actual_vias==expected_vias,(actual_vias,expected_vias)
    dest=work/'normalized-import.kicad_pcb';assert not dest.exists();assert pcbnew.SaveBoard(str(dest),board)
    inputs=[work/'input.kicad_pcb',work/'routed.ses',work/'native-input.dsn',work/'export.json',work/'router-command.json',session,Path(__file__)]
    with (work/'normalized-import.json').open('x') as f:
        json.dump(dict(source_sha256={str(p):sha(p) for p in inputs},raw_PCB_sha256=sha(dest),
            restored_native_via_padstacks=restored,session_vias=expected_vias,imported_vias=actual_vias,
            session_wires_and_via_placements_exact=True,exact_source_merge_required=True,native_checks_pending=True,fabrication_released=False),f,indent=2);f.write('\n')
    print('Restored circular via padstacks; imported all',actual_vias,'session vias')

if __name__=='__main__':run()
