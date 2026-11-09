"""Locate control-track blockers on a possible LED_35 global path.

Diagnostic only: all pads, existing vias/drills, power copper and non-control
tracks remain. Any reported blocker needs complete restoration before adoption.
"""
import copy
import json
import math
import time
from pathlib import Path

from shapely.geometry import LineString, Point
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.route_nf_surface import shape
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v4 as search

ROOT = Path(__file__).resolve().parent


def run():
    cp = ROOT/'staging/digital-led-sink-inputs-34/capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in cap['source_sha256'].items())
    ignored = [o for o in cap['objects'] if o['kind'] == 'PCB_TRACK' and o['net'].startswith('/CONTROLS/CONTROL_')]
    assert ignored and all(o['width_mm'] == .2 for o in ignored)
    ids = {o['uuid'] for o in ignored}
    work = copy.deepcopy(cap)
    work['objects'] = [o for o in work['objects'] if o['uuid'] not in ids]
    surface.WIDTH = layers.WIDTH = raster.WIDTH = search.WIDTH = .2
    surface.MARGIN = .01
    raster.STEP = search.STEP = .05
    raster.RASTER_MARGIN = math.sqrt(2)*raster.STEP/2+.002
    surface.SIGNAL_LAYERS = search.LAYERS = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    screen = DigitalViaScreen(work, signal_layers=search.LAYERS)
    net = '/LED/LED_35'
    start = next(o for o in work['objects'] if o.get('ref') == 'U3002' and o.get('pin') == '16')
    end = next(o for o in work['objects'] if o['kind'] == 'PAD' and o['net'] == net and o['ref'].startswith('J'))
    via = (33.444941, 22.040900)
    local = add(screen, net, dict(runs=[('F.Cu', [start['position_mm'], via])], vias=[via]))
    source = dict(point=via, layers=list(search.LAYERS), runs=[], vias=[], cost=0., group='LED')
    target = dict(point=end['position_mm'], layers=[f for f in search.LAYERS if end['layers'].get(f)], runs=[], vias=[], cost=0., group='header')
    result = search.route_multi(screen, net, [source], {f: [target] for f in search.LAYERS}, time.monotonic()+120, max_visits=5000000)
    paths = [cp, Path(__file__)]+[ROOT/n for n in
             ('audit_candidate.py', 'digital_via_spacing_v2.py', 'digital_xlat_escape_repair.py',
              'digital_native_spacing_search_v4.py', 'digital_continuous_via_bridges.py',
              'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py',
              'nf_minimum_logic.py', 'route_nf_surface.py', 'nf_pin_escape_routes.py')]
    report = dict(source_sha256={str(p): sha(p) for p in paths}, ignored_control_track_uuids=sorted(ids),
                  all_pads_vias_drills_keepouts_power_and_other_tracks_retained=True,
                  route_found=bool(result), PCB_emitted=False, fabrication_released=False)
    if result:
        runs = local['runs']+result['runs']
        vias = local['new_vias_mm']+result['vias']
        blockers = []
        for obj in ignored:
            geometries = {f: shape(ps) for f, ps in obj['layers'].items() if ps}
            track_hit = any(LineString(p).distance(geometries[f]) <= .310001 for f, p in runs if f in geometries)
            via_hit = any(Point(p).distance(g) <= .513001 for p in vias for g in geometries.values())
            if track_hit or via_hit:
                blockers.append({k: obj[k] for k in ('uuid', 'net', 'position_mm', 'end_mm', 'width_mm')})
        original = DigitalViaScreen(cap, signal_layers=search.LAYERS)
        report.update(runs=runs, vias=vias, planar_length_mm=sum(LineString(p).length for _, p in runs),
                      blockers=blockers, blocker_nets=sorted({o['net'] for o in blockers}),
                      all_segments_legal_against_original=all(original.legal(net, f, p) for f, p in runs),
                      all_vias_legal_against_original=all(original.via_legal(net, p) for p in vias))
    out = ROOT/'staging/digital-led35-global-obstructions-01'
    out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Diagnostic path found:', bool(result), 'blocking nets:', report.get('blocker_nets'))


if __name__ == '__main__':
    run()
