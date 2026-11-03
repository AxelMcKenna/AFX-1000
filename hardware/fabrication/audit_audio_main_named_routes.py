"""Replay bounded comparator-input routes and retained native audio circuitry."""

import argparse
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audio_main_control_routes import CONTROL_NETS
from hardware.fabrication.audio_main_layer_screen import LayeredSignalScreen
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_audio_main_six_preparation import check as preparation_check
from hardware.fabrication.audit_audio_main_six_preparation import verify_fill
from hardware.fabrication.audit_audio_main_supplies import without_fill
from hardware.fabrication.audit_audio_main_supply_completion import verify_native
from hardware.fabrication.audit_audio_main_surface_links import check as surface_check
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-six-local-01"
OUT = ROOT / "staging/audio-main-six-monitor-01"
NETS = {"/ADC/BIAS_SHIFT_L", "/ADC/BIAS_SHIFT_R", "/ADC/THRESH_UPPER", "/ADC/THRESH_LOWER"}
NOISY = set(CONTROL_NETS) | {"/CODEC/ADC_DATA", "/CODEC/BCLK", "/CODEC/WS", "/CODEC/SCL", "/CODEC/SDA",
                            "GAIN_LOW", "/BYPASS/BYPASS_LOW", "/BYPASS/INPUT_LOW"}


def point(xy):
    return tuple(round(float(v), 6) for v in xy)


def verify_routes(parent, board, record, captured):
    assert without_fill(board[:len(parent)]) == without_fill(parent), "Existing geometry changed"
    added = board[len(parent):]
    assert added and all(n[0] in ("segment", "via") for n in added)
    segments = {str(first(n, "uuid")[1]): n for n in added if n[0] == "segment"}
    vias = {str(first(n, "uuid")[1]): n for n in added if n[0] == "via"}
    assert len(segments)+len(vias) == len(added)
    assert set(segments) == {r["uuid"] for r in record["added_segments"]}
    assert set(vias) == {r["uuid"] for r in record["added_vias"]}
    names = {str(n[1]): str(n[2]) for n in children(parent, "net")}
    actual, actual_vias = {}, {}
    for row in record["added_segments"]:
        n = segments[row["uuid"]]
        net, face = names[str(first(n, "net")[1])], first(n, "layer")[1]
        start, end = [point(first(n, k)[1:3]) for k in ("start", "end")]
        assert net in NETS and net == row["net"] and face == row["layer"] and face in ("F.Cu", "In3.Cu", "B.Cu")
        assert float(first(n, "width")[1]) == row["width_mm"] == .2, "Monitor width changed"
        assert start == point(row["start_mm"]) and end == point(row["end_mm"])
        key = net, face, start, end
        assert key not in actual
        actual[key] = row["uuid"]
    for row in record["added_vias"]:
        n = vias[row["uuid"]]
        net, xy = names[str(first(n, "net")[1])], point(first(n, "at")[1:3])
        assert net in NETS and net == row["net"] and xy == point(row["xy_mm"])
        assert float(first(n, "size")[1]) == row["diameter_mm"] == .6
        assert float(first(n, "drill")[1]) == row["drill_mm"] == .3, "Monitor drill changed"
        assert first(n, "layers")[1:] == ["F.Cu", "B.Cu"]
        assert (net, xy) not in actual_vias
        actual_vias[net, xy] = row["uuid"]
    assert record["allowed_nets"] == sorted(NETS) and record["noisy_nets"] == sorted(NOISY)
    assert record["trace_width_mm"] == record["clearance_mm"] == .2 and record["planning_margin_mm"] == .01
    assert record["noisy_net_centreline_to_copper_mm"] == .71
    screen = LayeredSignalScreen(captured)
    for face in screen.layers:
        screen.geometry[face] = [(net, g, max(d, .71) if net in NOISY else d) for net, g, d in screen.geometry[face]]
        screen.trees[face] = STRtree([g for _, g, _ in screen.geometry[face]])
    objects = {o["uuid"]: o for o in captured["objects"]}
    pads = {(o["ref"], o["pin"]): o for o in objects.values() if o["kind"] == "PAD" and o["pin"]}
    membership = {uid: k for k, ids in captured["groups"].items() for uid in ids}
    groups = {frozenset([k]) for k in captured["groups"]}
    used_tracks, used_vias = set(), set()
    for row in record["routes"]:
        net = row["net"]
        assert net in NETS and row["purpose"] == "bias_window_comparator_input"
        p, q = [pads[tuple(k)] for k in row["endpoints"]]
        assert p["net"] == q["net"] == net
        left, right = [frozenset(side) for side in row["source_groups"]]
        assert left in groups and right in groups and left != right and not left & right, "False named-net island merge"
        assert membership[p["uuid"]] in left and membership[q["uuid"]] in right
        assert all(objects[captured["groups"][k][0]]["net"] == net for k in left | right)
        terminals = [p["position_mm"], q["position_mm"]]
        assert row["terminal_points_mm"] == terminals
        runs = row["runs"]
        assert len(runs) in (1, 3) and point(runs[0][1][0]) == point(terminals[0]) and point(runs[-1][1][-1]) == point(terminals[1])
        assert runs[0][0] in ("F.Cu", "B.Cu") and p["layers"].get(runs[0][0])
        assert runs[-1][0] in ("F.Cu", "B.Cu") and q["layers"].get(runs[-1][0])
        length = sum(LineString(ps).length for _, ps in runs)
        limit = min(40, 2*math.dist(*terminals)+6)
        assert abs(length-row["planar_length_mm"]) < 1e-7 and row["maximum_planar_length_mm"] == limit and length <= limit+1e-7
        assert len(row["new_vias_mm"]) == (2 if len(runs) == 3 else 0) and row["maximum_new_vias"] == 2
        if len(runs) == 3:
            assert runs[1][0] == "In3.Cu"
            assert all(LineString(ps).length <= 3.5+1e-7 for _, ps in (runs[0], runs[-1])), "Monitor surface neck too long"
            for i, xy in enumerate(row["new_vias_mm"]):
                key = net, point(xy)
                assert actual_vias[key] not in used_vias
                assert all(math.dist(xy, other) > .86 for _, other in screen.vias+screen.new_vias)
                assert all(math.dist(xy, other) > .86 for other in row["new_vias_mm"][:i])
                assert screen.via_legal(net, xy), "Monitor via violates copper, drills, protected regions or ground reference"
                assert point(runs[i][1][-1]) == point(runs[i+1][1][0]) == point(xy)
                used_vias.add(actual_vias[key])
        for face, ps in runs:
            assert screen.legal(net, face, ps), "Monitor trace violates copper, noisy-net clearance or protected regions"
            for start, end in zip(ps, ps[1:]):
                ident = actual[net, face, point(start), point(end)]
                assert ident not in used_tracks
                used_tracks.add(ident)
        screen.added.extend((net, face, LineString(ps)) for face, ps in runs)
        screen.new_vias.extend((net, xy) for xy in row["new_vias_mm"])
        groups.difference_update([left, right])
        groups.add(left | right)
    assert used_tracks == set(segments) and used_vias == set(vias), "Unreviewed named-net copper"
    smd = [shape(ps) for p in pads.values() if not any(p["drill_mm"]) for face, ps in p["layers"].items() if face in ("F.Cu", "B.Cu") and ps]
    minimum = min(Point(r["xy_mm"]).distance(g)-.15 for r in record["added_vias"] for g in smd)
    assert minimum >= .16-1e-7
    return round(minimum, 9)


def check():
    assert surface_check() == json.loads((SOURCE / "surface-delta-review.json").read_text())
    prep = ROOT / "staging/audio-main-six-control-01/preparation-retention-review.json"
    assert preparation_check() == json.loads(prep.read_text())
    names = ["native-inputs.json", "distribution-construction.json", "native-refill.json", "terminal-connectivity-review.json",
             "additional-terminal-review.json", "current-native-pads.json"]
    reports = {n: json.loads((OUT / n).read_text()) for n in names}
    for r in reports.values():
        verify_hashes(r["source_sha256"])
        assert not r["fabrication_released"]
    captured, record = reports["native-inputs.json"], reports["distribution-construction.json"]
    parent = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    board = read_sexpr((OUT / "audio_core.kicad_pcb").read_text())
    assert sha(OUT / "distribution-input.kicad_pcb") == record["authored_PCB_sha256"]
    ground = verify_fill(OUT, read_sexpr((OUT / "distribution-input.kicad_pcb").read_text()), "audio_core.kicad_pcb", "native-refill-export.kicad_pcb", reports["native-refill.json"])
    minimum = verify_routes(parent, board, record, captured)
    native = verify_native(OUT)
    source = json.loads((SOURCE / "terminal-connectivity-review.json").read_text())
    witness, extra = reports["terminal-connectivity-review.json"], reports["additional-terminal-review.json"]
    for key in ("retained_local_pairs", "retained_control_pairs", "ground_pads", "supply_pads"):
        assert witness[key] == source[key]
    objects = {o["uuid"]: o for o in captured["objects"]}
    expected = []
    for row in record["routes"]:
        contacts = [objects[uid] for side in row["source_groups"] for k in side for uid in captured["groups"][k]
                    if objects[uid]["kind"] == "PAD" and objects[uid]["pin"]]
        assert contacts and all(p["net"] == row["net"] for p in contacts)
        expected.append(dict(net=row["net"], source_groups=row["source_groups"], reference_terminal=[contacts[0]["ref"], contacts[0]["pin"]],
                             contacts=[dict(ref=p["ref"], pin=p["pin"], native_connected=True) for p in contacts]))
    assert witness["new_route_witnesses"] == expected
    inherited = json.loads((SOURCE / "additional-terminal-review.json").read_text())
    assert extra["retained_global_control_witnesses"] == inherited["retained_global_control_witnesses"]+source["new_route_witnesses"]
    assert len(extra["retained_global_control_witnesses"]) == 88
    assert extra["retained_private_timing_connections"] == inherited["retained_private_timing_connections"]
    def key(p):
        return p["ref"], p["pin"], point(p["position_mm"])
    old = {key(p): p for p in captured["objects"] if p["kind"] == "PAD"}
    current = {key(p): p for p in reports["current-native-pads.json"]["objects"]}
    assert old.keys() == current.keys() and len(old) == len(current) == 930
    assert all(all(p[k] == old[ident][k] for k in ("net", "layers", "drill_mm", "npth")) for ident, p in current.items())
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            assert sha(p) == sha(OUT / p.name)
    for p in (SOURCE / "libraries").rglob("*"):
        if p.is_file():
            assert sha(p) == sha(OUT / p.relative_to(SOURCE))
    opens = native["uncapped_open_connections"]
    assert opens == witness["uncapped_open_connections"] == extra["uncapped_open_connections"] == record["expected_native_opens"] == 180-len(record["routes"])
    return dict(source_sha256=relative_hashes([Path(__file__), prep, SOURCE / "surface-delta-review.json", SOURCE / "additional-terminal-review.json",
                OUT / "placement-native-review.json"]+[OUT / n for n in names]),
                checkpoint_added_monitor_joins=len(record["routes"]), checkpoint_added_tracks=len(record["added_segments"]),
                checkpoint_added_vias=len(record["added_vias"]), minimum_new_drill_edge_to_SMD_mm=minimum,
                all_existing_geometry_and_930_native_pads_preserved=True, inherited_native_witness_rows=88,
                ground_plane_area_mm2=ground, native_geometry_findings=0, native_ERC_findings=0, native_parity_findings=1,
                uncapped_open_connections=opens, physical_stack_material_cost_and_process_accepted=False,
                comparator_input_noise_and_fault_performance_qualified=False, PCB_routed=False, fabrication_released=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check()
    p = OUT / "named-route-review.json"
    if args.check:
        assert result == json.loads(p.read_text())
    else:
        with p.open("x") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    print(result["checkpoint_added_monitor_joins"], "comparator input joins;", result["uncapped_open_connections"], "opens; fabrication unreleased")
