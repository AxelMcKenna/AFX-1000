"""Conditional selected3G17 receiving screen; discrete-row transfer is not qualification."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def screen():
    auxlo, auxhi = 2.5, 2.7
    # 3G17 SCES470F p5 actual max1.87@3V,1.56@2.3V,125C; no interpolation claim.
    vt_enclosure = 1.87
    total_sink = 5e-6 + 0.25e-6 + 2e-6
    rhi, rlo = 10000 * 1.02, 10000 * 0.98
    high = auxlo - total_sink * rhi
    lowload = auxhi / rlo + total_sink
    nfload = 2.652 / (15000 * 0.97) + 7e-6
    openv = 7e-6 * 15000 * 1.03
    # U49 AUP2G14 actual85C column1.97V@2.3V,2.3mA (not25C2.05V).
    nfhigh = 1.97
    return dict(
        actual_buffer="SN74LVC3G17DCUR",
        actual_pin_pairs=[[1, 7], [3, 5], [6, 2]],
        receiver_VCC_allocation_v=[auxlo, auxhi],
        Schmitt_VTplus_discrete_upper_enclosure_v=vt_enclosure,
        supervisor_pullup_ohm=10000,
        supervisor_high_receiving_v=high,
        supervisor_high_margin_v=high - vt_enclosure,
        supervisor_low_sink_allocation_a=lowload,
        TPS3890_low_current_test_a=0.0004,
        TPS3890_low_voltage_max_v=0.25,
        supervisor_low_sink_times1p2_a=lowload * 1.2,
        NF_receiver_pulldown_ohm=15000,
        NF_total_resistance_error_fraction=0.03,
        NF_source_load_allocation_a=nfload,
        NF_open_input_max_v=openv,
        NF_U49_loaded_VOH85C_discrete_row_min_v=nfhigh,
        NF_conditional_static_high_margin_v=nfhigh - vt_enclosure,
        NF_U49_rated_temperature_C=[-40, 85],
        receiver_rated_temperature_C=[-40, 125],
        buffer_output_load_each_max_allocation_a=22e-6,
        buffer_VOH_100uA_continuous_VCC_min_v=auxlo - 0.1,
        downstream_LVC_VIH_enclosure_v=2.0,
        downstream_static_high_margin_v=auxlo - 0.1 - 2,
        continuous_VCC_intermediate_VI_current_transfer_verified=False,
        NF_loaded_VOH_supply_current_transfer_verified=False,
        complete_node_C_received_edges_and_supervisor_delay_accepted=False,
        slow_raw_input_Schmitt_is_actual_selected_device=True,
        source_READY_not_qualified_below_AUX_2p3V=True,
        partial_VCC_0_to_1p65V_failOFF_dynamic_capture_accepted=False,
        AUX_load_dynamic_heat_PDN_and_50nF_effective_bypass_accepted=False,
        mated_connector_tail_trim_wirebend_and_floor_fit_accepted=False,
        physical_and_fabrication_qualified=False,
    )


def main():
    dest = ROOT / "generated/reset-buffer-proposal"
    primary = dest / "sources"
    paths = [p for p in primary.iterdir() if p.is_file() and p.stat().st_size] + [
        Path(__file__),
        ROOT / "reset_buffer_patterns.py",
        ROOT / "control.py",
    ]
    contract = (
        ROOT.parents[2]
        / "qualification/boards/startup_negative_circuit/ready_integration/integration-contract.json"
    )
    if contract.exists():
        paths.append(contract)
    report = screen()
    assert report["supervisor_low_sink_times1p2_a"] < 0.0004
    report.update(
        source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        visual_reviews=[
            dict(
                path="sn74lvc3g17.pdf",
                pages=[24, 25, 26],
                drawing="4225266/A09/2014",
                land_mm=[0.85, 0.3],
                columns_mm=3.1,
                pitch_mm=0.5,
                R_mm=0.05,
                NSMD_expansion_mm=0.05,
                stencil_mm=0.125,
            ),
            dict(
                path="kemet-X7R-C1002.pdf",
                pages=[12],
                revision="2026-09-01",
                DensityB=dict(C_centre_offset=0.80, Y_horizontal=0.95, X_vertical=1.00, V1=3.10, V2=1.50),
            ),
            dict(
                path="jst-PH-mirror.pdf",
                pages=[1, 2],
                manufacturer_catalog_distributor_hosted=True,
                current_official_text_compared=True,
                editions_identical_not_asserted=True,
                pitch_mm=2,
                PCB_drill_mm=[0.7, 0.8],
                stock_KiCad_drill_mm=0.75,
                mated_height_reference_mm=8,
                stock_tail_mm=3.4,
                tail_trim_requirement_mm=1.5,
                trim_process_accepted=False,
            ),
        ],
        original_manufacturer_notices_preserved=True,
    )
    (dest / "receiving-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(screen(), indent=2))


if __name__ == "__main__":
    main()
