"""Reproducible bounded v2 overlay; v1 remains a retained failed margin case."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def revised():
    p = ROOT / "ports.json"
    d = json.loads(p.read_text())
    d["revision"] = "NC265-ports-v2-bounded-repair"
    d["parent_ports_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    for x in d["ports"]:
        if x["ref"] == "J4":
            x["anchor_mm"] = [79, 21]
    s = d["force_shared_strain_candidate"]
    s["channel_centres_u_mm"] = [68, 73, 79, 84]
    for hole in s["PCB_mount_holes"]:
        hole["drill_mm"] = 2.6
        hole["finished_minimum_diameter_receiving_mm"] = 2.5
    s["matched_screw_axis_max_diameter_receiving_mm"] = 2.0
    s["PCB_hole_relative_centring_receiving_mm"] = 0.2
    s["geometry_reserve_mm"] = 0.005
    s["radial_mount_bore_margin_mm"] = 0.045
    s["lower_body_normal_mm"] = [4.8, 13]
    s["cap_body_normal_mm"] = [5.3, 13]
    s["maximum_bolt_washer_UV_bounds_mm"] = [58, 17.5, 93, 26.57]
    s["maximum_rear_mount_hardware_normal_mm"] = [-3.83, -1.44]
    s["selected_mount_washer"] = "Accu HPW-M2-A2-BL"
    s["selected_cap_screw"] = "Accu SPP-M2-6-A2"
    s["proposed_channel_measured_wire_diameter_mm"] = 1.70
    s["matched_channel_diametric_compression_trial_mm"] = [0.02, 0.08]
    s["first_F_low_part_receiving_max_normal_under_bridge_mm"] = 3.0
    return d


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    d = revised()
    if args.output:
        if args.output.exists():
            raise RuntimeError("Fresh overlay output required")
        args.output.write_text(json.dumps(d, indent=2) + "\n")
    else:
        stored = json.loads((ROOT / "ports-v2.json").read_text())
        if d != stored:
            raise ValueError("Actual v2 differs from bounded overlay")
    print(json.dumps(dict(reproducible_v2=True, old_v1_preserved=True)))
