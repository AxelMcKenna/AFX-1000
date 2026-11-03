"""Plan the short, off-grid CHIP_EN bridge between two actual native islands."""
import math

from shapely.geometry import LineString

from hardware.fabrication.audio_main_global_controls import SignalScreen


def propose(captured):
    objects = {o['uuid']: o for o in captured['objects']}
    members = {i: key for key, ids in captured['groups'].items() for i in ids}
    pads = {(o['ref'], o['pin']): o for o in objects.values() if o['kind']=='PAD' and o['pin']}
    start, end = pads['U210', '6'], pads['R209', '1']
    net, point = 'CHIP_EN', [66.7, 8.3]
    assert start['net'] == end['net'] == net
    groups = [members[p['uuid']] for p in (start, end)]
    assert groups[0] != groups[1]
    screen = SignalScreen(captured)
    runs = [('F.Cu', [start['position_mm'], point]), ('B.Cu', [point, end['position_mm']])]
    assert screen.via_legal(net, point)
    assert all(math.dist(point, p) > .86 for _, p in screen.vias)
    assert all(screen.legal(net, face, ps) and LineString(ps).length <= 3.5 for face, ps in runs)
    length = sum(LineString(ps).length for _, ps in runs)
    terminals = [start['position_mm'], end['position_mm']]
    limit = min(180, 2.5*math.dist(*terminals)+10)
    assert length <= limit
    return dict(net=net, runs=runs, vias=[point], new_vias_mm=[point], groups=groups,
                source_groups=[[k] for k in groups], portals=[point, point],
                planar_length_mm=length, maximum_planar_length_mm=limit,
                terminal_points_mm=terminals, search_visits=0, layer_transition_count=1,
                planned_by='exact_off_grid_common_via', native_checks_pending=True)
