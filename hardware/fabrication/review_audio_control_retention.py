"""Review inherited control and private timing witnesses on an additive audio successor."""

import json
import shutil
import sys
from pathlib import Path

from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes


def review(source, output, expected_joins, entry):
    assert sys.platform == "linux", "Mac CAD remains disabled"
    import pcbnew

    from hardware.fabrication import capture_board

    dest = output / "additional-terminal-review.json"
    assert not dest.exists()
    applied = output / "applied-additional-native-review.py.txt"
    assert not applied.exists()
    shutil.copyfile(Path(__file__), applied)
    inputs = [applied, Path(__file__), entry, Path(capture_board.__file__), source / "terminal-connectivity-review.json", source / "additional-terminal-review.json",
              output / "audio_core.kicad_pcb", output / "distribution-construction.json", output / "terminal-connectivity-review.json",
              output / "placement-native-review.json", output / "drc.json", output / "erc.json"]
    before = relative_hashes(inputs)
    drc = json.loads((output / "drc.json").read_text())
    erc = json.loads((output / "erc.json").read_text())
    assert drc["violations"] == [] and drc["ignored_checks"] == erc["ignored_checks"] == []
    assert drc["schematic_parity"] == [dict(description="Missing footprint U201 (ES9292QPRO)", items=[], severity="warning", type="missing_footprint")]
    assert not any(s["violations"] for s in erc["sheets"])
    board = pcbnew.LoadBoard(str(output / "audio_core.kicad_pcb"))
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    conn.RecalculateRatsnest()
    pads = {(fp.GetReference(), p.GetNumber()): p for fp in board.GetFootprints() for p in fp.Pads() if p.GetNumber()}

    def connected(left, right):
        p, q = pads[tuple(left)], pads[tuple(right)]
        assert p.GetNetname() == q.GetNetname()
        return p == q or q.m_Uuid.AsString() in {o.m_Uuid.AsString() for o in conn.GetConnectedItems(p)}

    parent = json.loads((source / "terminal-connectivity-review.json").read_text())
    inherited = json.loads((source / "additional-terminal-review.json").read_text())
    controls = []
    for row in inherited["retained_global_control_witnesses"]+parent["new_route_witnesses"]:
        contacts = [dict(p, native_connected=connected([p["ref"], p["pin"]], row["reference_terminal"])) for p in row["contacts"]]
        assert all(p["native_connected"] for p in contacts)
        controls.append(dict(row, contacts=contacts))
    assert len(controls) == expected_joins
    retained_timing = [dict(r, native_connected=connected(*r["endpoints"])) for r in
                       inherited.get("retained_private_timing_connections", [])+
                       ([inherited["private_timing_connection"]] if "private_timing_connection" in inherited else [])]
    assert all(r["native_connected"] for r in retained_timing)
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
    pad_capture = output / "current-native-pads.json"
    pad_capture.write_text(json.dumps(dict(source_sha256=before, native_version=pcbnew.GetBuildVersion(),
                                           objects=objects, fabrication_released=False), separators=(",", ":"))+"\n")
    before.update(relative_hashes([pad_capture]))
    opens = conn.GetUnconnectedCount(False)
    assert opens == len(drc["unconnected_items"])
    result = dict(source_sha256=before, native_version=pcbnew.GetBuildVersion(), retained_global_control_witnesses=controls,
                  retained_private_timing_connections=retained_timing, uncapped_open_connections=opens,
                  fabrication_released=False)
    dest.write_text(json.dumps(result, indent=2)+"\n")
    print("Retained", expected_joins, "earlier global joins and", len(retained_timing), "private timing pairs; opens", opens)

