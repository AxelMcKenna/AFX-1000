"""Independent R2 terminal/value checks and bounded health-gate calculations."""

import copy
import itertools

from ...common.netlists import number
from ..verify import CONTRACT as ORIGINAL_PINS
from ..verify import VALUES as ORIGINAL_VALUES

EXPECTED = copy.deepcopy(ORIGINAL_PINS)
EXPECTED_VALUES = copy.deepcopy(ORIGINAL_VALUES)
for ci, ch in enumerate(("L", "R")):
    for index, polarity in [(3, "N"), (4, "P"), (10, "P"), (11, "N")]:
        EXPECTED["R" + str(index + 16 * ci)]["1"] = "SENSE_" + ch + polarity
    EXPECTED["R" + str(14 + 16 * ci)]["1"] = "PD_GATED"
    EXPECTED["R" + str(15 + 16 * ci)]["2"] = "NBIAS_" + ch
    for index, value in [
        (1, "2.49k 0.05%"),
        (2, "2.49k 0.05%"),
        (3, "1.21k 0.05%"),
        (4, "1.21k 0.05%"),
        (5, "3.3R 1%"),
        (6, "3.3R 1%"),
        (8, "100k 0.01%"),
        (9, "100k 0.01%"),
        (10, "10k 0.1%"),
        (11, "10k 0.1%"),
        (12, "10M 1%"),
        (14, "47k 1%"),
        (15, "68k 1%"),
        (16, "0.1R 1%"),
    ]:
        EXPECTED_VALUES["R" + str(index + 16 * ci)] = value
    EXPECTED_VALUES["C" + str(9 + 14 * ci)] = "47uF 25V X7S"
    for index in (10, 11):
        EXPECTED_VALUES["C" + str(index + 14 * ci)] = "47uF 6.3V X7S"
EXPECTED["J2"] = dict(
    zip(
        map(str, range(1, 21)),
        [
            "ADC_LP",
            "SENSE_LP",
            "AGND",
            "ADC_LN",
            "SENSE_LN",
            "AGND",
            "REF_ADC1",
            "AGND",
            "ADC_RP",
            "SENSE_RP",
            "AGND",
            "ADC_RN",
            "SENSE_RN",
            "AGND",
            "REF_ADC2",
            "AGND",
            "PD_GATED",
            "BIAS_OK",
            "DRV_ENABLE",
            "AGND",
        ],
    )
)
EXPECTED_VALUES["J2"] = "Conn_02x10_Odd_Even"
EXPECTED.update(
    {
        "U7": {
            "1": "BIAS_OK",
            "2": "BIAS_OK",
            "3": "V5_REG",
            "4": "BIAS_SHIFT_L",
            "5": "THRESH_UPPER",
            "6": "THRESH_LOWER",
            "7": "BIAS_SHIFT_L",
            "8": "BIAS_SHIFT_R",
            "9": "THRESH_UPPER",
            "10": "THRESH_LOWER",
            "11": "BIAS_SHIFT_R",
            "12": "AGND",
            "13": "BIAS_OK",
            "14": "BIAS_OK",
        },
        "U8": {
            "1": "PD_GATED",
            "2": "AGND",
            "3": "BIAS_OK",
            "4": "unconnected-(U8-Pad4)",
            "5": "V5_REG",
            "6": "V5_REG",
        },
        "R34": {"1": "V5_REG", "2": "BIAS_SHIFT_L"},
        "R35": {"1": "BIAS_SHIFT_L", "2": "NBIAS_L"},
        "R36": {"1": "V5_REG", "2": "BIAS_SHIFT_R"},
        "R37": {"1": "BIAS_SHIFT_R", "2": "NBIAS_R"},
        "R38": {"1": "V5_REG", "2": "THRESH_UPPER"},
        "R39": {"1": "THRESH_UPPER", "2": "AGND"},
        "R40": {"1": "V5_REG", "2": "THRESH_LOWER"},
        "R41": {"1": "THRESH_LOWER", "2": "AGND"},
        "R42": {"1": "V5_REG", "2": "BIAS_OK"},
        "R43": {"1": "DRV_ENABLE", "2": "PD_GATED"},
        "R44": {"1": "PD_GATED", "2": "AGND"},
        "C35": {"1": "V5_REG", "2": "AGND"},
        "C36": {"1": "V5_REG", "2": "AGND"},
    }
)
EXPECTED_VALUES.update(
    {
        "U7": "TLV9024DR",
        "U8": "TPS3808G50DBVR",
        **{
            "R" + str(k): v
            for k, v in [
                (34, "100k 0.01%"),
                (35, "10k 0.01%"),
                (36, "100k 0.01%"),
                (37, "10k 0.01%"),
                (38, "161k 0.01%"),
                (39, "10k 0.01%"),
                (40, "240k 0.01%"),
                (41, "10k 0.01%"),
                (42, "10k 1%"),
                (43, "10k 1%"),
                (44, "100k 1%"),
            ]
        },
        "C35": "100nF 16V X7R",
        "C36": "100nF 16V X7R",
    }
)


def check_circuit(parts, pins):
    assert pins == EXPECTED, "R2 independent terminal contract mismatch"
    assert set(parts) == set(EXPECTED_VALUES)
    for ref, value in EXPECTED_VALUES.items():
        assert parts[ref].findtext("value") == value, ref
    return True


def bias_window_truth(left, right, v5=5):
    sense = {ch: (v5 + 10 * bias) / 11 for ch, bias in [("L", left), ("R", right)]}
    upper = v5 * 10000 / 171000
    lower = v5 * 10000 / 250000
    nodes = dict(BIAS_SHIFT_L=sense["L"], BIAS_SHIFT_R=sense["R"], THRESH_UPPER=upper, THRESH_LOWER=lower)
    pairs = [("4", "5"), ("6", "7"), ("8", "9"), ("10", "11")]
    return all(nodes[EXPECTED["U7"][plus]] > nodes[EXPECTED["U7"][minus]] for minus, plus in pairs)


def pd_levels(reset_max=0.4, resistor_error=0.03, enable_min=2.7, negative_rails=(-0.286, -0.172)):
    """Guaranteed-level screen; bounded valid rails only, not abrupt fault dynamics."""
    assert reset_max >= 0 and 0 < resistor_error < 0.1
    off = []
    on = []
    for b1, b2, *signs in itertools.product(negative_rails, negative_rails, *([(-1, 1)] * 6)):
        series = [47000 * (1 + signs[i] * resistor_error) for i in (0, 1)]
        pull = [68000 * (1 + signs[i + 2] * resistor_error) for i in (0, 1)]
        request = 10000 * (1 + signs[4] * resistor_error)
        ground = 100000 * (1 + signs[5] * resistor_error)
        branch = [series[i] + pull[i] for i in (0, 1)]
        gate = (enable_min / request + b1 / branch[0] + b2 / branch[1]) / (
            1 / request + 1 / ground + 1 / branch[0] + 1 / branch[1]
        )
        for i, b in enumerate((b1, b2)):
            ratio = pull[i] / branch[i]
            error = 100e-9 * (series[i] * pull[i] / branch[i])
            off.append((reset_max - b) * ratio + error)
            on.append((gate - b) * ratio - error)
    return dict(
        maximum_disabled_pd_above_vminus_v=max(off),
        minimum_enabled_pd_above_vminus_v=min(on),
        manufacturer_disable_below_v=0.55,
        manufacturer_enable_above_v=1.15,
        static_levels_pass=max(off) < 0.55 and min(on) > 1.15,
        guaranteed_reset_low_v=reset_max,
        external_enable_min_v=enable_min,
        resistor_full_allocation_fraction=resistor_error,
        delay_or_partial_power_verified=False,
    )


def leakage_screen():
    return dict(
        reference_thevenin_ohm=50000,
        reference_divider_load_a=3.3 / 200000,
        full_temperature_opa192_bias_screen_v=5e-9 * 50000,
        added_0p2na_leakage_shift_v=0.2e-9 * 50000,
        finite_servo_dc_gain=number(EXPECTED_VALUES["R12"]) / 5000,
        integral_crossover_hz=1 / (2 * 3.141592653589793 * 5000 * 1e-6),
        physical_leakage_or_reference_loading_verified=False,
    )
