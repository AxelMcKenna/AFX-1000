"""Non-native source-bound pre-routing U23/C68 geometry screen against CP01."""

import hashlib
import json
import math
import re
from pathlib import Path

from ....cad.a12.repaired import height
from ...common.sexpr import children, first, read_sexpr
from ...output_stage.check_placement import courtyard, transform

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
WORK = ROOT / "generated/u23-band-placement-work"
CTX = (
    REPO
    / "hardware/cad/a12/thermal/enlarged_base_pot/context/hardware/cad/a12/enclosure_growth/integration_repaired/generated/checks.scad"
)


def box_hit(a, b):
    return all(min(a[i + 3], b[i + 3]) - max(a[i], b[i]) > 1e-8 for i in range(3))


def circle_gap(box, centre, radius):
    return math.hypot(*[max(box[i] - centre[i], 0, centre[i] - box[i + 3]) for i in (0, 1)]) - radius


def main():
    pcb = WORK / "rail_disconnect.kicad_pcb"
    parts = WORK / "components.json"
    text = CTX.read_text()
    source_sha = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (pcb, parts, CTX, Path(__file__))
    }

    def array(name):
        return json.loads(re.search("^" + name + "=(.*);$", text, re.M).group(1))

    boards = array("ui_native_boards")
    datum = next(b[1] for b in boards if b[0] == "E28")
    assert datum == [8, 108.5, 5.0]
    posts = array("tc2_centres")
    assert posts == [[130.0871, 168.922], [93.0871, 168.9352]]
    boxes = array("ui_native_boxes")
    cylinders = array("ui_native_cylinders")
    tree = read_sexpr(pcb.read_text())
    data = {r["ref"]: r for r in json.loads(parts.read_text())}
    results = {}
    for f in children(tree, "footprint"):
        ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
        if ref not in ("U23", "C68"):
            continue
        assert first(f, "layer")[1] == "B.Cu"
        ps = courtyard(f, "B.CrtYd")
        xy = [[ps[i] - 100 + datum[i] for i in (0, 1)], [ps[i + 2] - 100 + datum[i] for i in (0, 1)]]
        projection, basis = height(str(f[1]), ref, data[ref]["part"])
        box = (
            [min(p[i] for p in xy) for i in (0, 1)]
            + [datum[2] - projection]
            + [max(p[i] for p in xy) for i in (0, 1)]
            + [datum[2]]
        )
        expanded = [box[0] - 0.25, box[1] - 0.25, box[2] - 0.45, box[3] + 0.25, box[4] + 0.25, box[5] + 0.45]
        nominal_hits = []
        for row in boxes:
            if row[0] in ("E28_U23", "E28_C68"):
                continue
            other = [*row[1:4], *[row[i + 1] + row[i + 4] for i in range(3)]]
            if box_hit(box, other):
                nominal_hits.append(row[0])
        for row in cylinders:
            other = [
                row[1] - row[4] / 2,
                row[2] - row[4] / 2,
                row[3],
                row[1] + row[4] / 2,
                row[2] + row[4] / 2,
                row[3] + row[5],
            ]
            if box_hit(box, other) and circle_gap(box, row[1:3], row[4] / 2) < 0:
                nominal_hits.append(row[0])
        post_rows = []
        for centre in posts:
            post_rows.append(
                dict(
                    centre_world_mm=centre,
                    outer_radius_mm=3.6 / math.cos(math.pi / 128),
                    nominal_courtyard_radial_gap_mm=circle_gap(box, centre, 3.6 / math.cos(math.pi / 128)),
                    extra_0p25_clearance_gap_mm=circle_gap(expanded, centre, 3.6 / math.cos(math.pi / 128)),
                    extra_0p90_XY_gap_mm=circle_gap(
                        [box[0] - 0.9, box[1] - 0.9, box[2], box[3] + 0.9, box[4] + 0.9, box[5]],
                        centre,
                        3.6 / math.cos(math.pi / 128),
                    ),
                    post_z_range_mm=[2.7, 20],
                )
            )
        padpoints = {
            str(p[1]): [transform(f, first(p, "at")[1:3])[i] - 100 + datum[i] for i in (0, 1)]
            for p in children(f, "pad")
        }
        results[ref] = dict(
            part=data[ref]["part"],
            native_at=first(f, "at")[1:],
            courtyard_body_box_world_mm=box,
            projection_requirement_mm=projection,
            height_basis=basis,
            case_floor_z_top_mm=2.8,
            free_floor_after0p25_and0p2Z_mm=expanded[2] - 2.8,
            existing_component_nominal_hits=nominal_hits,
            post_checks=post_rows,
            pad_world_xy_mm=padpoints,
            native_housing_full_fit_not_yet_run=True,
            physical_qualified=False,
        )
        assert not nominal_hits and expanded[2] > 2.8
        assert all(p["extra_0p90_XY_gap_mm"] > 0 for p in post_rows)
    u, c = results["U23"], results["C68"]
    gap = c["courtyard_body_box_world_mm"][1] - u["courtyard_body_box_world_mm"][4]
    assert gap >= 0.25 - 1e-9
    report = dict(
        scope="Source-bound numeric pre-routing screen, no OpenSCAD run or physical fit certification",
        source_sha256=source_sha,
        authoritative_E28_datum_mm=datum,
        authoritative_CP01_TC02_centres_mm=posts,
        components=results,
        U23_C68_courtyard_gap_mm=gap,
        local_VCC14_to_bypass1_centerline_distance_mm=math.dist(
            u["pad_world_xy_mm"]["14"], c["pad_world_xy_mm"]["1"]
        ),
        board_south_world_y_mm=163,
        Trill_post_to_board_south_nominal_gap_mm=min(p[1] for p in posts)
        - 3.6 / math.cos(math.pi / 128)
        - 163,
        small_package_source_height_and_process_not_approved=True,
        full_MCAD_case_bore_and_hardware_checks_pending=True,
        no_copper_routed_and_no_qualification_granted=True,
    )
    assert all(hashlib.sha256((REPO / p).read_bytes()).hexdigest() == h for p, h in source_sha.items())
    (WORK / "generated/numeric-MCAD-screen.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: dict(
                    box=v["courtyard_body_box_world_mm"],
                    floor=v["free_floor_after0p25_and0p2Z_mm"],
                    posts=[p["extra_0p90_XY_gap_mm"] for p in v["post_checks"]],
                )
                for k, v in results.items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
