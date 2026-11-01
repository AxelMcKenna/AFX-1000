"""Translate actual native filled planes to routing-only DSN polygon/windows.

KiCad's overlapping unfilled priority-zone outlines are not actual conducting
planes. This adapter changes only DSN plane blocks and its design namespace.
Native source, rules, tracks, pads and explicit force guards remain unchanged.
Freerouting 2.5.0 Plane.java/Shape.java accept polygon boundaries plus windows.
"""

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import pcbnew

from hardware.qualification.boards.freerouting_bridge import copper
from hardware.qualification.boards.freerouting_force import area, contour, polygon

from .native_contract_compare import compare
from .native_force_compare import LAYERS, union
from .select_native_open_nets import span

PRIMARY = "https://raw.githubusercontent.com/freerouting/freerouting/v2.5.0/src/main/java/app/freerouting/io/specctra/parser/"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(workspace, filled, erosion_um=0):
    workspace, filled = Path(workspace).resolve(), Path(filled).resolve()
    assert workspace.is_relative_to(Path(__file__).resolve().parent / "generated")
    assert erosion_um in (0, 1), "Only the explicit zero/exact or conservative 1um trial is supported"
    metadata_path = workspace / "export.json"
    meta = json.loads(metadata_path.read_text())
    assert not meta.get("filled_plane_adapter_sha256"), "Never replace an existing plane translation"
    source = workspace / "source" / meta["source_filename"]
    assert sha(source) == meta["source_pcb_sha256"]
    original, board = pcbnew.LoadBoard(str(source)), pcbnew.LoadBoard(str(filled))
    assert copper(original, pcbnew) == copper(board, pcbnew), "Filled source changed actual routed copper"
    semantic = compare(source, filled)
    assert semantic["contracts_equal"], "Filled source changed native board contracts"
    dsn = workspace / meta["dsn_filename"]
    assert sha(dsn) == meta["dsn_sha256"]
    text = dsn.read_text()
    ranges = [span(text, m.start() + 4) for m in re.finditer(r"(?m)^    \(plane\b", text)]
    assert ranges, "Require actual original KiCad plane definitions"
    names = sorted({z.GetNetname() for z in board.Zones() if not z.GetIsRuleArea()})
    definitions, rows = [], []
    for net in names:
        assert net and net.startswith("/"), "Require explicit native net identity"
        for layer in LAYERS:
            shape = union(board, net.lstrip("/"), board.GetLayerID(layer))
            if not shape.OutlineCount():
                continue
            original_area = shape.Area() / 1e12
            if erosion_um:
                exact = pcbnew.SHAPE_POLY_SET()
                exact.BooleanAdd(shape)
                shape.Inflate(-1000, pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, 10, True)
                gained = pcbnew.SHAPE_POLY_SET()
                gained.BooleanSubtract(shape, exact)
                control = pcbnew.SHAPE_POLY_SET()
                control.BooleanSubtract(exact, exact)
                assert gained.Area() <= control.Area() + 1e4, "Conservative routing plane gained copper"
            emitted, windows = 0, 0
            for index in range(shape.OutlineCount()):
                boundary = contour(shape.COutline(index))
                holes = [contour(shape.CHole(index, k)) for k in range(shape.HoleCount(index))]
                emitted += area(boundary) - math.fsum(area(h) for h in holes)
                windows += len(holes)
                definitions.append(
                    "    (plane %s %s %s)"
                    % (
                        json.dumps(net),
                        polygon(layer, boundary),
                        " ".join("(window %s)" % polygon(layer, h) for h in holes),
                    )
                )
            expected = shape.Area() / 1e12
            assert math.isclose(emitted, expected, rel_tol=1e-10, abs_tol=1e-7)
            rows.append(
                dict(
                    net=net,
                    layer=layer,
                    outlines=shape.OutlineCount(),
                    windows=windows,
                    native_union_area_mm2=expected,
                    exact_native_area_before_erosion_mm2=original_area,
                    conservative_routing_only_area_omitted_mm2=original_area - expected,
                    emitted_area_mm2=emitted,
                )
            )
    assert definitions
    # Preserve every non-plane byte, including original wiring/rules/keepouts.
    chunks, cursor = [], 0
    for index, (start, end) in enumerate(ranges):
        chunks.append(text[cursor:start])
        chunks.append("\n".join(definitions) if index == 0 else "")
        cursor = end
    chunks.append(text[cursor:])
    result = "".join(chunks)
    assert len(re.findall(r"\(plane\b", result)) == len(definitions)
    report = dict(
        source_pcb_sha256=sha(source),
        actual_filled_pcb_sha256=sha(filled),
        original_dsn_sha256=sha(dsn),
        native_source_fill_contract=semantic,
        original_plane_count=len(ranges),
        actual_filled_plane_count=len(definitions),
        rows=rows,
        coordinate_conversion="native nm to DSN um at 0.001um precision; inverted Y",
        conservative_routing_only_erosion_um=erosion_um,
        original_native_copper_changed=False,
        primary_sources=[PRIMARY + "Plane.java", PRIMARY + "Shape.java"],
        adapter_source_sha256=sha(Path(__file__)),
        native_pcb_changed=False,
        original_force_keepouts_and_all_nonplane_dsn_bytes_unchanged=True,
        native_findings_exempted=False,
        final_native_and_copper_checks_required=True,
        physical_qualified=False,
    )
    report_path = workspace / "filled-plane-adapter.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    (workspace / "export-before-filled-planes.json").write_text(json.dumps(meta, indent=2) + "\n")
    name = "afx-" + hashlib.sha256((meta["design_name"] + sha(report_path)).encode()).hexdigest()[:24]
    revised = workspace / (name + ".dsn")
    assert not revised.exists()
    revised.write_text(result)
    meta.update(
        design_name=name,
        dsn_filename=revised.name,
        dsn_sha256=sha(revised),
        filled_plane_adapter_sha256=sha(report_path),
        actual_plane_source_sha256=sha(filled),
    )
    metadata_path.write_text(json.dumps(meta, indent=2) + "\n")
    print(
        "Translated", len(ranges), "unfilled definitions to", len(definitions), "actual filled plane islands"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    p.add_argument("filled")
    p.add_argument("--conservative-erosion-um", type=int, default=0)
    args = p.parse_args()
    main(args.workspace, args.filled, args.conservative_erosion_um)
