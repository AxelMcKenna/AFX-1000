"""Replay bypass-supervisor relocation, restored rails and repaired/new controls."""

import argparse
import copy
import json
import math
import re
from collections import Counter
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.audio_main_control_routes import CONTROL_NETS
from hardware.fabrication.audio_main_global_controls import LAYERS, SignalScreen
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audio_main_power_routes import RAILS
from hardware.fabrication.audit_audio_main_analog_ok import check as parent_check
from hardware.fabrication.audit_audio_main_placement import verify_geometry
from hardware.fabrication.audit_audio_main_supplies import without_fill
from hardware.fabrication.audit_audio_main_supply_completion import verify_native
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-controls-06"
OUT = ROOT / "staging/audio-main-bypass-repack-04"
DRAFT = ROOT / "staging/audio-main-bypass-repack-02"
INITIAL = ROOT / "staging/audio-main-bypass-repack-01"
REFS = {"U605", "C606"}
TARGETS = {"/BYPASS/INPUT_READY", "/BYPASS/INPUT_ENABLE", "/BYPASS/LOCAL_OK",
           "/BYPASS/PROCESS_HEALTH", "/BYPASS/TIMER_ENABLE"}

PRIVATE = {
    "cc214893-89fe-51f3-9ab0-dffa88e844df", "78995919-a9ad-5c85-88e9-99c1fd71a7e1",
    "ddc84dd6-8d93-55fe-98e6-a0b37cbff079", "049dbe51-db18-5966-81e9-ce7e94c1ec8a",
    "04423b7f-39c8-5628-8e10-d68ccd302ec7", "5f7d4c1a-1a82-58dc-92ce-a27b69357d6f",
}
ENTRIES = {
    "725132df-fc3d-511f-aeaa-2f7e178f5fac", "c5015426-9b2c-5fce-8c30-4c9bf7b0e109",
    "f4851338-4a24-5ac9-8e47-80c0b47eb1f3", "a2605fbd-cb20-5bc0-b487-eef218346a38",
}
GPIO = {
    "689bea6e-5162-541d-9514-d1e9ecc2b4e0", "1494d7dd-7715-5eb7-bda8-496faae018bf",
    "92d5366d-6ace-5c76-8f25-6b1a8659cb16", "792f5697-a2fe-5192-8344-ae9440270735",
    "508057c8-46fe-559a-bdc7-316ce0e9928c", "4f039948-602d-55e3-bdc1-e7c6e759167e",
    "327f6fca-563b-59fe-bfcd-d9b9eeb0e9c0", "284ed614-46f5-55cf-aa0c-40fb6871b98b",
    "04fd7b61-ed61-5539-a6a0-3597b0bbc26e", "0ed1257d-b9d9-54c3-9726-c4b1402b4361",
}
PORTS = (("U606", "3"), ("U606", "10"), ("U606", "11"), ("U606", "12"), ("U605", "1"))
TAILS = {"88d40865-8e6c-5733-baad-28475602dc56", "076f30fc-eb5d-5ee6-8e4d-9e612bf48de8",
         "78983202-f636-5cfe-bed8-9c2ffa7a8b7d"}
PRUNED = {"26bb8614-7642-5f48-a259-a76f872b5389", "ba32b5da-4e49-5507-ae0f-d6101321138b",
          "b2d7c597-9389-5b3a-8934-367701f3ea12", "85a191d1-2a00-547b-a5dc-ee0dd60613b2"}


def point_key(point):
    return tuple(round(float(v), 6) for v in point)


def verify_control_delta(board, record, captured):
    parent = read_sexpr((DRAFT / "escaped-input.kicad_pcb").read_text())
    retired = set(record["retired_unused_reserved_copper_uuids"]) | set(record["native_identified_abandoned_tail_uuids"])
    parent = [n for n in parent if not isinstance(n, list) or not n or n[0] not in ("segment", "via") or
              first(n, "uuid")[1] not in retired]
    assert without_fill(board[:len(parent)]) == without_fill(parent), "Parent analog/power copper, receiving or authored zones changed"
    added = board[len(parent):]
    assert added and all(n[0] in ("segment", "via") for n in added)
    segments = {str(first(n, "uuid")[1]): n for n in added if n[0] == "segment"}
    vias = {str(first(n, "uuid")[1]): n for n in added if n[0] == "via"}
    assert len(segments)+len(vias) == len(added)
    assert segments.keys() == {r["uuid"] for r in record["added_segments"]}
    assert vias.keys() == {r["uuid"] for r in record["added_vias"]}
    names = {str(n[1]): str(n[2]) for n in children(board, "net")}
    actual = {}
    for row in record["added_segments"]:
        node = segments[row["uuid"]]
        net, layer = names[str(first(node, "net")[1])], first(node, "layer")[1]
        points = [list(map(float, first(node, name)[1:3])) for name in ("start", "end")]
        assert net in TARGETS and net == row["net"], "Non-control net added"
        assert layer in LAYERS and layer == row["layer"]
        assert float(first(node, "width")[1]) == row["width_mm"] == .2, "Control width changed"
        assert math.dist(points[0], row["start_mm"]) < 1e-6 and math.dist(points[1], row["end_mm"]) < 1e-6
        key = (net, layer, point_key(points[0]), point_key(points[1]))
        assert key not in actual
        actual[key] = row["uuid"]
    actual_vias = {}
    for row in record["added_vias"]:
        node = vias[row["uuid"]]
        xy = list(map(float, first(node, "at")[1:3]))
        net = names[str(first(node, "net")[1])]
        assert net in TARGETS and net == row["net"] and math.dist(xy, row["xy_mm"]) < 1e-6
        assert float(first(node, "size")[1]) == row["diameter_mm"] == .6
        assert float(first(node, "drill")[1]) == row["drill_mm"] == .3, "Control drill changed"
        assert first(node, "layers")[1:] == ["F.Cu", "B.Cu"]
        key = (net, point_key(xy))
        assert key not in actual_vias
        actual_vias[key] = row["uuid"]
    objects = {o["uuid"]: o for o in captured["objects"]}
    groups = {}
    for key, ids in captured["groups"].items():
        contacts = set()
        for ident in ids:
            obj = objects[ident]
            for layer in LAYERS:
                if obj["layers"].get(layer):
                    for point in [obj["position_mm"]]+([obj["end_mm"]] if "end_mm" in obj else []):
                        contacts.add((layer, point_key(point)))
        groups[frozenset((key,))] = contacts
    screen = SignalScreen(captured)
    used_tracks, used_vias = set(), set()
    for row in record["routes"]:
        assert row["net"] in TARGETS
        left, right = [frozenset(side) for side in row["source_groups"]]
        assert left and right and left != right and not left & right and left in groups and right in groups, "False control island merge"
        assert all(objects[captured["groups"][key][0]]["net"] == row["net"] for key in left | right)
        runs = row["runs"]
        assert runs and (runs[0][0], point_key(runs[0][1][0])) in groups[left]
        assert (runs[-1][0], point_key(runs[-1][1][-1])) in groups[right]
        terminals = row.get("terminal_points_mm", row["portals"])
        assert math.dist(runs[0][1][0], terminals[0]) < 1e-7 and math.dist(runs[-1][1][-1], terminals[1]) < 1e-7
        # Search portals can be offset from a real pad by an explicit short
        # escape. Check the physical escape rather than treating that portal
        # as an already connected native terminal.
        for side, (terminal, portal) in enumerate(zip(terminals, row["portals"])):
            if math.dist(terminal, portal) > 1e-7:
                points = runs[0 if side == 0 else -1][1]
                assert math.dist(points[-1 if side == 0 else 0], portal) < 1e-7
                assert LineString(points).length <= 3.5+1e-8, "Control pad escape exceeds 3.5 mm"
                assert any(math.dist(portal, xy) < 1e-7 for xy in row["new_vias_mm"]), "Control escape has no plated portal"
        length = sum(LineString(points).length for _, points in runs)
        limit = min(180, 2.5*math.dist(*terminals)+10)
        if row["net"] == "/BYPASS/INPUT_ENABLE":
            assert row["explicit_longer_route_comparison"] is True
            assert row["timing_loading_return_noise_and_EMC_qualified"] is False
            neck = next(p for p in record["reserved_control_escapes"] if p["net"] == row["net"])
            limit = 40-sum(LineString(points).length for _, points in neck["runs"])
        assert abs(length-row["planar_length_mm"]) < 1e-7 and abs(limit-row["maximum_planar_length_mm"]) < 1e-7
        assert length <= limit+1e-8, "Control route length budget changed"
        assert len(row["new_vias_mm"]) <= 4, "Control via-count limit changed"
        for i, xy in enumerate(row["new_vias_mm"]):
            key = (row["net"], point_key(xy))
            assert actual_vias[key] not in used_vias
            assert all(math.dist(xy, p) > .86 for _, p in screen.vias+screen.new_vias)
            assert all(math.dist(xy, p) > .86 for p in row["new_vias_mm"][:i])
            assert screen.via_legal(row["net"], xy), "Control drill violates actual copper, reference or solder lands"
            assert len({face for face, points in row["runs"] if LineString(points).distance(Point(xy)) < 1e-7}) >= 2, "Unused routed control via"
            used_vias.add(actual_vias[key])
        available_vias = [(n, p) for n, p in screen.vias+screen.new_vias]+[(row["net"], p) for p in row["new_vias_mm"]]
        for i, (layer, points) in enumerate(runs):
            assert layer in LAYERS and len(points) > 1 and screen.legal(row["net"], layer, points), "Control trace violates native obstacle or analog-region screen"
            if i:
                assert math.dist(runs[i-1][1][-1], points[0]) < 1e-7
                assert any(net == row["net"] and math.dist(xy, points[0]) < 1e-7 for net, xy in available_vias), "Layer transition has no plated connection"
            for start, end in zip(points, points[1:]):
                ident = actual[(row["net"], layer, point_key(start), point_key(end))]
                assert ident not in used_tracks
                used_tracks.add(ident)
        joined = groups.pop(left) | groups.pop(right)
        for layer, points in runs:
            screen.added.append((row["net"], layer, LineString(points)))
            joined.update((layer, point_key(p)) for p in points)
        for xy in row["new_vias_mm"]:
            screen.new_vias.append((row["net"], xy))
            joined.update((layer, point_key(xy)) for layer in LAYERS)
        groups[left | right] = joined
    assert used_tracks == segments.keys() and used_vias == vias.keys(), "Unaccounted control copper"
    assert record["trace_width_mm"] == record["clearance_mm"] == .2 and record["planning_margin_mm"] == .01
    assert record["allowed_control_nets"] == sorted(TARGETS) and record["signal_layers"] == list(LAYERS)
    smd = [shape(ps) for o in captured["objects"] if o["kind"] == "PAD" and not any(o["drill_mm"])
           for layer, ps in o["layers"].items() if layer in ("F.Cu", "B.Cu") and ps]
    minimum = min(Point(row["xy_mm"]).distance(g)-.15 for row in record["added_vias"] for g in smd)
    assert minimum >= .16-1e-7, "Control via drill approaches an SMD solder land"
    return dict(tracks=len(children(board, "segment")), vias=len(children(board, "via")),
                added_global_control_pairs=len(record["routes"]), added_global_control_tracks=len(segments),
                added_global_control_vias=len(vias), minimum_new_control_drill_edge_to_SMD_mm=round(minimum, 9),
                all_parent_analog_power_lands_copper_drills_and_authored_zones_exact=True)


def verify_terminals(report, record, captured):
    parent = json.loads((SOURCE / "terminal-connectivity-review.json").read_text())
    assert report["retained_local_pairs"] == [dict(r, additive_successor_native_connected=True) for r in parent["retained_local_pairs"]], "Local analog pair lost"
    assert report["retained_control_pairs"] == [dict(r, additive_successor_native_connected=True) for r in parent["retained_control_pairs"]], "Prior control pair lost"
    assert report["ground_pads"] == parent["ground_pads"], "Ground terminal lost"
    assert report["supply_pads"] == parent["supply_pads"], "Supply or sense terminal lost"
    objects = {o["uuid"]: o for o in captured["objects"]}
    expected = []
    for row in record["routes"]:
        contacts = [objects[i] for side in row["source_groups"] for key in side for i in captured["groups"][key]
                    if objects[i]["kind"] == "PAD" and objects[i]["pin"]]
        assert contacts
        expected.append(dict(net=row["net"], source_groups=row["source_groups"], reference_terminal=[contacts[0]["ref"], contacts[0]["pin"]],
                             contacts=[dict(ref=p["ref"], pin=p["pin"], native_connected=True) for p in contacts]))
    assert report["new_route_witnesses"] == expected, "New control closure lacks complete native pad witnesses"


def fps(board):
    return {next(p[2] for p in children(f, 'property') if p[1] == 'Reference'): f
            for f in children(board, 'footprint')}


def shift(point):
    return [round(float(point[0])-47.5, 8), round(float(point[1])-40, 8)]


def verify_preparation(prepared, record, plan):
    expected = read_sexpr((SOURCE / 'audio_core.kicad_pcb').read_text())
    assert set(record['declared_pose_changes']) == REFS
    assert set(record['translated_copper_uuids']) == PRIVATE
    assert set(record['removed_copper_uuids']) == ENTRIES | GPIO
    assert {i for ids in record['pruned_abandoned_power_copper_uuids'].values() for i in ids} == PRUNED
    wanted = {'U605': [20, 4, 90], 'C606': [17, 3.75, 270]}
    for ref, fp in fps(expected).items():
        if ref in REFS:
            before = list(map(float, first(fp, 'at')[1:4]))
            assert record['declared_pose_changes'][ref] == dict(before=before, after=wanted[ref])
            first(fp, 'at')[1:3] = shift(before[:2])
    removed = ENTRIES | GPIO | PRUNED
    expected = [n for n in expected if not isinstance(n, list) or not n or n[0] not in ('segment', 'via') or
                str(first(n, 'uuid')[1]) not in removed]
    for n in expected:
        if isinstance(n, list) and n and n[0] in ('segment', 'via') and str(first(n, 'uuid')[1]) in PRIVATE:
            for key in (('at',) if n[0] == 'via' else ('start', 'end')):
                first(n, key)[1:3] = shift(first(n, key)[1:3])
    assert prepared == read_sexpr(sexpr(expected)), 'Undeclared pose, land, copper, hole or zone change'
    expected_plan = json.loads((SOURCE / 'plan.json').read_text())
    for ref in REFS:
        expected_plan['poses'][ref] = [*wanted[ref], 'F']
        expected_plan['expanded_receiving_bounds_mm'][ref] = courtyard(fps(prepared)[ref], 'F.CrtYd')
    for cell in expected_plan['local_cells']:
        if cell['owner'] in REFS:
            for terminal in cell['terminals']:
                terminal['owner_position_mm'] = shift(terminal['owner_position_mm'])
    expected_plan['source_sha256'].update(relative_hashes([DRAFT / 'applied-prepare.py.txt', SOURCE / 'plan.json']))
    assert plan == expected_plan, 'Receiving limits or unrelated placement changed'


def verify_added_phase(before, after, additions, mode):
    nets = {str(n[2]): n[1] for n in children(before, 'net')}
    expected = copy.deepcopy(before)
    seen = set()
    for row in additions:
        assert row['uuid'] not in seen
        seen.add(row['uuid'])
        if row['kind'] == 'segment':
            width = row['width_mm']
            assert row['layer'] in LAYERS
            assert width in ((.2, .6) if mode == 'power' else (.2,))
            if mode == 'power':
                assert row['net'] in ('V3V3_IO', '5V_DIG')
                assert width == (.6 if row['purpose'] == 'supervisor_power_trunk' else .2)
            if width == .2:
                assert math.dist(row['start_mm'], row['end_mm']) <= 3.5+1e-8
            expected.append([a('segment'), [a('start'), *row['start_mm']], [a('end'), *row['end_mm']],
                             [a('width'), width], [a('layer'), row['layer']], [a('net'), nets[row['net']]],
                             [a('uuid'), row['uuid']]])
        else:
            assert row['kind'] == 'via' and row['diameter_mm'] == .6 and row['drill_mm'] == .3
            expected.append([a('via'), [a('at'), *row['xy_mm']], [a('size'), .6], [a('drill'), .3],
                             [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), nets[row['net']]], [a('uuid'), row['uuid']]])
    assert after == read_sexpr(sexpr(expected)), 'Unreviewed phase copper or altered parent object'


def verify_phase_terminals(prepared_capture, power_record, powered_capture, escape_record):
    objects = {o['uuid']: o for o in prepared_capture['objects']}
    members = {i: k for k, ids in prepared_capture['groups'].items() for i in ids}
    pads = {(o['ref'], o['pin']): o for o in objects.values() if o['kind'] == 'PAD' and o['pin']}
    assert {tuple(b['terminal']) for b in power_record['branches']} == {('U605', '5'), ('U605', '3'), ('C606', '1')}
    for branch in power_record['branches']:
        net, terminal = branch['net'], tuple(branch['terminal'])
        assert pads[terminal]['net'] == net
        assert branch['root_terminal'] == list(RAILS[net])
        assert members[pads[terminal]['uuid']] == branch['source_group']
        assert members[pads[RAILS[net]]['uuid']] == branch['root_group']
        assert members[branch['root_contact']['endpoint_uuid']] == branch['root_group']
        assert branch['source_group'] != branch['root_group']
        neck = branch['escape']
        assert math.dist(neck['paths'][0][1][0], pads[terminal]['position_mm']) < 1e-7
        assert sum(LineString(ps).length for _, ps in neck['paths']) <= 3.5+1e-8
        assert math.dist(branch['trunk_path_mm'][0], neck['xy_mm']) < 1e-7
        assert math.dist(branch['trunk_path_mm'][-1], branch['root_contact']['xy_mm']) < 1e-7
    objects = {o['uuid']: o for o in powered_capture['objects']}
    members = {i: k for k, ids in powered_capture['groups'].items() for i in ids}
    pads = {(o['ref'], o['pin']): o for o in objects.values() if o['kind'] == 'PAD' and o['pin']}
    for pad in pads.values():
        if pad['net'] in RAILS:
            assert members[pad['uuid']] == members[pads[RAILS[pad['net']]]['uuid']], 'Rail or sense terminal disconnected'
    assert {(r['ref'], r['pin']) for r in escape_record['escapes']} == set(PORTS)
    screen = SignalScreen(powered_capture)
    for row in escape_record['escapes']:
        pad = pads[row['ref'], row['pin']]
        assert row['net'] == pad['net'] and row['group'] == members[pad['uuid']]
        assert math.dist(row['runs'][0][1][0], pad['position_mm']) < 1e-7
        assert math.dist(row['runs'][-1][1][-1], row['point']) < 1e-7
        assert sum(LineString(ps).length for _, ps in row['runs']) <= 3.5+1e-8
        assert screen.via_legal(row['net'], row['point'])
        assert all(screen.legal(row['net'], face, points) for face, points in row['runs'])
        screen.new_vias.append((row['net'], row['point']))
        screen.added.extend((row['net'], face, LineString(points)) for face, points in row['runs'])


def verify_actual_pads(board, current):
    from shapely.affinity import translate
    old = json.loads((INITIAL / 'native-inputs.json').read_text())
    def key(p):
        point = shift(p['position_mm']) if p['ref'] in REFS else p['position_mm']
        return p['ref'], p['pin'], point_key(point)
    expected = {key(o): o for o in old['objects'] if o['kind'] == 'PAD'}
    actual = {(p['ref'], p['pin'], point_key(p['position_mm'])): p for p in current['objects']}
    assert len(expected) == len(actual) == 930 and expected.keys() == actual.keys()
    for k, p in actual.items():
        original = expected[k]
        assert all(p[t] == original[t] for t in ('net', 'drill_mm', 'npth'))
        assert p['layers'].keys() == original['layers'].keys()
        for layer, ps in p['layers'].items():
            previous = shape(original['layers'][layer])
            if p['ref'] in REFS:
                previous = translate(previous, xoff=-47.5, yoff=-40)
            assert shape(ps).hausdorff_distance(previous) < .0021, 'Actual manufacturer land changed'
    smd = [shape(ps) for p in actual.values() if not any(p['drill_mm']) for layer, ps in p['layers'].items()
           if layer in ('F.Cu', 'B.Cu') and ps]
    minimum = min(Point(list(map(float, first(v, 'at')[1:3]))).distance(g)-float(first(v, 'drill')[1])/2
                  for v in children(board, 'via') for g in smd)
    assert minimum >= .16-1e-7, 'Actual via drill approaches an SMD solder land'
    return minimum


def verify_full_budgets(record):
    ports = {p['net']: p for p in record['reserved_control_escapes']}
    unused, unused_copper = set(), set()
    original = json.loads((DRAFT / 'escape-construction.json').read_text())
    for row in record['routes']:
        port = ports[row['net']]
        length = sum(LineString(p).length for _, p in row['runs'])
        terminals = [row['runs'][0][1][0], row['runs'][-1][1][-1]]
        for i, terminal in enumerate(terminals):
            if math.dist(terminal, port['point']) < 1e-7:
                length += sum(LineString(p).length for _, p in port['runs'])
                terminals[i] = port['runs'][0][1][0]
        assert terminals == row['physical_terminal_points_mm']
        limit = 40 if row['net'] == '/BYPASS/INPUT_ENABLE' else min(180, 2.5*math.dist(*terminals)+10)
        assert abs(length-row['escape_inclusive_length_mm']) < 1e-7 and length <= limit+1e-8
        assert abs(limit-row['maximum_escape_inclusive_length_mm']) < 1e-7
        faces = {port['runs'][0][0]}
        faces.update(face for face, ps in row['runs'] if LineString(ps).distance(Point(port['point'])) < 1e-7)
        active = len(faces) > 1
        assert len(row['new_vias_mm'])+int(active) == row['fresh_vias_including_reserved'] <= 4
        if not active:
            old_vias = {r['uuid'] for r in original['additions'] if r['net'] == row['net'] and r['kind'] == 'via'}
            unused.update(old_vias)
            unused_copper.update(old_vias)
            ends_at_old_port = any(math.dist(p, port['point']) < 1e-7 for p in
                                   (row['runs'][0][1][0], row['runs'][-1][1][-1]))
            if not ends_at_old_port:
                assert any(math.dist(p, port['runs'][0][1][0]) < 1e-7 for p in
                           (row['runs'][0][1][0], row['runs'][-1][1][-1]))
                unused_copper.update(r['uuid'] for r in original['additions'] if r['net'] == row['net'] and r['kind'] == 'segment')
    assert set(record['retired_unused_reserved_via_uuids']) == unused
    assert set(record['retired_unused_reserved_copper_uuids']) == unused_copper


def verify_tail_chains(record, captured):
    prior = ROOT / 'staging/audio-main-bypass-repack-03'
    native = json.loads((prior / 'placement-native-review.json').read_text())
    verify_hashes(native['source_sha256'])
    assert all(sha(prior / name) == h for name, h in native['raw_report_sha256'].items())
    violations = json.loads((prior / 'drc.json').read_text())['violations']
    assert len(violations) == 2 and all(v['type'] == 'track_dangling' for v in violations)
    initial = {v['items'][0]['uuid'] for v in violations}
    assert initial == {'594e0456-9fec-53d0-af4b-6dcbc5da6278', 'e0d7d6b7-36ac-5ebd-a401-c2d3e2e7fde1'}
    old = read_sexpr((prior / 'distribution-input.kicad_pcb').read_text())
    names = {n[1]: str(n[2]) for n in children(old, 'net')}
    tracks = {str(first(n, 'uuid')[1]): n for n in children(old, 'segment')}
    vias = children(old, 'via')
    retired = record['native_identified_abandoned_tail_nodes']
    ids = {str(first(n, 'uuid')[1]) for n in retired}
    assert len(retired) == len(ids) == 57 and TAILS <= ids
    assert ids == set(record['native_identified_abandoned_tail_uuids'])
    new = [n for n in retired if str(first(n, 'uuid')[1]) not in TAILS]
    assert len(new) == 54 and initial <= {str(first(n, 'uuid')[1]) for n in new}
    removed_lines = {}
    for node in new:
        ident = str(first(node, 'uuid')[1])
        assert node == tracks[ident] and node[0] == 'segment'
        assert first(node, 'layer')[1] == 'F.Cu'
        width = float(first(node, 'width')[1])
        assert width == (.2 if ident == '952bdad5-d109-5923-be37-dd721f8f49ea' else .6)
        net = names[first(node, 'net')[1]]
        assert net in ('V3V3_IO', '5V_DIG')
        points = [tuple(map(float, first(node, k)[1:3])) for k in ('start', 'end')]
        free_end = False
        for point in points:
            p = Point(point)
            if any(names[first(v, 'net')[1]] == net and math.dist(point, list(map(float, first(v, 'at')[1:3]))) <=
                   float(first(v, 'size')[1])/2+.000001 for v in vias):
                continue
            if any(o['kind'] == 'PAD' and o['pin'] and o['net'] == net and
                   shape(o['layers'].get('F.Cu', [])).buffer(.000001).covers(p) for o in captured['objects']):
                continue
            adjacent = any(i != ident and names[first(t, 'net')[1]] == net and first(t, 'layer')[1] == 'F.Cu' and
                           LineString([tuple(map(float, first(t, k)[1:3])) for k in ('start', 'end')]).distance(p) < .000001
                           for i, t in tracks.items())
            if not adjacent:
                free_end = True
                break
        assert free_end, 'Retired rail copper is not an abandoned leaf'
        removed_lines[ident] = (net, LineString(points))
        del tracks[ident]
    # Every retired rail belongs to one of the two native-identified chains.
    reachable = set(initial)
    while True:
        expanded = reachable | {i for i, (n, line) in removed_lines.items() if
                                 any(n == removed_lines[j][0] and line.distance(removed_lines[j][1]) < .000001 for j in reachable)}
        if expanded == reachable:
            break
        reachable = expanded
    assert reachable == removed_lines.keys(), 'Unrelated rail copper retired'


def check():
    parent = parent_check()
    assert parent == json.loads((SOURCE / 'routing-handoff.json').read_text())
    phase_names = ('preparation-record.json', 'prepared-native-inputs.json', 'power-construction.json',
                   'powered-native-inputs.json', 'escape-construction.json', 'escaped-native-inputs.json',
                   'control-routing-proposal.json', 'distribution-construction.json', 'plan.json')
    phases = {n: json.loads((DRAFT / n).read_text()) for n in phase_names}
    names = ('distribution-construction.json', 'native-refill.json', 'terminal-connectivity-review.json',
             'fill-entry.json', 'review-entry.json', 'additional-terminal-review.json', 'current-native-pads.json', 'retain-entry.json')
    reports = {n: json.loads((OUT / n).read_text()) for n in names}
    for report in list(phases.values())+list(reports.values()):
        verify_hashes(report['source_sha256'])
    boards = {phase: read_sexpr((DRAFT / (phase+'-input.kicad_pcb')).read_text())
              for phase in ('prepared', 'powered', 'escaped')}
    for phase, manifest in (('prepared', 'preparation-record.json'), ('powered', 'power-construction.json'), ('escaped', 'escape-construction.json')):
        assert sha(DRAFT / (phase+'-input.kicad_pcb')) == phases[manifest]['authored_PCB_sha256']
    verify_preparation(boards['prepared'], phases['preparation-record.json'], phases['plan.json'])
    verify_added_phase(boards['prepared'], boards['powered'], phases['power-construction.json']['additions'], 'power')
    verify_added_phase(boards['powered'], boards['escaped'], phases['escape-construction.json']['additions'], 'escape')
    verify_phase_terminals(phases['prepared-native-inputs.json'], phases['power-construction.json'],
                           phases['powered-native-inputs.json'], phases['escape-construction.json'])
    record = reports['distribution-construction.json']
    verify_tail_chains(record, phases['escaped-native-inputs.json'])
    draft_record = phases['distribution-construction.json']
    assert {k: v for k, v in record.items() if k not in ('source_sha256', 'authored_PCB_sha256',
            'native_identified_abandoned_tail_uuids', 'native_identified_abandoned_tail_nodes')} == {
            k: v for k, v in draft_record.items() if k not in ('source_sha256', 'authored_PCB_sha256')}
    assert record['routes'] == phases['control-routing-proposal.json']['routes']
    assert len(record['routes']) == 5 and {r['net'] for r in record['routes']} == TARGETS
    assert sha(OUT / 'distribution-input.kicad_pcb') == record['authored_PCB_sha256']
    board = read_sexpr((OUT / 'audio_core.kicad_pcb').read_text())
    assert without_fill(board) == without_fill(read_sexpr((OUT / 'distribution-input.kicad_pcb').read_text()))
    refill = reports['native-refill.json']
    assert sha(OUT / 'audio_core.kicad_pcb') == refill['filled_PCB_sha256']
    assert sha(OUT / 'native-refill-export.kicad_pcb') == refill['native_export_sha256']
    native_export = read_sexpr((OUT / 'native-refill-export.kicad_pcb').read_text())
    fills = {str(first(z, 'uuid')[1]): children(z, 'filled_polygon') for z in children(native_export, 'zone') if not children(z, 'keepout')}
    polygons = []
    for zone in children(board, 'zone'):
        if not children(zone, 'keepout'):
            assert children(zone, 'filled_polygon') == fills[str(first(zone, 'uuid')[1])]
            polygons.extend(Polygon([tuple(map(float, p[1:3])) for p in children(first(f, 'pts'), 'xy')]).buffer(0)
                            for f in children(zone, 'filled_polygon'))
    view = dict(record, added_segments=[r for r in record['control_additions'] if r['kind'] == 'segment'],
                added_vias=[r for r in record['control_additions'] if r['kind'] == 'via'], trace_width_mm=.2,
                clearance_mm=.2, planning_margin_mm=.01, allowed_control_nets=sorted(TARGETS), signal_layers=list(LAYERS))
    proof = verify_control_delta(board, view, phases['escaped-native-inputs.json'])
    verify_full_budgets(record)
    witness = reports['terminal-connectivity-review.json']
    verify_terminals(witness, record, phases['escaped-native-inputs.json'])
    extra = reports['additional-terminal-review.json']
    old_witness = json.loads((SOURCE / 'terminal-connectivity-review.json').read_text())
    old_extra = json.loads((SOURCE / 'additional-terminal-review.json').read_text())
    assert extra['retained_global_control_witnesses'] == old_extra['retained_global_control_witnesses']+old_witness['new_route_witnesses']
    assert len(extra['retained_global_control_witnesses']) == 57
    assert extra['retained_private_timing_connections'] == old_extra['retained_private_timing_connections']
    assert len(extra['retained_private_timing_connections']) == 2
    native = verify_native(OUT)
    assert native['uncapped_open_connections'] == witness['uncapped_open_connections'] == extra['uncapped_open_connections'] == 205
    assert native['uncapped_open_connections'] == parent['uncapped_open_connections']-3
    assert proof['tracks'] == witness['tracks'] and proof['vias'] == witness['vias']
    assert json.loads((OUT / 'plan.json').read_text()) == phases['plan.json']
    geometry_board = [n for n in board if not isinstance(n, list) or not n or n[0] not in ('segment', 'via', 'zone')]
    geometry_board += [children(board, 'zone')[0]]
    parts, pins = netlist(OUT / 'native-netlist.xml')
    geometry = verify_geometry(geometry_board, phases['plan.json'], parts, pins)
    for p in SOURCE.rglob('*'):
        if p.is_file() and (p.suffix in ('.kicad_sch', '.kicad_pro', '.kicad_sym', '.kicad_dru', '.kicad_mod') or p.name in ('fp-lib-table', 'sym-lib-table')):
            assert (OUT / p.relative_to(SOURCE)).read_bytes() == p.read_bytes()
    minimum = verify_actual_pads(board, reports['current-native-pads.json'])
    counts = Counter()
    for row in json.loads((OUT / 'drc.json').read_text())['unconnected_items']:
        nets = [re.search(r'\[([^]]+)\]', item['description']).group(1) for item in row['items']]
        assert len(set(nets)) == 1
        counts[nets[0]] += 1
    assert sum(counts[n] for n in CONTROL_NETS) == 4
    paths = [Path(__file__), ROOT / 'audio_main_bypass_repack.py', ROOT / 'audio_main_bypass_input_enable.py',
             SOURCE / 'routing-handoff.json', INITIAL / 'native-inputs.json']
    paths += [DRAFT / n for n in phase_names]+[OUT / n for n in names]+[OUT / 'placement-native-review.json']
    return dict(source_sha256=relative_hashes(paths), **geometry, tracks=proof['tracks'], vias=proof['vias'],
                native_geometry_findings=0, native_ERC_findings=0, native_missing_codec_footprint_findings=1,
                all_native_categories_enabled=True, uncapped_open_connections=205, remaining_control_connections=4,
                remaining_control_connections_by_net={n: counts[n] for n in sorted(CONTROL_NETS) if counts[n]},
                inherited_global_control_joins=57, repaired_existing_control_joins=2, new_global_control_joins=3,
                added_global_control_pairs=60, retained_native_local_pairs=138, added_control_pairs=17,
                connected_ground_pads=200, connected_supply_pads=161, retained_private_timing_pairs=2,
                ground_plane_area_mm2=round(unary_union(polygons).area, 6),
                minimum_screened_drill_edge_to_SMD_copper_mm=round(minimum, 9),
                explicit_longer_INPUT_ENABLE_comparison_mm=next(r['escape_inclusive_length_mm'] for r in record['routes'] if r['net']=='/BYPASS/INPUT_ENABLE'),
                control_timing_signal_integrity_EMI_and_installed_fault_qualified=False,
                analog_PDN_thermal_stability_noise_and_manufacturing_qualified=False,
                physical_codec_ADC_star_geometry_verified=False,
                complete_mating_harness_support_and_case_receiving_qualified=False,
                PCB_routed=False, fabrication_released=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = check()
    path = OUT / 'routing-handoff.json'
    if args.check:
        assert result == json.loads(path.read_text())
    else:
        with path.open('x') as f:
            json.dump(result, f, indent=2)
            f.write('\n')
    print('Bypass routing comparison:', result['uncapped_open_connections'], 'opens;', result['remaining_control_connections'], 'control gaps; not for fabrication')
