"""Source-bound SERIAL_1 trial with explicit restoration of every removed branch.

No board is emitted here: successful proposals require native construction,
connectivity replay and physical review before adoption.
"""
import copy
import itertools
import json
import time
from pathlib import Path

from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_continuous_net_route import route
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

ROOT = Path(__file__).resolve().parent
FACES = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
SERIAL = '/LED/SERIAL_1'
PERMIT = '/PROCESSOR/MCU_PERMIT'
CLOCK = '/LED/CLOCK_5V'
LED = '/LED/LED_48'


def run():
    cp = ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json'
    dp = ROOT/'staging/digital-interface-hard-obstructions-32-01/diagnosis.json'
    kp=ROOT/'staging/digital-serial1-target-cutset-02/diagnosis.json'
    cap, diag, cut = [json.loads(p.read_text()) for p in (cp, dp, kp)]
    for record in (cap, diag, cut):
        assert all(sha(Path(p)) == h for p, h in record['source_sha256'].items())
    escapes = [r['options'][0] for r in diag['results'] if (r['ref'], r['pin']) in [('U3002','29'), ('U3003','4')]]
    assert len(escapes) == 2
    removed = set(cut['base_removed_uuids']) | set(cut['selected_extra_uuids'])
    assert cut['potential_access'] and cut['inclusion_minimal_within_tested_objects']
    objects = {o['uuid']: o for o in cap['objects']}
    assert len(removed) == 14 and removed <= objects.keys()
    assert {objects[u]['net'] for u in removed} == {PERMIT, CLOCK, LED, "/CONTROLS/CONTROL_30"}
    assert all(objects[u]['kind'] in ('PCB_TRACK','PCB_VIA') for u in removed)
    work = copy.deepcopy(cap)
    work['objects'] = [o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH = layers.WIDTH = .2
    surface.CLEARANCE = .2
    surface.MARGIN = .001
    surface.SIGNAL_LAYERS = FACES
    tasks = [
        ('permit trunk', PERMIT, 'In5.Cu', (45.,13.8), {('In5.Cu',(38.3,19.7))}),
        ('permit branch', PERMIT, 'B.Cu', (41.5,16.9125), {('In5.Cu',(45.,13.8)),('In5.Cu',(38.3,19.7))}),
        ('clock', CLOCK, 'F.Cu', (75.25,19.425), {('B.Cu',(71.6,19.8))}),
        ('led48', LED, 'F.Cu', (74.15,20.725), {('In3.Cu',(73.3976,17.2734))}),
        ('control30', '/CONTROLS/CONTROL_30', 'F.Cu', (81.9,11.1), {('F.Cu',(82.,14.6))}),
        ('serial', SERIAL, 'F.Cu', (42.75,14.075), {('F.Cu',(75.25,20.075))}),
    ]
    orders = [[tasks[i] for i in order] for order in [
        (5,1,3,0,2,4), (1,3,5,0,2,4), (3,1,5,2,0,4),
        (1,5,3,0,2,4), (3,5,1,2,0,4), (5,3,1,4,2,0),
        (2,3,1,5,0,4), (1,0,3,2,5,4), (4,1,3,5,2,0),
        (3,2,1,0,5,4), (5,4,1,3,0,2), (1,3,5,4,2,0)]]
    attempts, selected = [], None
    deadline = time.monotonic()+510
    for order in orders:
        if time.monotonic() >= deadline:
            break
        screen = CloseMarginViaScreen(work, signal_layers=FACES)
        attempt = dict(order=[t[0] for t in order], repairs=[])
        attempts.append(attempt)
        attempt['fixed_escapes_used'] = False
        routes = []
        for name, net, face, start, ends in order:
            crossings = [(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in work['objects'] if o['net']==net and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]
            crossings += [(p,list(FACES)) for n,p in screen.new_vias if n==net]
            result = route(screen,net,face,start,ends,min(deadline,time.monotonic()+45),existing_crossings=crossings)
            entry = dict(task=name,found=bool(result))
            attempt['repairs'].append(entry)
            if result:
                added = add(screen,net,result)
                routes.append(added)
                entry.update(planar_length_mm=added['planar_length_mm'],new_vias=len(added['new_vias_mm']))
            print(json.dumps(entry),flush=True)
            if not result:
                break
        attempt['routes'] = routes
        if len(attempt['repairs'])==6 and all(r['found'] for r in attempt['repairs']):
            selected = routes
            break
    paths = [cp,dp,kp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_continuous_net_route.py','digital_xlat_escape_repair.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_planned_region_screen.py','digital_region_reachability.py','digital_polygon_path.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    report = dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=sorted(removed),removed_objects=[objects[u] for u in sorted(removed)],attempts=attempts,complete_route_proposal=selected,all_other_copper_retained=True,component_positions_preserved=True,native_rules_relaxed=False,native_checks_pending=bool(selected),candidate_emitted=False,fabrication_released=False)
    out=ROOT/'staging/digital-serial1-joint-repair-02'
    out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Complete joint proposal:',bool(selected),flush=True)


if __name__=='__main__':
    run()
