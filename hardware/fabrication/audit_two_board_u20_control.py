"""Verify U20 output-sense, feedback-trim and configuration against native copper."""
import json
import math
from pathlib import Path
from shapely.geometry import Point, LineString
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children, read_sexpr
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.route_nf_surface import shape

BASE = STAGING / 'two-board-power-u20-output-native-02'
OUT = STAGING / 'two-board-power-u20-control-native-01'
BEFORE = STAGING / 'two-board-power-routing-inputs-2478-u20-output/capture.json'
AFTER = STAGING / 'two-board-power-routing-inputs-2472-u20-control/capture.json'


def run():
    report_path = OUT / 'u20-control-routing.json'
    report, before, after = [json.loads(p.read_text()) for p in [report_path, BEFORE, AFTER]]
    assert not report['moves']
    for d in [report, before, after]:
        for name, h in d['source_sha256'].items():
            assert sha(REPO / name) == h, name
    for folder in [BASE, OUT]:
        native = json.loads((folder / 'review.json').read_text())
        for name, h in native['artifact_sha256'].items():
            assert sha(folder / name) == h, name
    trees = [read_sexpr((p / 'power_protection.kicad_pcb').read_text()) for p in [BASE, OUT]]
    fps = [{prop(f, 'Reference')[2]: f for f in children(t, 'footprint')} for t in trees]
    assert fps[0].keys() == fps[1].keys() and len(fps[1]) == 1100
    assert all(geometry(f) == geometry(fps[1][ref]) for ref, f in fps[0].items())
    def shell(t):
        return [n for n in t if not (isinstance(n, list) and n and n[0] in ['footprint', 'segment', 'via', 'arc', 'net'])]
    assert shell(trees[0]) == shell(trees[1])
    oldparts, oldpins = read_netlist(BASE / 'netlist.xml')
    parts, pins = read_netlist(OUT / 'netlist.xml')
    assert oldpins == pins and oldparts.keys() == parts.keys() and len(parts) == 1085
    for ref in parts:
        for field in ['value', 'footprint']:
            assert oldparts[ref].findtext(field) == parts[ref].findtext(field)
    old, new = [{o['uuid']: o for o in c['objects']} for c in [before, after]]
    def physical(o):
        return {k: v for k, v in o.items() if k not in ['uuid', 'group']}
    aliases = {}
    for u in old.keys() - new.keys():
        assert old[u]['kind'] == 'PAD'
        hits = [v for v in new.keys() - old.keys() if physical(old[u]) == physical(new[v])]
        assert len(hits) == 1
        aliases[u] = hits[0]
    assert len(aliases) == len(set(aliases.values()))
    oldkeys = {aliases.get(u, u) for u in old}
    for uid, o in old.items():
        assert physical(o) == physical(new[aliases.get(uid, uid)]), uid
    assert before['zones'] == after['zones'] and len(after['zones']) == 2
    groups = {u: set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        mapped = {aliases.get(u, u) for u in g}
        assert mapped <= groups[next(iter(mapped))]
    def pads(ref, pin):
        return [o for o in new.values() if o.get('ref') == ref and o.get('pin') == pin]
    intended = {
        'sense': [('P_C207','1'), ('P_R200','1')],
        'trim': [('P_R200','2'), ('P_R206','1')],
        'FSEL': [('P_U20','1'), ('P_R202','1')],
        'MODE': [('P_U20','2'), ('P_R203','1')],
        'quiet-ground': [('P_U20','5'), ('P_C200','2'), ('P_R201','2'), ('P_R202','2'), ('P_R203','2')],
    }
    verified_groups = {}
    for name, terminals in intended.items():
        g = groups[pads(*terminals[0])[0]['uuid']]
        assert all(o['uuid'] in g for ref,pin in terminals for o in pads(ref,pin)), name
        verified_groups[name] = g
    assert len({tuple(sorted(g)) for g in verified_groups.values()}) == len(intended)
    assert verified_groups['quiet-ground'] != groups[pads('P_U20','9')[0]['uuid']]
    allowed = set().union(*verified_groups.values())
    added = set()
    mounts = [o for o in new.values() if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    assert len(mounts) == 15
    for r in report['routes']:
        points = r['path_mm']
        assert len(points) == len(r['segment_uuids']) + 1
        line = LineString(points)
        assert abs(line.length - r['length_mm']) < 2e-6 and line.length <= r['maximum_length_mm']
        for u, p, q in zip(r['segment_uuids'], points, points[1:]):
            assert u not in added and u not in oldkeys
            added.add(u)
            o = new[u]
            assert o['kind'] == 'PCB_TRACK' and o['net'] == r['net'] and o['width_mm'] == r['width_mm']
            assert set(o['layers']) == {r['layer']}
            assert math.dist(o['position_mm'], p) < 2e-6 and math.dist(o['end_mm'], q) < 2e-6
            assert u in allowed
            assert all(LineString([p, q]).distance(Point(m['position_mm'])) >
                       max(3.6, max(m['drill_mm']) / 2 + .5) + o['width_mm'] / 2 + .01 - 2e-6 for m in mounts)
    for v in report['vias']:
        u = v['uuid']
        assert u not in oldkeys and u not in added
        added.add(u)
        o = new[u]
        assert o['kind'] == 'PCB_VIA' and o['net'] == v['net']
        assert o['width_mm'] == .6 and o['drill_mm'] == .3 and o['via_type'] == 4
        assert o['position_mm'] == v['position_mm'] and o['span'] == ['F.Cu', 'B.Cu']
        assert set(o['layers']) == set(after['copper_layers']) and u in allowed
    assert added == new.keys() - oldkeys and len(report['routes']) == 13 and len(report['vias']) == 7 and len(added) == 23
    for u in added:
        for ps in new[u]['layers'].values():
            if ps:
                assert all(shape(ps).distance(shape(z['authored_outline'])) > 2 for z in after['zones'])
    smd = [shape(ps) for o in new.values() if o['kind'] == 'PAD' and not any(o['drill_mm'])
           for layer, ps in o['layers'].items() if layer in ['F.Cu', 'B.Cu'] and ps]
    tree = STRtree(smd)
    gaps = []
    for o in new.values():
        if o['kind'] == 'PCB_VIA':
            p = Point(o['position_mm'])
            gap = p.distance(smd[int(tree.nearest(p))]) - o['drill_mm'] / 2
            assert gap >= .15 - 2e-6
            gaps.append(gap)
    assert len(gaps) == 164 and sum(o['kind'] == 'PCB_TRACK' for o in new.values()) == 2232
    drc, erc = [json.loads((OUT / n).read_text()) for n in ['drc.json', 'erc.json']]
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings = [v for s in erc['sheets'] for v in s.get('violations', [])]
    assert len(warnings) == 2 and all(v['type'] == 'ground_pin_not_ground' and v['severity'] == 'warning' for v in warnings)
    assert before['native_uncapped_opens'] == 2478 and after['native_uncapped_opens'] == 2472
    switching = [shape(ps) for o in new.values() if any(n in o['net'] for n in ['P03_D_SW', 'P03_D_BOOT'])
                 for ps in o['layers'].values() if ps]
    sense_copper = [shape(ps) for u in added if new[u]['net'] == pins['P_R200','1']
                    for ps in new[u]['layers'].values() if ps]
    projected_gap = min(a.distance(b) for a in sense_copper for b in switching)
    assert projected_gap >= 1.15 - 2e-6
    assert abs(projected_gap - report['minimum_projected_sense_to_switching_copper_mm']) < 3e-6
    paths = [Path(__file__), report_path, BEFORE, AFTER,
             REPO / 'hardware/fabrication/audit_two_board_power_delta.py',
             REPO / 'hardware/fabrication/route_nf_surface.py']
    for folder in [BASE, OUT]:
        paths.extend(folder / n for n in ['power_protection.kicad_pcb', 'netlist.xml', 'review.json', 'drc.json', 'erc.json'])
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
                  components=1085, footprints=1100, unchanged_complete_pin_net_map=True,
                  all_component_poses_values_and_packages_unchanged=True,
                  all_old_copper_objects_unchanged=True, existing_local_U23_planes_unchanged=True,
                  all_previous_native_connection_groups_preserved=len(before['all_groups']),
                  local_route_sections=13, added_segments=16, added_vias=7,
                  old_opens=2478, new_opens=2472, connections_closed=6,
                  output_sense_connected=True, feedback_trim_connected=True, configuration_connected=True,
                  quiet_return_to_PGND_pending=True,
                  verified_terminal_groups=intended,
                  minimum_projected_sense_to_switching_copper_mm=projected_gap,
                  minimum_all_via_drill_to_SMD_mm=min(gaps), vias_screened=164,
                  geometry_findings=0, parity_findings=0, erc_errors=0, erc_warnings=2,
                  sense_reference_plane_and_all_power_return_planes_complete=False,
                  current_capacity_thermal_and_return_impedance_qualified=False,
                  effective_capacitance_and_stability_qualified=False,
                  electrical_and_manufacturing_qualified=False, full_installed_fit_verified=False,
                  fabrication_released=False)
    with (OUT / 'u20-control-audit.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, indent=2))


if __name__ == '__main__':
    run()
