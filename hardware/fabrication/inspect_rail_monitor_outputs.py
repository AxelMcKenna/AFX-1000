"""Cross-check unreleased E13 CAM coordinates and produce an honest review BOM."""

import argparse
import csv
import io
import json
import math
import re
from collections import Counter
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.evidence_paths import recorded_path

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "hardware/fabrication/staging/rail-monitor-r83-land-native-01"
DEFAULT = REPO / "hardware/fabrication/staging/rail-monitor-manufacturing-review-02"
FUNCTIONS = {
    "F_Cu": "Copper,L1,Top", "In1_Cu": "Copper,L2,Inr", "In2_Cu": "Copper,L3,Inr", "B_Cu": "Copper,L4,Bot",
    "F_Mask": "Soldermask,Top", "B_Mask": "Soldermask,Bot", "F_Paste": "Paste,Top", "B_Paste": "Paste,Bot",
    "F_Silkscreen": "Legend,Top", "B_Silkscreen": "Legend,Bot", "Edge_Cuts": "Profile,NP",
}


def parse_drills(text):
    if "\nMETRIC\n" not in text or "absolute / metric / decimal" not in text:
        raise ValueError("Require absolute decimal-mm Excellon")
    tools, hits, selected = {}, [], None
    for line in text.splitlines():
        if not line or line.startswith(";") or line in ("M48", "FMAT,2", "METRIC", "%", "G90", "G05", "M30"):
            continue
        match = re.fullmatch(r"T(\d+)C(\d+(?:\.\d+)?)", line)
        if match:
            tools[int(match[1])] = float(match[2])
        elif re.fullmatch(r"T\d+", line):
            selected = int(line[1:])
        elif line.startswith(("X", "Y", "G00", "G01", "G85", "R")):
            match = re.fullmatch(r"X(-?\d+(?:\.\d+)?)Y(-?\d+(?:\.\d+)?)", line)
            if match is None or selected not in tools:
                raise ValueError("Unsupported or unselected Excellon hit: "+line)
            hits.append((tools[selected], float(match[1]), float(match[2])))
        else:
            raise ValueError("Unsupported Excellon command: "+line)
    if not text.rstrip().endswith("M30"):
        raise ValueError("Missing Excellon terminator")
    return hits


def match_holes(actual, expected, tolerance=0.000500001):
    remaining = list(expected)
    maximum_error = 0.0
    for diameter, x, y in actual:
        matches = [i for i, hole in enumerate(remaining)
                   if abs(diameter-hole[0]) < 1e-8 and abs(x-hole[1]) <= tolerance and abs(y-hole[2]) <= tolerance]
        if len(matches) != 1:
            raise ValueError("Drill count, diameter, coordinate or origin mismatch")
        _, ex, ey = remaining.pop(matches[0])
        maximum_error = max(maximum_error, abs(x-ex), abs(y-ey))
    if remaining:
        raise ValueError("Missing drill hits")
    return maximum_error


def edge(a, b):
    return tuple(sorted((tuple(round(v, 6) for v in a), tuple(round(v, 6) for v in b))))


def profile_edges(text):
    if "%FSLAX46Y46*%" not in text or "%MOMM*%" not in text or "G02*" in text or "G03*" in text:
        raise ValueError("Require linear absolute 4.6 mm profile")
    result, current = [], None
    for line in text.splitlines():
        if not line.startswith(("X", "Y")):
            continue
        match = re.fullmatch(r"X(-?\d+)Y(-?\d+)D0([12])\*", line)
        if match is None:
            raise ValueError("Unsupported profile command")
        point = (int(match[1])/1e6, -int(match[2])/1e6)  # Back to PCB +Y-down coordinates.
        if match[3] == "1":
            if current is None:
                raise ValueError("Profile draws without a start")
            result.append(edge(current, point))
        current = point
    return Counter(result)


def csv_text(header, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue()


def build(folder):
    export_path = folder / "export-review.json"
    exported = json.loads(export_path.read_text())
    assert exported["status"] == "REVIEW_ONLY_UNRELEASED_CANDIDATE" and not exported["fabrication_approved"]
    for name, digest in exported["source_sha256"].items():
        assert sha(recorded_path(name)) == digest, name
    for name, digest in exported["generated_file_sha256"].items():
        assert sha(folder / name) == digest, name
    geometry = json.loads((folder / "native-geometry.json").read_text())
    assert geometry["board_copper_layers"] == 4
    layer_functions = {}
    for suffix, function in FUNCTIONS.items():
        path = folder / "gerbers" / ("rail_monitor-"+suffix+".gbr")
        text = path.read_text()
        assert "%TF.FileFunction,"+function+"*%" in text
        assert "%FSLAX46Y46*%" in text and "%MOMM*%" in text and text.rstrip().endswith("M02*")
        assert "%TF.SameCoordinates,Original*%" in text
        layer_functions[path.name] = function
    assert len(list((folder / "gerbers").glob("*.gbr"))) == 11
    assert not list((folder / "gerbers").glob("*.gbrjob")), "Unapproved inferred stack must stay outside CAM input"
    expected_edges = []
    for polygon in geometry["outline"]:
        assert not polygon["holes"], "Explicit profile-hole support required"
        points = polygon["outer"]
        expected_edges.extend(edge(a, b) for a, b in zip(points, points[1:]+points[:1]))
    assert profile_edges((folder / "gerbers/rail_monitor-Edge_Cuts.gbr").read_text()) == Counter(expected_edges)
    drill_counts, drill_errors = {}, {}
    for kind in ("PTH", "NPTH"):
        text = (folder / "drills" / ("rail_monitor-"+kind+".drl")).read_text()
        polarity = "NonPlated" if kind == "NPTH" else "Plated"
        assert f"TF.FileFunction,{polarity},1,4,{kind}" in text
        hits = parse_drills(text)
        expected = [(h["diameter_mm"], h["position_mm"][0], -h["position_mm"][1])
                    for h in geometry["drills"] if h["kind"] == kind]
        drill_errors[kind] = match_holes(hits, expected)
        drill_counts[kind] = len(hits)
    parts, _ = netlist(SOURCE / "netlist.xml")
    footprints = {row["ref"]: row for row in geometry["footprints"]}
    placements = list(csv.DictReader((folder / "assembly/native-positions.csv").read_text().splitlines()))
    assert len(placements) == len({row["Ref"] for row in placements})
    assert {row["Ref"] for row in placements} == set(parts)
    proposal_path = REPO / "hardware/fabrication/parts/rail-monitor-resistors-01/candidates.json"
    proposals = json.loads(proposal_path.read_text())
    for name, digest in proposals["source_sha256"].items():
        assert sha(recorded_path(name)) == digest, name
    candidates = {row["ref"]: row for row in proposals["parts"]}
    groups, status_count, output_placements = {}, Counter(), []
    through_hole = {h["ref"] for h in geometry["drills"] if h["ref"] != "VIA" and h["kind"] == "PTH"}
    for row in placements:
        ref = row["Ref"]
        actual = footprints[ref]
        assert not actual["dnp"] and not actual["exclude_from_bom"]
        assert row["Val"] == actual["value"] == parts[ref].findtext("value")
        assert row["Package"] == actual["footprint"] == parts[ref].findtext("footprint").split(":", 1)[-1]
        assert math.isclose(float(row["PosX"]), actual["position_mm"][0], abs_tol=1e-6)
        assert math.isclose(float(row["PosY"]), -actual["position_mm"][1], abs_tol=1e-6)
        delta = (float(row["Rot"])-actual["rotation_degrees"]+180) % 360 - 180
        assert abs(delta) < 1e-6
        assert row["Side"] == ("top" if actual["layer"] == "F.Cu" else "bottom")
        technology = "through_hole" if ref in through_hole else "SMD"
        if ref in candidates:
            assert candidates[ref]["source_value"] == row["Val"]
            code, status = candidates[ref]["candidate_order_code"], "syntax_derived_unconfirmed"
        elif ref.startswith("U"):
            code, status = row["Val"], "schematic_code_unqualified"
        else:
            code, status = "", "UNRESOLVED_ORDER_CODE"
        status_count[status] += 1
        group = (row["Val"], parts[ref].findtext("footprint"), code, status, row["Side"], technology)
        groups.setdefault(group, []).append(ref)
        output_placements.append([ref, row["Val"], parts[ref].findtext("footprint"), row["PosX"], row["PosY"],
                                  row["Rot"], row["Side"], technology, status])
    assert len(parts) == 181 and len(footprints) == 185
    assert {r for r, f in footprints.items() if f["exclude_from_bom"]} == set(footprints)-set(parts)
    bom = csv_text(["references", "quantity", "value", "footprint", "proposed_order_code", "order_code_status", "side", "technology"],
                   [[" ".join(refs), len(refs), *group] for group, refs in groups.items()])
    pos = csv_text(["reference", "value", "footprint", "X_mm", "Y_mm", "KiCad_rotation_deg", "side", "technology", "order_code_status"],
                   output_placements)
    inputs = [export_path, SOURCE / "netlist.xml", proposal_path, Path(__file__)]
    lands = json.loads((SOURCE / "r83-land-review.json").read_text())
    rounding_radius = math.sqrt(2) * drill_errors["PTH"]
    report = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in inputs},
                  layer_functions=layer_functions, outline_centerline_size_mm=[80, 70], profile_matches_native_outline=True,
                  drill_counts=drill_counts, maximum_drill_axis_rounding_error_mm=drill_errors,
                  drill_match_axis_tolerance_mm=0.000500001, placement_rows=len(placements), electrical_parts=len(parts),
                  conservative_via_drill_to_SMD_gap_after_coordinate_rounding_mm=lands["minimum_drill_to_SMD_gap_mm"]-rounding_radius,
                  fabrication_drill_diameter_and_registration_tolerances_included=False,
                  placement_value_package_side_rotation_and_origin_match=True,
                  excluded_mechanical_features=sorted(set(footprints)-set(parts)),
                  BOM_quantity=sum(len(refs) for refs in groups.values()), BOM_groups=len(groups), order_code_status_counts=dict(status_count),
                  KiCad_inferred_stackup_and_finish_accepted=False, fabricator_or_assembler_DFM_accepted=False,
                  complete_BOM_approved=False, fabrication_approved=False)
    return report, {"assembly/review-bom.csv": bom, "assembly/review-placement.csv": pos}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, default=DEFAULT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    folder = args.folder.resolve()
    assert folder.is_relative_to(REPO / "hardware/fabrication/staging")
    report, files = build(folder)
    files["manufacturing-inspection.json"] = json.dumps(report, indent=2)+"\n"
    for name, text in files.items():
        path = folder / name
        if args.check:
            assert path.read_text() == text, "Stale derived file: "+name
        else:
            with path.open("x") as stream:
                stream.write(text)
    print(json.dumps({k: report[k] for k in ("drill_counts", "placement_rows", "BOM_quantity", "BOM_groups", "order_code_status_counts")}))


if __name__ == "__main__":
    main()
