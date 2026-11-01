"""Native pad/track copper constraints for the rejected and chosen J29 poses."""

import hashlib
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / "processor-awg18-ear-fanout-j29/processor_carrier.kicad_pcb"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inspect(path, pose):
    b = pcbnew.LoadBoard(str(path))
    f = next(f for f in b.GetFootprints() if f.GetReference() == "J29")
    if pose:
        f.SetOrientationDegrees(pose[2])
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(pose[0]), pcbnew.FromMM(pose[1])))
    rows = []
    for p in f.Pads():
        for track in b.GetTracks():
            if p.GetNetname() == track.GetNetname():
                continue
            for layer in [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]:
                if not track.IsOnLayer(layer):
                    continue
                pp = pcbnew.SHAPE_POLY_SET()
                tp = pcbnew.SHAPE_POLY_SET()
                xp = pcbnew.SHAPE_POLY_SET()
                p.TransformShapeToPolygon(
                    pp, layer, pcbnew.FromMM(0.25), pcbnew.FromMM(0.001), pcbnew.ERROR_OUTSIDE
                )
                track.TransformShapeToPolygon(tp, layer, 0, pcbnew.FromMM(0.001), pcbnew.ERROR_OUTSIDE)
                xp.BooleanIntersection(pp, tp)
                if xp.Area() > 0:
                    rows.append(
                        dict(
                            pad=p.GetNumber(),
                            pad_net=p.GetNetname(),
                            track_net=track.GetNetname(),
                            layer=b.GetLayerName(layer),
                            track_uuid=track.m_Uuid.AsString(),
                            intersection_with_pad_clearance_halo_mm2=xp.Area() / 1e12,
                        )
                    )
    return rows


def run():
    candidate = ROOT / "processor_carrier.kicad_pcb"
    before = [sha(PARENT), sha(candidate)]
    rejected = inspect(PARENT, (174, 136.5, -90))
    accepted = inspect(candidate, None)
    assert {(r["pad"], r["track_net"]) for r in rejected} == {("2", "/MCU_PERMIT"), ("3", "/BCLK")}, rejected
    assert not accepted, accepted
    assert before == [sha(PARENT), sha(candidate)]
    report = dict(
        parent_pcb_sha256=before[0],
        candidate_pcb_sha256=before[1],
        source_code_sha256=sha(Path(__file__)),
        native_version=pcbnew.GetBuildVersion(),
        rejected_pose_native_mm_degrees=[174, 136.5, -90],
        rejected_actual_foreign_track_clearance_intersections=rejected,
        chosen_pose_native_mm_degrees=[175, 134, 0],
        chosen_actual_foreign_track_clearance_intersections=accepted,
        all_foreign_routes_unchanged_required=True,
        clearance_halo_mm=0.25,
        pad_polygon_outer_error_mm=0.001,
        full_native_DRC_separate=True,
        physical_qualified=False,
    )
    (ROOT / "generated/native-constraints.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Rejected2 foreign collisions; chosen0", before[1])


if __name__ == "__main__":
    run()
