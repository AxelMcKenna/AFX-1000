"""Preserve current connections while freeing the proven SERIAL_1 source escape.

The serial escape is independently replayed but not installed as a dangling
via. Only MCU_PERMIT and LED37 copper changes; no routing-completion claim.
"""
import copy,json,math,uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_native_route_cleanup import prune_single_face_vias
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL,PERMIT
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';rp=ROOT/'staging/digital-serial1-joint-source-restoration-01/diagnosis.json'
    cap,recipe=[json.loads(p.read_text()) for p in (cp,rp)]
    for r in (cap,recipe):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    proposal=recipe['selected_source_proposals'][0];led='/LED/LED_37'
    source_ids=set(recipe['removed_uuids'])
    removed={o['uuid'] for o in cap['objects'] if o['uuid'] in source_ids and o['net'] in (PERMIT,led)}
    removed.update(('4b7c5f77-b3cf-535f-a5fd-e79ee80dde39','c7e804c1-3053-5223-8d97-43e9701185b2','53e5831a-7edd-5215-b4fa-5299a17ca0f6'))
    assert len(removed)==8
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    screen=CloseMarginViaScreen(work,signal_layers=FACES);routes=[]
    for old in proposal['routes']:
        if old['net']==SERIAL:continue
        r=copy.deepcopy(old)
        if r['net']==led and not r['new_vias_mm']:
            assert r['runs']==[['In3.Cu',[[43.85,21.2],[43.84,21.33]]]]
            r['runs'][0][1].append([41.6,22.8])
        routes.append(add(screen,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm'])))
    escape=next(r for r in proposal['routes'] if r['net']==SERIAL)
    add(screen,SERIAL,dict(runs=escape['runs'],vias=escape['new_vias_mm']))
    routes,pruned=prune_single_face_vias(work,routes)
    pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    original=read_sexpr(pcb.read_text());board=copy.deepcopy(original)
    retired=[n for tag in ('segment','via') for n in children(board,tag) if first(n,'uuid')[1] in removed]
    assert len(retired)==len(removed)
    for n in retired:board.remove(n)
    for r in routes:
        for face,path in r['runs']:
            for p,q in zip(path,path[1:]):
                if math.dist(p,q)<1e-7:continue
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:SERIAL1-SOURCE:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),r['net']],[a('uuid'),uid]])
        for p in r['new_vias_mm']:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:SERIAL1-SOURCE-via:{sha(cp)}:{r["net"]}:{p}'))
            board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),r['net']],[a('uuid'),uid]])
    out=ROOT/'staging/digital-serial1-source-preparation-01';out.mkdir(exist_ok=False)
    dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
    paths=[cp,rp,pcb,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_native_route_cleanup.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},candidate_PCB_sha256=sha(dest),candidate_emitted=True,
        removed_uuids=sorted(removed),removed_objects=retired,routes=routes,pruned_unused_vias=pruned,geometry_delta=geometry_delta(original,board),
        future_serial_escape_replayed_but_not_installed=escape,expected_opens_unchanged=31,native_checks_pending=True,native_rules_relaxed=False,fabrication_released=False),indent=2)+'\n')
    print('Prepared source-side candidate; native validation pending; expected opens remain 31',flush=True)

if __name__=='__main__':run()
