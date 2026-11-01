"""Optional independent KiCad reader; no PCB mutation and no solver dependency."""

import hashlib
import json
import platform
from pathlib import Path


def main():
    import pcbnew
    import wx

    app = wx.App(False)
    root = Path(__file__).resolve().parent
    pcb = root.parent / "u102/stronger/sources/power_p03.kicad_pcb"
    board = pcbnew.LoadBoard(str(pcb))
    rows = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetNetname().lstrip("/") != "AGND":
                continue
            centre = pcbnew.ToMM(pad.GetPosition())
            if not 118 <= centre[0] <= 134 or not 113 <= centre[1] <= 129:
                continue
            bounds = pad.GetBoundingBox()
            rows.append(
                dict(
                    reference=footprint.GetReference(),
                    pad=pad.GetNumber(),
                    footprint_angle_degrees=footprint.GetOrientationDegrees(),
                    pad_absolute_angle_degrees=pad.GetOrientationDegrees(),
                    centre_mm=list(pcbnew.ToMM(pad.GetPosition())),
                    unrotated_size_mm=list(pcbnew.ToMM(pad.GetSize())),
                    world_bbox_size_mm=[bounds.GetWidth() / 1e6, bounds.GetHeight() / 1e6],
                )
            )
    report = dict(
        pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
        reader_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        kicad_version=pcbnew.GetBuildVersion(),
        python_version=platform.python_version(),
        method="Unmodified captured PCB loaded via native pcbnew with wx.App; read-only PAD orientation and bounding boxes",
        rows=sorted(rows, key=lambda r: (r["reference"], r["pad"])),
        physical_validation=False,
    )
    (root / "sources/u102-native-pad-orientation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Saved", len(rows), "native AGND pad records")
    app.Destroy()


if __name__ == "__main__":
    main()
