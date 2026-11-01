"""Actual native via/reference-plane check on the clip-compatible successor."""

import hashlib
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def main():
    path = ROOT / "fan_power_health.kicad_pcb"
    board = pcbnew.LoadBoard(str(path))
    vias = [t for t in board.GetTracks() if isinstance(t, pcbnew.PCB_VIA)]
    assert vias and all(v.GetDrill() >= pcbnew.FromMM(.3) and v.GetWidth(pcbnew.F_Cu) >= pcbnew.FromMM(.65) for v in vias)
    assert all(v.GetFrontTentingMode() == pcbnew.TENTING_MODE_TENTED and v.GetBackTentingMode() == pcbnew.TENTING_MODE_TENTED for v in vias)
    assert not [t for t in board.GetTracks() if not isinstance(t, pcbnew.PCB_VIA) and t.GetLayer() == pcbnew.In1_Cu]
    board.BuildConnectivity()
    grounds = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == "/GND":
                assert any(isinstance(t, pcbnew.ZONE) and t.GetLayer() == pcbnew.In1_Cu
                           for t in board.GetConnectivity().GetConnectedItems(pad)), (fp.GetReference(), pad.GetNumber())
                grounds.append([fp.GetReference(), pad.GetNumber()])
    report = dict(source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  PCB_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  actual_GND_pads_connected_to_actual_In1=grounds, vias=len(vias),
                  via_minimum_diameter_mm=.65, via_minimum_drill_mm=.3,
                  all_front_back_tented=True, In1_signal_tracks=0,
                  physical_qualified=False, PDN_qualified=False, fabrication_released=False)
    (ROOT / "native-reference-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(len(grounds), "GNDpads attachedactualIn1;", len(vias), "conventionaltentedvias;0In1signaltracks")


if __name__ == "__main__":
    main()
