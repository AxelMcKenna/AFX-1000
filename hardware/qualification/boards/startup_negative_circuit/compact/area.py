"""Actual library-courtyard inventory of the NF03C complete private schematic proposal."""

import json
from pathlib import Path

from hardware.electronics.common.sexpr import read_sexpr, children, first
from hardware.qualification.boards.startup_negative_protection.capture import sha
from .circuit import ROOT

LIB = Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints")


def inventory():
    assert not (ROOT / "handoff.json").exists(), "Immutable NF03C; create a successor"
    parts = json.loads((ROOT / "components.json").read_text())
    result = []
    for c in parts:
        lib, name = c["footprint"].split(":")
        path = LIB / (lib + ".pretty") / (name + ".kicad_mod")
        fp = read_sexpr(path.read_text())
        xy = []
        area = 0
        rectangles = 0
        edges = []
        for node in fp:
            if not isinstance(node, list) or not node or node[0] not in ("fp_rect", "fp_line", "fp_poly"):
                continue
            if not children(node, "layer") or first(node, "layer")[1] != "F.CrtYd":
                continue
            if node[0] == "fp_rect":
                a, b = first(node, "start")[1:], first(node, "end")[1:]
                pts = [
                    (float(a[0]), float(a[1])),
                    (float(b[0]), float(a[1])),
                    (float(b[0]), float(b[1])),
                    (float(a[0]), float(b[1])),
                ]
                area += abs((pts[1][0] - pts[0][0]) * (pts[2][1] - pts[1][1]))
                xy += pts
                rectangles += 1
            elif node[0] == "fp_poly":
                pts = [tuple(map(float, p[1:])) for p in children(first(node, "pts"), "xy")]
                area += abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))) / 2
                xy += pts
            else:
                a = tuple(map(float, first(node, "start")[1:]))
                b = tuple(map(float, first(node, "end")[1:]))
                edges.append((a, b))
                xy += [a, b]
        if edges:
            rest = list(edges)
            a, b = rest.pop()
            pts = [a, b]
            while rest:
                found = False
                for i, (a, b) in enumerate(rest):
                    if a == pts[-1]:
                        pts.append(b)
                        rest.pop(i)
                        found = True
                        break
                    if b == pts[-1]:
                        pts.append(a)
                        rest.pop(i)
                        found = True
                        break
                assert found, (c["ref"], "unclosed courtyard")
            assert pts[0] == pts[-1]
            area += abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:]))) / 2
        assert xy and area > 0, c["ref"]
        bbox = [min(p[0] for p in xy), min(p[1] for p in xy), max(p[0] for p in xy), max(p[1] for p in xy)]
        result.append(
            dict(
                ref=c["ref"],
                part=c["part"],
                footprint=c["footprint"],
                courtyard_area_mm2=area,
                courtyard_bbox_mm=bbox,
                library_file=str(path),
                library_sha256=sha(path),
                manufacturer_land_pattern_and_height_accepted=False,
            )
        )
    by = {}
    for p in result:
        n = p["footprint"]
        r = by.setdefault(n, dict(count=0, sum_courtyard_mm2=0))
        r["count"] += 1
        r["sum_courtyard_mm2"] += p["courtyard_area_mm2"]
    total = sum(p["courtyard_area_mm2"] for p in result)
    answer = dict(
        revision="NF03C-actual-library-footprint-inventory",
        parts=len(result),
        rows=result,
        by_footprint=by,
        sum_front_courtyard_area_mm2=total,
        area_times1p2_reference_mm2=1.2 * total,
        added_enclosure_strip_geometry_mm=[334, 31.4],
        strip_gross_floor_area_mm2=334 * 31.4,
        strip_is_allocated_usable_pcb_area=False,
        candidate_board_outline_or_placement_created=False,
        notes=[
            "Courtyard polygon areas from actual KiCad library files, not package marketing dimensions",
            "Summed courtyards are a lower-bound placement requirement, not a packed PCB or routing proof",
            "Old/current controls, fan path, posts, lead strain relief and module EMI/filter/isolation keepouts still occupy space",
            "Two TMR1-1215 modules require nominal17x7.62x11mm body plus declared manufacturer dimensional tolerances and receiving lead-seat review",
            "Existing E28 REF/inverters/sourceOV/globalfault latch are reused as explicit integration.json contracts; new E28 pin/net changes remain unimplemented",
        ],
        vertical_candidate_projection=dict(world_x_mm=[125,325],world_y_mm=184.5,world_z_mm=[6.5,34.5],receiving_board_mm=[200,28],deep_modules_world_x_requirement_mm=[160,220],all_parts_inside_face_only=True,board_or_mounts_authored=False,floor_airflow_fit_verified=False),
        feasible_fit_qualified=False,
        physical_qualified=False,
    )
    (ROOT / "generated/footprint-area.json").write_text(json.dumps(answer, indent=2) + "\n")
    print("Actual", len(result), "courtyards:", total, "mm2;1.2x", 1.2 * total)
    return answer


if __name__ == "__main__":
    inventory()
