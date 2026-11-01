"""Read-only native uncapped airwire count and input/filled track-net equality."""

import argparse
import hashlib
import json
from pathlib import Path

import pcbnew


def tracks(board):
    result = {}
    for item in board.GetTracks():
        row = dict(
            kind=item.GetClass(),
            net=item.GetNetname().lstrip("/"),
            width_nm=(
                [
                    item.GetWidth(board.GetLayerID(n))
                    for n in ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")
                ]
                if item.GetClass() == "PCB_VIA"
                else item.GetWidth()
            ),
            start_nm=[item.GetStart().x, item.GetStart().y],
            end_nm=[item.GetEnd().x, item.GetEnd().y],
            layers=list(item.GetLayerSet().Seq()),
        )
        if item.GetClass() == "PCB_VIA":
            row["drill_nm"] = item.GetDrillValue()
        result[item.m_Uuid.AsString()] = row
    return result


def check(source, filled, drc, output):
    source, filled, drc, output = map(Path, (source, filled, drc, output))
    before = pcbnew.LoadBoard(str(source))
    b = pcbnew.LoadBoard(str(filled))
    a, z = tracks(before), tracks(b)
    differences = [
        dict(uuid=u, source=a.get(u), filled=z.get(u))
        for u in sorted(set(a) | set(z))
        if a.get(u) != z.get(u)
    ]
    b.BuildConnectivity()
    c = b.GetConnectivity()
    c.RecalculateRatsnest()
    actual = c.GetUnconnectedCount(False)
    raw = json.loads(drc.read_text())
    reported = len(raw["unconnected_items"])
    counts = {}
    for row in raw["violations"]:
        k = row["type"] + ":" + row["severity"]
        counts[k] = counts.get(k, 0) + 1
    inputs = [source, filled, drc, Path(__file__)]
    report = dict(
        source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        native_version=pcbnew.GetBuildVersion(),
        method="Load filled PCB; BuildConnectivity; GetConnectivity.RecalculateRatsnest; GetUnconnectedCount(False)",
        uncapped_unconnected_count=actual,
        raw_reported_unconnected_count=reported,
        reported_count_equals_native_uncapped=actual == reported,
        track_and_via_geometry_and_net_differences_after_native_fill=differences,
        source_track_via_geometry_and_nets_preserved=not differences,
        raw_violation_counts=counts,
        known_cli_DRC_cap_caveat="KiCad10.0.7 DRC report has per-type caps; all-track-errors does not remove them. Uncapped connectivity is independently obtained here.",
        no_source_or_filled_PCB_written=True,
        physical_qualified=False,
    )
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("uncapped", actual, "reported", reported, "track/via differences", len(differences), flush=True)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("source", "filled", "drc", "output"):
        p.add_argument(n, type=Path)
    a = p.parse_args()
    check(a.source, a.filled, a.drc, a.output)
