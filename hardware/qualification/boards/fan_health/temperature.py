"""Conditional NTC/ADC comparisons. Beta approximation is not an R/T guarantee."""

import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def code(temp, r25=20000, beta=4013, pull=20000, series=1000,
         vcc=3.3, injected_a=0, error=0):
    ntc = r25 * math.exp(beta * (1 / (temp + 273.15) - 1 / 298.15))
    ratio = ntc / (pull + ntc)
    resistance = series + pull * ntc / (pull + ntc)
    return 1024 * (ratio + injected_a * resistance / vcc) + error


def crossing(parameters):
    lo, hi = 25., 100.
    for _ in range(60):
        mid = (lo + hi) / 2
        if code(mid, *parameters) > 186:
            lo = mid
        else:
            hi = mid
    return hi


def compute():
    # Each range is an explicit receiving comparison, including the complete
    # resistor environment, not a transfer of typical ADC data to a guarantee.
    ranges = [
        [19800, 20200], [4013 * .99, 4013 * 1.01], [19900, 20100],
        [970, 1030], [3.234, 3.366], [-1.1e-6, 1.1e-6], [-3, 3],
    ]
    corners = list(itertools.product(*ranges))
    crossings = [crossing(c) for c in corners]
    short_max = 1024 * 1.1e-6 * 1030 / 3.234 + 3
    open_min = 1024 * (1 - 1.1e-6 * (20100 + 1030) / 3.234) - 3
    max_cold = max(code(-10, *c) for c in corners)
    # Maximum sensor power for any positive NTC resistance occurs at Rntc=Rp.
    sensor_power = 3.366**2 / (4 * 19900)
    return dict(
        revision="FH01-203AT-2-conditional-beta-and-ADC-comparison",
        part="SEMITEC 203AT-2", nominal_r25_ohm=20000, nominal_beta_25_85_k=4013,
        firmware_hot_code=186, firmware_short_code=8, firmware_open_code=1000,
        modeled_trip_interval_c=[min(crossings), max(crossings)], corners=len(corners),
        comparison_ranges=dict(zip(
            ["r25_ohm", "beta_k", "pull_ohm", "series_ohm", "vcc_v", "total_injected_a", "total_adc_error_lsb"], ranges,
        )),
        conditional_short_code_upper=short_max,
        conditional_open_code_lower=open_min,
        cold_minus10_code_upper=max_cold,
        short_and_open_detected_under_comparison=short_max <= 8 and open_min >= 1000,
        maximum_sensor_self_heat_power_w=sensor_power,
        typical_still_air_temperature_rise_c=sensor_power / .002,
        typical_free_air_time_constant_s=15,
        receiving_adc_errors_are_manufacturer_guarantees=False,
        beta_approximation_discrepancy_bounded=False,
        actual_rt_curve_obtained=False,
        actual_sensor_location_and_lag_qualified=False,
        guaranteed_hot_trip_interval_c=None,
        physical_qualified=False,
        fabrication_released=False,
        limitations=[
            "ATtiny84A absolute ADC accuracy2LSB is typical at4V/200kHz; no maximum at this3.3V/62.5kHz operating point is inferred.",
            "The1uA I/O leakage test limit is at5.5V/input rails;1.1uA total at these analog voltages is an unaccepted receiving requirement.",
            "203AT-2 beta25/85 does not bound beta-model interpolation error at the trip point; true supplierR/T curve or actual characterization is required.",
            "Approximate15s free-air lag and2mW/K dissipation are typical, not placement or shutdown response bounds.",
            "An open/short code comparison does not detect every sensor failure, including a plausible fixed resistance or poor thermal contact.",
        ],
    )


if __name__ == "__main__":
    result = compute()
    (ROOT / "generated/temperature-comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Conditional beta-model trip interval:", result["modeled_trip_interval_c"])
    print("Guaranteed hot trip interval:", result["guaranteed_hot_trip_interval_c"])
