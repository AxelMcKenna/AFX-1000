"""Confirm proposed two-pad passive moves with KiCad's native transform."""
import argparse
import json
from pathlib import Path
import pcbnew
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    assert all(all(c.isalnum() or c in '-_' for c in n) for n in [args.plan, args.output])
    base = STAGING / 'two-board-power-permission-native-04'
    plan = STAGING / args.plan / 'placement.json'
    out = STAGING / args.output
    assert not out.exists()
    board = pcbnew.LoadBoard(str(base / 'power_protection.kicad_pcb'))
    data = json.loads(plan.read_text())
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    records = []
    for ref, (xy, rotation, flip) in data['moves'].items():
        f = fps[ref]
        angle = f.GetOrientationDegrees()
        assert len(list(f.Pads())) == 2
        assert all(not p.GetDrillSize().x and not p.GetDrillSize().y for p in f.Pads())
        if flip:
            f.Flip(f.GetPosition(), False)
        f.SetOrientationDegrees((angle + rotation) % 360)
        f.SetPosition(pcbnew.VECTOR2I(round(xy[0] * 1e6), round(xy[1] * 1e6)))
        records.append(dict(ref=ref, side=board.GetLayerName(f.GetLayer()),
            position_mm=xy, angle_degrees=f.GetOrientationDegrees(),
            pads=[dict(pin=p.GetNumber(), net=p.GetNetname(),
                xy=[pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)]) for p in f.Pads()]))
    out.mkdir()
    path = out / 'native-poses.kicad_pcb'
    pcbnew.SaveBoard(str(path), board)
    sources = [Path(__file__), plan, base / 'power_protection.kicad_pcb']
    report = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
        artifact_sha256={path.name: sha(path)}, native_version=pcbnew.GetBuildVersion(),
        poses=records, only_declared_footprints_to_be_imported=True,
        retained_copper_not_rerouted_in_pose_fixture=True, fabrication_released=False)
    (out / 'poses.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(poses=len(records), flips=sum(v[2] for v in data['moves'].values()))))


if __name__ == '__main__':
    run()
