"""Native actual-copper neck geometry; no resistance/ampacity certification.

Read only the frozen supported board. Union native fills and actual primitive
polygons in a bounded region. A thin cut between the actual H4/H9 metal
exclusions tests local bypass topology. Cross sections intersect native integer
polygons, including holes; they are geometric widths, not current ratings.
"""

import hashlib
import json
import math
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
BASE = ROOT
PCB = BASE / "generated/filled.kicad_pcb"
EXPECTED = json.loads((ROOT / "generated/native.json").read_text())["artifact_sha256"][
    str(PCB.relative_to(ROOT.parents[5]))
]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def polygon(points):
    p = pcbnew.SHAPE_POLY_SET()
    p.NewOutline()
    for x, y in points:
        p.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    p.Simplify()
    return p


def component(p, xy):
    v = pcbnew.VECTOR2I(pcbnew.FromMM(xy[0]), pcbnew.FromMM(xy[1]))
    return [i for i in range(p.OutlineCount()) if p.Contains(v, i)]


def cross_section(p, a, u, low, high):
    # Solve a+t*u against every actual contour edge; midpoint parity is then
    # evaluated by native Contains, avoiding assumptions about contour winding.
    hits = [low, high]
    for i in range(p.OutlineCount()):
        contours = [p.COutline(i)] + [p.CHole(i, j) for j in range(p.HoleCount(i))]
        for c in contours:
            for k in range(c.PointCount()):
                q, r = c.CPoint(k), c.CPoint((k + 1) % c.PointCount())
                q = (q.x / 1e6, q.y / 1e6)
                r = (r.x / 1e6, r.y / 1e6)
                e = (r[0] - q[0], r[1] - q[1])
                w = (q[0] - a[0], q[1] - a[1])
                den = u[0] * e[1] - u[1] * e[0]
                if abs(den) < 1e-14:
                    continue
                t = (w[0] * e[1] - w[1] * e[0]) / den
                s = (w[0] * u[1] - w[1] * u[0]) / den
                if -1e-9 <= s <= 1 + 1e-9 and low < t < high:
                    hits.append(t)
    hits = sorted(set(round(t, 10) for t in hits))
    intervals = []
    for lo, hi in zip(hits, hits[1:]):
        m = (lo + hi) / 2
        if hi - lo > 1e-8 and component(p, (a[0] + m * u[0], a[1] + m * u[1])):
            intervals.append([lo, hi])
    return {"intervals_mm": intervals, "total_width_mm": sum(y - x for x, y in intervals)}


def run():
    assert sha(PCB) == EXPECTED
    b = pcbnew.LoadBoard(str(PCB))
    assert b.GetCopperLayerCount() == 4
    roi = polygon([(247.5, 146.5), (264, 146.5), (264, 165), (247.5, 165)])
    a = (246.0, 161.0)
    end = (252.0, 150.2)
    d = math.dist(a, end)
    u = ((end[0] - a[0]) / d, (end[1] - a[1]) / d)
    v = (-u[1], u[0])
    half = 0.001
    cut = polygon(
        [
            (a[0] + half * v[0], a[1] + half * v[1]),
            (end[0] + half * v[0], end[1] + half * v[1]),
            (end[0] - half * v[0], end[1] - half * v[1]),
            (a[0] - half * v[0], a[1] - half * v[1]),
        ]
    )
    top_cut = polygon([(251.999, 148), (252.001, 148), (252.001, 150.2), (251.999, 150.2)])
    rows = []
    for lname in ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]:
        layer = b.GetLayerID(lname)
        for net in ["5V_DIG", "AGND"]:
            cu = pcbnew.SHAPE_POLY_SET()
            for z in b.Zones():
                if not z.GetIsRuleArea() and z.IsOnLayer(layer) and z.GetNetname().lstrip("/") == net:
                    cu.BooleanAdd(z.GetFilledPolysList(layer))
            for obj in list(b.GetTracks()) + [pad for fp in b.GetFootprints() for pad in fp.Pads()]:
                if obj.IsOnLayer(layer) and obj.GetNetname().lstrip("/") == net:
                    p = pcbnew.SHAPE_POLY_SET()
                    obj.TransformShapeToPolygon(p, layer, 0, pcbnew.FromMM(0.001), pcbnew.ERROR_INSIDE)
                    cu.BooleanAdd(p)
            cu.BooleanIntersection(roi)
            cu.Simplify()
            source = (259.4, 158 if net == "5V_DIG" else 162)
            west = (247.6, 154)
            sc, wc = component(cu, source), component(cu, west)
            before = bool(set(sc) & set(wc))
            after = pcbnew.SHAPE_POLY_SET(cu)
            after.BooleanSubtract(cut)
            after.Simplify()
            sac, wac = component(after, source), component(after, west)
            top_only = pcbnew.SHAPE_POLY_SET(cu)
            top_only.BooleanSubtract(top_cut)
            top_only.Simplify()
            both = pcbnew.SHAPE_POLY_SET(after)
            both.BooleanSubtract(top_cut)
            both.Simplify()
            top_section = cross_section(cu, (252, 148), (0, 1), 0, 2.2)
            top_connected = bool(set(component(top_only, source)) & set(component(top_only, west)))
            both_connected = bool(set(component(both, source)) & set(component(both, west)))
            section = cross_section(cu, a, u, 0, d)
            vertical = []
            for k in range(821):
                x = 248 + k * 0.01
                s = cross_section(cu, (x, 146.5), (0, 1), 0, 18.5)
                vertical.append({"x_native_mm": round(x, 2), **s})
            rows.append(
                dict(
                    layer=lname,
                    net=net,
                    area_in_roi_mm2=cu.Area() / 1e12,
                    source_probe_native_mm=source,
                    west_probe_native_mm=west,
                    probes_connected_before_cut=before,
                    probes_connected_after_cut=bool(set(sac) & set(wac)),
                    source_component_indices_before=sc,
                    west_component_indices_before=wc,
                    centre_line_actual_copper=section,
                    new_top_corridor_actual_copper=top_section,
                    probes_connected_after_top_cut_only=top_connected,
                    probes_connected_after_both_cuts=both_connected,
                    vertical_sections=vertical,
                )
            )
    ports = []
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname().lstrip("/") == "5V_DIG":
                ports.append(
                    {
                        "ref": fp.GetReference(),
                        "pin": pad.GetNumber(),
                        "native_mm": [pad.GetPosition().x / 1e6, pad.GetPosition().y / 1e6],
                    }
                )
    report = dict(
        method=__doc__,
        native_version=pcbnew.GetBuildVersion(),
        source_filled_pcb=str(PCB.relative_to(ROOT.parents[4])),
        source_filled_pcb_sha256=sha(PCB),
        source_code_sha256=sha(Path(__file__)),
        roi_native_mm=[247.5, 146.5, 264, 165],
        metal_centre_line_native_mm=[a, end],
        centre_separation_mm=d,
        topology_cut_width_mm=2 * half,
        top_cut_axis_native_mm=[[252, 148], [252, 150.2]],
        actual_top_bypass_added=False,
        parent_PDN_inherited=False,
        actual_5V_DIG_pad_nodes=ports,
        rows=rows,
        polygon_shape_error_mm=0.001,
        physical_qualified=False,
        ampacity_qualified=False,
        fabrication_released=False,
        full_PDN_solved=False,
    )
    (ROOT / "generated/native-neck.json").write_text(json.dumps(report, indent=2) + "\n")
    assert sha(PCB) == EXPECTED
    for r in rows:
        if r["centre_line_actual_copper"]["total_width_mm"]:
            print(
                r["layer"],
                r["net"],
                r["centre_line_actual_copper"],
                r["probes_connected_before_cut"],
                r["probes_connected_after_cut"],
            )
    active = [row for row in rows if row["centre_line_actual_copper"]["total_width_mm"] > 0]
    assert {(row["layer"], row["net"]) for row in active} == {
        ("F.Cu", "5V_DIG"),
        ("In1.Cu", "AGND"),
        ("In2.Cu", "5V_DIG"),
        ("B.Cu", "5V_DIG"),
    }
    for row in active:
        assert row["probes_connected_before_cut"] and not row["probes_connected_after_cut"]
        assert row["probes_connected_after_top_cut_only"] and not row["probes_connected_after_both_cuts"]
        assert row["new_top_corridor_actual_copper"]["total_width_mm"] == 0
        print("ACCESSGATE", row["layer"], row["net"], row["centre_line_actual_copper"])
    print("PORTS", ports)


if __name__ == "__main__":
    run()
