"""Reroute RAW5 locally around real clip keepouts; no part/width reduction."""

import hashlib
import json
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point(p):
    return (round(p.x / 1e6, 5), round(p.y / 1e6, 5))


def xy(p):
    return pcbnew.VECTOR2I(*(pcbnew.FromMM(v) for v in p))


def main():
    assert not (ROOT / "handoff.json").exists()
    path = ROOT / "fan_power_health.kicad_pcb"
    history = ROOT / "history/clip-keepout-force-conflict"
    history.mkdir(parents=True, exist_ok=False)
    for name in ["fan_power_health.kicad_pcb", "construction.json", "drc-first.json", "drc-first.log"]:
        shutil.copyfile(ROOT / name, history / name)
    manager = pcbnew.GetSettingsManager()
    project = ROOT / "fan_power_health.kicad_pro"
    assert manager.LoadProject(str(project))
    board = pcbnew.LoadBoard(str(path))
    board.SetProject(manager.GetProject(str(project)))
    poses = {f.GetReference(): (f.GetPosition().x, f.GetPosition().y,
                              f.GetOrientationDegrees(), f.IsFlipped(), f.GetValue())
             for f in board.GetFootprints()}
    moves = {(18.2, 1.9): (18.2, 2.4), (18.2, 36.6): (18.2, 35.6)}
    changed, removed = [], []
    via_count = 0
    for item in list(board.GetTracks()):
        if item.GetNetname() != "/FAN5V_IN":
            continue
        if isinstance(item, pcbnew.PCB_VIA):
            old = point(item.GetPosition())
            if old in moves:
                changed.append(dict(role="via", old_mm=old, new_mm=moves[old],
                                    diameter_mm=item.GetWidth(pcbnew.F_Cu) / 1e6,
                                    drill_mm=item.GetDrillValue() / 1e6))
                item.SetPosition(xy(moves[old]))
                via_count += 1
            continue
        a, b = point(item.GetStart()), point(item.GetEnd())
        if item.GetLayer() == pcbnew.B_Cu and {a, b} == {(25., 36.6), (18.2, 36.6)}:
            assert item.GetWidth() == pcbnew.FromMM(1.)
            removed.append(dict(layer="B.Cu", old_mm=[a, b], width_mm=1.))
            board.Remove(item)
            continue
        for end, old in [("start", a), ("end", b)]:
            if old in moves:
                changed.append(dict(role="track_" + end, layer=board.GetLayerName(item.GetLayer()),
                                    old_mm=old, new_mm=moves[old], width_mm=item.GetWidth() / 1e6))
                (item.SetStart if end == "start" else item.SetEnd)(xy(moves[old]))
    assert via_count == 2 and len(removed) == 1
    new_path = [(18.2, 35.6), (21.2, 35.6), (22.2, 36.6), (25., 36.6)]
    for a, b in zip(new_path, new_path[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(xy(a))
        track.SetEnd(xy(b))
        track.SetLayer(pcbnew.B_Cu)
        track.SetWidth(pcbnew.FromMM(1.))
        track.SetNet(board.FindNet("/FAN5V_IN"))
        board.Add(track)
    assert {f.GetReference(): (f.GetPosition().x, f.GetPosition().y,
                              f.GetOrientationDegrees(), f.IsFlipped(), f.GetValue())
            for f in board.GetFootprints()} == poses
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(path), board)
    report = dict(scope="RAW5 trunk repair for actual clip isolation; original FPC01 remains sealed",
                  source_script_sha256=sha(Path(__file__)), previous_pcb_sha256=sha(history / path.name),
                  output_pcb_sha256=sha(path), changed_endpoints_and_vias=changed,
                  removed_tracks=removed, added_B_Cu_1mm_path=new_path,
                  all84_component_poses_values_sides_unchanged=True, track_or_via_dimensions_reduced=False,
                  original_critical_RAW5_geometry_inherited=False, fresh_native_DRC_required=True,
                  new_force_copper_IR_and_source_current_qualified=False,
                  physical_qualified=False, fabrication_released=False)
    (ROOT / "raw-trunk-repair.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Moved2RAW5vias and rerouted1mmBtrunk; original0.5/0.2mmbranches retained; nativeDRC required")


if __name__ == "__main__":
    main()
