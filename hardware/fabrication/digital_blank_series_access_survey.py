"""Filter R1013 placements by potential continuous access to both nets."""
import copy
import itertools
import json
import math
import time
import uuid
from pathlib import Path

from shapely.affinity import translate
from shapely.geometry import Point, LineString, Polygon, box
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.audit_candidate import sha, geometry_delta
from hardware.fabrication.digital_core_layout import pad_box
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add, route
from hardware.fabrication.digital_region_point_access import reachability
import hardware.fabrication.digital_xlat_escape_repair as repair
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v4 as search

ROOT = Path(__file__).resolve().parent
SRC, DATA = '/PROCESSOR/LED_BLANK_SRC', 'LED_BLANK'


def polys(g):
    return [dict(outer=list(g.exterior.coords), holes=[list(h.coords) for h in g.interiors])]


def run():
    cp = ROOT/'staging/digital-led35-dac-pot-inputs-33/capture.json'
    tp = ROOT/'staging/digital-blank-series-templates-01/templates.json'
    cap, templates = [json.loads(p.read_text()) for p in (cp, tp)]
    for receipt in (cap, templates):
        assert all(sha(Path(p)) == h for p, h in receipt['source_sha256'].items())
    assert all(sha(tp.parent/r['file']) == r['sha256'] for r in templates['templates'])
    pcb = next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    original = read_sexpr(pcb.read_text())
    fps = {next(p[2] for p in children(f, 'property') if p[1] == 'Reference'): f for f in children(original, 'footprint')}
    old = fps['R1013']
    assert list(map(float, first(old, 'at')[1:])) == [45.56, 38.5, 90] and first(old, 'layer')[1] == 'B.Cu'
    removed = [n for tag in ('segment', 'via') for n in children(original, tag) if first(n, 'net')[1] == SRC]
    ids = {first(n, 'uuid')[1] for n in removed}
    assert ids == {'56a79310-d0cf-5887-980f-e8d1cda12bc8'}
    base = copy.deepcopy(cap)
    base['objects'] = [o for o in base['objects'] if o['uuid'] not in ids and o.get('ref') != 'R1013']
    surface.WIDTH = layers.WIDTH = raster.WIDTH = search.WIDTH = .2
    surface.MARGIN = .01
    surface.SIGNAL_LAYERS = search.LAYERS = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    repair.search = search
    screen = DigitalViaScreen(base, signal_layers=search.LAYERS)
    profile = Polygon([(0,0),(64,0),(64,3),(104,3),(104,9),(114,9),(114,60),(0,60)])
    sides = {r: first(f, 'layer')[1][0] for r, f in fps.items()}
    courts = {r: box(*courtyard(f, sides[r]+'.CrtYd')) for r, f in fps.items() if r != 'R1013'}
    through = {r: [box(*pad_box(f, p, .5)) for p in children(f, 'pad') if p[2] == 'thru_hole'] for r, f in fps.items() if r != 'R1013'}
    mounts = [box(x-3.6,y-3.6,x+3.6,y+3.6) for x,y in [(4,4),(66,13),(110,25),(4,36),(110,44)]]
    geometries = {side: [(o['net'], surface.shape(o['layers'][side+'.Cu'])) for o in base['objects'] if o['layers'].get(side+'.Cu')] for side in ('F','B')}
    trees = {s: STRtree([g for n, g in rows]) for s, rows in geometries.items()}
    drilled = [(Point(p), r) for _, p, r, _ in screen.drilled]
    contacts_by_net = {n: {(f,tuple(p)) for o in base['objects'] if o['net'] == n for f in search.LAYERS if o['layers'].get(f) for p in [o['position_mm']]+([o['end_mm']] if o['kind'] == 'PCB_TRACK' else [])} for n in (SRC,DATA)}
    poses = []
    counts = dict(screened=0, mechanical=0, pad_clear=0)
    for template in templates['templates']:
        fp = read_sexpr((tp.parent/template['file']).read_text())
        side = template['side']
        court = box(*courtyard(fp, side+'.CrtYd'))
        for x, y in itertools.product([39+i*.5 for i in range(63)], [20+i*.5 for i in range(47)]):
            counts['screened'] += 1
            cc = translate(court, x, y)
            if not profile.covers(cc) or cc.distance(profile.boundary) < .5-1e-8 or any(cc.distance(m) < .15-1e-8 for m in mounts):
                continue
            if any(cc.distance(g) < .3-1e-8 for r, g in courts.items() if sides[r] == side):
                continue
            if any(cc.intersection(g).area > 1e-10 for r, rows in through.items() if sides[r] != side for g in rows):
                continue
            counts['mechanical'] += 1
            pads = []
            for p in template['pads']:
                g = translate(surface.shape(p['polygons']), x, y)
                if any(n != p['net'] and g.distance(h) < .21-1e-8 for i in trees[side].query(g.buffer(.22)) for n, h in [geometries[side][int(i)]]):
                    break
                if any(q.distance(g)-r < .16-1e-8 for q, r in drilled):
                    break
                pads.append(dict(uuid=p['uuid'], ref='R1013', pin=p['pin'], net=p['net'], kind='PAD',
                                 position_mm=[p['position_mm'][0]+x,p['position_mm'][1]+y],
                                 drill_mm=[0,0], layers={side+'.Cu':polys(g)}, group=None))
            if len(pads) != 2:
                continue
            counts['pad_clear'] += 1
            moved = copy.deepcopy(fp)
            first(moved, 'at')[1:3] = [x,y]
            score = sum((2 if p['net'] == SRC else 1)*min(math.dist(p['position_mm'],q) for f,q in contacts_by_net[p['net']]) for p in pads)
            poses.append(dict(side=side, angle=template['angle'], position_mm=[x,y], template=template['file'], pads=pads, footprint=moved, score=score))
    poses.sort(key=lambda p: p['score'])
    print('Placement screen:', counts, flush=True)
    access = {}
    for net in (SRC,DATA):
        anchors = [(f,o['position_mm']) for o in base['objects'] if o['kind'] == 'PAD' and o['net'] == net for f in search.LAYERS if o['layers'].get(f)]
        crossings = [(o['position_mm'],[f for f in search.LAYERS if o['layers'].get(f)]) for o in base['objects'] if o['net'] == net and (o['kind'] == 'PCB_VIA' or o['kind'] == 'PAD' and any(o.get('drill_mm',[0,0])))]
        probes = [(p['side']+'.Cu',next(o['position_mm'] for o in p['pads'] if o['net'] == net)) for p in poses]
        access[net] = reachability(screen,net,anchors,anchors,search.LAYERS,existing_crossings=crossings,probes=probes)
        print(net,'potentially accessible poses:',sum(r['connected_to_sources'] for r in access[net]['probe_results']),flush=True)
    eligible = [i for i in range(len(poses)) if all(access[n]['probe_results'][i]['connected_to_sources'] for n in (SRC,DATA))]
    paths = [cp,tp,pcb,Path(__file__)] + [tp.parent/r['file'] for r in templates['templates']] + [ROOT/n for n in
        ('audit_candidate.py','digital_core_layout.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py',
         'digital_continuous_escape_options_v4.py','digital_multilayer_escape_routes_v4.py','digital_visibility_escape.py',
         'digital_native_spacing_search_v4.py','digital_native_spacing_search_v3.py','digital_native_spacing_search_v2.py',
         'digital_continuous_via_bridges.py','nf_minimum_logic.py','nf_pin_escape_routes.py','route_nf_surface.py',
         'nf_softstart_joint_screen.py','nf_softstart_cell_routes.py','digital_region_point_access.py')]
    paths.append(ROOT.parent/'electronics/output_stage/check_placement.py')
    report = dict(source_sha256={str(p):sha(p) for p in paths},placement_counts=counts,access=access,
                  eligible_pose_indices=eligible,poses=[{k:v for k,v in p.items() if k != 'footprint'} for p in poses],
                  hypothetical_moved_pad_copper_omitted_for_optimistic_access_test=True,
                  joint_route_feasibility_not_established=True,candidate_emitted=False,fabrication_released=False)
    out = ROOT/'staging/digital-blank-series-access-survey-01'
    out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Both nets potentially accessible:',len(eligible),flush=True)


if __name__ == '__main__':
    run()
