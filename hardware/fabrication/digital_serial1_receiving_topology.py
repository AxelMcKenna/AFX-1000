"""Distinguish disconnected receiving paths from bounded route-finder failures.

Replay recorded proposals independently, then remove one preceding global route
at a time for diagnosis only. This never emits or adopts a board.
"""
import copy
import itertools
import json
import math
from pathlib import Path

from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_region_point_access import reachability
from hardware.fabrication.digital_screen_branch import branch
from hardware.fabrication.digital_serial1_joint_repair import ROOT, FACES, SERIAL, CLOCK, LED
from hardware.fabrication.digital_serial1_packed_repair_v3 import contacts
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers


def run():
    cp = ROOT/'staging/digital-serial1-source-preparation-inputs-31-02/capture.json'
    rp = ROOT/'staging/digital-serial1-combined-restoration-03/construction.json'
    cap, report = [json.loads(p.read_text()) for p in (cp, rp)]
    for record in (cap, report):
        assert all(sha(Path(p)) == h for p, h in record['source_sha256'].items())
    assert not report['candidate_emitted']
    work = copy.deepcopy(cap)
    work['objects'] = [o for o in cap['objects'] if o['uuid'] not in report['removed_uuids'] and o.get('ref') != 'R3015'] + copy.deepcopy(report['component_move']['pads'])
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .001
    surface.SIGNAL_LAYERS = FACES
    base = CloseMarginViaScreen(work, signal_layers=FACES)
    for net in (SERIAL, CLOCK, LED):
        base.obstacles(net)
    observations = []
    # Inspect the first two packs, whose successful prefixes differ in order.
    for attempt in report['attempts'][:2]:
        for order in attempt['orders']:
            failed = order['repairs'][-1]
            assert not failed['found']
            net = failed['net']
            routes = order['routes']
            assert len(routes) == 6 + sum(r['found'] for r in order['repairs'])
            if net == SERIAL:
                start = routes[0]['new_vias_mm'][0]
                destination = next(r['new_vias_mm'][0] for r in routes[3:6] if r['net'] == SERIAL)
                ends = {(f, tuple(destination)) for f in FACES}
            else:
                start = next(r['new_vias_mm'][0] for r in routes[3:6] if r['net'] == net)
                ref, pin = {CLOCK: ('R3016', '2'), LED: ('J3005', '1')}[net]
                ends = contacts(work, net, ref, pin)
            for omitted in [None, *range(6, len(routes))]:
                screen = branch(base)
                for i, route in enumerate(routes):
                    if i != omitted:
                        add(screen, route['net'], dict(runs=route['runs'], vias=route['new_vias_mm']))
                crossings = [(o['position_mm'], [f for f in FACES if o['layers'].get(f)]) for o in work['objects'] if o['net'] == net and (o['kind'] == 'PCB_VIA' or o['kind'] == 'PAD' and any(o.get('drill_mm', [0, 0])))]
                crossings += [(p, list(FACES)) for n, p in screen.new_vias if n == net]
                topology = reachability(PlannedRegionScreen(screen, net), net, [('F.Cu', start)], sorted(ends), FACES, existing_crossings=crossings)
                vias = [e['point_mm'] for e in topology['component_witness'] if e['kind'] == 'new_via']
                item = dict(target_pack=attempt['target_pack'], order=order['order'], failed_net=net,
                            omitted_route_index=omitted, omitted_net=routes[omitted]['net'] if omitted is not None else None,
                            region_report=topology,
                            witness_new_vias_mutually_spaced=all(math.dist(p, q) > .563 for p, q in itertools.combinations(vias, 2)))
                observations.append(item)
                print('Topology', item['target_pack'], net, 'omit', item['omitted_net'], 'connected', topology['connected'], 'via spacing', item['witness_new_vias_mutually_spaced'], flush=True)
    paths = [cp, rp, Path(__file__)] + [ROOT/n for n in (
        'audit_candidate.py', 'digital_planned_region_screen.py', 'digital_region_point_access.py',
        'digital_screen_branch.py', 'digital_serial1_joint_repair.py', 'digital_serial1_packed_repair_v3.py',
        'digital_via_spacing_close_margin.py', 'digital_via_spacing_v2.py', 'digital_xlat_escape_repair.py',
        'route_nf_surface.py', 'nf_minimum_logic.py', 'digital_latch_supply_repack.py',
        'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py')]
    out = ROOT/'staging/digital-serial1-receiving-topology-01'
    out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p): sha(p) for p in paths},
        observations=observations, candidate_emitted=False, native_rules_relaxed=False,
        omission_is_diagnostic_only=True, global_infeasibility_proven=False,
        fabrication_released=False), indent=2)+'\n')


if __name__ == '__main__':
    run()
