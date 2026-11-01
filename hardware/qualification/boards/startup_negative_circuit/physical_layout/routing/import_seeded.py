"""Bounded seeded-router import, preserving a rejected result for native review."""

import faulthandler
import hashlib
import importlib.util
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "power-seeded-six-layer"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def copper(board):
    rows = []
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            rows.append(("via", t.GetPosition().x, t.GetPosition().y,
                         t.GetWidth(pcbnew.F_Cu), t.GetDrillValue(), t.GetNetname()))
        else:
            ends = sorted([(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)])
            rows.append(("track", *ends[0], *ends[1], t.GetWidth(), t.GetLayer(), t.GetNetname()))
    return sorted(rows)


def main():
    faulthandler.enable()
    output = WORK / "output.kicad_pcb"
    assert not output.exists()
    original = WORK / "output.ses"
    text = original.read_text()
    assert text.count("(component \n") == 1
    adapted = WORK / "adapted-output.ses"
    assert not adapted.exists()
    adapted.write_text(text.replace("(component \n", '(component ""\n'))
    # Reuse the explicit pose/grid/drill checks of the first import, without
    # changing its source or evidence. Its WORK is overridden only in memory.
    spec = importlib.util.spec_from_file_location("first_import", ROOT.parent / "import_route.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.WORK = WORK
    module.main()
    source = pcbnew.LoadBoard(str(WORK / "input.kicad_pcb"))
    result = pcbnew.LoadBoard(str(output))
    before, after = copper(source), copper(result)
    # Native importer may split/merge or round the original protected paths.
    # Record exact discrepancies; do not silently declare equivalent copper.
    missing = [r for r in before if r not in after]
    result.BuildConnectivity()
    c = result.GetConnectivity()
    c.RecalculateRatsnest()
    (WORK / "seed-review.json").write_text(json.dumps(dict(
        source_PCB_sha256=sha(WORK / "input.kicad_pcb"),
        output_PCB_sha256=sha(output), importer_sha256=sha(ROOT.parent / "import_route.py"),
        driver_sha256=sha(Path(__file__)), original_session_sha256=sha(original),
        adapted_session_sha256=sha(adapted), original_literal_objects=len(before),
        result_objects=len(after), literal_objects_missing_exactly=missing,
        exact_literal_objects_retained=not missing,
        uncapped_native_missing_connections=c.GetUnconnectedCount(False),
        native_DRC_required=True, adopted=False, physical_qualified=False,
        fabrication_released=False), indent=2) + "\n")


if __name__ == "__main__":
    main()
