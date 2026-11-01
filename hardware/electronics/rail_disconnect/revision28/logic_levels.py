"""Conditional settled RUN/READY and logic fanout corners from actual pins.

These are circuit requirements under declared total-error/leakage allocations.
They do not establish brownout, source-off leakage, edge timing or qualification.
"""

import hashlib
import json
from pathlib import Path

from .auxiliary import value
from .manufacturer import ROOT
from .positive import components


def screen(parts=None, source_interval=(2.533478630, 2.656441450), pullup=2200):
    parts = components() if parts is None else parts
    by = {c["ref"]: c for c in parts}

    def pins(ref):
        return {str(p["number"]): p for p in by[ref]["pins"]}

    required = {
        1: "POWER_RUN",
        2: "E28_NOT_RUN",
        3: "E28_AUX_VALID",
        4: "E28_NOT_AUX",
        5: "E28_FAULT",
        6: "E28_NOT_FAULT",
        9: "E28_NOT_RUN",
        8: "E28_RUN_LOGIC",
        11: "P03_SOURCES_READY",
        10: "E28_NOT_SOURCE_READY",
        13: "E28_NOT_SOURCE_READY",
        12: "E28_SOURCE_READY_LOGIC",
    }
    assert by["U28"]["part"] == "SN74LVC14APWR"
    assert all(pins("U28")[str(n)]["net"] == net for n, net in required.items())
    assert not any(
        c["ref"] != "U28"
        and c["part"].startswith("SN74LVC")
        and p["kind"] == "input"
        and p["net"] in ("POWER_RUN", "P03_SOURCES_READY")
        for c in parts
        for p in c["pins"]
    )
    total_r_error = 0.02
    source_r_error = 0.03
    board_leak = 2e-6
    lvc_leak = 20e-6
    outputs = []
    external = {"E28_FAULT": 20e-6, "E28_OUTPUT_READY": 20e-6, "E28_MASTER_ENABLE": 20e-6}
    for c in parts:
        if not c["part"].startswith("SN74LVC"):
            continue
        for output in c["pins"]:
            if output["kind"] != "output":
                continue
            net = output["net"]
            loads = []
            for receiver in parts:
                for p in receiver["pins"]:
                    if p["net"] != net or p["kind"] != "input":
                        continue
                    if receiver["part"].startswith("SN74LVC"):
                        current = lvc_leak
                    elif receiver["part"].startswith("SN74AUP"):
                        current = 0.5e-6
                    else:
                        continue
                    loads.append(dict(ref=receiver["ref"], pin=p["number"], requirement_a=current))
            current = sum(p["requirement_a"] for p in loads) + external.get(net, 0) + board_leak
            if net == "E28_SAFE_REQUEST":
                current += 2.7 / (value(by["R140"]) * (1 - total_r_error))
            schmitt = any(x["ref"] == "U28" for x in loads)
            outputs.append(
                dict(
                    driver=[c["ref"], output["number"]],
                    net=net,
                    loads=loads,
                    high_load_requirement_a=current,
                    external_load_requirement_a=external.get(net, 0),
                    within_100ua_characterization_row=current <= 100e-6,
                    high_min_requirement_v=2.50 - 0.3,
                    low_max_requirement_v=0.3,
                    receiving_high_threshold_requirement_v=2.0 if schmitt else 1.7,
                    receiving_low_threshold_requirement_v=0.4 if schmitt else 0.7,
                )
            )
    ready_r = value(by["R142"])
    run_r = value(by["R93"])
    rp = pullup * (1 + source_r_error)
    rd = ready_r * (1 - total_r_error)
    # One raw Schmitt input replaces the former two ordinary LVC inputs.
    high = (min(source_interval) / rp - lvc_leak - board_leak) / (1 / rp + 1 / rd)
    open_ready = ready_r * (1 + total_r_error) * lvc_leak
    open_ready_with_board = ready_r * (1 + total_r_error) * (lvc_leak + board_leak)
    open_run = run_r * (1 + total_r_error) * (lvc_leak + board_leak)
    low_sink = max(source_interval) / (pullup * (1 - source_r_error)) + lvc_leak + board_leak
    return dict(
        receiver_supply_requirement_v=[2.50, 2.70],
        logic_temperature_requirement_c=[-40, 125],
        source_aux_interval_requirement_v=list(source_interval),
        source_ready_pullup_ohm=pullup,
        source_pullup_total_error_requirement=source_r_error,
        receiver_pull_down_total_error_requirement=total_r_error,
        raw_ready_pull_down_ohm=ready_r,
        raw_run_pull_down_ohm=run_r,
        additional_unverified_board_or_source_leak_requirement_a=board_leak,
        ready_received_high_v=high,
        ready_high_margin_to_2v_v=high - 2,
        ready_open_input_leak_only_v=open_ready,
        ready_open_with_board_leak_v=open_ready_with_board,
        run_open_with_board_leak_v=open_run,
        raw_low_threshold_requirement_v=0.4,
        ready_asserted_source_sink_requirement_a=low_sink,
        ltc2910_low_table_vcc_min_v=2.3,
        ltc2910_low_table_vol_max_v=0.3,
        ltc2910_low_table_sink_a=0.0025,
        raw_ready_conditional_corners_pass=high >= 2 and open_ready_with_board < 0.4 and low_sink <= 0.0025,
        raw_run_open_conditional_corner_pass=open_run < 0.4,
        ordinary_logic_output_rows=outputs,
        ordinary_logic_settled_loading_pass=all(x["within_100ua_characterization_row"] for x in outputs),
        external_output_contract=dict(
            max_dc_load_per_pin_a=20e-6,
            receiver_vih_max_v=1.7,
            receiver_vil_min_v=0.7,
            externally_drive_outputs=False,
            selected_receivers_accepted=False,
        ),
        raw_run_driver_requirement=dict(
            high_min_v=2.0,
            low_max_v=0.3,
            dc_high_source_requirement_a=2.7 / (run_r * (1 - total_r_error)) + lvc_leak + board_leak,
            selected_driver_and_harness_accepted=False,
        ),
        primary_conditions=[
            "TI LVC14A SCAS285AC tables6.7/PW0014A4220202/B",
            "Threshold envelopes use the2.3/2.5/2.7V table corners;actual intermediate-supply transfer is an acceptance hold",
            "20uA input-leak row is tested atVCC3.6V/VI0or5.5V;actual low-voltage/hot/board leakage is not silently qualified",
            "TI LVC14A has no Ioff guarantee;external output drive is prohibited and partial-AUX behavior remains open",
            "Schmitt inputs remove the ordinary-LVC input transition-rate dependency;actual reset/logic propagation and startup captures remain required",
        ],
        complete_aux_current_ledger_accepted=False,
        source_off_leakage_accepted=False,
        total_resistor_error_and_contamination_accepted=False,
        actual_input_thresholds_accepted=False,
        physical_brownout_or_fault_qualified=False,
        build_ready=False,
        physical_qualified=False,
    )


def main():
    result = screen()
    result["source_hashes"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (
            ROOT / "rail_disconnect.kicad_pcb",
            ROOT / "rail_disconnect.kicad_sch",
            ROOT / "components.json",
            Path(__file__),
        )
    }
    primary = Path("/private/tmp/e28-sn74lvc14a.pdf")
    result["primary_schmitt_pdf_sha256"] = hashlib.sha256(primary.read_bytes()).hexdigest()
    (ROOT / "generated/logic-level-corners.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "Conditional READY HIGH",
        result["ready_received_high_v"],
        "V;open",
        result["ready_open_with_board_leak_v"],
        "V;RUN open",
        result["run_open_with_board_leak_v"],
        "V;all<=100uA",
        result["ordinary_logic_settled_loading_pass"],
    )


if __name__ == "__main__":
    main()
