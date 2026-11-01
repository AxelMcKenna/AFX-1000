"""Export actual filled force copper as DSN obstacles, without changing a PCB.

Keepout windows follow Freerouting 2.5.0's io/specctra/parser/Shape.java.
All protected force routes must already be locked. AGND remains withdrawable.
Native filled-copper subtraction is still mandatory after a routed candidate.
"""

import math

from hardware.electronics.rail_disconnect.revision28.native_contract_compare import compare
from hardware.electronics.rail_disconnect.revision28.native_force_compare import FORCE_NETS, LAYERS, union


def contour(chain):
    return [(chain.CPoint(i).x, chain.CPoint(i).y) for i in range(chain.PointCount())]


def area(points):
    # Shift before the shoelace sum to avoid cancellation from absolute PCB XY.
    x0, y0 = points[0]
    p = [(x - x0, y - y0) for x, y in points]
    return abs(math.fsum(x * yy - xx * y for (x, y), (xx, yy) in zip(p, p[1:] + p[:1]))) / 2e12


def polygon(layer, points):
    assert len(points) >= 3
    return "(polygon %s 0 %s)" % (
        layer,
        " ".join("%.3f %.3f" % (x / 1000, -y / 1000) for x, y in points),
    )


def guards(source, filled, protected_uuids, pcbnew):
    from .freerouting_bridge import copper, sha

    original, board = pcbnew.LoadBoard(str(source)), pcbnew.LoadBoard(str(filled))
    assert copper(original, pcbnew) == copper(board, pcbnew), "Force fill input changed routed copper"
    contract = compare(source, filled)
    assert contract["contracts_equal"], "Force fill input changed the native board contract"
    assert all(
        t.m_Uuid.AsString() in protected_uuids
        for t in original.GetTracks()
        if t.GetNetname().lstrip("/") in FORCE_NETS
    ), "Every existing force track/via must remain locked"
    shapes, rows = [], []
    for net in sorted(FORCE_NETS):
        net_area = 0
        for name in LAYERS:
            source_shape = union(board, net, board.GetLayerID(name))
            if not source_shape.OutlineCount():
                continue
            # Router coordinates are coarser than native nm. A routing-only
            # 1um expansion removes near-touching sub-grid seams conservatively;
            # native subtraction independently proves original copper coverage.
            shape = pcbnew.SHAPE_POLY_SET()
            shape.BooleanAdd(source_shape)
            shape.Inflate(1000, pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, 10, True)
            lost, self_control = pcbnew.SHAPE_POLY_SET(), pcbnew.SHAPE_POLY_SET()
            lost.BooleanSubtract(source_shape, shape)
            self_control.BooleanSubtract(source_shape, source_shape)
            assert lost.Area() <= self_control.Area() + 1e4, "Guard expansion lost source copper"
            outlines, holes, emitted_area = shape.OutlineCount(), 0, 0
            for index in range(outlines):
                outside = contour(shape.COutline(index))
                windows = [contour(shape.CHole(index, i)) for i in range(shape.HoleCount(index))]
                holes += len(windows)
                emitted_area += area(outside) - math.fsum(area(p) for p in windows)
                shapes.append(
                    '(keepout "force-%s-%s-%d" %s %s)'
                    % (
                        net,
                        name,
                        index,
                        polygon(name, outside),
                        " ".join("(window %s)" % polygon(name, p) for p in windows),
                    )
                )
            native_area = shape.Area() / 1e12
            assert math.isclose(emitted_area, native_area, rel_tol=1e-10, abs_tol=1e-7), (
                "Emitted force outline/window area differs from native union",
                net,
                name,
                emitted_area,
                native_area,
            )
            net_area += native_area
            if outlines:
                rows.append(
                    dict(
                        net=net,
                        layer=name,
                        outlines=outlines,
                        windows=holes,
                        native_area_mm2=native_area,
                        original_force_area_mm2=source_shape.Area() / 1e12,
                        original_copper_not_covered_mm2=lost.Area() / 1e12,
                        source_self_subtraction_control_mm2=self_control.Area() / 1e12,
                        emitted_area_mm2=emitted_area,
                    )
                )
        assert net_area > 0, "Missing actual filled force copper: " + net
    return "\n".join(shapes), dict(
        source_pcb_sha256=sha(source),
        filled_pcb_sha256=sha(filled),
        source_fill_contract=contract,
        rows=rows,
        keepout_count=len(shapes),
        coordinate_conversion="Native nm to DSN um at 0.001um precision; Y inverted",
        conservative_routing_only_expansion_um=1,
        agnd_converted_to_keepout=False,
        physical_qualified=False,
        routed_force_copper_preserved=False,
    )
