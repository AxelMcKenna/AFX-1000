"""Sparse supplier nominal curve comparison; no interpolation/temperature guarantee."""

import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def nominal(temp, points):
    if not points[0][0] <= temp <= points[-1][0]:
        raise ValueError("No extrapolation beyond published nominal points")
    for (t0, r0), (t1, r1) in zip(points, points[1:]):
        if t0 <= temp <= t1:
            weight = (1 / (temp + 273.15) - 1 / (t0 + 273.15)) / (1 / (t1 + 273.15) - 1 / (t0 + 273.15))
            return math.exp(math.log(r0) + weight * math.log(r1 / r0))
    raise AssertionError(temp)


def compute():
    manifest = json.loads((ROOT / "sources/manifest.json").read_text())
    for name, row in manifest.items():
        assert hashlib.sha256((ROOT / "sources" / name).read_bytes()).hexdigest() == row["sha256"]
    points = json.loads((ROOT / "nominal-203AT-ohm.json").read_text())["points_temp_c_resistance_ohm"]
    rows = []
    for temp, published in points:
        beta = 20000 * math.exp(4013 * (1 / (temp + 273.15) - 1 / 298.15))
        rows.append(dict(temp_c=temp, published_nominal_ohm=published, beta_nominal_ohm=beta,
                         beta_relative_error_fraction=beta / published - 1))
    ranges = [[.99, 1.01], [-40.13, 40.13], [19900, 20100], [970, 1030],
              [3.234, 3.366], [-1.1e-6, 1.1e-6], [-3, 3]]
    trips = []
    # R25 and delta-beta are only a conditional perturbation of the nominal
    # table. They do NOT establish full-temperature manufacturing tolerance.
    for scale, dbeta, pull, series, vcc, injection, error in itertools.product(*ranges):
        lo, hi = 25., 100.
        for _ in range(60):
            t = (lo + hi) / 2
            ntc = nominal(t, points) * scale * math.exp(dbeta * (1 / (t + 273.15) - 1 / 298.15))
            code = 1024 * (ntc / (pull + ntc) + injection * (series + pull * ntc / (pull + ntc)) / vcc) + error
            if code > 186:
                lo = t
            else:
                hi = t
        trips.append(hi)
    return dict(scope="Legacy supplier nominal R/T table vs beta comparison",
                published_nominal_table_available=True, points=len(points),
                nominal_point_comparisons=rows,
                interpolation="Piecewise linear ln(R) against 1/T(K); sensitivity only",
                interpolation_error_bounded=False, local_manufacturing_RT_tolerance_bounded=False,
                ADC_complete_error_requirement_lsb=3,
                conditional_table_model_trip_interval_c=[min(trips), max(trips)],
                conditional_tolerance_corners=len(trips),
                guaranteed_sensor_trip_interval_c=None, assembled_shutdown_ceiling_c=None,
                firmware_hot_code_unchanged=186,
                sources_sha256={**{n: row["sha256"] for n, row in manifest.items()},
                                "nominal-203AT-ohm.json": hashlib.sha256((ROOT / "nominal-203AT-ohm.json").read_bytes()).hexdigest()},
                physical_qualified=False, thermal_qualified=False, fabrication_released=False)


if __name__ == "__main__":
    result = compute()
    (ROOT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Conditional table-model trip:", result["conditional_table_model_trip_interval_c"])
    print("Guaranteed trip:", result["guaranteed_sensor_trip_interval_c"])
