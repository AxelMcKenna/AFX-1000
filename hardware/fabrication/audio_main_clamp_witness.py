"""Confirm the extra V5 clamp-pad connection made by the local supply route."""

import json
import sys
from pathlib import Path

from hardware.fabrication.audio_main_local_routes import relative_hashes

OUT = Path(__file__).resolve().parent / "staging/audio-main-local-routing-03"


def run():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    import pcbnew

    pcb = OUT / "audio_core.kicad_pcb"
    board = pcbnew.LoadBoard(str(pcb))
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    conn.RecalculateRatsnest()
    pads = {(f.GetReference(), p.GetNumber()): p for f in board.GetFootprints() for p in f.Pads()}
    p, q = pads[("D102", "2")], pads[("U102", "3")]
    assert p.GetNetname() == q.GetNetname() == "V5_REG"
    assert q.m_Uuid.AsString() in {v.m_Uuid.AsString() for v in conn.GetConnectedItems(p)}
    result = dict(source_sha256=relative_hashes([Path(__file__), pcb, OUT / "placement-native-review.json"]),
                  native_version=pcbnew.GetBuildVersion(), ref="D102", pin="2", owner="U102", owner_pin="3",
                  net="V5_REG", native_connected=True, uncapped_open_connections=conn.GetUnconnectedCount(False),
                  analog_performance_and_full_routing_qualified=False, fabrication_released=False)
    with (OUT / "additional-clamp-connectivity.json").open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print("Native confirmed D102.2 V5 clamp joins U102.3; opens", result["uncapped_open_connections"])


if __name__ == "__main__":
    run()
