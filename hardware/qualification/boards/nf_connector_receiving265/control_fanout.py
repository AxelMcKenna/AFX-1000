"""Exact rigid transform/subset of the already continuously certified NC01 exits."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    target = ROOT / "control-fanout.json"
    if target.exists():
        raise RuntimeError("Fresh local fanout output required")
    src = ROOT / "inputs/references/NC01-local-fanout.json"
    old = json.loads(src.read_text())
    ports = json.loads((ROOT / "ports-v2.json").read_text())
    j1 = next(p for p in ports["ports"] if p["ref"] == "J1")
    routes = []
    for p in old["routes"]:
        if p["circuit"] == 4:
            continue
        n = p["circuit"]
        u, v = j1["anchor_mm"]
        points = [[u + x, v + z, 10 - y] for x, y, z in p["native_points"]]
        routes.append(
            dict(
                circuit=n,
                net=j1["physical_pads"][str(n)],
                native_points_uvw_mm=points,
                world_points_mm=[[172 + a, 180.5 - c, 3.5 + b] for a, b, c in points],
                radius_mm=p["radius_mm"],
                straight_mm=p["straight_mm"],
            )
        )
    live = {p["circuit"] for p in routes}
    certs = {
        key: value
        for key, value in old["certificates"].items()
        if all(int(n) in live for n in key.split("-"))
    }
    if len(routes) != 29 or len(certs) != 406 or not all(c["certified"] for c in certs.values()):
        raise ValueError("Wrong certified subset")
    d = dict(
        revision="NC265-29wire-local-exit-proposal",
        source_old30_wire_netlabels_NOT_inherited=True,
        J1_pin4_wire_and_contact_omitted=True,
        routes=routes,
        certificates=certs,
        rigid_transform="u=5+oldx;v=17.5+oldz;w=10-oldy;properrotationandtranslation",
        radius_mm=14,
        wire_OD_max_mm=old["wire_OD_max_mm"],
        required_manufacturer_Rmin_mm=old["source_required_radius_mm"],
        all406_continuous_pair_certificates_preserved_by_rigid_isometry=True,
        local_relative_pose_stress_mm=old["local_relative_pose_stress_mm"],
        pair_clearance_mm=old["wire_pair_clearance_mm"],
        chord_bound_mm=old["chord_bound_mm"],
        required_centerline_separation_mm=old["required_centerline_separation_mm"],
        receiving_wire_exit_plane_w_mm=10,
        actual_mate_wire_exit_plane_and_crimp_alignment_measured=False,
        shared_bundle_placement_and_harness_restraint_NOT_qualified=True,
        source_entry_into_opaque_mate_body_NOT_proven=True,
        actual_new265_components_fullunit_controls_power_and_remote_destinations_NOT_screened=True,
        physical_qualified=False,
        fabrication_released=False,
        source_sha256={str(p): sha(p) for p in [Path(__file__), src, ROOT / "ports-v2.json"]},
    )
    target.write_text(json.dumps(d, indent=2) + "\n")
    print(json.dumps(dict(wires=29, pairs=406, Rmin14=True, actual_new_board_fit=False)))


if __name__ == "__main__":
    build()
