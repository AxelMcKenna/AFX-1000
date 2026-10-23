#!/usr/bin/env python3
"""Reproducible line-level and watchdog design calculations; no EDA dependencies.

These are design constraints and an ideal logic model, not SPICE, ERC, or bench
evidence. Preserve unmeasured component tolerances as explicit assumptions.
"""

import csv
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"

DBU_REFERENCE = 0.775  # V RMS; conventional rounded reference
HEADROOM_DB = 20
CODEC_FS_RMS = 1.0  # Seed3 nominal reference; must be calibrated on the board
OUTPUT_R = 100.0
LOAD_R = 10000.0  # combined load across both parallel output connector pairs
RAIL_TOLERANCE = 0.05
SWING_RESERVE = 2.0  # assumption for screening, NOT an op-amp guarantee


def parallel(a, b):
    return a * b / (a + b)


def calculate():
    modes = []
    for name, nominal in [("send_return", 10 ** (-10 / 20)), ("master", DBU_REFERENCE * 10 ** (4 / 20))]:
        full_scale = nominal * 10 ** (HEADROOM_DB / 20)
        peak = full_scale * math.sqrt(2)
        modes.append(
            dict(
                mode=name,
                nominal_rms_v=nominal,
                target_headroom_db=HEADROOM_DB,
                full_scale_rms_v=full_scale,
                full_scale_peak_v=peak,
                ideal_input_gain=CODEC_FS_RMS / full_scale,
                ideal_output_gain=full_scale / CODEC_FS_RMS,
                amplifier_peak_before_output_resistor_v=peak * (1 + OUTPUT_R / LOAD_R),
            )
        )
    # Screen both modes with the same voltage reserve and load assumptions.
    supplies = []
    for label, rail in [
        ("single_5V_midpoint", 2.5),
        ("single_9V_midpoint", 4.5),
        ("single_12V_midpoint", 6),
        ("bipolar_12V", 12),
        ("bipolar_15V", 15),
        ("bipolar_18V", 18),
        ("bipolar_22V", 22),
    ]:
        available_peak = max(0, rail * (1 - RAIL_TOLERANCE) - SWING_RESERVE) / (1 + OUTPUT_R / LOAD_R)
        available_rms = available_peak / math.sqrt(2)
        supplies.append(
            dict(
                supply=label,
                nominal_rail_magnitude_v=rail,
                assumed_rail_tolerance=RAIL_TOLERANCE,
                assumed_output_swing_reserve_v=SWING_RESERVE,
                available_connector_peak_v=available_peak,
                available_connector_rms_v=available_rms,
                meets_send_return_target=available_rms >= modes[0]["full_scale_rms_v"],
                meets_master_target=available_rms >= modes[1]["full_scale_rms_v"],
            )
        )
    # Draft always-connected feedback paths. Relay contacts only add/remove a
    # shunt branch, so contact bounce cannot open the amplifier feedback loop.
    networks = []
    for name, ri, ro in [
        ("send_return", 10000, parallel(127000, 43200)),
        ("master", parallel(10000, 3480), 127000),
    ]:
        gi, go = ri / 32400, ro / 10000
        nominal = modes[len(networks)]["nominal_rms_v"]
        networks.append(
            dict(
                mode=name,
                input_rin_ohm=32400,
                input_effective_rf_ohm=ri,
                output_rin_ohm=10000,
                output_effective_rf_ohm=ro,
                input_gain_magnitude=gi,
                output_gain_magnitude=go,
                unloaded_unity_error_db=20 * math.log10(gi * go),
                loaded_unity_error_db=20 * math.log10(gi * go * LOAD_R / (LOAD_R + OUTPUT_R)),
                nominal_input_dbfs=20 * math.log10(nominal * gi / CODEC_FS_RMS),
                nominal_adc_headroom_db=20 * math.log10(CODEC_FS_RMS / (nominal * gi)),
            )
        )
    cap_nf, cap_tolerance, timing_tolerance = 0.15, 0.05, 0.15
    watchdog = dict(
        part="TPS3431SDRBR",
        cwd_capacitance_pf=cap_nf * 1000,
        capacitor_tolerance=cap_tolerance,
        assumed_timing_tolerance=timing_tolerance,
        timeout_typ_ms=77.4 * cap_nf + 55,
        timeout_min_ms=(77.4 * cap_nf * (1 - cap_tolerance) + 55) * (1 - timing_tolerance),
        timeout_max_ms=(77.4 * cap_nf * (1 + cap_tolerance) + 55) * (1 + timing_tolerance),
        callback_period_ms=1000 * 128 / 48000,
        falling_heartbeat_period_ms=2 * 1000 * 128 / 48000,
        fault_latch="SN74LVC1G74DCTR",
        relay_drive_gate="SN74LVC1G08DBVR",
    )
    # Sanity checks against independently stated physical requirements.
    assert math.isclose(modes[0]["full_scale_rms_v"], math.sqrt(10), rel_tol=1e-12)
    assert 17.36 < modes[1]["full_scale_peak_v"] < 17.38
    assert not next(s for s in supplies if s["supply"] == "single_12V_midpoint")["meets_master_target"]
    assert next(s for s in supplies if s["supply"] == "bipolar_22V")["meets_master_target"]
    assert cap_nf * (1 - cap_tolerance) >= 0.1  # manufacturer's minimum modeled capacitor
    assert watchdog["falling_heartbeat_period_ms"] < watchdog["timeout_min_ms"] / 10
    return dict(
        revision="E01",
        status="design constraints; schematic and physical verification pending",
        codec_nominal_full_scale_rms_v=CODEC_FS_RMS,
        output_series_ohm=OUTPUT_R,
        combined_minimum_load_ohm=LOAD_R,
        modes=modes,
        supply_screen=supplies,
        candidate_resistor_networks=networks,
        watchdog=watchdog,
    )


def verify_latch_model():
    """Exercise async clear + edge rearm, including WDO auto recovery while hung.

    Ideal behavior only: does not cover propagation/recovery time, metastability,
    electrical levels, coil dynamics, contacts, or the missing rail supervisors.
    """
    q, previous = False, False
    rows = []
    events = [
        ("reset", False, False, False),
        ("rails and watchdog ready", True, False, False),
        ("MCU requests processing", True, True, True),
        ("audio stops; watchdog expires", False, True, False),
        ("WDO auto recovers; MCU still frozen high", True, True, False),
        ("WDO faults again; MCU still frozen high", False, True, False),
        ("WDO auto recovers again", True, True, False),
        ("MCU drops request", True, False, False),
        ("new healthy MCU rising edge", True, True, True),
        ("manual bypass clears latch", False, True, False),
        ("manual bypass released with request stuck high", True, True, False),
        ("MCU drops request after bypass", True, False, False),
        ("new MCU request after bypass", True, True, True),
        ("MCU drops request without a hardware fault", True, False, False),
    ]
    for event, fault_n, permit, expected in events:
        if not fault_n:
            q = False
        elif permit and not previous:
            q = True
        drive = q and permit
        assert drive == expected, event
        rows.append(dict(event=event, fault_n=fault_n, mcu_permit=permit, latched_armed=q, relay_drive=drive))
        previous = permit
    return dict(
        model="ideal positive-edge D flop, asynchronous active-low clear, D=1, PRE_N=1; Q AND permit",
        passed=True,
        events=rows,
        excluded=[
            "electrical/propagation timing",
            "power ramp/undervoltage",
            "relay/coil dynamics",
            "faults in watchdog or gate ICs",
        ],
    )


def terminal_rows():
    # Named terminals deliberately avoid implying a verified package footprint.
    return [
        ("U_WD", "TPS3431SDRBR", "VDD", "3V3"),
        ("U_WD", "TPS3431SDRBR", "GND / exposed pad", "GND"),
        ("U_WD", "TPS3431SDRBR", "WDI", "SEED_D13_HEARTBEAT"),
        ("U_WD", "TPS3431SDRBR", "SET1", "3V3"),
        ("U_WD", "TPS3431SDRBR", "EN", "3V3"),
        ("U_WD", "TPS3431SDRBR", "CWD", "WATCHDOG_CWD"),
        ("U_WD", "TPS3431SDRBR", "WDO", "FAULT_N"),
        ("U_WD", "TPS3431SDRBR", "ENOUT", "FAULT_N"),
        ("C_WD", "150pF C0G 5%", "1", "WATCHDOG_CWD"),
        ("C_WD", "150pF C0G 5%", "2", "GND"),
        ("R_HEART", "100k", "1", "SEED_D13_HEARTBEAT"),
        ("R_HEART", "100k", "2", "GND"),
        ("R_FAULT", "4.7k", "1", "3V3"),
        ("R_FAULT", "4.7k", "2", "FAULT_N"),
        ("U_LATCH", "SN74LVC1G74DCTR", "VCC / D / PRE_N", "3V3"),
        ("U_LATCH", "SN74LVC1G74DCTR", "GND", "GND"),
        ("U_LATCH", "SN74LVC1G74DCTR", "CLR_N", "FAULT_N"),
        ("U_LATCH", "SN74LVC1G74DCTR", "CLK", "SEED_D26_PERMIT"),
        ("U_LATCH", "SN74LVC1G74DCTR", "Q", "RELAY_ARMED"),
        ("U_LATCH", "SN74LVC1G74DCTR", "Q_N", "NO_CONNECT"),
        ("U_AND", "SN74LVC1G08DBVR", "VCC", "3V3"),
        ("U_AND", "SN74LVC1G08DBVR", "GND", "GND"),
        ("U_AND", "SN74LVC1G08DBVR", "A", "RELAY_ARMED"),
        ("U_AND", "SN74LVC1G08DBVR", "B", "SEED_D26_PERMIT"),
        ("U_AND", "SN74LVC1G08DBVR", "Y", "RELAY_DRIVE"),
        ("R_PERMIT", "100k", "1", "SEED_D26_PERMIT"),
        ("R_PERMIT", "100k", "2", "GND"),
        ("R_GATE", "100R", "1", "RELAY_DRIVE"),
        ("R_GATE", "100R", "2", "BYPASS_GATE"),
        ("R_GATEDOWN", "100k", "1", "BYPASS_GATE"),
        ("R_GATEDOWN", "100k", "2", "GND"),
        ("Q_BYPASS", "AO3400A", "G", "BYPASS_GATE"),
        ("Q_BYPASS", "AO3400A", "S", "GND"),
        ("Q_BYPASS", "AO3400A", "D", "BYPASS_COIL_LOW"),
        ("K_BYPASS_OUT", "G6K-2F-Y DC5", "coil+", "5V"),
        ("K_BYPASS_OUT", "G6K-2F-Y DC5", "coil-", "BYPASS_COIL_LOW"),
        ("K_ISOLATE_IN", "G6K-2F-Y DC5", "coil+", "5V"),
        ("K_ISOLATE_IN", "G6K-2F-Y DC5", "coil-", "BYPASS_COIL_LOW"),
        ("SW_BYPASS", "DPDT maintained; part pending", "pole A common", "FAULT_N"),
        ("SW_BYPASS", "DPDT maintained; part pending", "pole A bypass", "GND"),
        ("SW_BYPASS", "DPDT maintained; part pending", "pole B common", "SEED_D0_BYPASS"),
        ("SW_BYPASS", "DPDT maintained; part pending", "pole B bypass", "GND"),
        ("RAIL_SUPERVISORS", "parts pending", "open-drain fault outputs", "FAULT_N"),
    ]


def diagram():
    # Diagram of the circuit contract; full analog/PCB schematic remains open.
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="620" viewBox="0 0 1200 620">
<title>E01 independent bypass and gain switching circuit draft</title>
<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#496a7a"/></marker></defs>
<rect width="1200" height="620" fill="#f8fafb"/>
<g font-family="Arial,sans-serif" fill="#172f3c">
<text x="30" y="36" font-size="24" font-weight="bold">Standalone audio / bypass — E01 circuit contract</text>
<text x="30" y="62" font-size="15">Design draft · no routed PCB · analog rails and protection parts remain open</text>
<g fill="white" stroke="#91a9b5" stroke-width="1.5">
<rect x="30" y="112" width="180" height="72" rx="8"/><rect x="290" y="112" width="210" height="72" rx="8"/>
<rect x="590" y="112" width="210" height="72" rx="8"/><rect x="900" y="112" width="260" height="72" rx="8"/>
<rect x="30" y="268" width="210" height="78" rx="8"/><rect x="290" y="268" width="220" height="78" rx="8"/>
<rect x="590" y="268" width="210" height="78" rx="8"/><rect x="900" y="268" width="260" height="78" rx="8"/>
<rect x="30" y="420" width="210" height="78" rx="8"/><rect x="290" y="420" width="220" height="78" rx="8"/>
<rect x="590" y="420" width="210" height="78" rx="8"/><rect x="900" y="420" width="260" height="78" rx="8"/>
</g>
<g stroke="#496a7a" stroke-width="2" fill="none" marker-end="url(#a)">
<path d="M210 148H290"/><path d="M500 148H590"/><path d="M800 148H900"/>
<path d="M120 184V222H1030V184"/><path d="M135 346V394H615V346"/>
<path d="M510 307H590"/><path d="M800 307H900"/>
<path d="M240 459H270V307H290"/><path d="M510 459H550V325H590"/>
<path d="M240 436H270V364H850V325H900"/>
<path d="M1030 346V381H1178V148H1160"/>
</g>
<g font-size="17" text-anchor="middle">
<text x="120" y="142">Stereo line input</text><text x="120" y="167" font-size="14">RCA / TS alternatives</text>
<text x="395" y="141">Input isolation relay</text><text x="395" y="167" font-size="14">NO → gain / ADC</text>
<text x="695" y="142">Local DSP / DAC</text><text x="695" y="167" font-size="14">48 kHz · gain / output amp</text>
<text x="1030" y="141">Output selector relay</text><text x="1030" y="167" font-size="14">NC dry / NO processed → output</text>
<text x="135" y="296">Manual bypass</text><text x="135" y="322" font-size="14">direct hardware fault pull-down</text>
<text x="400" y="296">TPS3431 watchdog</text><text x="400" y="322" font-size="14">150 pF · ~67 ms typical</text>
<text x="695" y="292">Fault latch</text><text x="695" y="313" font-size="13">async clear / new MCU</text><text x="695" y="332" font-size="13">permit rising edge arms Q</text>
<text x="1030" y="296">Q AND MCU permit</text><text x="1030" y="322" font-size="14">MOSFET → both bypass coils</text>
<text x="135" y="449">Audio callback</text><text x="135" y="475" font-size="14">D26 permit / D13 heartbeat</text>
<text x="400" y="449">Power-good faults</text><text x="400" y="475" font-size="14">3.3 V / 5 V / both audio rails</text>
<text x="695" y="449">D9 gain-relay driver</text><text x="695" y="475" font-size="14">2 × DPDT · one per channel</text>
<text x="1030" y="449">CONNECTION switch</text><text x="1030" y="475" font-size="14">D25 sense · gain only</text>
</g>
<path d="M900 459H800" stroke="#496a7a" stroke-width="2" marker-end="url(#a)"/>
<text x="520" y="216" font-size="14" fill="#317b63">Unpowered path: input directly to output; processing input disconnected</text>
<text x="30" y="548" font-size="16">Gain change: debounce 8 ms → dry wait 20 ms → switch D9 → settle 30 ms → healthy rearm ≥350 ms</text>
<text x="30" y="576" font-size="15">Watchdog recovery cannot rearm a permit stuck high. A new MCU permit edge is required.</text>
<text x="30" y="602" font-size="13" fill="#687c88">Rails, suppression, input protection, footprints and relay timing require a full schematic and bench verification.</text>
</g></svg>"""


def main():
    OUT.mkdir(exist_ok=True)
    levels, logic = calculate(), verify_latch_model()
    (OUT / "line-levels.json").write_text(json.dumps(levels, indent=2) + "\n")
    (OUT / "bypass-logic.json").write_text(json.dumps(logic, indent=2) + "\n")
    data = io.StringIO()
    writer = csv.writer(data)
    writer.writerow(["reference", "part_or_value", "named_terminal", "net"])
    writer.writerows(terminal_rows())
    (OUT / "bypass-terminals.csv").write_text(data.getvalue())
    (OUT / "audio-bypass.svg").write_text(diagram())
    print("Line-level constraints and 14 ideal latch scenarios checked; E01 draft assets generated.")


if __name__ == "__main__":
    main()
