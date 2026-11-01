"""Conditional installed bottom heat-transfer requirement, retaining loaded CH20.

The solved coefficient is a requirement of this approximate model. It is not
an installed coefficient, a fan flow specification or a qualified margin.
"""

import hashlib
import json
from pathlib import Path

from ..coupled_housing20.coupled import solve
from ..coupled_housing20.geometry import build

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / "coupled_housing20"
REPO = Path(__file__).resolve().parents[5]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    # Require a complete, immutable parent before running a derived calculation.
    handoff = read(PARENT / "handoff.json")
    bound = handoff["files_sha256"]
    assert all(sha(PARENT / name) == value for name, value in bound.items())
    inputs = {str((PARENT / name).relative_to(REPO)): value for name, value in bound.items()}
    for path in [PARENT / "handoff.json", Path(__file__)]:
        inputs[str(path.relative_to(REPO))] = sha(path)
    contract = read(PARENT / "geometry-contract.json")
    dims = read(PARENT / "sources/dimensions.json")
    design = read(PARENT / "sources/base-design.json")
    design["housing"] = dims["candidate_outer_shell"]
    design["shell_fasteners"] = dims["candidate_shell_fasteners_xy"]
    design["feet"]["centres"] = dims["new_feet_candidate_xy"]
    sources = read(PARENT / "sources/wu-analysis.json")["source_placements"]["unplaced_hotcluster"]
    geometry = build(contract, tuple(contract["coarse_grid"]))
    cache = {}

    def evaluate(h):
        if h not in cache:
            result, _ = solve(
                contract,
                design,
                sources,
                geometry,
                h,
                0.5,
                heat_scale=1.2,
                contact_r=(0.2, 0.2),
            )
            assert result["converged"] and not result["base_temperature_prescribed"]
            assert abs(result["energy_residual_w"]) < 1e-6
            assert result["max_node_balance_residual_w"] < 1e-6
            assert result["conduction_graph_components"] == 1
            cache[h] = result
            print(f"h={h:.8f}, base_peak={result['base_peak_c']:.8f}", flush=True)
        return cache[h]["base_peak_c"]

    brackets = []
    # Fixed bounded search; never extrapolate a passing installed condition.
    for target in [65.0, 60.0]:
        lower, upper = 3.0, 32.0
        low_temp, high_temp = evaluate(lower), evaluate(upper)
        if low_temp <= target or high_temp > target:
            brackets.append(
                dict(
                    target_base_c=target,
                    bracket_found=False,
                    tested_h_range=[lower, upper],
                    tested_peak_c=[low_temp, high_temp],
                    reason="Target is not bracketed by the declared search endpoints.",
                )
            )
            continue
        for _ in range(12):
            mid = (lower + upper) / 2
            if evaluate(mid) > target:
                lower = mid
            else:
                upper = mid
        assert evaluate(lower) > target >= evaluate(upper)
        brackets.append(
            dict(
                target_base_c=target,
                bracket_found=True,
                failing_h=lower,
                failing_peak_c=evaluate(lower),
                passing_h=upper,
                passing_peak_c=evaluate(upper),
                numerical_h_interval_w_per_m2k=upper - lower,
                numerical_interval_is_not_physical_uncertainty=True,
            )
        )
    ordered = sorted(cache)
    assert all(cache[a]["base_peak_c"] > cache[b]["base_peak_c"] for a, b in zip(ordered, ordered[1:]))
    assert all(sha(REPO / name) == value for name, value in inputs.items())
    report = dict(
        scope=__doc__,
        source_sha256=inputs,
        parent_handoff_sha256=sha(PARENT / "handoff.json"),
        placement="unplaced_hotcluster",
        grid=contract["coarse_grid"],
        retained_heat_w=contract["retained_heat_w"],
        stress_heat_w=1.2 * contract["retained_heat_w"],
        stress_is_planning_diagnostic_not_measured_upper=True,
        fin_face_fraction=0.5,
        contact_r_k_per_w=[0.2, 0.2],
        targets=brackets,
        evaluated_cases=[dict(h=h, result=cache[h]) for h in ordered],
        peak_decreases_for_every_tested_increase_in_h=True,
        coefficient_applies_uniformly_to_declared_bottom_effective_area=True,
        actual_installed_h_established=False,
        fan_or_cfm_selected=False,
        spatial_refinement_performed=False,
        real_package_board_TIM_air_paths_resolved=False,
        panel_control_temperatures_qualified=False,
        thermal_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
        qualified20percent_margin=False,
    )
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    (out / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
