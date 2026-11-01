"""Conditional E28 AUX recenter contract from actual reference-window parts.

A receiver range is a design requirement, not an accepted source/harness property.
No unpowered/brownout waveform or input-leakage characterization is inferred.
"""

import hashlib
import itertools
import json
from pathlib import Path

from .manufacturer import ROOT
from .positive import components


def value(part):
    word = part["part"].split()[0]
    return float(word.rstrip("kM")) * (1e6 if word.endswith("M") else 1e3 if word.endswith("k") else 1)


def screen(parts=None, receiver_interval=(2.50, 2.70)):
    parts = components() if parts is None else parts
    # Precision native parts are0.01%/5ppm;100C is maxdistancefrom25C.
    precision_fraction = 0.0001 + 5e-6 * 100
    rows = []
    for name, upper in (("REF_LOW", True), ("REF_HIGH", False)):
        aux = name + "_AUX"
        positive = name + "_POSITIVE"
        output = name + "_OK"

        def resistor(nets):
            return next(
                p for p in parts if p["ref"].startswith("R") and {x["net"] for x in p["pins"]} == set(nets)
            )

        top = resistor(("V2V5_AUX", aux))
        bottom = resistor((aux, "AGND"))
        ser = resistor((positive, "PROTECT_REF" if upper else aux))
        feedback = resistor((positive, output))
        for p in (top, bottom, ser):
            assert "0.01% 5ppm" in p["part"]
        assert value(feedback) == 20e6
        margins = []
        for va, vr, st, sb, ss, sf, op, ip, im in itertools.product(
            receiver_interval,
            (1.25 * 0.997, 1.25 * 1.003),
            (-1, 1),
            (-1, 1),
            (-1, 1),
            (-1, 1),
            (0, 1),
            (-1, 1),
            (-1, 1),
        ):
            rt = value(top) * (1 + st * precision_fraction)
            rb = value(bottom) * (1 + sb * precision_fraction)
            rs = value(ser) * (1 + ss * precision_fraction)
            # 2%total feedback-R envelope is an explicit unaccepted construction
            # requirement, covering its1%initial andadditionaltemperature/aging.
            rf = value(feedback) * (1 + sf * 0.02)
            vo = va * op
            if upper:
                vm = (va / rt - im * 1.2e-9) / (1 / rt + 1 / rb)
                vp = (vr / rs + vo / rf - ip * 1.2e-9) / (1 / rs + 1 / rf)
            else:
                # AUXdivider is loaded by the10kseries+20Mfeedback branch.
                # Solve the two actual finite-impedance nodes together.
                g11 = 1 / rt + 1 / rb + 1 / rs
                g22 = 1 / rs + 1 / rf
                cross = -1 / rs
                a = va / rt
                b = vo / rf - ip * 1.2e-9
                vp = (b * g11 - cross * a) / (g11 * g22 - cross * cross)
                vm = vr  # reference source error already bounded±0.3%
            margins.append(vp - vm - 0.004)
        rows.append(
            dict(
                name=name,
                parts=[p["ref"] for p in (top, bottom, ser, feedback)],
                minimum_asserted_margin_v=min(margins),
                total_precision_R_fraction=precision_fraction,
                feedback_R_total_fraction_requirement=0.02,
                offset_abs_v=0.004,
                input_bias_abs_a=1.2e-9,
            )
        )
    maximum_aux = max(receiver_interval)
    return dict(
        receiver_interval_requirement_v=list(receiver_interval),
        source_or_harness_accepted=False,
        complete_aux_load_ledger_closed=False,
        lvc_input_leakage_and_delta_icc_full_temperature_ledger_closed=False,
        comparator_error_at_actual_supply_and_common_mode_accepted=False,
        comparator_offset_table_condition="TLV1824 offset table defaults VS12V/VCMVS/2; operating-point transfer/board leakage remains an acceptance requirement, not an extrapolated guarantee",
        selected_comparator_minimum_supply_v=2.4,
        supervisor_release_maximum_screen_v=2.478,
        startup_release_guard_v=min(receiver_interval) - 2.478,
        reference_window=rows,
        logic_supply_characterized_band_v=[2.3, 2.7],
        receiver_within_current_logic_band=min(receiver_interval) >= 2.3 and maximum_aux <= 2.7,
        master_voh_min_v_at2v3_2v3ma_fulltemp=1.97,
        u20_mr_vih_max_v=0.7 * maximum_aux,
        u20_mr_static_high_margin_v=1.97 - 0.7 * maximum_aux,
        aup_vih_max_v=1.6,
        lvc_vih_requirement_v=1.7,
        si8751_vih_max_v=0.5 * maximum_aux,
        master_external_load_requirement_a=0.0001,
        master_total_high_load_requirement_a=0.0023,
        si8751_input_leakage_maximum_guaranteed=False,
        complete_master_load_accepted=False,
        complete_aux_load_allocation_a=0.060,
        retained_four_driver_supply_current_max_a=0.038,
        aux_source_minimum_needed_v=min(receiver_interval),
        partial_power=dict(
            settled_logic_mask_tested=False,
            falling_slew_bounded=False,
            supervisor_propagation_and_actual_gate_turnoff_waveforms_measured=False,
            external_receivers_selected=False,
            external_drive_into_J6_J9_outputs_forbidden_requirement=True,
        ),
        physical_qualified=False,
        build_ready=False,
    )


def main():
    result = screen()
    result["primary_sources"] = {
        "TLV1824": dict(
            url="https://www.ti.com/lit/ds/symlink/tlv1824.pdf",
            sha256=hashlib.sha256(Path("/private/tmp/e28-tlv1824.pdf").read_bytes()).hexdigest(),
            sections="5.3/5.7",
        ),
        "AUP": dict(
            url="https://www.ti.com/lit/ds/symlink/sn74aup2g08.pdf",
            sha256=hashlib.sha256(Path("/private/tmp/e28-sn74aup2g08.pdf").read_bytes()).hexdigest(),
            sections="5.3/5.5",
        ),
        "TPS3890": dict(
            url="https://www.ti.com/lit/ds/symlink/tps3890.pdf",
            sha256=hashlib.sha256(Path("/private/tmp/e28-tps3890.pdf").read_bytes()).hexdigest(),
            sections="6.5/6.6",
        ),
    }
    result["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (ROOT / "generated/auxiliary-recenter-screen.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "AUX receiver contract",
        result["receiver_interval_requirement_v"],
        "window margins",
        [(r["name"], r["minimum_asserted_margin_v"]) for r in result["reference_window"]],
        "MRmargin",
        result["u20_mr_static_high_margin_v"],
    )


if __name__ == "__main__":
    main()
