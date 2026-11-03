"""Verify the GAIN_REQ repair, retained geometry and exhaustive noise gap checks."""

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from shapely.geometry import LineString, Point

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audio_main_noise_audit import measure
from hardware.fabrication.audio_main_quiet_screen import QuietTraceScreen
from hardware.fabrication.audit_audio_main_named_routes import NETS, NOISY
from hardware.fabrication.audit_audio_main_six_preparation import verify_fill
from hardware.fabrication.audit_audio_main_supplies import without_fill
from hardware.fabrication.audit_audio_main_supply_completion import verify_native
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-six-monitor-01"
OUT = ROOT / "staging/audio-main-six-monitor-03"
GAIN = "/BYPASS/GAIN_REQ"


def point(xy):
    return tuple(round(float(v), 6) for v in xy)


def verify_preparation(source, prepared, record):
    retired = set(record["retired_copper_uuids"])
    removed = [n for n in children(source, "segment") if str(first(n, "uuid")[1]) in retired]
    assert len(retired) == len(removed) == 15 and removed == record["retired_nodes"]
    names = {str(n[1]): str(n[2]) for n in children(source, "net")}
    adjacency = defaultdict(set)
    for n in removed:
        assert names[str(first(n, "net")[1])] == GAIN and first(n, "layer")[1] == "F.Cu" and float(first(n, "width")[1]) == .2
        start, end = [point(first(n, k)[1:3]) for k in ("start", "end")]
        adjacency[start].add(end)
        adjacency[end].add(start)
    ends = {(33.0875, 49.0), (3.0, 45.62)}
    assert {p for p, neighbors in adjacency.items() if len(neighbors) == 1} == ends
    assert all(len(neighbors) in (1, 2) for neighbors in adjacency.values())
    seen, pending = set(), [next(iter(ends))]
    while pending:
        p = pending.pop()
        if p not in seen:
            seen.add(p)
            pending.extend(adjacency[p]-seen)
    assert seen == set(adjacency), "Retired copper is not the single declared header branch"
    expected = [n for n in source if n not in removed]
    assert without_fill(prepared) == without_fill(expected), "Undeclared source geometry changed"


def legacy_measurement():
    captured = json.loads((SOURCE / "native-inputs.json").read_text())
    record = json.loads((SOURCE / "distribution-construction.json").read_text())
    verify_hashes(captured["source_sha256"])
    verify_hashes(record["source_sha256"])
    parent_path = ROOT / "staging/audio-main-six-local-01/audio_core.kicad_pcb"
    parent = read_sexpr(parent_path.read_text())
    board = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    assert without_fill(board[:len(parent)]) == without_fill(parent)
    names = {str(n[1]): str(n[2]) for n in children(board, "net")}
    extra = board[len(parent):]
    assert all(n[0] in ("segment", "via") and names[str(first(n, "net")[1])] in NETS for n in extra)
    assert not NETS & NOISY  # All captured noisy geometry is unchanged.
    rows = [dict(uuid=str(first(n, "uuid")[1]), kind="PCB_TRACK", net=names[str(first(n, "net")[1])],
                 position_mm=list(map(float, first(n, "start")[1:3])), end_mm=list(map(float, first(n, "end")[1:3])),
                 copper_faces=[first(n, "layer")[1]]) for n in extra if n[0] == "segment"]
    assert {r["uuid"] for r in rows} == {r["uuid"] for r in record["added_segments"]}
    measurement = measure(captured, NETS, NOISY, quiet_tracks=rows)
    assert measurement["trace_count"] == 34 and len(measurement["violations"]) == 4
    return dict(source_sha256=relative_hashes([Path(__file__), ROOT / "audio_main_noise_audit.py",
                SOURCE / "native-inputs.json", SOURCE / "distribution-construction.json", SOURCE / "audio_core.kicad_pcb", parent_path,
                ROOT / "audio_main_global_controls.py", ROOT / "audio_main_monitor_routes.py", ROOT / "audit_audio_main_named_routes.py"]),
                superseded_spacing_review=str((SOURCE / "named-route-review.json").relative_to(ROOT.parents[1])),
                defect="Legacy legal() searched only .5 mm around a line while enforcing enlarged .71 mm clearances",
                consequence="Four new segment/noisy-copper relationships violate the stated policy; native DRC and connection counts are unaffected",
                measurement=measurement, electrical_noise_qualified=False, fabrication_released=False)


def verify_added(parent, board, record, captured):
    assert without_fill(board[:len(parent)]) == without_fill(parent), "Prepared geometry changed"
    extra = board[len(parent):]
    assert extra and all(n[0] in ("segment", "via") for n in extra)
    segments = {str(first(n, "uuid")[1]): n for n in extra if n[0] == "segment"}
    vias = {str(first(n, "uuid")[1]): n for n in extra if n[0] == "via"}
    assert len(segments)+len(vias) == len(extra) and len(vias) == 1
    assert set(segments) == {r["uuid"] for r in record["added_segments"]}
    assert set(vias) == {r["uuid"] for r in record["added_vias"]}
    names = {str(n[1]): str(n[2]) for n in children(board, "net")}
    actual = {}
    for row in record["added_segments"]:
        n = segments[row["uuid"]]
        net, face = names[str(first(n, "net")[1])], first(n, "layer")[1]
        start, end = [point(first(n, k)[1:3]) for k in ("start", "end")]
        assert net == row["net"] and net in (GAIN, "/ADC/BIAS_SHIFT_R") and face == row["layer"] and face in ("F.Cu", "In3.Cu", "B.Cu")
        assert float(first(n, "width")[1]) == row["width_mm"] == .2
        assert start == point(row["start_mm"]) and end == point(row["end_mm"])
        key = net, face, start, end
        assert key not in actual
        actual[key] = row["uuid"]
    vrow = record["added_vias"][0]
    via = vias[vrow["uuid"]]
    assert names[str(first(via, "net")[1])] == vrow["net"] == GAIN
    assert point(first(via, "at")[1:3]) == point(vrow["xy_mm"])
    assert float(first(via, "size")[1]) == vrow["diameter_mm"] == .6
    assert float(first(via, "drill")[1]) == vrow["drill_mm"] == .3
    assert first(via, "layers")[1:] == ["F.Cu", "B.Cu"]
    objects = {o["uuid"]: o for o in captured["objects"]}
    pads = {(o["ref"], o["pin"]): o for o in objects.values() if o["kind"] == "PAD" and o["pin"]}
    membership = {uid: k for k, ids in captured["groups"].items() for uid in ids}
    control, quiet = QuietTraceScreen(captured, NETS), QuietTraceScreen(captured, NOISY)
    assert len(record["routes"]) == 2
    used = set()
    for i, row in enumerate(record["routes"]):
        net, runs = row["net"], row["runs"]
        left, right = row["source_groups"]
        assert len(left) == len(right) == 1 and left != right
        assert all(objects[captured["groups"][k][0]]["net"] == net for k in left+right)
        if i == 0:
            assert net == GAIN and row["purpose"] == "quiet_gpio_repair" and row["repaired_existing_join"]
            p, q = pads["R607", "1"], pads["J602", "4"]
            assert row["endpoints"] == [["R607", "1"], ["J602", "4"]]
            assert len(runs) == 2 and [r[0] for r in runs] == ["F.Cu", "In3.Cu"]
            assert q["layers"].get("In3.Cu") and row["new_vias_mm"] == [vrow["xy_mm"]]
            xy = row["new_vias_mm"][0]
            assert point(runs[0][1][-1]) == point(runs[1][1][0]) == point(xy)
            assert control.via_legal(net, xy) and all(math.dist(xy, other) > .86 for _, other in control.vias)
            assert LineString(runs[0][1]).length <= 3.5
            limit = min(180, 2.5*math.dist(p["position_mm"], q["position_mm"])+10)
            screen = control
        else:
            assert net == "/ADC/BIAS_SHIFT_R" and row["purpose"] == "short_comparator_surface_bridge" and not row["repaired_existing_join"]
            assert len(runs) == 1 and runs[0][0] == "B.Cu" and row["new_vias_mm"] == []
            a, b = row["native_contacts"]
            p, q = objects[a["uuid"]], objects[b["uuid"]]
            assert p["kind"] == "PCB_VIA" and (q["ref"], q["pin"]) == ("R136", "2")
            assert a == dict(uuid=p["uuid"], face="B.Cu", point_mm=p["position_mm"])
            assert b == dict(uuid=q["uuid"], face="B.Cu", point_mm=q["position_mm"])
            limit = min(8, 1.6*math.dist(p["position_mm"], q["position_mm"])+.5)
            screen = quiet
        assert p["net"] == q["net"] == net and row["terminal_points_mm"] == [p["position_mm"], q["position_mm"]]
        assert membership[p["uuid"]] == left[0] and membership[q["uuid"]] == right[0]
        assert point(runs[0][1][0]) == point(p["position_mm"]) and point(runs[-1][1][-1]) == point(q["position_mm"])
        length = sum(LineString(ps).length for _, ps in runs)
        assert abs(length-row["planar_length_mm"]) < 1e-7 and row["maximum_planar_length_mm"] == limit and length <= limit
        for face, ps in runs:
            assert screen.legal(net, face, ps), "Corrected trace clearance check failed"
            for start, end in zip(ps, ps[1:]):
                ident = actual[net, face, point(start), point(end)]
                assert ident not in used
                used.add(ident)
        for s in (control, quiet):
            s.added.extend((net, face, LineString(ps)) for face, ps in runs)
            s.new_vias.extend((net, xy) for xy in row["new_vias_mm"])
    assert used == set(segments)
    assert record["trace_width_mm"] == record["clearance_mm"] == .2 and record["planning_margin_mm"] == .01
    assert record["noisy_net_centreline_to_copper_mm"] == .71 and record["repaired_existing_control_joins"] == record["new_comparator_joins"] == 1
    smd = [shape(ps) for o in captured["objects"] if o["kind"] == "PAD" and not any(o["drill_mm"])
           for face, ps in o["layers"].items() if face in ("F.Cu", "B.Cu") and ps]
    minimum = min(Point(vrow["xy_mm"]).distance(g)-.15 for g in smd)
    assert minimum >= .16-1e-7
    return round(minimum, 9)


def check():
    names = ["preparation-record.json", "prepared-refill.json", "prepared-native-inputs.json", "distribution-construction.json",
             "native-refill.json", "terminal-connectivity-review.json", "additional-terminal-review.json", "current-native-pads.json", "final-native-inputs.json"]
    reports = {n: json.loads((OUT / n).read_text()) for n in names}
    for r in reports.values():
        verify_hashes(r["source_sha256"])
        assert not r["fabrication_released"]
    source = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    prepared = read_sexpr((OUT / "prepared-input.kicad_pcb").read_text())
    assert sha(OUT / "prepared-input.kicad_pcb") == reports["preparation-record.json"]["authored_PCB_sha256"]
    verify_preparation(source, prepared, reports["preparation-record.json"])
    verify_fill(OUT, prepared, "prepared-refilled.kicad_pcb", "prepared-native-export.kicad_pcb", reports["prepared-refill.json"])
    record, captured = reports["distribution-construction.json"], reports["prepared-native-inputs.json"]
    assert captured["native_uncapped_opens"] == 174 and captured["layer_count"] == 6
    assert sha(OUT / "distribution-input.kicad_pcb") == record["authored_PCB_sha256"]
    authored = read_sexpr((OUT / "distribution-input.kicad_pcb").read_text())
    ground = verify_fill(OUT, authored, "audio_core.kicad_pcb", "native-refill-export.kicad_pcb", reports["native-refill.json"])
    board = read_sexpr((OUT / "audio_core.kicad_pcb").read_text())
    minimum = verify_added(read_sexpr((OUT / "prepared-refilled.kicad_pcb").read_text()), board, record, captured)
    native = verify_native(OUT)
    source_witness = json.loads((SOURCE / "terminal-connectivity-review.json").read_text())
    witness, extra = reports["terminal-connectivity-review.json"], reports["additional-terminal-review.json"]
    for key in ("retained_local_pairs", "retained_control_pairs", "ground_pads", "supply_pads"):
        assert witness[key] == source_witness[key]
    objects = {o["uuid"]: o for o in captured["objects"]}
    expected = []
    for row in record["routes"]:
        contacts = [objects[uid] for side in row["source_groups"] for k in side for uid in captured["groups"][k]
                    if objects[uid]["kind"] == "PAD" and objects[uid]["pin"]]
        expected.append(dict(net=row["net"], source_groups=row["source_groups"], reference_terminal=[contacts[0]["ref"], contacts[0]["pin"]],
                             contacts=[dict(ref=p["ref"], pin=p["pin"], native_connected=True) for p in contacts]))
    assert witness["new_route_witnesses"] == expected
    inherited = json.loads((SOURCE / "additional-terminal-review.json").read_text())
    assert extra["retained_global_control_witnesses"] == inherited["retained_global_control_witnesses"]+source_witness["new_route_witnesses"]
    assert len(extra["retained_global_control_witnesses"]) == 95
    assert extra["retained_private_timing_connections"] == inherited["retained_private_timing_connections"]
    def pad_key(p):
        return p["ref"], p["pin"], point(p["position_mm"])
    old = {pad_key(p): p for p in captured["objects"] if p["kind"] == "PAD"}
    current = {pad_key(p): p for p in reports["current-native-pads.json"]["objects"]}
    assert old.keys() == current.keys() and len(old) == len(current) == 930
    assert all(all(p[k] == old[ident][k] for k in ("net", "layers", "drill_mm", "npth")) for ident, p in current.items())
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_sym", ".kicad_dru") or p.name in ("audio_core.kicad_pro", "plan.json", "fp-lib-table", "sym-lib-table"):
            assert sha(p) == sha(OUT / p.name)
    for p in (SOURCE / "libraries").rglob("*"):
        if p.is_file():
            assert sha(p) == sha(OUT / p.relative_to(SOURCE))
    final = reports["final-native-inputs.json"]
    assert final["native_uncapped_opens"] == native["uncapped_open_connections"] == witness["uncapped_open_connections"] == extra["uncapped_open_connections"] == record["expected_native_opens"] == 172
    assert final["layer_count"] == 6
    # These authored lands receive different pad UUIDs across native loads;
    # compare every physical land instead of treating those UUIDs as stable.
    final_pads = {pad_key(p): p for p in final["objects"] if p["kind"] == "PAD"}
    assert final_pads.keys() == current.keys() and len(final_pads) == 930
    assert all(all(p[k] == current[ident][k] for k in ("net", "layers", "drill_mm", "npth")) for ident, p in final_pads.items())
    assert {o["uuid"] for o in final["objects"] if o["kind"] != "PAD"} == {o["uuid"] for o in captured["objects"] if o["kind"] != "PAD"} | {r["uuid"] for r in record["added_segments"]+record["added_vias"]}
    noise = measure(final, NETS, NOISY)
    assert noise["trace_count"] == 41 and noise["same_layer_pairs_measured"] == 14303 and noise["violations"] == []
    counts = Counter()
    for row in json.loads((OUT / "drc.json").read_text())["unconnected_items"]:
        net = re.search(r"\[([^]]+)\]", row["items"][0]["description"]).group(1)
        counts[net] += 1
    assert counts[GAIN] == 0 and {n: counts[n] for n in NETS if counts[n]} == {"/ADC/THRESH_LOWER": 1}
    paths = [Path(__file__), ROOT / "audio_main_noise_audit.py", ROOT / "audio_main_quiet_screen.py", SOURCE / "terminal-connectivity-review.json",
             SOURCE / "additional-terminal-review.json", OUT / "previous-spacing-erratum.json", OUT / "placement-native-review.json"]+[OUT / n for n in names]
    return dict(source_sha256=relative_hashes(paths), retired_GPIO_branch_segments=15, repaired_existing_control_joins=1,
                new_comparator_joins=1, checkpoint_added_tracks=len(record["added_segments"]), checkpoint_added_vias=1,
                minimum_new_drill_edge_to_SMD_mm=minimum, all_unretired_geometry_and_930_native_pads_exact=True,
                ground_plane_area_mm2=ground, exhaustive_noise_geometry=noise, remaining_comparator_input_gaps={"/ADC/THRESH_LOWER": 1},
                native_geometry_findings=0, native_ERC_findings=0, native_parity_findings=1, uncapped_open_connections=172,
                physical_stack_material_cost_and_process_accepted=False, noise_and_installed_fault_performance_qualified=False,
                PCB_routed=False, fabrication_released=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    erratum = legacy_measurement()
    ep = OUT / "previous-spacing-erratum.json"
    if args.check:
        assert erratum == json.loads(ep.read_text())
    else:
        with ep.open("x") as f:
            json.dump(erratum, f, indent=2)
            f.write("\n")
    result = check()
    p = OUT / "clearance-repair-review.json"
    if args.check:
        assert result == json.loads(p.read_text())
    else:
        with p.open("x") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    print("GAIN_REQ repaired; 1 comparator gap closed; 172 opens; exhaustive .71 mm policy now passes")
