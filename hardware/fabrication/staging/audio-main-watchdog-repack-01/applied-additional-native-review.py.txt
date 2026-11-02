"""Native witnesses for the relocated watchdog and all earlier global controls."""

import json
import shutil
import sys
from pathlib import Path

from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-controls-02"
OUT = ROOT / "staging/audio-main-watchdog-repack-01"


def run():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    import pcbnew

    from hardware.fabrication import capture_board

    dest = OUT / "additional-terminal-review.json"
    assert not dest.exists()
    applied = OUT / "applied-additional-native-review.py.txt"
    assert not applied.exists()
    shutil.copyfile(Path(__file__), applied)
    inputs = [applied, Path(capture_board.__file__), SOURCE / "terminal-connectivity-review.json",
              OUT / "audio_core.kicad_pcb", OUT / "distribution-construction.json", OUT / "terminal-connectivity-review.json",
              OUT / "placement-native-review.json", OUT / "drc.json", OUT / "erc.json"]
    before = relative_hashes(inputs)
    drc = json.loads((OUT / "drc.json").read_text())
    erc = json.loads((OUT / "erc.json").read_text())
    assert drc["violations"] == [] and drc["ignored_checks"] == erc["ignored_checks"] == []
    assert drc["schematic_parity"] == [dict(description="Missing footprint U201 (ES9292QPRO)", items=[], severity="warning", type="missing_footprint")]
    assert not any(s["violations"] for s in erc["sheets"])
    board = pcbnew.LoadBoard(str(OUT / "audio_core.kicad_pcb"))
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    conn.RecalculateRatsnest()
    pads = {(fp.GetReference(), p.GetNumber()): p for fp in board.GetFootprints() for p in fp.Pads() if p.GetNumber()}

    def connected(left, right):
        p, q = pads[tuple(left)], pads[tuple(right)]
        assert p.GetNetname() == q.GetNetname()
        return p == q or q.m_Uuid.AsString() in {o.m_Uuid.AsString() for o in conn.GetConnectedItems(p)}

    parent = json.loads((SOURCE / "terminal-connectivity-review.json").read_text())
    controls = []
    for row in parent["new_route_witnesses"]:
        contacts = [dict(p, native_connected=connected([p["ref"], p["pin"]], row["reference_terminal"])) for p in row["contacts"]]
        assert all(p["native_connected"] for p in contacts)
        controls.append(dict(row, contacts=contacts))
    assert len(controls) == 48
    timing = dict(net="/BYPASS/CWD", endpoints=[["U601", "2"], ["C601", "1"]], native_connected=connected(["U601", "2"], ["C601", "1"]))
    assert timing["native_connected"]
    construction = json.loads((OUT / "distribution-construction.json").read_text())
    escapes = []
    for row in construction["reserved_control_escapes"]:
        pad = pads[row["ref"], row["pin"]]
        x, y = row["via"]
        vias = [o for o in conn.GetConnectedItems(pad) if o.GetClass() == "PCB_VIA" and
                o.GetPosition().x == round(x*1e6) and o.GetPosition().y == round(y*1e6)]
        assert len(vias) == 1 and pad.GetNetname() == vias[0].GetNetname() == row["net"]
        escapes.append(dict(ref=row["ref"], pin=row["pin"], net=row["net"], via_mm=row["via"], native_connected=True))
    objects = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            obj = dict(kind="PAD", ref=fp.GetReference(), pin=pad.GetNumber(), net=pad.GetNetname(),
                       position_mm=[pad.GetPosition().x/1e6, pad.GetPosition().y/1e6],
                       drill_mm=[pad.GetDrillSize().x/1e6, pad.GetDrillSize().y/1e6],
                       npth=int(pad.GetAttribute()) == int(pcbnew.PAD_ATTRIB_NPTH), layers={})
            for layer in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu"):
                lid = board.GetLayerID(layer)
                if pad.IsOnLayer(lid):
                    poly = pcbnew.SHAPE_POLY_SET()
                    pad.TransformShapeToPolygon(poly, lid, 0, pcbnew.FromMM(.001), pcbnew.ERROR_OUTSIDE)
                    poly.Simplify()
                    obj["layers"][layer] = capture_board.polygons(poly)
            objects.append(obj)
    verify_hashes(before)
    pad_capture = OUT / "current-native-pads.json"
    pad_capture.write_text(json.dumps(dict(source_sha256=before, native_version=pcbnew.GetBuildVersion(),
                                           objects=objects, fabrication_released=False), separators=(",", ":"))+"\n")
    before.update(relative_hashes([pad_capture]))
    opens = conn.GetUnconnectedCount(False)
    assert opens == len(drc["unconnected_items"])
    result = dict(source_sha256=before, native_version=pcbnew.GetBuildVersion(), retained_global_control_witnesses=controls,
                  private_timing_connection=timing, reserved_control_escapes=escapes, uncapped_open_connections=opens,
                  fabrication_released=False)
    dest.write_text(json.dumps(result, indent=2)+"\n")
    print("Retained all 48 earlier global control joins; private timing and both reserved GPIO escapes connected; opens", opens)


if __name__ == "__main__":
    run()
