"""P01 source replacement and total-path resistance requirements.

Values tagged as allocations require measurement/selection. They are not
guaranteed properties of the existing routed PSU, E25, headers or harnesses.
"""

from copy import deepcopy

TI = "https://www.ti.com/lit/ds/symlink/"
ADI = "https://www.analog.com/media/en/technical-documentation/data-sheets/"

SOURCES = {
    "TPS62903": {
        "url": TI + "tps62903.pdf",
        "revision": "SLVSES3A, March 2021",
        "sections": "5, 6.3, 6.5, 7.3.1, 8.2",
        "facts": "External FB full-temperature error ±0.9%; FB leakage max70nA; VIN3..17V; 3A. Direct COUT max50uF at1MHz; extra capacitance requires associated series resistance. MODE21k selects external FB,1MHz,forced PWM,no discharge.",
    },
    "LT3045": {
        "url": ADI + "3045fa.pdf",
        "revision": "Rev. D",
        "sections": "Electrical Characteristics; Pin Functions; Applications pp16,23",
        "facts": "500mA. External SET drive must sink100uA and limit clamp current to20mA. Full-temperature output offset±2mV; OUTS stays local at COUT. DD exposed pad is GND. COUT effective minimum10uF.",
    },
    "ADR4550B": {
        "url": ADI + "adr4520_4525_4530_4533_4540_4550.pdf",
        "revision": "Rev. G, July 2025",
        "sections": "Table6; Table9; Terminology",
        "facts": "SOIC B grade initial error±1mV; box TC2ppm/C over−40..125C; line max10ppm/V; source-load regulation max80ppm/mA. Minimum5.3V input reserved at≤2mA. Solder, humidity, hysteresis and aging require independent allocations/qualification; typical drift is not a guaranteed lifetime limit.",
    },
    "OPA4192": {
        "url": TI + "opa4192.pdf",
        "revision": "SBOS620E, November 2015",
        "sections": "Pin Configuration; Electrical Characteristics",
        "facts": "Retain the existing conservative full-temperature350uV offset and5nA input-bias allocations. Reuse U5C as a unity-gain local SET buffer; its changed compensation needs a fresh loop check.",
    },
}


def candidate():
    """Return independent mutable inputs for analysis and fault regressions."""
    common = dict(
        supply_length_m=0.35,
        return_length_m=0.35,
        conductor_area_mm2=2.08,
        copper_resistivity_20c_ohm_m=1.8e-8,
        copper_temperature_coefficient_per_c=0.00393,
        copper_maximum_c=85,
        mated_contacts_per_conductor=2,
        contact_resistance_hot_end_of_life_max_ohm=0.001,
        # Cross-domain ground error remains even with separate harness returns.
        shared_ground_transfer_resistance_max_ohm=0.001,
    )
    analog = dict(
        **common,
        source_pcb_supply_max_ohm=0.001,
        source_pcb_return_max_ohm=0.001,
        e25_pcb_supply_max_ohm=0.0005,
        e25_pcb_return_max_ohm=0.0005,
        destination_pcb_supply_max_ohm=0.0005,
        destination_pcb_return_max_ohm=0.0005,
    )
    digital = dict(
        **common,
        source_pcb_supply_max_ohm=0.0015,
        source_pcb_return_max_ohm=0.0015,
        e25_pcb_supply_max_ohm=0.0015,
        e25_pcb_return_max_ohm=0.0015,
        destination_pcb_supply_max_ohm=0.001,
        destination_pcb_return_max_ohm=0.001,
    )
    return deepcopy(
        dict(
            revision="P01",
            topology="Source feedback stays upstream of E25; all source/protected names and connector pin orders unchanged",
            input_boundary_v=[10.5, 13.2],
            analog_reference=dict(
                nominal_v=5.0,
                initial_error_v=0.001,
                box_temperature_coefficient_per_c=2e-6,
                box_temperature_span_c=165,
                line_regulation_per_v=10e-6,
                line_input_span_v=9.9,
                reference_load_max_a=1e-6,
                load_regulation_per_ma=80e-6,
                # Requirements, not guaranteed typical-drift figures.
                assembly_hysteresis_humidity_aging_reserve_v=0.002,
                buffer_offset_v=350e-6,
                buffer_bias_abs_a=5e-9,
                input_filter_ohm=1000,
                set_feedback_ohm=100000,
                set_isolation_ohm=6800,
                set_current_max_a=102e-6,
                set_clamp_current_max_a=0.020,
                maximum_buffer_rail_v=24,
                ldo_offset_v=0.002,
                ldo_extra_load_error_v=0.0005,
                ldo_extra_voltage_error_v=0.0003,
                ldo_extra_line_error_v=54e-6,
                dropout_allocation_v=0.600,
                reference_minimum_supply_v=5.3,
                ldo_ground_current_allocation_a=0.025,
                reference_supply_current_max_a=0.000950,
                minimum_effective_local_output_capacitance_f=10e-6,
            ),
            digital_feedback=dict(
                reference_v=0.6,
                full_temperature_reference_fraction=0.009,
                top_series_ohm=[14700, 33],
                bottom_ohm=2000,
                total_resistor_fraction=0.001,
                input_leakage_abs_a=70e-9,
                mode_to_ground_ohm=21000,
                frequency_allocation_hz=[0.8e6, 1.2e6],
                inductor_nominal_h=2.2e-6,
                inductor_tolerance_fraction=0.20,
                inductor_hot_dcr_allocation_ohm=0.050,
                high_side_hot_resistance_max_ohm=0.111,
                low_side_hot_resistance_max_ohm=0.040,
                minimum_peak_current_limit_a=4.0,
                maximum_peak_current_limit_a=5.5,
                inductor_hot_saturation_requirement_a=5.5,
                maximum_direct_effective_capacitance_f=50e-6,
                minimum_direct_effective_capacitance_f=6e-6,
                local_effective_capacitance_f=[10e-6, 40e-6],
                soft_start_capacitance_f=[0.8e-6, 1.2e-6],
                soft_start_current_a=[2.3e-6, 2.7e-6],
                tracking_gain=[0.740, 0.760],
                extra_load_capacitance_allocation_f=200e-6,
                # Allocation, not a maximum from efficiency graphs or RthetaJA.
                converter_loss_allocation_w=0.90,
                maximum_junction_allocation_c=125,
                ambient_allocation_c=55,
            ),
            rails={
                "V5_REG": dict(
                    distribution=analog,
                    ripple_reserve_v=0.001,
                    load_step_reserve_v=0.002,
                ),
                "5V_DIG": dict(
                    distribution=digital,
                    ripple_reserve_v=0.010,
                    load_step_reserve_v=0.010,
                ),
            },
        )
    )


def circuit():
    """Review-only replacement pin/net contract; not a native schematic/PCB."""
    return dict(
        scope="Replacement channels for a new PSU revision, not drop-in substitutions",
        feedback_crosses_disconnect=False,
        analog_output_sense_net="V5_REG_SRC",
        digital_feedback_top_net="5V_DIG_SRC",
        devices={
            "U2_NEW": dict(
                part="TPS62903RPJR",
                package="TI RPJ0009A; new pad/stencil review required",
                pins={
                    "1": None,
                    "2": "DIG_SW_NEW",
                    "3": "5V_DIG_SRC",
                    "4": "AGND",
                    "5": "SUPPLY_ENABLE",
                    "6": "VIN_PROTECTED",
                    "7": "DIG_MODE_NEW",
                    "8": "DIG_SS_NEW",
                    "9": "DIG_FB_NEW",
                },
            ),
            "U9_NEW": dict(
                part="LT3045IDD#PBF",
                package="ADI DD 10-lead3x3 DFN plus ground exposed pad; not old U9 EP/OUT",
                pins={
                    "1": "V5_PRE",
                    "2": "V5_PRE",
                    "3": "V5_PRE",
                    "4": None,
                    "5": "AGND",
                    "6": "V5_PRE",
                    "7": "V5_REG_SET",
                    "8": "AGND",
                    "9": "V5_REG_SRC",
                    "10": "V5_REG_SRC",
                    "11": "AGND",
                },
            ),
            "U14_NEW": dict(
                part="ADR4550BRZ",
                package="8-lead SOIC; new layout required",
                pins={
                    "1": None,
                    "2": "V5_PRE",
                    "3": None,
                    "4": "AGND",
                    "5": None,
                    "6": "PREF_5V_NEW",
                    "7": None,
                    "8": None,
                },
            ),
            "U5C_REUSED": dict(
                part="OPA4192ID channel C",
                pins={
                    "4": "RAW_P22",
                    "11": "AGND",
                    "10": "PREF_5V_FILTER_NEW",
                    "9": "V5_REG_FB",
                    "8": "V5_REG_DRIVE",
                },
            ),
        },
        passive_connections=[
            ["R_DIG_TOP_A", 14700, "5V_DIG_SRC", "DIG_TOP_MID_NEW"],
            ["R_DIG_TOP_B", 33, "DIG_TOP_MID_NEW", "DIG_FB_NEW"],
            ["R_DIG_BOTTOM", 2000, "DIG_FB_NEW", "AGND"],
            ["R_DIG_MODE", 21000, "DIG_MODE_NEW", "AGND"],
            ["L_DIG_NEW", 2.2e-6, "DIG_SW_NEW", "5V_DIG_SRC"],
            ["C_DIG_SS", 1e-6, "DIG_SS_NEW", "AGND"],
            ["R_REF_FILTER", 1000, "PREF_5V_NEW", "PREF_5V_FILTER_NEW"],
            ["C_REF_FILTER", 1e-6, "PREF_5V_FILTER_NEW", "AGND"],
            ["R_SET_LIMIT", 6800, "V5_REG_DRIVE", "V5_REG_SET"],
            ["R_SET_FB", 100000, "V5_REG_SET", "V5_REG_FB"],
            ["C_SET_COMP", 47e-9, "V5_REG_DRIVE", "V5_REG_FB"],
            ["C_SET", 100e-9, "V5_REG_SET", "AGND"],
        ],
        change_notes=[
            "Remove old V5_REG gain-two divider bottom resistor; use local unity DC SET feedback.",
            "LT3045 OUTS ties to its local output capacitor, upstream of E25.",
            "LT3045 PGFB ties to V5_PRE to disable its fast SET-charge mode; PG unused.",
            "Add manufacturer-required local input/output/reference bypass capacitors; effective values, MPNs and placement remain open.",
            "Replace old TPS62933F bootstrap/RT network; new part has different pins, mode and inductance.",
        ],
        native_erc_verified=False,
        native_pcb_layout_implemented=False,
        physical_fit_verified=False,
        build_ready=False,
    )
