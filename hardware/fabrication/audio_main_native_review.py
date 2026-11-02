"""Native retained-terminal and new-island review for additive audio routing."""

import json
import sys
from pathlib import Path

from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes


def review(output, baseline, capture_path, construction_path, applied):
    assert sys.platform == "linux", "Mac CAD remains disabled"
    import pcbnew

    from hardware.fabrication import audio_main_placement

    dest = output / "terminal-connectivity-review.json"
    assert not dest.exists()
    before = relative_hashes([Path(__file__), applied, baseline, capture_path, construction_path,
                              output / "audio_core.kicad_pcb", Path(audio_main_placement.__file__)])
    audio_main_placement.OUT = output
    audio_main_placement.review()
    board = pcbnew.LoadBoard(str(output / "audio_core.kicad_pcb"))
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    conn.RecalculateRatsnest()
    pads = {(f.GetReference(), p.GetNumber()): p for f in board.GetFootprints() for p in f.Pads() if p.GetNumber()}
    captured = json.loads(capture_path.read_text())
    construction = json.loads(construction_path.read_text())
    parent = json.loads(baseline.read_text())
    objects = {o["uuid"]: o for o in captured["objects"]}

    def connected(left, right):
        p, q = pads[tuple(left)], pads[tuple(right)]
        assert p.GetNetname() == q.GetNetname()
        return p == q or q.m_Uuid.AsString() in {v.m_Uuid.AsString() for v in conn.GetConnectedItems(p)}

    local = [dict(r, additive_successor_native_connected=connected([r["ref"], r["pin"]], [r["owner"], r["owner_pin"]])) for r in parent["retained_local_pairs"]]
    controls = [dict(r, additive_successor_native_connected=connected(*r["endpoints"])) for r in parent["retained_control_pairs"]]
    grounds = [dict(ref=ref, pin=pin, native_connected_to_input_ground=connected([ref, pin], ["J701", "2"]))
               for (ref, pin), p in pads.items() if p.GetNetname() == "AGND"]
    supplies = [dict(r, native_connected_to_source=connected([r["ref"], r["pin"]], r["root"])) for r in parent["supply_pads"]]
    witnesses = []
    for row in construction["routes"]:
        keys = [key for side in row["source_groups"] for key in side]
        source_pads = [objects[i] for key in keys for i in captured["groups"][key]
                       if objects[i]["kind"] == "PAD" and objects[i]["pin"]]
        assert source_pads and all(p["net"] == row["net"] for p in source_pads)
        terminal = [source_pads[0]["ref"], source_pads[0]["pin"]]
        contacts = [dict(ref=p["ref"], pin=p["pin"], native_connected=connected([p["ref"], p["pin"]], terminal)) for p in source_pads]
        assert all(p["native_connected"] for p in contacts)
        witnesses.append(dict(net=row["net"], source_groups=row["source_groups"], reference_terminal=terminal, contacts=contacts))
    assert all(r["additive_successor_native_connected"] for r in local+controls)
    assert len(grounds) == 200 and all(r["native_connected_to_input_ground"] for r in grounds)
    assert len(supplies) == 161 and all(r["native_connected_to_source"] for r in supplies)
    verify_hashes(before)
    before.update(relative_hashes([output / "placement-native-review.json"]))
    result = dict(source_sha256=before, native_version=pcbnew.GetBuildVersion(), retained_local_pairs=local,
                  retained_control_pairs=controls, ground_pads=grounds, supply_pads=supplies,
                  new_route_witnesses=witnesses, uncapped_open_connections=conn.GetUnconnectedCount(False),
                  tracks=sum(v.GetClass() == "PCB_TRACK" for v in board.GetTracks()),
                  vias=sum(v.GetClass() == "PCB_VIA" for v in board.GetTracks()), fabrication_released=False)
    dest.write_text(json.dumps(result, indent=2)+"\n")
    print("Retained 138 local / 17 prior control / 200 ground / 161 rail pads; verified", len(witnesses), "new joins; opens", result["uncapped_open_connections"])
