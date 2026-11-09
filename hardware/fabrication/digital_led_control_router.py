"""Eight-layer LED/control exchange retaining every other net as protected copper.

Import only produces a raw candidate; a separate exact-geometry merge and
native review are required before selection. Source files remain unchanged.
"""
import argparse
import math
import json
import re
import shlex
import shutil
import sys
from pathlib import Path

from hardware.fabrication.audit_candidate import native_evidence_errors,sha
from hardware.fabrication.bypass_import import identity
from hardware.electronics.common.sexpr import read_sexpr,children,first

ROOT=Path(__file__).resolve().parent

def export(source,work):
    import pcbnew
    pcb=source/'digital_core.kicad_pcb';project=pcb.with_suffix('.kicad_pro')
    review=json.loads((source/'review.json').read_text())
    assert not native_evidence_errors(project,review)
    assert review['status']['counts']['schematic_parity']==review['status']['counts']['erc']==0
    assert all(v['type']=='via_dangling' and v['severity']=='warning' for v in json.loads((source/'drc.json').read_text())['violations'])
    work.mkdir(exist_ok=False);shutil.copyfile(pcb,work/'input.kicad_pcb')
    board=pcbnew.LoadBoard(str(pcb));manager=pcbnew.GetSettingsManager()
    assert manager.LoadProject(str(project));board.SetProject(manager.GetProject(str(project)))
    def manual(name):
        movable = (name.startswith('/LED/LED_') or name.startswith('/CONTROLS/CONTROL_')
                   or name in {'/LED/SERIAL_0','/LED/SERIAL_1','LED_XLAT','LED_BLANK','BYPASS_SENSE'})
        return not movable
    fixed={item.m_Uuid.AsString() for item in board.GetTracks() if manual(str(item.GetNetname()))}
    removed_base=set()
    for item in board.GetTracks():item.SetLocked(item.m_Uuid.AsString() in fixed)
    assert pcbnew.ExportSpecctraDSN(board,str(work/'native-input.dsn'))
    text=(work/'native-input.dsn').read_text()
    wiring=text[text.index('  (wiring'):]
    # KiCad may combine contiguous source segments into a single DSN path.
    assert 0<len(re.findall(r'\(type fix\)',wiring))<len(re.findall(r'\((?:wire|via)\s',wiring))
    text=text[:text.index('  (wiring')]+wiring.replace('(type fix)','(type protect)').replace('(type route)','(type normal)')
    wiring=text[text.index('  (wiring'):]
    # DSN protects the declared SD/power/local objects; the original PCB lock flags
    # are never saved or adopted from the routing interchange.
    counts={kind:len(re.findall(r'\('+kind+r'\s',wiring)) for kind in ['wire','via']}
    protected=len(re.findall(r'\(type protect\)',wiring))
    movable=len(re.findall(r'\(type normal\)',wiring))
    assert '(type route)' not in wiring and movable+protected==counts['wire']+counts['via']
    assert 0<protected<counts['wire']+counts['via'],(protected,counts)
    text=text.replace('(clearance 50 (type smd_smd))','(clearance 200 (type smd_smd))')
    match=re.search(r'    \(class kicad_default ([\s\S]*?)(      \(circuit[\s\S]*?\n    \))',text);assert match
    names=set(shlex.split(match.group(1)))
    excluded={n for n in names if manual(n)}
    included=names-excluded
    rules=match.group(2).replace('(circuit','(circuit\n        (use_layer F.Cu In3.Cu In5.Cu B.Cu)',1)
    classes='\n'.join('    (class '+label+' '+' '.join(json.dumps(n) for n in sorted(nets))+'\n'+rules for label,nets in [('AFX_DIGITAL_SIGNALS',included),('AFX_MANUAL',excluded)])
    text=text[:match.start()]+classes+text[match.end():]
    assert '(snap_angle' not in text
    text=text.replace('  (structure\n','  (structure\n    (snap_angle none)\n',1)
    pattern=r'\(shape \(circle ([^\s()]+) ([\d.]+)(?: ([\d.-]+) ([\d.-]+))?\)\)'
    circle_shapes=[]
    def polygon_circle(match):
        layer=match[1];diameter=float(match[2]);radius=diameter/2/math.cos(math.pi/64)
        x,y=float(match[3] or 0),float(match[4] or 0)
        # Circumscribed, never undersized; add 0.001 um for decimal roundoff.
        radius += .001
        points=' '.join(f'{x+radius*math.cos(2*math.pi*i/64):.6f} {y+radius*math.sin(2*math.pi*i/64):.6f}' for i in range(64))
        circle_shapes.append(dict(layer=layer,diameter_um=diameter,circumscribed_sides=64))
        return '(shape (polygon '+layer+' 0 '+points+'))'
    text=re.sub(pattern,polygon_circle,text)
    assert circle_shapes
    (work/'routing-view.dsn').write_text(text)
    template=ROOT/'staging/digital-signal-routing-03/config/freerouting.json'
    (work/'config').mkdir()
    profile=json.loads(template.read_text())
    profile['router']['layers']=[dict(routable=i in (0,3,5,7),preferred_direction_horizontal=i%2==0) for i in range(8)]
    (work/'config/freerouting.json').write_text(json.dumps(profile,indent=2)+'\n')
    inputs=[pcb,project,source/'review.json',template,Path(__file__)]
    (work/'export.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},source_PCB_sha256=sha(pcb),
        routing_DSN_sha256=sha(work/'routing-view.dsn'),native_DSN_sha256=sha(work/'native-input.dsn'),
        circle_shape_conversion=circle_shapes,angle_restriction="none",removed_base_UUIDs=sorted(removed_base),protected_source_objects=counts,protected_DSN_items=protected,movable_DSN_items=movable,unlocked_DSN_type="normal",expected_footprints=len(identity(board)),
        routed_net_names=sorted(included),manual_net_names=sorted(excluded),expected_opens=review['uncapped_open_connections'],
        SD_power_local_copper_protected=True,protected_source_UUIDs=sorted(fixed),trial_signal_copper_may_be_rerouted=True,source_lock_flags_unchanged=True,native_acceptance_pending=True,fabrication_released=False),indent=2)+'\n')
    print('Protected DSN',counts,'routable nets',len(included),flush=True)

def import_raw(work):
    import pcbnew
    export=json.loads((work/'export.json').read_text());command=json.loads((work/'router-command.json').read_text())
    assert command['returncode']==0 and command['session_exists']
    assert sha(work/'routed.ses')==command['session_sha256']
    assert sha(work/'input.kicad_pcb')==export['source_PCB_sha256']
    assert not (work/'raw-import.kicad_pcb').exists()
    board=pcbnew.LoadBoard(str(work/'input.kicad_pcb'));before=identity(board)
    assert pcbnew.ImportSpecctraSES(board,str(work/'routed.ses'))
    after=identity(board)
    for ref in before:
        p,q=before[ref],after[ref]
        assert p[:3]==q[:3] and p[5:]==q[5:]
        assert max(abs(p[3]-q[3]),abs(p[4]-q[4]))<=500
    assert pcbnew.SaveBoard(str(work/'raw-import.kicad_pcb'),board)
    inputs=[work/'input.kicad_pcb',work/'routed.ses',work/'export.json',work/'router-command.json',Path(__file__)]
    (work/'raw-import.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},raw_PCB_sha256=sha(work/'raw-import.kicad_pcb'),exact_source_merge_required=True,native_checks_pending=True,fabrication_released=False),indent=2)+'\n')

if __name__=='__main__':
    assert sys.platform=='linux','Mac CAD remains disabled'
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['export','import']);parser.add_argument('--source');parser.add_argument('--workspace',required=True);args=parser.parse_args()
    for value in [args.source,args.workspace]:assert value is None or (value and all(c.isalnum() or c in '-_' for c in value))
    work=ROOT/'staging'/args.workspace
    if args.action=='export':export(ROOT/'staging'/args.source,work)
    else:import_raw(work)
