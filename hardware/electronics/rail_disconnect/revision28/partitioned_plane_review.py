"""Independent native integer union check of DSN convex filled-plane pieces."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import pcbnew

from ...common.sexpr import first, read_sexpr
from .native_force_compare import union
from .select_native_open_nets import span


def main(workspace, filled):
    workspace, filled = Path(workspace), Path(filled)
    meta = json.loads((workspace / "export.json").read_text())
    dsn = workspace / meta["dsn_filename"]
    assert hashlib.sha256(dsn.read_bytes()).hexdigest() == meta["dsn_sha256"]
    board = pcbnew.LoadBoard(str(filled))
    assert hashlib.sha256(filled.read_bytes()).hexdigest() == meta["actual_plane_source_sha256"]
    text = dsn.read_text()
    shapes = {}
    for match in re.finditer(r"(?m)^[ \t]*\(plane\b", text):
        start, end = span(text, match.end() - len("(plane"))
        node = read_sexpr(text[start:end])
        assert len(node) == 3, "Require a plain convex piece without windows/other modifiers"
        polygon = first(node, "polygon")
        assert str(polygon[2]) == "0"
        key = (str(node[1]).lstrip("/"), str(polygon[1]))
        shape = shapes.setdefault(key, pcbnew.SHAPE_POLY_SET())
        shape.NewOutline()
        values = list(map(float, polygon[3:]))
        for i in range(0, len(values), 2):
            x, y = values[i] * 1000, -values[i + 1] * 1000
            assert abs(x - round(x)) < 0.001 and abs(y - round(y)) < 0.001
            shape.Append(round(x), round(y))
    rows = []
    for (net, layer), pieces in sorted(shapes.items()):
        native = union(board, net, board.GetLayerID(layer))
        actual = pcbnew.SHAPE_POLY_SET()
        actual.BooleanAdd(pieces)
        lost, gained, control = (pcbnew.SHAPE_POLY_SET() for i in range(3))
        lost.BooleanSubtract(native, actual)
        gained.BooleanSubtract(actual, native)
        control.BooleanSubtract(native, native)
        rows.append(
            dict(
                net=net,
                layer=layer,
                source_area_mm2=native.Area() / 1e12,
                emitted_union_area_mm2=actual.Area() / 1e12,
                lost_area_mm2=lost.Area() / 1e12,
                gained_area_mm2=gained.Area() / 1e12,
                source_self_subtraction_control_mm2=control.Area() / 1e12,
                matches_native_within_self_control=(
                    lost.Area() <= control.Area() + 1e4 and gained.Area() <= control.Area() + 1e4
                ),
            )
        )
    expected = {
        (z.GetNetname().lstrip("/"), board.GetLayerName(layer))
        for z in board.Zones()
        if not z.GetIsRuleArea()
        for layer in z.GetLayerSet().CuStack()
        if z.GetFilledPolysList(layer).Area() > 0
    }
    assert expected == set(shapes), (
        "An actual native filled net/layer is missing or invented",
        expected - set(shapes),
        set(shapes) - expected,
    )
    report = dict(
        dsn_sha256=meta["dsn_sha256"],
        source_filled_sha256=meta["actual_plane_source_sha256"],
        verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        rows=rows,
        all_native_filled_layers_covered=True,
        all_native_unions_match=all(r["matches_native_within_self_control"] for r in rows),
        numerical_area_allowance_above_self_control_mm2=1e-8,
        native_pcb_changed=False,
        physical_qualified=False,
    )
    (workspace / "native-convex-plane-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Native union review:", report["all_native_unions_match"], "net/layers", len(rows))
    assert report["all_native_unions_match"], "Convex plane union differs from actual native copper"


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    p.add_argument("filled")
    args = p.parse_args()
    main(args.workspace, args.filled)
