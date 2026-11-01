"""FP01 native two-channel fan protection draft, not a qualified fan controller."""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.netlists import netlist

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
OUT = ROOT / "generated"
P03 = REPO / "hardware/electronics/power_distribution/p03/candidates/aux-u10-combined"
SF = REPO / "hardware/cad/a12/thermal/forced_air_sunon"
TI = "https://www.ti.com/lit/ds/symlink/tps2553.pdf"
JST = "https://www.jst-mfg.com/product/pdf/eng/eXH.pdf"
VISHAY = "https://www.vishay.com/docs/28758/tnpw_e3.pdf"
KEMET = "https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf"
WIMA = "https://www.wima.de/wp-content/uploads/media/d_WIMA_MKS_2.pdf"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(n, name, net, kind="passive", side="L"):
    return dict(number=str(n), name=name, net=net, kind=kind, side=side)


def components():
    parts = []

    def add(ref, part, footprint, pins, x, y, source, note):
        parts.append(
            dict(ref=ref, part=part, footprint=footprint, pins=pins, x=x, y=y, source=source, note=note)
        )

    def connector(ref, n, nets, x, y, note):
        add(
            ref,
            f"JST B{n}B-XH-A / XHP-{n} / SXH-001T-P0.6",
            f"Connector_JST:JST_XH_B{n}B-XH-A_1x{n:02d}_P2.50mm_Vertical",
            [pin(i + 1, net, net) for i, net in enumerate(nets)],
            x,
            y,
            JST,
            note,
        )

    connector(
        "J1",
        2,
        ["FAN5V_IN", "FAN_GND"],
        55.88,
        45.72,
        "NEW operating DIG-force branch only. P03J3 is TEST ONLY and cannot supply this circuit. AWG22 input; actual source joint/return/harness unimplemented.",
    )
    connector(
        "J4",
        6,
        ["FAN_GND", "FAN5V_IN", "FAN_L_FAULT_N", "FAN_R_FAULT_N", "FAN_L_TACH", "FAN_R_TACH"],
        233.68,
        45.72,
        "To future health board. FAULT open-drain needs host pullups; TACH can reach switched5V, requires5V-tolerant input with power-off protection. No E28RUN interlock implemented.",
    )
    for index, side in enumerate(["L", "R"]):
        offset = index * 100
        y = 114.3 + index * 165.1
        prefix = "FAN_" + side
        add(
            "U" + str(1 + offset),
            "TPS2553DBVR-1",
            "Package_TO_SOT_SMD:SOT-23-6",
            [
                pin(1, "IN", "FAN5V_IN", "power_in"),
                pin(2, "GND", "FAN_GND", "power_in"),
                pin(3, "EN", "FAN5V_IN", "input"),
                pin(4, "FAULT_N", prefix + "_FAULT_N", "open_collector", "R"),
                pin(5, "ILIM", prefix + "_ILIM", "output", "R"),
                pin(6, "OUT", prefix + "_5V", "power_out", "R"),
            ],
            55.88,
            y,
            TI,
            "ExactDBVpinmapIN1/GND2/EN3/FAULT4/ILIM5/OUT6. ActivehighEN tiedinput; overcurrent/reverse latch resets only by source power cycle. Thermal cycling behavior remains distinct.",
        )
        for j, (value, a, b, note) in enumerate(
            [
                (
                    "100k 0.1%25ppm TNPW0805100KBEEA",
                    prefix + "_ILIM",
                    "FAN_GND",
                    "All-in100k±1% is a receiving requirement; includes initial/TCR/life/assembly, not just catalogue initial tolerance.",
                ),
                (
                    "10k 0.1%25ppm TNPW080510K0BEEA",
                    prefix + "_5V",
                    prefix + "_TACH",
                    "Tach pullup follows SWITCHED fan power, not always-on host power. Sink<=.53mA in proposed5.2V/.99R scenario.",
                ),
                (
                    "100k 0.1%25ppm TNPW0805100KBEEA",
                    prefix + "_5V",
                    "FAN_GND",
                    "Output bleed; does not prove discharge time with unknown fan capacitance.",
                ),
            ]
        ):
            add(
                "R" + str(j + 1 + offset),
                value,
                "Resistor_SMD:R_0805_2012Metric",
                [pin(1, "1", a), pin(2, "2", b, side="R")],
                157.48,
                y + j * 40.64,
                VISHAY,
                note,
            )
        for j in range(2):
            add(
                "C" + str(j + 1 + offset),
                "100nF25V C0G5% C1206C104J3GACTU",
                "Capacitor_SMD:C_1206_3216Metric",
                [pin(1, "1", "FAN5V_IN"), pin(2, "2", "FAN_GND", side="R")],
                55.88,
                y + 45.72 + j * 35.56,
                KEMET,
                "Parallel pair at EACH IN/GND. Proposed complete effective±6% gives188nF minimum >100nF recommendation; actual lot/life verification open.",
            )
        add(
            "C" + str(3 + offset),
            "1uF63V10% WIMA MKS2C041001F00KSSD",
            "Capacitor_THT:C_Rect_L7.2mm_W5.0mm_P5.00mm",
            [pin(1, "1", prefix + "_5V"), pin(2, "2", "FAN_GND", side="R")],
            233.68,
            y + 50.8,
            WIMA,
            "Proposed.8..1.2uF complete effective receiving interval unverified; fan internal capacitance and motor startup current remain unknown.",
        )
        connector(
            "J" + str(index + 2),
            3,
            ["FAN_GND", prefix + "_5V", prefix + "_TACH"],
            233.68,
            y,
            "Sunon bare leads black1/red2/yellow3; this NEWXH assignment is not a supplied factory connector. AWG26 crimp/insulation acceptance and retention open;3A catalogue rating appliesAWG22 only.",
        )
    return parts


def current_interval(resistor_ohm=100000, tolerance=0.01):
    if not 15000 <= resistor_ohm * (1 - tolerance) <= resistor_ohm * (1 + tolerance) <= 232000:
        raise ValueError("ILIM resistor outside recommended region")
    lo = resistor_ohm * (1 - tolerance) / 1000
    hi = resistor_ohm * (1 + tolerance) / 1000
    # TI Equation1 uses resistor in kOhm and output in mA.
    return [25230 / hi**1.016 / 1000, 22980 / lo**0.94 / 1000]


def analyze():
    assert (
        sha(Path("/private/tmp/afx-tps2553.pdf"))
        == "413aec7178e722bdeacd701a7d4d4f20e5aa09bee0c60ab2176751b6f1ae6da5"
    )
    originals = json.loads((P03 / "components.json").read_text())
    j3 = next(c for c in originals if c["ref"] == "J3")
    j23 = next(c for c in originals if c["ref"] == "J23")
    assert "TEST ONLY" in j3["note"] and j23["pins"][0]["net"] == "5V_DIG_SRC"
    sf = json.loads((SF / "analysis.json").read_text())
    assert sf["preferred_prototype_candidate"] == "V1"
    motor = sf["parts"]["V1"]
    lower, upper = current_interval()
    normal = 1.2 * motor["current_max_a"]
    assert lower > normal
    # New protective/control loads partition remaining digital reserve.
    switch_pair = 2 * 0.00014
    tach_pair = 2 * 5.2 / 9900
    bleed_pair = 2 * 5.2 / 99000
    protective_provision = 1.2 * (switch_pair + tach_pair + bleed_pair)
    nf_provision = 0.0313  # Rounded above NF03's31.21435mA diagnostic; not a physical bound.
    remaining = (
        0.416 - motor["two_fan_twenty_percent_current_provision_a"] - protective_provision - nf_provision
    )
    assert remaining > 0
    voltage_low = 4.992227729652826 - 0.022 - 0.416 * 0.15 - normal * 0.35
    return dict(
        revision="FP01-native-protection-section-draft",
        exact_switch="TPS2553DBVR-1",
        current_limit_interval_a=[lower, upper],
        normal_motor_current_with20pct_a=normal,
        steady_switch_drop_at135mohm_v=normal * 0.135,
        steady_switch_heat_at135mohm_w=normal**2 * 0.135,
        minimum_input_decoupling_receiving_f=2 * 100e-9 * 0.94,
        digital_reserve_partition=dict(
            original_a=0.416,
            motor_pair_provision_a=motor["two_fan_twenty_percent_current_provision_a"],
            new_switch_tach_bleed_provision_a=protective_provision,
            NF03_control_interface_provision_a=nf_provision,
            remaining_for_health_logic_and_LED_a=remaining,
            allocation_is_not_a_hot_dynamic_current_bound=True,
        ),
        source_port_correction=dict(
            old_FV01_J3_suggestion_usable=False,
            native_J3_note=j3["note"],
            source_stud="P03.J23",
            return_stud="P03.J21",
            new_branch_tap_connector_joint_and_return_implemented=False,
            operating_force_links_may_not_be_bypassed=True,
        ),
        conditional_voltage_screen=dict(
            source_low_v=4.992227729652826,
            dynamic_and_spread_v=0.022,
            shared_feed_complete_loop_receiving_ohm=0.15,
            each_branch_complete_loop_receiving_ohm=0.35,
            calculated_fan_low_v=voltage_low,
            twenty_percent_25c_start_target_v=1.2 * 3.5,
            receiving_resistances_physical_upper_bounds_proven=False,
            true_complete_fan_voltage_interval_v=None,
        ),
        current_limit_two_fault_diagnostic_a=2 * upper,
        maximum_fault_energy_j=None,
        holds=[
            "Actual Sunon installed/hot startup and locked-rotor current and internal capacitance are unknown; current-limit threshold does not prove successful starting.",
            "TI short-circuit response2us is typical. The5..10ms deglitch and3ms turnoff test load do not bound actual fan/inductive/charged-capacitor cutoff energy.",
            "Supply-current140uA row is atRILIM20k/6.5V; use at100k is a receiving allocation pending characterization, not an exact applicable bound.",
            "TPS2553-1 latches overcurrent/reverse faults but ambient thermal shutdown can cycle. This is not an unconditional no-autoretry or thermal-interlock guarantee.",
            "FAULT outputs are open-drain without on-board pullups. Host may pull up only to its valid supply and must tolerate off states.",
            "Tach pullups follow fan power. Future receiver must tolerate switched5V with power-off protection; no direct3V3-MCU connection is approved.",
            "No fan-health pulse qualification, watchdog, temperature sensing or fail-off E28 enable contact is implemented by this protection-section draft.",
            "Fan5V feed requires a NEW operating force-path branch with fresh copper/contact/return solve and CAD. ExistingJ3 test header is rejected.",
            "Steady voltage uses unaccepted full-loop resistance allocations, source interval and dynamic allowances. Actual signed ground/contact/transient terms remain unresolved.",
            "No nativePCB, MCAD, crimp/strain/clamp, thermal, acoustic, ESD, source-collapse or physical test qualification is inherited.",
        ],
        physical_qualified=False,
        health_interlock_implemented=False,
        PCB_implemented=False,
        fabrication_released=False,
    )


def main():
    ROOT.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    source = ROOT / "sources"
    source.mkdir(exist_ok=True)
    inputs = [
        Path(__file__),
        REPO / "hardware/electronics/common/flat_schematic.py",
        REPO / "hardware/electronics/common/netlists.py",
        REPO / "hardware/electronics/common/symbols.py",
        P03 / "components.json",
        P03 / "generated/netlist.xml",
        P03 / "power_p03.kicad_pcb",
        SF / "analysis.json",
        SF / "handoff.json",
    ]
    source_hashes = {}
    for path in inputs:
        target = source / path.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert sha(target) == sha(path), "Captured source changed: " + str(path)
        else:
            shutil.copy2(path, target)
        source_hashes[str(path.relative_to(REPO))] = sha(path)
    parts = components()
    generate(
        ROOT,
        "FP01",
        "fan_protection",
        parts,
        [
            (
                20,
                405,
                "FP01: native protection section only. NEWforce-path supply branch; P03J3 TEST ONLY is prohibited.",
            ),
            (
                20,
                415,
                "Motor/current-limit/startup/ground/thermal bounds unverified. Health/temperature/E28RUN interlock and PCB not implemented.",
            ),
            (
                20,
                425,
                "J4TACH can reach switched5V. Future receiver MUST be5V tolerant with power-off protection. No directMCU connection.",
            ),
        ],
        (300, 440),
        [("FAN5V_IN", 20.32, 20.32), ("FAN_GND", 60.96, 20.32)],
    )
    cli = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    env = dict(
        os.environ,
        KICAD10_FOOTPRINT_DIR="/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints",
    )
    commands = []
    for args in [
        ["sch", "export", "netlist", "--format", "kicadxml", "--output", str(OUT / "netlist.xml")],
        ["sch", "export", "svg", "--output", str(OUT / "schematic-svg")],
        ["sch", "erc", "--format", "json", "--output", str(OUT / "erc.json")],
    ]:
        cmd = [cli, *args, str(ROOT / "fan_protection.kicad_sch")]
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        label = "erc" if args[1] == "erc" else args[2]
        (OUT / (label + ".log")).write_text(result.stdout + result.stderr)
        commands.append(dict(command=cmd, returncode=result.returncode))
        assert result.returncode == 0, (label, result.stderr)
    actual, pins = netlist(OUT / "netlist.xml")
    expected = {c["ref"]: {p["number"]: p["net"] for p in c["pins"]} for c in parts}
    assert set(actual) == set(expected) and pins == expected
    erc = json.loads((OUT / "erc.json").read_text())
    findings = [v for sheet in erc["sheets"] for v in sheet["violations"]]
    assert not findings, findings
    report = analyze()
    report.update(
        source_sha256=source_hashes,
        components=len(parts),
        native_pin_maps_match=True,
        native_ERC_findings=0,
        native_commands=commands,
        TI_primary_pdf_sha256=sha(Path("/private/tmp/afx-tps2553.pdf")),
        source_capture_sha256={str(p.relative_to(ROOT)): sha(p) for p in source.rglob("*") if p.is_file()},
    )
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "FP01",
        len(parts),
        "parts, nativeERC/parity0; limit",
        report["current_limit_interval_a"],
        "A; remaining health allocation",
        report["digital_reserve_partition"]["remaining_for_health_logic_and_LED_a"],
        "A",
    )


if __name__ == "__main__":
    main()
