"""Shorten LED09's native In5 chain using independently screened chords."""
import copy
import json
import math
import uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha, geometry_delta
from hardware.fabrication.digital_route_shortcuts import simplify
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_serial1_joint_repair import ROOT, FACES
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

NET='/LED/LED_09'


def run():
    cp=ROOT/'staging/digital-led09-closed-inputs-29/capture.json'
    cap=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
    pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    rows=[o for o in cap['objects'] if o['net']==NET and o['kind']=='PCB_TRACK' and o['layers'].get('In5.Cu')]
    assert len(rows)==27
    removed={o['uuid'] for o in rows}
    path=[(4.625,19.875)]
    unused=rows[:]
    while unused:
        matches=[o for o in unused if any(math.dist(path[-1],o[k])<1e-7 for k in ('position_mm','end_mm'))]
        assert len(matches)==1
        o=matches[0]
        path.append(tuple(o['end_mm'] if math.dist(path[-1],o['position_mm'])<1e-7 else o['position_mm']))
        unused.remove(o)
    assert path[-1]==(53.16,51.46)
    work=copy.deepcopy(cap)
    work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH=layers.WIDTH=.2
    surface.MARGIN=.001
    surface.SIGNAL_LAYERS=FACES
    screen=CloseMarginViaScreen(work,signal_layers=FACES)
    result=simplify(screen,NET,dict(runs=[('In5.Cu',path)],vias=[]))
    selected=add(screen,NET,result)
    old_length=sum(math.dist(o['position_mm'],o['end_mm']) for o in rows)
    assert selected['planar_length_mm']<old_length and not selected['new_vias_mm']
    before=read_sexpr(pcb.read_text())
    board=copy.deepcopy(before)
    retired=[n for n in children(board,'segment') if first(n,'uuid')[1] in removed]
    assert len(retired)==27
    for n in retired:
        board.remove(n)
    for face,points in selected['runs']:
        for p,q in zip(points,points[1:]):
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:LED09-SHORTCUT:{sha(cp)}:{face}:{p}:{q}'))
            board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),NET],[a('uuid'),uid]])
    out=ROOT/'staging/digital-led09-screened-shortcuts-01'
    out.mkdir(exist_ok=False)
    dest=out/pcb.name
    dest.write_text(sexpr(board)+'\n')
    paths=[cp,pcb,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_route_shortcuts.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_serial1_joint_repair.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]+[ROOT.parent/'electronics/common/sexpr.py',ROOT.parents[1]/'tests/tooling/test_digital_route_shortcuts.py']
    report=dict(source_sha256={str(p):sha(p) for p in paths},candidate_PCB_sha256=sha(dest),candidate_emitted=True,
                removed_uuids=sorted(removed),removed_objects=retired,routes=[selected],geometry_delta=geometry_delta(before,board),
                before_trunk_length_mm=old_length,after_trunk_length_mm=selected['planar_length_mm'],native_rules_relaxed=False,
                native_checks_pending=True,global_optimum_proven=False,electrical_performance_qualified=False,fabrication_released=False)
    (out/'construction.json').write_text(json.dumps(report,indent=2)+'\n')
    print('LED09 trunk shortened:',old_length,'->',selected['planar_length_mm'])


if __name__=='__main__':
    run()
