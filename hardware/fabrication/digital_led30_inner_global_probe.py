"""Explore LED30 global paths without using the crowded front face.

This is a diagnostic. Removed foreign copper must be restored before any PCB
candidate can be accepted.
"""
import copy
import json
import time
from pathlib import Path
from shapely.geometry import LineString, Point
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_serial1_joint_repair import ROOT, FACES
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_screen_branch import branch
from hardware.fabrication.digital_costed_region_route_v3 import route
from hardware.fabrication.digital_combine_costed_routes import center_vertices
from hardware.fabrication.digital_route_shortcuts import simplify
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers


def run():
    cp = ROOT/'staging/digital-led16-closed-inputs-27/capture.json'
    rp = ROOT/'staging/digital-led30-whole-trunks-01/construction.json'
    cap, prior = [json.loads(p.read_text()) for p in (cp,rp)]
    for record in (cap,prior):
        assert all(sha(Path(p)) == h for p,h in record['source_sha256'].items())
    work = copy.deepcopy(cap)
    work['objects'] = [o for o in cap['objects'] if o['uuid'] not in prior['removed_uuids']]
    surface.WIDTH = layers.WIDTH = .2; surface.MARGIN = .001; surface.SIGNAL_LAYERS = FACES
    base = CloseMarginViaScreen(work,signal_layers=FACES)
    net = '/LED/LED_30'
    source = next(o for o in cap['objects'] if o.get('ref') == 'U3002' and o.get('pin') == '11')
    target = next(o for o in cap['objects'] if o.get('ref') == 'J3003' and o.get('pin') == '19')
    via = (33.997,19.339932)
    lead = prior['attempts'][0]['search']['route']['runs'][-1]
    assert lead[0] == 'F.Cu' and tuple(lead[1][0]) == via and lead[1][-1] == source['position_mm']
    full = branch(base)
    escape = add(full,net,dict(runs=[lead],vias=[via]))
    screen = branch(full)
    screen.geometry = {f:g for f,g in screen.geometry.items() if f != 'F.Cu'}
    screen.added = []  # Only the same-net front lead is omitted from this global search.
    faces = tuple(screen.geometry)
    result = route(screen,net,[(f,via) for f in faces],[(f,target['position_mm']) for f in faces],
                   time.monotonic()+110,max_refinements=180)
    routes, cuts = [], []
    if result['route']:
        raw = result['route']
        normal, changes = center_vertices(full,dict(net=net,runs=raw['runs'],new_vias_mm=raw['vias']),[via])
        simple = simplify(full,net,dict(runs=normal['runs'],vias=normal['new_vias_mm']))
        routes = [escape,add(full,net,simple)]
        for o in cap['objects']:
            if o['uuid'] not in prior['removed_uuids']:
                continue
            gs = {f:surface.shape(ps) for f,ps in o['layers'].items() if ps}
            hit = any(LineString(p).distance(gs[f]) <= .3015 for r in routes for f,p in r['runs'] if f in gs)
            hit |= any(Point(p).distance(g) <= .501 for r in routes for p in r['new_vias_mm'] for g in gs.values())
            if hit:
                cuts.append(o)
        minimal = copy.deepcopy(cap)
        removed = {o['uuid'] for o in cuts}
        minimal['objects'] = [o for o in cap['objects'] if o['uuid'] not in removed]
        replay = CloseMarginViaScreen(minimal,signal_layers=FACES)
        for r in routes:
            add(replay,net,dict(runs=r['runs'],vias=r['new_vias_mm']))
        print('LED30 length',sum(r['planar_length_mm'] for r in routes),'cuts',len(cuts),flush=True)
        for o in cuts:
            print(o['uuid'],o['net'],o['kind'],o['position_mm'],o.get('end_mm'),flush=True)
    out = ROOT/'staging/digital-led30-inner-global-probe-01';out.mkdir(exist_ok=False)
    names = ('audit_candidate.py','digital_serial1_joint_repair.py','digital_via_spacing_close_margin.py',
             'digital_via_spacing_v2.py','digital_screen_branch.py','digital_costed_region_route.py',
             'digital_costed_region_route_v3.py','digital_polygon_path.py','digital_region_reachability.py',
             'digital_planned_region_screen.py','digital_combine_costed_routes.py','digital_route_shortcuts.py',
             'digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py',
             'nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')
    paths = [cp,rp,Path(__file__)]+[ROOT/n for n in names]
    report = dict(source_sha256={str(p):sha(p) for p in paths},search=result,routes=routes,
                  removed_uuids=[o['uuid'] for o in cuts],blocking_objects=cuts,
                  global_routing_faces=faces,foreign_connections_restored=False,
                  candidate_emitted=False,native_rules_relaxed=False,fabrication_released=False)
    (out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    run()
