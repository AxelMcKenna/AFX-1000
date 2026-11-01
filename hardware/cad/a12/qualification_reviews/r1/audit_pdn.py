"""Independently multiply the fresh finite matrices for all 96 saved fixtures."""

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
PACKET = REPO / "hardware/cad/a12/harness/proposals/processor-awg18-ear-fanout-j29-central-r1-pdn"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-11, abs_tol=1e-13), (a, b)


def main():
    h = read(PACKET / "handoff.json")
    assert len(h["files_sha256"]) == 28
    for n, expected in h["files_sha256"].items():
        assert sha(PACKET / n) == expected, n
    a = read(PACKET / "generated/coarse.json")
    e = read(PACKET / "generated/updated-endpoint-intercept.json")
    for n, expected in a["source_sha256"].items():
        assert sha(PACKET / n) == expected, n
    for n, expected in e["source_sha256"].items():
        assert sha(REPO / n) == expected, n
    assert not a["prior_matrix_inherited"] and not a["spatial_refinement_performed"]
    assert a["known_positive_allocations_a"] == {"seed": 1.0, "led": 0.764, "bypass": 0.14, "monitor": 0.08}
    close(a["known_positive_total_a"], 1.984)
    close(a["reserve_unassigned_a"], 0.416)
    close(a["Seed_local_return_for_known_exports_a"], 1 - 0.035 - 0.02 - 0.02)
    pos = a["networks"]["5V_DIG"]["transfer_resistance_ohm"]
    ground = a["networks"]["AGND"]["transfer_resistance_ohm"]
    seed_r = a["networks"]["SEED_VIN"]["transfer_resistance_ohm"]["seed"]["seed"]
    maxkcl = 0
    for n in a["networks"].values():
        assert n["all_native_drill_voids"] == 270
        assert not n["equipotential_pad_or_via_short_used"]
        assert n["resolved_component_nodes"] + n["unexcited_floating_nodes"] == n["nodes"]
        maxkcl = max(maxkcl, n["max_absolute_kcl_residual_a"])
        matrix = n["transfer_resistance_ohm"]
        for drive, row in matrix.items():
            assert row[drive] > 0
            for measure in set(row).intersection(matrix):
                close(row[measure], matrix[measure][drive])
    assert maxkcl < 1e-8 and a["networks"]["SEED_VIN"]["finite_physical_barrels"] == 6
    assert len(a["fixture_corners"]) == 96
    grouped = {}
    for f in a["fixture_corners"]:
        loads, currents = f["positive_loads_a"], f["ground_fixture_injections_a"]
        close(math.fsum(loads.values()), math.fsum(currents.values()))
        close(math.fsum(loads.values()), f["total_input_allocation_or_fixture_a"])
        seedport = next(p for p in currents if p.startswith("U1."))
        ledport = next(p for p in currents if p.startswith("J11."))
        ports = {"seed": seedport, "led": ledport, "bypass": "J14.2", "monitor": "J15.2"}

        def g_voltage(port):
            return math.fsum(i * ground[p][port] for p, i in currents.items() if p != "J13.2")

        for load, port in ports.items():
            vp = math.fsum(current * pos[drive][load] for drive, current in loads.items())
            close(vp, f["positive_only_copper_drop_v"][load])
            loop = vp + g_voltage(port) + (loads["seed"] * seed_r if load == "seed" else 0)
            close(loop, f["local_fixture_loop_copper_drop_v"][load])
        for port, value in f["quiet_to_Seed_reference_fixture_offsets_v"].items():
            close(value, g_voltage(port) - g_voltage(seedport))
        assert not f["complete_physical_return_solution"]
        grouped.setdefault(str(f["hypothetical_reserve_fixture_at"]), []).append(f)
    for name, fixtures in grouped.items():
        assert len(fixtures) == 32
        for load in ports:
            values = [f["local_fixture_loop_copper_drop_v"][load] for f in fixtures]
            saved = a["fixture_loop_copper_drop_intervals_v"][name][load]
            close(min(values), saved[0])
            close(max(values), saved[1])
    assert e["complete_guaranteed_Seed_VIN_interval_v"] is None
    assert not h["complete_source_to_load_PDN_solved"] and not h["spatial_refinement_bound_proven"]
    assert not h["physical_qualified"] and not h["fabrication_released"]
    result = dict(
        scope=__doc__,
        packet_handoff_sha256=sha(PACKET / "handoff.json"),
        packet_hashes_checked=28,
        all96_fixture_copper_products_recomputed=True,
        all960_quiet_reference_differences_recomputed=True,
        transfer_reciprocity_checked=True,
        max_saved_KCL_residual_a=maxkcl,
        actual_Seed_finite_copper_ohm=seed_r,
        saved_model_grid_mm=a["grid_mm"],
        saved_model_temperature_c=a["network_temperature_c"],
        new_finite_mesh_solve_or_refinement_performed=False,
        complete_PDN_or_voltage_or_physical_qualification=False,
        independent_saved_evidence_review_passed=True,
        script_sha256=sha(Path(__file__)),
    )
    (ROOT / "pdn-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
