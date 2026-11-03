"""Replay the isolated U205 SENSE entry and completed CODEC_PGOOD receiver."""

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audio_main_control_routes import CONTROL_NETS
from hardware.fabrication.audio_main_global_controls import LAYERS, SignalScreen
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_audio_main_chip_enable import check as parent_check
from hardware.fabrication.audit_audio_main_supplies import without_fill
from hardware.fabrication.audit_audio_main_supply_completion import verify_native
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-controls-07"
OUT = ROOT / "staging/audio-main-controls-08"
TARGETS = {"/CODEC/CODEC_PGOOD"}


def point_key(point):
    return tuple(round(float(v), 6) for v in point)


def verify_copper(board, record, captured):
    assert len(record["routes"]) == 1 and {r["net"] for r in record["routes"]} == TARGETS, "The CODEC_PGOOD receiver is required"
    parent = read_sexpr((OUT / "prepared-input.kicad_pcb").read_text())
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
        assert abs(length-row["planar_length_mm"]) < 1e-7 and abs(limit-row["maximum_planar_length_mm"]) < 1e-7
        assert length <= limit+1e-8, "Control route length budget changed"
        assert len(row["new_vias_mm"]) <= 4, "Control via-count limit changed"
        for i, xy in enumerate(row["new_vias_mm"]):
            key = (row["net"], point_key(xy))
            assert actual_vias[key] not in used_vias
            assert all(math.dist(xy, p) > .86 for _, p in screen.vias+screen.new_vias)
            assert all(math.dist(xy, p) > .86 for p in row["new_vias_mm"][:i])
            assert screen.via_legal(row["net"], xy), "Control drill violates actual copper, reference or solder lands"
            faces = {face for face, points in row["runs"] if LineString(points).distance(Point(xy)) < 1e-7}
            assert len(faces) >= 2, "Unused control via has fewer than two routed faces"
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


def verify_inherited(report):
    parent = json.loads((SOURCE / "terminal-connectivity-review.json").read_text())
    extra = json.loads((SOURCE / "additional-terminal-review.json").read_text())
    expected = extra["retained_global_control_witnesses"]+parent["new_route_witnesses"]
    assert len(expected) == 63
    assert report["retained_global_control_witnesses"] == expected, "Earlier global control connection lost"
    timing = extra["retained_private_timing_connections"]
    assert len(timing) == 2
    assert report["retained_private_timing_connections"] == timing, "Earlier private timing connection lost"


def verify_sense_entry(prepared, record, captured):
    from hardware.electronics.common.netlists import netlist
    from hardware.fabrication.audio_main_power_routes import PowerSpace

    net = '/CODEC/A3V3'
    retired = {'99a1b50c-4e72-5b12-bc97-0a06ca84a952', 'ecefc565-a7d4-5a5c-b9bd-87ff4d9a257a',
               '3e1729db-6aa8-58c6-a274-7579db99df44'}
    assert set(record['retired_copper_uuids']) == retired
    parent = read_sexpr((SOURCE/'audio_core.kicad_pcb').read_text())
    old = {str(first(n,'uuid')[1]):n for n in parent if isinstance(n,list) and n and n[0] in ('segment','via')}
    assert {str(first(n,'uuid')[1]) for n in record['retired_nodes']} == retired
    assert all(n == old[str(first(n,'uuid')[1])] for n in record['retired_nodes'])
    names = {str(n[1]):str(n[2]) for n in children(parent,'net')}
    assert all(names[str(first(old[i],'net')[1])] == net for i in retired)
    expected = [n for n in parent if not isinstance(n,list) or not n or n[0] not in ('segment','via') or str(first(n,'uuid')[1]) not in retired]
    additions = record['additions']
    assert len(additions)==3 and [r['kind'] for r in additions]==['via','segment','segment']
    via = additions[0]
    assert via['net']==net and via['xy_mm']==[84.3,20.8] and via['diameter_mm']==.6 and via['drill_mm']==.3
    code = next(n[1] for n in children(parent,'net') if str(n[2])==net)
    expected.append([a('via'),[a('at'),84.3,20.8],[a('size'),.6],[a('drill'),.3],
                     [a('layers'),'F.Cu','B.Cu'],[a('net'),code],[a('uuid'),via['uuid']]])
    paths = [('F.Cu',[84.3,24.1],[84.3,20.8]),('B.Cu',[84.3,20.8],[84.6,22.1])]
    for row,(layer,start,end) in zip(additions[1:],paths):
        assert row['net']==net and row['layer']==layer and row['start_mm']==start and row['end_mm']==end
        assert row['width_mm']==.2, 'SENSE width changed'
        expected.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),.2],
                         [a('layer'),layer],[a('net'),code],[a('uuid'),row['uuid']]])
    assert prepared == read_sexpr(sexpr(expected)), 'SENSE rework changed unretired parent geometry or component poses'
    parts,pins = netlist(OUT/'native-netlist.xml')
    assert parts['U205'].findtext('value')=='TPS389033DSET'
    assert pins['U205']['1']==net.lstrip('/') and pins['U205']['4']==pins['U205']['3']=='V3V3_IO'
    assert pins['U205']['6']=='CODEC/CODEC_PGOOD'
    assessment = record['sense_branch_assessment']
    front = [[85,24.1],[84.3,24.1],[84.3,20.8]]
    back = [[84.3,20.8],[84.6,22.1],[83.8,24.8]]
    length = LineString(front).length+LineString(back).length
    assert assessment['terminal']==['U205','1'] and assessment['part']=='TPS389033DSET' and assessment['net']==net
    assert assessment['front_path_mm']==front and assessment['back_path_mm']==back
    assert abs(length-assessment['actual_leaf_length_mm']) < 1e-8 and length <= assessment['maximum_leaf_length_mm']==12
    assert assessment['trace_width_mm']==.2 and assessment['source_trunk_contact_mm']==[83.8,24.8]
    assert assessment['retained_source_trunk_width_mm']==.6
    root = next(n for n in children(parent,'segment') if str(first(n,'uuid')[1])=='d39e4975-3361-5522-816c-8f9745321f04')
    assert float(first(root,'width')[1])==.6 and str(first(root,'layer')[1])=='B.Cu'
    rho = 1.724e-8*(1+.00393*(125-20))
    resistance = rho*(12e-3)/(.16e-3*18e-6)
    assert assessment['assumed_minimum_finished_width_mm']==.16 and assessment['assumed_minimum_copper_um']==18
    assert assessment['assumed_copper_temperature_C']==125 and assessment['engineering_current_allowance_A']==.001
    assert abs(assessment['maximum_trace_only_resistance_ohm']-resistance)<1e-12
    assert abs(assessment['maximum_trace_only_drop_V']-resistance*.001)<1e-12
    assert assessment['primary_document_url']=='https://www.ti.com/lit/ds/symlink/tps3890.pdf'
    assert assessment['primary_document_revision']=='SLVSD65A, May 2016'
    assert assessment['datasheet_fixed_variant_ISENSE_entry_A_at_VSENSE_5V']==8e-6
    assert assessment['current_allowance_is_not_a_datasheet_guarantee_at_3V3'] is True
    assert assessment['adjustable_variant_100nA_not_used'] is True
    assert assessment['ordinary_VDD_and_MR_feeds_unchanged'] is True
    assert assessment['electrical_noise_accuracy_transients_and_installed_process_qualified'] is False
    # Test the new hole without the already-centred shortcut or its new spurs.
    new_ids = {r['uuid'] for r in additions}
    context = dict(captured,objects=[o for o in captured['objects'] if o['uuid'] not in new_ids])
    screen = SignalScreen(context)
    assert screen.via_legal(net,via['xy_mm'])
    assert all(math.dist(p,via['xy_mm'])>.86 for _,p in screen.vias)
    physical = PowerSpace(context)
    assert physical.surface.legal(net,'F.Cu',front) and physical.surface.legal(net,'B.Cu',back)
    # A quiet SENSE leaf uses the existing power-route policy; no noisy PG
    # copper is exempted from the stronger all-layer analog-region screen.
    leaf_ids = new_ids | {'84ca6e3b-ea1d-5788-ab80-edda1bb9e9d0','38c90714-3217-5020-850b-191752d7a827'}
    leaves = {layer:unary_union([shape(o['layers'][layer]) for o in captured['objects'] if o['uuid'] in leaf_ids and o['layers'].get(layer)])
              for layer in LAYERS}
    contact = Point(83.8,24.8).buffer(.6)
    for o in captured['objects']:
        if o['net']!=net or o['uuid'] in leaf_ids or (o.get('ref'),o.get('pin'))==('U205','1'):
            continue
        for layer,ps in o['layers'].items():
            if layer in leaves and ps:
                assert leaves[layer].difference(contact).intersection(shape(ps)).area<1e-10, 'SENSE entry carries another supply load'
    return assessment


def minimum_actual_drill_gap(board, pads):
    smd = [shape(ps) for p in pads if not any(p['drill_mm']) for layer,ps in p['layers'].items() if layer in ('F.Cu','B.Cu') and ps]
    minimum = min(Point(list(map(float,first(v,'at')[1:3]))).distance(g)-float(first(v,'drill')[1])/2
                  for v in children(board,'via') for g in smd)
    assert minimum >= .16-1e-7, 'Actual drill approaches an SMD solder land'
    return minimum


def check():
    parent = parent_check()
    assert parent == json.loads((SOURCE / "routing-handoff.json").read_text())
    names = ("prepared-native-inputs.json", "distribution-construction.json", "native-refill.json", "terminal-connectivity-review.json", "fill-entry.json", "review-entry.json", "additional-terminal-review.json", "current-native-pads.json", "retain-entry.json", "pg-routing-proposal.json")
    reports = {name: json.loads((OUT / name).read_text()) for name in names}
    for report in reports.values():
        verify_hashes(report["source_sha256"])
    capture, record = reports["prepared-native-inputs.json"], reports["distribution-construction.json"]
    refill, witness = reports["native-refill.json"], reports["terminal-connectivity-review.json"]
    assert record["routes"] == reports["pg-routing-proposal.json"]["routes"], "Selected paths differ from checked planning proposal"
    assert sha(OUT / "distribution-input.kicad_pcb") == record["authored_PCB_sha256"]
    assert sha(OUT / "audio_core.kicad_pcb") == refill["filled_PCB_sha256"] and sha(OUT / "native-refill-export.kicad_pcb") == refill["native_export_sha256"]
    preparation = json.loads((OUT / "preparation-record.json").read_text())
    verify_hashes(preparation["source_sha256"])
    assert sha(OUT/"prepared-input.kicad_pcb")==preparation["authored_PCB_sha256"]
    prepared = read_sexpr((OUT/"prepared-input.kicad_pcb").read_text())
    sense = verify_sense_entry(prepared,preparation,capture)
    assert record["sense_branch_assessment"]==sense
    board = read_sexpr((OUT / "audio_core.kicad_pcb").read_text())
    assert without_fill(board) == without_fill(read_sexpr((OUT / "distribution-input.kicad_pcb").read_text()))
    native_export = read_sexpr((OUT / "native-refill-export.kicad_pcb").read_text())
    fills = {str(first(z, "uuid")[1]): children(z, "filled_polygon") for z in children(native_export, "zone") if not children(z, "keepout")}
    polygons = []
    for zone in children(board, "zone"):
        if not children(zone, "keepout"):
            assert children(zone, "filled_polygon") == fills[str(first(zone, "uuid")[1])]
            polygons += [Polygon([tuple(map(float, p[1:3])) for p in children(first(f, "pts"), "xy")]).buffer(0) for f in children(zone, "filled_polygon")]
    proof = verify_copper(board, record, capture)
    verify_terminals(witness, record, capture)
    verify_inherited(reports["additional-terminal-review.json"])
    native = verify_native(OUT)
    opens = native["uncapped_open_connections"]
    assert opens == witness["uncapped_open_connections"] == reports["additional-terminal-review.json"]["uncapped_open_connections"] == 203
    assert opens == parent["uncapped_open_connections"]-proof["added_global_control_pairs"]
    assert proof["tracks"] == witness["tracks"] and proof["vias"] == witness["vias"]
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            assert (OUT / p.name).read_bytes() == p.read_bytes()
    for p in (SOURCE / "libraries").rglob("*"):
        if p.is_file():
            assert (OUT / p.relative_to(SOURCE)).read_bytes() == p.read_bytes()
    # The additive board retains exact footprint syntax. Check the actual
    # native polygons as well, rather than trusting only the source poses.
    def pad_key(p):
        return p["ref"], p["pin"], tuple(p["position_mm"])
    original_pads = {pad_key(p): p for p in capture["objects"] if p["kind"] == "PAD"}
    current_pads = {pad_key(p): p for p in reports["current-native-pads.json"]["objects"]}
    assert len(original_pads) == len(current_pads) == 930 and original_pads.keys() == current_pads.keys()
    for key, pad in current_pads.items():
        assert all(pad[k] == original_pads[key][k] for k in ("kind", "net", "layers", "drill_mm", "npth")), "Native pad geometry changed"
    counts = Counter()
    for row in json.loads((OUT / "drc.json").read_text())["unconnected_items"]:
        nets = [re.search(r"\[([^]]+)\]", item["description"]).group(1) for item in row["items"]]
        assert len(set(nets)) == 1
        counts[nets[0]] += 1
    assert sum(counts[n] for n in CONTROL_NETS) == 2
    paths = [Path(__file__), ROOT / "audio_main_global_controls.py", ROOT / "audio_main_codec_pgood_repack.py",
             ROOT / "review_audio_control_retention.py", ROOT / "audio_main_native_review.py", SOURCE / "routing-handoff.json"]
    paths += [OUT / n for n in names]+[OUT / "placement-native-review.json", OUT/"preparation-record.json", OUT/"prepared-input.kicad_pcb"]
    result = dict(parent)
    result.update(proof)
    result["added_global_control_pairs"] += parent["added_global_control_pairs"]
    result["checkpoint_added_control_tracks"] = result.pop("added_global_control_tracks")
    result["checkpoint_added_control_vias"] = result.pop("added_global_control_vias")
    result.update(source_sha256=relative_hashes(paths), uncapped_open_connections=opens,
                  remaining_control_connections=sum(counts[n] for n in CONTROL_NETS),
                  remaining_control_connections_by_net={n: counts[n] for n in sorted(CONTROL_NETS) if counts[n]},
                  ground_plane_area_mm2=round(unary_union(polygons).area, 6),
                  minimum_screened_drill_edge_to_SMD_copper_mm=round(minimum_actual_drill_gap(board,reports["current-native-pads.json"]["objects"]),9),
                  codec_A3V3_sense_branch_assessment=sense,
                  control_timing_signal_integrity_EMI_and_installed_fault_qualified=False,
                  PCB_routed=False, fabrication_released=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check()
    p = OUT / "routing-handoff.json"
    if args.check:
        assert result == json.loads(p.read_text())
    else:
        with p.open("x") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    print("CODEC_PGOOD connection:", result["added_global_control_pairs"], "joins;", result["remaining_control_connections"], "control gaps; total opens", result["uncapped_open_connections"])
