"""Replay the additive control copper and independently check native witnesses."""

import argparse
import json
import math
from pathlib import Path

from shapely.geometry import LineString

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audio_main_control_routes import (
    CONTROL_NETS,
    MAX_ENDPOINT_DISTANCE,
    MAX_PATH_LENGTH,
)
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_audio_main_ground import check as parent_check
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import Screen

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-ground-02"
OUT = ROOT / "staging/audio-main-controls-01"


def verify_board(board, construction, captured):
    parent = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    assert board[:len(parent)] == parent, "Changed parent analog copper, receiving, drills or reference plane"
    added = board[len(parent):]
    assert added and all(n[0] == "segment" for n in added), "Only surface control segments may be added"
    nodes = {str(first(n, "uuid")[1]): n for n in added}
    assert len(nodes) == len(added) == construction["added_segments"]
    names = {str(n[1]): str(n[2]) for n in children(board, "net")}
    pads = {(o["ref"], o["pin"]): o for o in captured["objects"] if o["kind"] == "PAD" and o["pin"]}
    membership = {ident: key for key, ids in captured["groups"].items() for ident in ids}
    roots = {key: key for key in captured["groups"]}
    used = set()
    screen = Screen(captured)

    def root(key):
        while roots[key] != key:
            key = roots[key]
        return key

    for row in construction["routes"]:
        net, layer = row["net"], row["layer"]
        assert net in CONTROL_NETS, "Undeclared control net"
        assert layer in ("F.Cu", "B.Cu"), "Reserved inner layer used"
        p, q = [pads[tuple(key)] for key in row["endpoints"]]
        assert p["net"] == q["net"] == net and layer in p["layers"] and layer in q["layers"]
        left, right = membership[p["uuid"]], membership[q["uuid"]]
        assert row["source_groups"] == [left, right]
        assert root(left) != root(right), "Already connected source islands counted as progress"
        assert math.dist(p["position_mm"], q["position_mm"]) <= MAX_ENDPOINT_DISTANCE
        points = row["points_mm"]
        assert math.dist(points[0], p["position_mm"]) < 1e-7 and math.dist(points[-1], q["position_mm"]) < 1e-7
        length = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
        assert 0 < length <= MAX_PATH_LENGTH and abs(length-row["length_mm"]) < 1e-7, "Control route length budget"
        assert screen.legal(net, layer, points), "Control copper violates native obstacle planning screen"
        identifiers = row["segment_uuids"]
        assert len(identifiers) == len(points)-1
        for ident, start, end in zip(identifiers, points, points[1:]):
            assert ident not in used
            n = nodes[ident]
            assert names[str(first(n, "net")[1])] == net and first(n, "layer")[1] == layer
            assert float(first(n, "width")[1]) == .2, "Control width changed"
            assert math.dist(list(map(float, first(n, "start")[1:3])), start) < 1e-6
            assert math.dist(list(map(float, first(n, "end")[1:3])), end) < 1e-6
            used.add(ident)
        roots[root(right)] = root(left)
        screen.added.append((net, layer, LineString(points)))
    assert used == nodes.keys(), "Unreviewed new copper"
    assert construction["width_mm"] == construction["clearance_mm"] == .2
    assert construction["maximum_endpoint_distance_mm"] == MAX_ENDPOINT_DISTANCE
    assert construction["maximum_path_length_mm"] == MAX_PATH_LENGTH
    assert construction["screen_margin_mm"] == .01 and construction["allowed_control_nets"] == sorted(CONTROL_NETS)
    return dict(added_control_pairs=len(construction["routes"]), added_control_tracks=len(added),
                tracks=len(children(board, "segment")), vias=len(children(board, "via")),
                all_parent_analog_copper_lands_drills_and_plane_fill_exact=True)


def verify_witnesses(report, construction):
    expected = [dict(endpoints=r["endpoints"], net=r["net"], native_connected=True) for r in construction["routes"]]
    assert report["new_control_pairs"] == expected, "Control endpoints are not all native connected"
    prior = json.loads((SOURCE / "local-connectivity-review.json").read_text())["connections"]
    assert report["retained_local_pairs"] == [dict(r, retained_native_connected=True) for r in prior], "Local analog connection lost"
    pads = json.loads((SOURCE / "native-pad-capture.json").read_text())["objects"]
    expected_keys = {(p["ref"], p["pin"]) for p in pads if p["net"] == "AGND"}
    ground = report["ground_pads"]
    assert {(p["ref"], p["pin"]) for p in ground} == expected_keys and len(ground) == 200
    assert all(p["native_connected_to_input_ground"] for p in ground), "Ground connection lost"


def check():
    parent = parent_check()
    assert parent == json.loads((SOURCE / "routing-handoff.json").read_text())
    names = ("native-inputs.json", "construction.json", "placement-native-review.json", "control-connectivity-review.json")
    reports = {name: json.loads((OUT / name).read_text()) for name in names}
    for report in reports.values():
        verify_hashes(report["source_sha256"])
    capture = reports["native-inputs.json"]
    construction = reports["construction.json"]
    native = reports["placement-native-review.json"]
    witness = reports["control-connectivity-review.json"]
    assert sha(OUT / "audio_core.kicad_pcb") == construction["candidate_PCB_sha256"]
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            assert (OUT / p.name).read_bytes() == p.read_bytes(), "Electrical source or receiving plan changed"
    proof = verify_board(read_sexpr((OUT / "audio_core.kicad_pcb").read_text()), construction, capture)
    verify_witnesses(witness, construction)
    assert witness["tracks"] == proof["tracks"] and witness["vias"] == proof["vias"] == parent["vias"]
    drc, erc = [json.loads((OUT / name).read_text()) for name in ("drc.json", "erc.json")]
    assert drc["violations"] == [] and drc["ignored_checks"] == erc["ignored_checks"] == []
    assert drc["schematic_parity"] == json.loads((SOURCE / "drc.json").read_text())["schematic_parity"]
    assert not any(s["violations"] for s in erc["sheets"]) and len(erc["sheets"]) == 7
    assert all(sha(OUT / name) == h for name, h in native["raw_report_sha256"].items())
    assert native["DRC_geometry_findings"] == native["ERC_findings"] == 0 and native["schematic_parity_findings"] == 1
    assert all(c["returncode"] == 0 for c in native["complete_native_commands"])
    opens = native["uncapped_open_connections"]
    assert opens == len(drc["unconnected_items"]) == witness["uncapped_open_connections"]
    assert opens <= parent["uncapped_open_connections"] - proof["added_control_pairs"]
    inputs = [Path(__file__), ROOT / "audio_main_control_routes.py", ROOT / "route_nf_surface.py",
              SOURCE / "routing-handoff.json"] + [OUT / name for name in names]
    result = dict(parent)
    result.update(proof)
    result.update(source_sha256=relative_hashes(inputs), uncapped_open_connections=opens,
                  retained_native_local_pairs=len(witness["retained_local_pairs"]),
                  retained_native_ground_pads=len(witness["ground_pads"]),
                  new_control_native_geometry_findings=0,
                  control_timing_coupling_EMI_and_installed_fault_qualified=False,
                  PCB_routed=False, fabrication_released=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check()
    path = OUT / "routing-handoff.json"
    if args.check:
        assert result == json.loads(path.read_text())
    else:
        with path.open("x") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    print("Audio controls:", result["added_control_pairs"], "added pairs;", result["uncapped_open_connections"], "opens")
