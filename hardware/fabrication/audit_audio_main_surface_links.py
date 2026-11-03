"""Replay a surface-only audio delta without qualifying its incomplete parent."""

import argparse
import json
import math
from pathlib import Path

from shapely.geometry import LineString

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_audio_main_supplies import without_fill
from hardware.fabrication.audit_audio_main_supply_completion import verify_native
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import Screen

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-six-control-01"
OUT = ROOT / "staging/audio-main-six-local-01"
FEEDBACK = {("U103", "1", "2"), ("U103", "7", "6"),
            ("U104", "1", "2"), ("U104", "8", "9"),
            ("U305", "1", "2"), ("U305", "7", "6")}
LOCAL_NETS = {"/ADC/THRESH_LOWER", "/ADC/THRESH_UPPER", "/ADC/REF_DIV_L", "/ADC/REF_DIV_R",
              "/DAC/CM_SUM_L", "/DAC/CM_SUM_R", "/DAC/RX_POS_L", "/DAC/RX_POS_R",
              "/INPUT/ATTN_L", "/INPUT/ATTN_R", "/INPUT/BUF_IN_L", "/INPUT/BUF_IN_R",
              "/DAC/HP_NODE_L", "/DAC/HP_NODE_R", "RECV_L", "RECV_R", "/CODEC/SCL", "/CODEC/SDA"}


def point(xy):
    return tuple(round(float(v), 6) for v in xy)


def verify_delta(parent, board, record, captured):
    assert without_fill(board[:len(parent)]) == without_fill(parent), "Existing board changed"
    added = board[len(parent):]
    assert added and all(n[0] == "segment" for n in added), "Only surface segments are allowed"
    tracks = {str(first(n, "uuid")[1]): n for n in added}
    assert len(tracks) == len(added) == len(record["added_segments"])
    assert set(tracks) == {r["uuid"] for r in record["added_segments"]}
    assert record["added_vias"] == []
    assert record["trace_width_mm"] == record["clearance_mm"] == .2
    assert record["planning_margin_mm"] == .01
    names = {str(n[1]): str(n[2]) for n in children(parent, "net")}
    actual = {}
    for r in record["added_segments"]:
        n = tracks[r["uuid"]]
        net, face = names[str(first(n, "net")[1])], first(n, "layer")[1]
        start, end = [point(first(n, k)[1:3]) for k in ("start", "end")]
        assert face in ("F.Cu", "B.Cu") and face == r["layer"] and net == r["net"]
        assert float(first(n, "width")[1]) == r["width_mm"] == .2, "New trace width changed"
        assert start == point(r["start_mm"]) and end == point(r["end_mm"])
        key = net, face, start, end
        assert key not in actual
        actual[key] = r["uuid"]
    objects = {o["uuid"]: o for o in captured["objects"]}
    pads = {(o["ref"], o["pin"]): o for o in objects.values() if o["kind"] == "PAD" and o["pin"]}
    membership = {uid: k for k, ids in captured["groups"].items() for uid in ids}
    groups = {frozenset([k]) for k in captured["groups"]}
    screen, used, loops = Screen(captured), set(), set()
    for r in record["routes"]:
        p, q = [pads[tuple(k)] for k in r["endpoints"]]
        assert p["net"] == q["net"] == r["net"] and r["new_vias_mm"] == []
        left, right = [frozenset(s) for s in r["source_groups"]]
        assert left != right and left in groups and right in groups and not left & right, "False island merge"
        assert membership[p["uuid"]] in left and membership[q["uuid"]] in right
        assert len(r["runs"]) == 1
        face, points = r["runs"][0]
        assert face in ("F.Cu", "B.Cu") and p["layers"].get(face) and q["layers"].get(face)
        assert point(points[0]) == point(p["position_mm"]) and point(points[-1]) == point(q["position_mm"])
        assert r["terminal_points_mm"] == [p["position_mm"], q["position_mm"]]
        distance = math.dist(p["position_mm"], q["position_mm"])
        if r["purpose"] == "local_buffer_feedback":
            key = p["ref"], p["pin"], q["pin"]
            assert p["ref"] == q["ref"] and key in FEEDBACK and key not in loops
            loops.add(key)
            limit = 2.5
        elif r["purpose"] == "local_reference_buffer_feed":
            assert r["endpoints"] in [[["U104", "2"], ["U104", "5"]], [["U104", "9"], ["U104", "12"]]]
            limit = 6.0
        else:
            assert r["purpose"] == "short_passive_signal_link" and r["net"] in LOCAL_NETS and distance <= 6
            limit = min(8, 1.6*distance+.5)
        length = LineString(points).length
        assert abs(length-r["planar_length_mm"]) < 1e-7 and r["maximum_planar_length_mm"] == limit
        assert length <= limit+1e-7 and screen.legal(r["net"], face, points), "Trace exceeds its physical screen or length budget"
        for start, end in zip(points, points[1:]):
            ident = actual[r["net"], face, point(start), point(end)]
            assert ident not in used
            used.add(ident)
        screen.added.append((r["net"], face, LineString(points)))
        groups.difference_update([left, right])
        groups.add(left | right)
    assert used == set(tracks) and loops == FEEDBACK, "Unreviewed copper or missing buffer feedback"
    return len(record["routes"])


def check():
    names = ["native-inputs.json", "distribution-construction.json", "native-refill.json",
             "terminal-connectivity-review.json", "additional-terminal-review.json", "current-native-pads.json"]
    reports = {name: json.loads((OUT / name).read_text()) for name in names}
    for r in reports.values():
        verify_hashes(r["source_sha256"])
        assert not r["fabrication_released"]
    capture, record = reports["native-inputs.json"], reports["distribution-construction.json"]
    parent = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    board = read_sexpr((OUT / "audio_core.kicad_pcb").read_text())
    authored = OUT / "distribution-input.kicad_pcb"
    refill = reports["native-refill.json"]
    assert sha(authored) == record["authored_PCB_sha256"]
    assert sha(OUT / "audio_core.kicad_pcb") == refill["filled_PCB_sha256"]
    assert sha(OUT / "native-refill-export.kicad_pcb") == refill["native_export_sha256"]
    assert without_fill(board) == without_fill(read_sexpr(authored.read_text()))
    export = read_sexpr((OUT / "native-refill-export.kicad_pcb").read_text())
    fills = {str(first(z, "uuid")[1]): children(z, "filled_polygon") for z in children(export, "zone") if not children(z, "keepout")}
    planes = [z for z in children(board, "zone") if not children(z, "keepout")]
    assert {first(z, "layer")[1] for z in planes} == {"In1.Cu", "In4.Cu"} and len(planes) == 2
    for z in planes:
        assert children(z, "filled_polygon") == fills[str(first(z, "uuid")[1])] and children(z, "filled_polygon")
    count = verify_delta(parent, board, record, capture)
    native = verify_native(OUT)
    source = json.loads((SOURCE / "terminal-connectivity-review.json").read_text())
    witness = reports["terminal-connectivity-review.json"]
    for key in ("retained_local_pairs", "retained_control_pairs", "ground_pads", "supply_pads"):
        assert witness[key] == source[key], "Earlier connection lost"
    objects = {o["uuid"]: o for o in capture["objects"]}
    expected = []
    for r in record["routes"]:
        contacts = [objects[uid] for side in r["source_groups"] for k in side for uid in capture["groups"][k]
                    if objects[uid]["kind"] == "PAD" and objects[uid]["pin"]]
        expected.append(dict(net=r["net"], source_groups=r["source_groups"], reference_terminal=[contacts[0]["ref"], contacts[0]["pin"]],
                             contacts=[dict(ref=p["ref"], pin=p["pin"], native_connected=True) for p in contacts]))
    assert witness["new_route_witnesses"] == expected
    extra = reports["additional-terminal-review.json"]
    inherited = json.loads((SOURCE / "additional-terminal-review.json").read_text())
    assert extra["retained_global_control_witnesses"] == inherited["retained_global_control_witnesses"]+source["new_route_witnesses"]
    assert len(extra["retained_global_control_witnesses"]) == 67
    assert extra["retained_private_timing_connections"] == inherited["retained_private_timing_connections"]
    assert len(extra["retained_private_timing_connections"]) == 2
    def pad_key(p):
        return p["ref"], p["pin"], point(p["position_mm"])
    original_pads = {pad_key(p): p for p in capture["objects"] if p["kind"] == "PAD"}
    current_pads = {pad_key(p): p for p in reports["current-native-pads.json"]["objects"]}
    assert original_pads.keys() == current_pads.keys() and len(current_pads) == 930
    for k, p in current_pads.items():
        assert all(p[key] == original_pads[k][key] for key in ("net", "layers", "drill_mm", "npth")), "Native pad changed"
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            assert sha(p) == sha(OUT / p.name)
    for p in (SOURCE / "libraries").rglob("*"):
        if p.is_file():
            assert sha(p) == sha(OUT / p.relative_to(SOURCE))
    assert native["uncapped_open_connections"] == witness["uncapped_open_connections"] == extra["uncapped_open_connections"] == 201-count == record["expected_native_opens"]
    return dict(source_sha256=relative_hashes([Path(__file__), SOURCE / "terminal-connectivity-review.json",
                SOURCE / "additional-terminal-review.json", OUT / "placement-native-review.json"]+[OUT / name for name in names]),
                added_surface_joins=count, completed_local_buffer_feedback_pairs=len(FEEDBACK),
                added_surface_tracks=len(record["added_segments"]), added_vias=0,
                all_parent_copper_footprints_and_stack_exact=True, actual_native_pads_unchanged=930,
                native_geometry_findings=0, native_ERC_findings=0, native_parity_findings=1,
                uncapped_open_connections=native["uncapped_open_connections"],
                delta_only=True, parent_preparation_independently_audited=False,
                electrical_performance_qualified=False, physical_stack_accepted=False,
                PCB_routed=False, fabrication_released=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check()
    path = OUT / "surface-delta-review.json"
    if args.check:
        assert result == json.loads(path.read_text())
    else:
        with path.open("x") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    print(result["added_surface_joins"], "native-verified surface joins;", result["uncapped_open_connections"], "opens; fabrication unreleased")
