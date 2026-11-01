"""End-to-end lower bounds for a saved local DIGITAL escape.

An empty local collision result cannot waive the selected installed wire length
or prove its receiving termination. Relaxing all remaining obstacles gives a
useful rejection test without pretending to have routed the remaining harness.
"""

import argparse
import json
import math
from pathlib import Path

from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

from ..generate import REPO, sha

ROOT = Path(__file__).resolve().parent


def distance_to_box(point, box):
    return math.sqrt(
        sum(max(box[i + 1] - point[i], 0, point[i] - box[i + 1] - box[i + 4]) ** 2 for i in range(3))
    )


def run(folder):
    report = json.loads((folder / "analysis.json").read_text())
    native = json.loads((folder / "verification.json").read_text())
    hashes = {**report["source_sha256"], **native["evidence_inputs_sha256"]}
    for n, h in hashes.items():
        assert sha(REPO / n) == h, "Local escape input changed: " + n
    _, data, fresh = snapshot()
    hashes.update(fresh)
    pcb = REPO / "hardware/electronics/processor_carrier/processor_carrier.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "J1"] for p in children(f, "property"))
    )
    assert "PinHeader_1x02_P2.54mm" in str(fp[1])
    board = next(b for b in data["boards"] if b[0] == "dsp_carrier")
    receiving_box = next(b for b in data["envelopes"] if b[0] == "e19_J1")
    formed = "separate_wire_proposal" in report
    wire = report["separate_wire_proposal"]["wire"] if formed else report["selected_wire"]
    rows = []
    for path in report["routes"]:
        pad = next(p for p in children(fp, "pad") if str(first(p, "net")[-1]).lstrip("/") == path["net"])
        xy = transform(fp, first(pad, "at")[1:3])
        target = [xy[0] - 100 + board[1], xy[1] - 100 + board[2], board[3] + board[6]]
        end = path["escape_end_mm"]
        local_length = (
            path["initial_straight_mm"] + path["nominal_bend_radius_mm"] * math.pi / 2
            if formed
            else path["arc_length_mm"] + path["straight_length_mm"]
        )
        to_pad = math.dist(end, target)
        to_box = distance_to_box(end, receiving_box)
        limit = wire["installed_length_max_m"] * 1000
        rows.append(
            dict(
                net=path["net"],
                receiving_pad=str(pad[1]),
                receiving_pad_xy_board_face_mm=target,
                local_escape_length_mm=local_length,
                unobstructed_remainder_to_pad_mm=to_pad,
                total_lower_bound_to_pad_mm=local_length + to_pad,
                unobstructed_remainder_to_anywhere_in_receiving_reserve_mm=to_box,
                total_lower_bound_to_receiving_reserve_mm=local_length + to_box,
                selected_installed_length_limit_mm=limit,
                receiving_finished_drill_nominal_mm=float(first(pad, "drill")[1]),
                exceeds_limit_even_with_relaxed_receiving_reserve=local_length + to_box > limit,
            )
        )
    for p in [Path(__file__), pcb, folder / "analysis.json", folder / "verification.json"]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    result = dict(
        scope="Relaxed end-to-end length rejection test for current E19 J1 interface; remaining obstacles, forming/terminations/strain slack and branch wiring are not routed",
        rows=rows,
        current_receiving_body_reserve=receiving_box,
        source_sha256=hashes,
        local_escape_native_clear=native["local_formed_escape_clear" if formed else "local_escape_native_clear"],
        selected_length_incompatible=any(
            r["exceeds_limit_even_with_relaxed_receiving_reserve"] for r in rows
        ),
        local_unmodelled_source_bare_joint_and_board_penetration_length_credited_mm=0,
        source_bare_length_above_face_included_mm=3.1 if formed else 0,
        selected_wire_awg=wire["awg"],
        selected_wire_nominal_core_OD_mm=wire.get("conductor_nominal_od_mm"),
        current_receiving_interface_selected_for_this_wire=False,
        current_E19_header_accepts_AWG14=False,
        receiving_wire_exit_and_contact_selected=False,
        complete_output_harness=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    assert all(sha(REPO / n) == h for n, h in hashes.items()), "Source changed during length audit"
    (folder / "length-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            dict(rows=rows, selected_length_incompatible=result["selected_length_incompatible"]), indent=2
        )
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    result = run(parser.parse_args().folder.resolve())
    raise SystemExit(1 if result["selected_length_incompatible"] else 0)
