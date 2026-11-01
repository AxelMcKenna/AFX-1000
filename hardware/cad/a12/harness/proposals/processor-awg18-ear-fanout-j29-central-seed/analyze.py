"""Seed3 endpoint/R1 conditional budget; never a complete assembled PDN pass."""

import hashlib
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist, number
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.power_distribution.p03.analysis import source_bounds
from hardware.electronics.power_distribution.p03.models import disconnect_startup

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]
SRC = ROOT / "sources/repository"
CARRIER = SRC / "hardware/cad/a12/harness/proposals/processor-awg18-ear-fanout-j29-central"
PDN = (
    SRC
    / "hardware/cad/a12/harness/proposals/processor-awg18-ear-fanout-j29-central-pdn/generated/coarse.json"
)
P03 = SRC / "hardware/electronics/power_distribution/p03/candidates/aux-u10-combined/generated/netlist.xml"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def power_rating(nominal_r, ambient, hotmax):
    # Both primary30100/30121 impose this separate resistance-value derating.
    value_factor = 1 if nominal_r <= 0.1 else 1 - 0.2 * (nominal_r - 0.1) / 0.4
    return value_factor * max(0, min(1, (hotmax - ambient) / (hotmax - 70)))


def resistor_interval(nominal, bodytemp=150, aging=0.01, solder=0.005, absolute_drift=0):
    # Explicit test-based additive scenario; NOT a general mission-life guarantee.
    error = 0.01 + 75e-6 * abs(bodytemp - 25) + aging + solder
    return [nominal * (1 - error) - absolute_drift, nominal * (1 + error) + absolute_drift]


def run():
    capture = json.loads((ROOT / "capture.json").read_text())
    for p, h in capture["source_sha256"].items():
        assert sha(SRC / p) == h
    parts, pins = netlist(CARRIER / "generated/netlist.xml")
    p03, _ = netlist(P03)
    assert number(parts["R1"].findtext("value")) == 0.47 and pins["R1"] == {"1": "5V_DIG", "2": "SEED_VIN"}
    caps = []
    for ref, p in pins.items():
        if ref.startswith("C") and set(p.values()) == {"SEED_VIN", "AGND"}:
            caps.append(
                dict(
                    ref=ref,
                    native_value=parts[ref].findtext("value"),
                    nominal_f=number(parts[ref].findtext("value")),
                )
            )
    assert {c["ref"] for c in caps} == {"C1", "C2"}
    sources, source_details = source_bounds(p03)
    coarse = json.loads(PDN.read_text())
    loops = coarse["fixture_loop_copper_drop_intervals_v"]["None"]["seed"]
    source = sources["DIG"]
    load = 1.0
    # Source-to-J13 design allocations. Neither measured bounds nor a coupled replacement.
    # The8mohm lead removes the old .5mohm E19 escape share from the8.5mohm total;
    # actual E19 copper is supplied separately by its finite matrix.
    allocations = dict(
        P03_regulator_to_positive_stud=0.001,
        source_positive_lug_lead=0.002,
        E28_positive_copper=0.003,
        E28_four_ON_switches=0.020 / 4,
        processor_force_lead_excluding_E19_escape=0.008,
        processor_return_lead_excluding_E19_escape=0.008,
        digital_return_bar=0.002,
    )
    assumed_max_shared_a = 2.4
    known_design_drop = assumed_max_shared_a * sum(allocations.values())
    dynamic = 0.020
    spread = 0.002
    # The existing E28PCB return violates2mohm even as a diagnostic; retain symbolically.
    unknown_terms = [
        "E28_J4_to_J8_actual_ground_transfer_with_all_control_and_cap_currents",
        "P03_signed_reference_and_return_multiport_offset_including_average_converter_ground_currents",
        "actual_socket_VIN_contact_and_unknown_AGND_DGND_current_sharing",
        "remote_exported3V3_positive_and_ground_loops",
        "native_mesh/material/contact/temperature uncertainty",
        "full_effective_C_and_loadstep_startup_or_fault_drop",
    ]
    rows = []
    for mpn, nominal, tmax, absdrift in [
        ("WSL2512R4700FEA", 0.47, 170, 0.001),
        ("WSLT2512R4700FEA", 0.47, 275, 0),
        ("WSL2512R1000FEA", 0.10, 170, 0.001),
    ]:
        ri = resistor_interval(nominal, absolute_drift=absdrift)
        p = load * load * ri[1]
        ambient = []
        for ta in [40, 70, 85, 100, 125]:
            rating = power_rating(nominal, ta, tmax)
            ambient.append(
                dict(
                    ambient_scenario_c=ta,
                    manufacturer_value_and_ambient_derated_rating_w=rating,
                    factor1p2_times_load_power_w=1.2 * p,
                    power_ratio_rating_to_load=rating / p,
                    twenty_percent_power_capacity_screen=rating >= 1.2 * p,
                )
            )
        # This is the intercept before all explicitly unknown signed drops/contacts.
        low = source[0] - dynamic - spread - known_design_drop - loops[1] - load * ri[1]
        high = source[1] + dynamic + spread
        maxambient = tmax - (1.2 * p / power_rating(nominal, 70, tmax)) * (tmax - 70)
        rows.append(
            dict(
                mpn=mpn,
                proposed_not_installed=True,
                nominal_ohm=nominal,
                component_TCR_ppm_per_c=75,
                TCR_table_body_temperature_domain_c=[-55, 150 if "WSLT" in mpn else 155],
                body_temperature_used_for_TCR_scenario_c=150,
                resistance_scenario_ohm=ri,
                total_drift_is_not_mission_life_guarantee=True,
                load_a=load,
                resistor_max_power_scenario_w=p,
                manufacturer_P70_after_high_R_derating_w=power_rating(nominal, 70, tmax),
                ambient_scenarios=ambient,
                maximum_ambient_for_20percent_power_capacity_under_stated_Rscenario_c=maxambient,
                maximum_actual_body_temperature_for_this_TCRscreen_c=150,
                required_theta_to_hold150body_at125ambient_k_per_w=25 / p,
                required_theta_to_hold150body_at100ambient_k_per_w=50 / p,
                conditional_VIN_intercept_v=[low, high],
                unallocated_downward_voltage_budget_to_module4V_v=low - 4,
                unknown_drop_or_ground_terms=unknown_terms,
                endpoint_or_thermal_qualified=False,
                RC_isolation_change_vs_0p47_factor=nominal / 0.47,
            )
        )
    master = disconnect_startup()["DIG"]
    slew = master["maximum_slew_v_per_s"]
    nominal_external_c = sum(c["nominal_f"] for c in caps)
    cmax = nominal_external_c * 1.2 * 1.15
    r = rows[1]["resistance_scenario_ohm"]
    ramp_i = cmax * slew
    startup = dict(
        actual_local_capacitors=caps,
        known_external_nominal_subtotal_f=nominal_external_c,
        illustrative_initial20percent_positive_X7R_temperature15percent_subtotal_f=cmax,
        capacitor_MPNs_effective_C_ESR_and_maximums_accepted=False,
        module_onboard_diagram10uF_plus100nF_is_not_complete_maximum_inventory=True,
        complete_module_input_capacitance_and_internal_regulator_part_unverified=True,
        retained_E28_max_slew_v_per_s=slew,
        E28_slew_and_7p1mF_complete_network_qualified=False,
        known_external_subtotal_ramp_current_a=ramp_i,
        not_additional_to_shared7p1mF_if_already_included=True,
        R1_1A_plus_known_external_ramp_current_a=load + ramp_i,
        WSLT_1A_plus_known_external_ramp_power_w=(load + ramp_i) ** 2 * r[1],
        late_closure_external_subtotal_energy_j=0.5 * cmax * 5.1**2,
        late_closure_unlimited_resistive_peak_a=5.1 / r[0],
        late_closure_unlimited_R1_peak_w=5.1**2 / r[0],
        hotplug_peak_is_not_rating_or_proven_actual_waveform=True,
        resistor_pulse_repetition_and_E28_SOAs_not_qualified=True,
        whole_source_startup_guard_feed_and_module_boot_not_qualified=True,
    )
    tree = read_sexpr((CARRIER / "processor_carrier.kicad_pcb").read_text())
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "R1"] for p in children(f, "property"))
    )
    lands = [
        dict(
            pin=p[1],
            local_at=list(map(float, first(p, "at")[1:3])),
            size_mm=list(map(float, first(p, "size")[1:3])),
        )
        for p in children(fp, "pad")
    ]
    recommendation = dict(
        candidate_MPN="WSLT2512R4700FEA",
        same_nominal_R_preserves_RC=True,
        candidate_voltage_does_not_demonstrate_need_to_reduce0p47_at1A=True,
        existing_generic1W_not_a_complete_selection=True,
        preserve_native_central_source=True,
        native_actual_R1_lands=lands,
        manufacturer_recommended_lands=dict(each_mm=[1.65, 3.68], inner_gap_mm=4.06),
        manufacturer_pad_to_existing_alternate_assembly_approval=False,
        maximum_body_mm=[6.604, 3.434, 0.889],
        nominal_dissipation_inside_existing_Seed_input_power_not_extra_whole_unit_heat=True,
        selection_not_promoted_to_BOM_or_fabrication=True,
    )
    sdk_cpp = (SRC / "build-hardware/libDaisy/src/daisy_seed.cpp").read_text()
    sdk_h = (SRC / "build-hardware/libDaisy/src/daisy_seed.h").read_text()
    assert "seed_3_pin(PORTH, 6)" in sdk_cpp and "return BoardVersion::DAISY_SEED_3" in sdk_cpp
    assert (
        "DAISY_SEED_3" in sdk_h
        and "Same configuration used for Seed Rev4, Seed Rev7 (1.2), and Seed3" in sdk_cpp
    )
    firmware = dict(
        pinned_commit=json.loads((SRC / "hardware/firmware/dependencies.json").read_text())["libDaisy"][
            "commit"
        ],
        source_contains_Seed3_PH6_detection=True,
        source_contains_Seed3_enum=True,
        source_default_codec_init_comment_includes_Seed3=True,
        exact_assembled_revision_and_USB_or_bootloader_runtime_tested=False,
        external_audio_profile_and_fixed_pin_usage_requires_physical_test=True,
    )
    report = dict(
        scope=__doc__,
        source_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                PDN,
                P03,
                CARRIER / "generated/netlist.xml",
                CARRIER / "processor_carrier.kicad_pcb",
                ROOT / "capture.json",
                Path(__file__),
                ROOT / "sources/primary/Daisy_Seed3_datasheet-v2p1p0.pdf",
                ROOT / "sources/primary/Vishay-30100-wsl-2023.pdf",
                ROOT / "sources/primary/Vishay-30121-wslt2512-2024.pdf",
            ]
        },
        selected_module="DaisySeed3",
        manufacturer_datasheet_revision="v2.1.0",
        VIN_operating_v=[4, 17],
        VIN_operating_basis="Table3printedp7 explicitly expectedoperatingrange andPowerVINp11; NOT inferredfromabsoluteTable1",
        one_ampere_retained_not_reduced=True,
        half_ampere_legacy_note_and_screen_superseded_only_in_this_new_packet=True,
        source_voltage_interval_v=source,
        source_interval_assumptions=source_details,
        source_dynamic_allocation_v=dynamic,
        local_spread_allocation_v=spread,
        source_to_receiver_design_resistances_ohm=allocations,
        source_shared_current_design_envelope_a=assumed_max_shared_a,
        source_design_drop_without_unknown_ground_and_socket_v=known_design_drop,
        actual_new_E19_finite_fixture_copper_loop_v=loops,
        E19_model_is_unaccepted_coarse_not_a_bound=True,
        unknown_signed_ground_socket_and_network_terms=unknown_terms,
        R1_candidates=rows,
        startup=startup,
        recommendation=recommendation,
        firmware=firmware,
        internal_Seed3_regulator_identity_and_full_BOM_available=False,
        complete_source_to_Seed_guaranteed_interval_v=None,
        twenty_percent_screen_definition="Deratedratedpower>=1.2*actual1Aloadpower, NOT1.2Acurrent orcertifiedmissionlife",
        complete_endpoint_and_R1_thermal_qualified=False,
        fabrication_released=False,
        physical_qualified=False,
    )
    for p, h in report["source_sha256"].items():
        assert sha(ROOT / p) == h
    (ROOT / "generated/endpoint-R1.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "source",
        source,
        "WSLTnormalintercept",
        rows[1]["conditional_VIN_intercept_v"],
        "WSLT125Pmargin",
        rows[1]["ambient_scenarios"][-1]["power_ratio_rating_to_load"],
    )


if __name__ == "__main__":
    run()
