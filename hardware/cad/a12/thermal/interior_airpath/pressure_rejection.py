"""Reject the AP02 nominal base meter in the declared low-speed sensitivity.

This is a one-orifice diagnostic, not an installed fan/branch prediction.
Fan pressure is the parent airflow-model planning input. No physical result.
"""

import json
from pathlib import Path

from .polygon_contract import primitive_contracts
from .stage import OUT, ROOT, sha, write


def calculate(area_mm2, flow_m3_h, rho, discharge):
    return rho / 2 * (flow_m3_h / 3600 / (discharge * area_mm2 * 1e-6)) ** 2


def report():
    rho = 101325 / (287.05 * 313.15)
    guard = primitive_contracts()["guard_area_gauge"]["volume"] / .1
    guard_loss = calculate(guard, 5, rho, .6)
    remaining = 9.046 - guard_loss
    losses = {str(a): calculate(a, 1.2, rho, .6) for a in [125, 200, 250, 300]}
    return dict(
        revision="AP02-pressure-rejection", source_sha256={
            "pressure_rejection.py": sha(Path(__file__)),
            "polygon_contract.py": sha(ROOT / "polygon_contract.py"),
            "generated/analysis.json": sha(OUT / "analysis.json"),
        },
        inputs=dict(ambient_C=40, pressure_Pa=101325, air_gas_constant=287.05,
                    density_kg_m3=rho, discharge_coefficient=.6,
                    base_target_m3_h=1.2, total_target_m3_h=10,
                    each_fan_target_m3_h=5, planning_fan_speed_rpm=5300,
                    parent_model_fan_pressure_Pa=9.046,
                    parent_latest_heat_provision_W=37.28570586,
                    fan_pressure_and_heat_are_provisional_not_measurements=True),
        guard_area_each_mm2=guard, common_guard_loss_Pa=guard_loss,
        remaining_after_guard_before_base_pins_turns_outlet_Pa=remaining,
        meter_loss_Pa_by_total_area_mm2=losses,
        meter125_excess_before_other_base_losses_Pa=losses["125"] - remaining,
        nominal125_base_target_rejected=losses["125"] > remaining,
        source_scopes="New parent heat/control planning is cited as a scenario; not adopted electrical hardware.",
        limitations=[
            "A discharge coefficient is an unverified planning scenario.",
            "Parent fan pressure is a curve sensitivity, not guaranteed installed performance.",
            "Additional base pin, turn, outlet and approach losses are omitted and are nonnegative.",
            "No base or interior flow allocation follows from gross aperture area.",
            "C3 shadows 335.2663 mm2 of floor projection; actual lateral flow needs a channel model.",
            "Pressure result does not invalidate the scoped CAD fits; it rejects their nominal125 meter allocation.",
        ], airflow_target_met=False, physical_qualified=False, thermal_qualified=False,
    )


def build():
    p = OUT / "pressure-rejection.json"
    if p.exists() or (ROOT / "handoff.json").exists():
        raise RuntimeError("Existing AP02 evidence cannot be overwritten")
    d = report()
    if not d["nominal125_base_target_rejected"]:
        raise RuntimeError("The declared rejected sensitivity unexpectedly changed")
    write(p, d)
    print(json.dumps(d))


if __name__ == "__main__":
    build()
