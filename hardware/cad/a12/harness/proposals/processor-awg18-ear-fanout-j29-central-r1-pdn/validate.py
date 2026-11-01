"""Source, KCL, signed-current and no-false-release guards for the coarse packet."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def validate(r, check_files=True):
    assert r["grid_mm"] == 0.2 and r["lattice_origin_offset_mm"] == [0.025, 0.025]
    assert (
        r["known_positive_total_a"] == 1.984
        and r["input_max_target_a"] == 2.4
        and r["reserve_unassigned_a"] == 0.416
    )
    assert r["Seed_local_return_for_known_exports_a"] == 0.925
    assert r["scenario"]["copper_mm"] == [0.07] * 4 and r["scenario"]["finished_barrel_wall_mm"] == 0.025
    assert not r["scenario"]["material_stackup_temperature_or_process_accepted"]
    assert r["above_board_source_face"] == "F.Cu"
    assert len(r["all_AGND_drive_ports"]) == 23 and {"J14.2", "J15.2"} <= set(r["outward_AGND_ports"])
    assert "J1.2" not in r["all_AGND_drive_ports"]
    for n in r["networks"].values():
        assert n["max_absolute_kcl_residual_a"] < 1e-7
        assert n["source_face"][1] == "F.Cu" and not n["equipotential_pad_or_via_short_used"]
        assert n["all_native_drill_voids"] == 270 and n["bounds_native_mm"] == [100, 100, 264.5, 165]
    assert len(r["fixture_corners"]) == 96
    for f in r["fixture_corners"]:
        assert (
            abs(sum(f["ground_fixture_injections_a"].values()) - sum(f["positive_loads_a"].values())) < 1e-12
        )
        assert not f["complete_physical_return_solution"]
        assert f["positive_loads_a"]["seed"] == 1 and f["positive_loads_a"]["led"] == 0.764
        g = f["ground_fixture_injections_a"]
        seed = [g[p] for p in ["U1.20", "U1.40"] if p in g]
        assert seed == [0.925]
        if f["hypothetical_reserve_fixture_at"] is None:
            assert abs(sum(f["positive_loads_a"].values()) - 1.984) < 1e-12
        else:
            assert (
                f["not_a_complete_arbitrary_reserve_bound"]
                and abs(sum(f["positive_loads_a"].values()) - 2.4) < 1e-12
            )
    assert not r["spatial_refinement_performed"] and not r["prior_matrix_inherited"]
    assert (
        not r["full_source_to_load_PDN_solved"]
        and not r["physical_qualified"]
        and not r["fabrication_released"]
    )
    if check_files:
        for rel, h in r["source_sha256"].items():
            assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == h, rel


if __name__ == "__main__":
    validate(json.loads((ROOT / "generated/coarse.json").read_text()))
    print("Coarse source/KCL/signed-current guards pass; physical PDN not qualified")
