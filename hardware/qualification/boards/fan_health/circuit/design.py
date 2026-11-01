"""FH02 native health interlock draft. No physical or source-budget acceptance."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.netlists import netlist

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
OUT = ROOT / "generated"
TI = "https://www.ti.com/lit/ds/symlink/{}.pdf"
KEMET = "https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf"
VISHAY = "https://www.vishay.com/docs/28758/tnpw_e3.pdf"
JST = "https://www.jst-mfg.com/product/pdf/eng/eXH.pdf"
FP = REPO / "hardware/qualification/boards/fan_protection"
NF = REPO / "hardware/qualification/boards/startup_negative_circuit/compact"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pin(number, name, net, kind="passive", side="L"):
    return dict(number=str(number), name=name, net=net, kind=kind, side=side)


def components():
    parts = []

    def add(ref, part, footprint, pins, source, note=""):
        # Separate logical cells; these are NOT proposed PCB placements.
        k = len(parts)
        parts.append(
            dict(
                ref=ref,
                part=part,
                footprint=footprint,
                pins=pins,
                x=round(55.88 + (k % 5) * 137.16, 2),
                y=round(71.12 + (k // 5) * 111.76, 2),
                source=source,
                note=note,
            )
        )

    def ic(ref, part, footprint, entries, document, note=""):
        add(
            ref,
            part,
            footprint,
            [
                pin(n, name, net, kind, "R" if kind in ("output", "open_collector", "power_out") else "L")
                for n, name, net, kind in entries
            ],
            TI.format(document),
            note,
        )

    def r(ref, value, a, b, note=""):
        add(
            ref,
            value + " TNPW0805 / exact value code in selection.json",
            "Resistor_SMD:R_0805_2012Metric",
            [pin(1, "1", a), pin(2, "2", b, side="R")],
            VISHAY,
            note,
        )

    def c(ref, value, a, b, note=""):
        if value == "10uF":
            part, fp, source = (
                "10uF 25V C3225X7R1E106K250AC",
                "Capacitor_SMD:C_1210_3225Metric",
                "https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3225X7R1E106K250AC",
            )
        elif value == "100nF":
            part, fp, source = "100nF 25V C0G C1206C104J3GACTU", "Capacitor_SMD:C_1206_3216Metric", KEMET
        else:
            code = {"10nF": "103", "2.7nF": "272", "15pF": "150"}[value]
            part, fp, source = (
                value + " 50V C0G C1206C" + code + "J5GACTU",
                "Capacitor_SMD:C_1206_3216Metric",
                KEMET,
            )
        add(ref, part, fp, [pin(1, "1", a), pin(2, "2", b, side="R")], source, note)

    def logic5(ref, part, document, a, y, supply="V3V3", open_drain=False):
        ic(
            ref,
            part,
            "Package_TO_SOT_SMD:SOT-353_SC-70-5",
            [
                (1, "NC", None, "no_connect"),
                (2, "A", a, "input"),
                (3, "GND", "GND", "power_in"),
                (4, "Y", y, "open_collector" if open_drain else "output"),
                (5, "VCC", supply, "power_in"),
            ],
            document,
        )

    def and_gate(ref, a, b, y):
        ic(
            ref,
            "SN74LVC1G08DCKR",
            "Package_TO_SOT_SMD:SOT-353_SC-70-5",
            [
                (1, "A", a, "input"),
                (2, "B", b, "input"),
                (3, "GND", "GND", "power_in"),
                (4, "Y", y, "output"),
                (5, "VCC", "V3V3", "power_in"),
            ],
            "sn74lvc1g08",
            "2.0V VIH applies over actual3.0..3.6V supply row. All inputs have active push-pull drivers; rawopen-drain WD_OK is Schmittconditioned first.",
        )

    ic(
        "U1",
        "ATtiny84A-SSUR",
        "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
        [
            (1, "VCC", "V3V3", "power_in"),
            (2, "PB0_XTAL1", "XTAL1", "passive"),
            (3, "PB1_XTAL2", "XTAL2", "passive"),
            (4, "PB3_RESET_N", "MCU_RESET_N", "input"),
            (5, "PB2", "MCU_TACH_R", "input"),
            (6, "PA7", "MCU_HEALTH", "output"),
            (7, "PA6_MOSI", "ISP_MOSI", "bidirectional"),
            (8, "PA5_MISO", "ISP_MISO", "bidirectional"),
            (9, "PA4_SCK", "ISP_SCK", "input"),
            (10, "PA3", "MCU_TACH_L", "input"),
            (11, "PA2", "HEARTBEAT", "output"),
            (12, "PA1_ADC1", "TEMP_R_ADC", "input"),
            (13, "PA0_ADC0", "TEMP_L_ADC", "input"),
            (14, "GND", "GND", "power_in"),
        ],
        "attiny84a",
        "Microchip DS40002269A source bytes captured. External4MHz crystal; CPU4MHz, Timer1/8, ADC/64 per captured root firmware. 3mA VCC-pin current is receiving, NOT a transferable bare-external-clock table guarantee.",
    )
    parts[-1]["source"] = (
        "https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny24A-44A-84A-Data-Sheet-DS40002269A.pdf"
    )
    ic(
        "U2",
        "TPS7A1633DGNR",
        "Package_SO:HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm",
        [
            (1, "OUT", "V3V3", "power_out"),
            (2, "DNC", None, "no_connect"),
            (3, "PG", "WD_OK", "open_collector"),
            (4, "GND", "GND", "power_in"),
            (5, "EN", "FAN5V_IN", "input"),
            (6, "NC", None, "no_connect"),
            (7, "DELAY", "LDO_DELAY", "passive"),
            (8, "IN", "FAN5V_IN", "power_in"),
            (9, "EP", "GND", "power_in"),
        ],
        "tps7a16",
        "Fixed output: pin2 MUST remain unconnected. PG joins open-drain WD_OK; rising85..95% output threshold is not a precision3.3V monitor. All regulator caps same FRONT face, local direct ground in future layout.",
    )
    ic(
        "U3",
        "SN74LVC2G17DCKR",
        "Package_TO_SOT_SMD:SOT-363_SC-70-6",
        [
            (1, "1A", "FAN_L_TACH", "input"),
            (2, "GND", "GND", "power_in"),
            (3, "2A", "FAN_R_TACH", "input"),
            (4, "2Y", "TACH_R_BUF", "output"),
            (5, "VCC", "V3V3", "power_in"),
            (6, "1Y", "TACH_L_BUF", "output"),
        ],
        "sn74lvc2g17",
        "5.5V tolerant Schmitt inputs/Ioff. Fan-side pullups follow switched5V in FP01; no always-on pullup phantom-feed.",
    )
    ic(
        "U4",
        "TPS3431SDRBR",
        "Package_SON:VSON-8-1EP_3x3mm_P0.65mm_EP1.65x2.4mm",
        [
            (1, "VDD", "V3V3", "power_in"),
            (2, "CWD", "WD_CWD", "passive"),
            (3, "EN", "WD_EN", "input"),
            (4, "GND", "GND", "power_in"),
            (5, "SET1", "V3V3", "input"),
            (6, "WDI", "HEARTBEAT_FAST", "input"),
            (7, "WDO_N", "WD_OK", "open_collector"),
            (8, "ENOUT", "WD_OK", "open_collector"),
            (9, "EP", "GND", "power_in"),
        ],
        "tps3431",
        "TI permits tying ENOUT/WDO. Timeout independently blocks permission and clocksRAW5latch; it doesNOTdriveMCURESET, because startupENOUTLOW would createEXTRF and conflictwithcleanPOR firmware. Watchdogretry MUST NOT reclosecontact.",
    )
    logic5("U5", "SN74AUP1G17DCKR", "sn74aup1g17", "WD_OK", "WD_OK_FAST")
    ic(
        "U6",
        "SN74LVC1T45DBVR",
        "Package_TO_SOT_SMD:SOT-23-6",
        [
            (1, "VCCA", "V3V3", "power_in"),
            (2, "GND", "GND", "power_in"),
            (3, "A", "WD_OK_FAST", "input"),
            (4, "B", "WD_OK_5", "output"),
            (5, "DIR", "V3V3", "input"),
            (6, "VCCB", "FAN5V_IN", "power_in"),
        ],
        "sn74lvc1t45",
        "A-to-B; either supply atGND isolates both ports. RAW5 B pulldown forces fault on complete3.3V loss; intermediate-rail behavior remains receiving.",
    )
    logic5("U7", "SN74LVC1G14DCKR", "sn74lvc1g14", "WD_OK_5", "FAULT_CLK", "FAN5V_IN")
    ic(
        "U8",
        "SN74LVC1G74DCUR",
        "Package_SO:VSSOP-8_2.3x2mm_P0.5mm",
        [
            (1, "CLK", "FAULT_CLK", "input"),
            (2, "D", "FAN5V_IN", "input"),
            (3, "Q_N", "HW_NOFAULT_5", "output"),
            (4, "GND", "GND", "power_in"),
            (5, "Q", None, "output"),
            (6, "CLR_N", "RAW_CLEAR_FAST", "input"),
            (7, "PRE_N", "FAN5V_IN", "input"),
            (8, "VCC", "FAN5V_IN", "power_in"),
        ],
        "sn74lvc1g74",
        "IndependentRAW5-powered positive-edge latch; D=1. First watchdog failure storesQ=1/Q_N=0 until RAW5 power-cycle clear. 3.3V-only resets cannot intentionally clear it.",
    )
    ic(
        "U9",
        "TPS389001DSET",
        "Package_SON:WSON-6_1.5x1.5mm_P0.5mm",
        [
            (1, "SENSE", "RAW_POR_SENSE", "input"),
            (2, "GND", "GND", "power_in"),
            (3, "MR_N", "FAN5V_IN", "input"),
            (4, "VDD", "FAN5V_IN", "power_in"),
            (5, "CT", "RAW_POR_CT", "passive"),
            (6, "RESET_N", "RAW_CLEAR_N", "open_collector"),
        ],
        "tps3890",
        "Dedicatedrawpower-cycle clear nominal1.7963V; assertion/deassertion and1.65V latch retention crossover must be characterized. CT delays clear RELEASE, not fault capture.",
    )
    logic5("U10", "SN74LVC1G17DCKR", "sn74lvc1g17", "RAW_CLEAR_N", "RAW_CLEAR_FAST", "FAN5V_IN")
    logic5("U11", "SN74LVC1G17DCKR", "sn74lvc1g17", "HW_NOFAULT_5", "HW_NOFAULT")
    and_gate("U12", "MCU_HEALTH", "WD_OK_FAST", "HEALTH_AND_WD")
    and_gate("U13", "HEALTH_AND_WD", "HW_NOFAULT", "LEAF_PERMISSION")
    logic5("U14", "SN74LVC1G06DCKR", "sn74lvc1g06", "LEAF_PERMISSION", "LED_K", open_drain=True)
    logic5("U16", "SN74LVC1G34DCKR", "sn74lvc1g34", "HEARTBEAT", "HEARTBEAT_FAST")
    add(
        "U15",
        "TLP175A(TPL,E)",
        "RMX_FH02:TLP175A_11-4M1S_Receiving",
        [
            pin(1, "LED_A", "LED_A"),
            pin(3, "LED_K", "LED_K"),
            pin(4, "CONTACT_A", "P03_POWER_RUN"),
            pin(6, "CONTACT_B", "E28_POWER_RUN", side="R"),
        ],
        "https://toshiba.semicon-storage.com/info/TLP175A_datasheet_en_20230525.pdf?did=13665&prodName=TLP175A",
        "Normally-open isolated contact ONLY P03J106.3→E28J5.3. 1/3LED and4/6contact exact pins. Recommendedambient≤65°C. No E28_MASTER_ENABLE connection.",
    )
    add(
        "X1",
        "ABLS-4.000MHZ-12-D4Y-T",
        "RMX_FH02:ABLS_Manufacturer_Land",
        [pin(1, "XTAL1", "XTAL1"), pin(2, "XTAL2", "XTAL2", side="R")],
        "https://abracon.com/Resonators/abls.pdf",
        "4MHzfundamental/CL12pF/−40..85C/initial±30ppm/temp±30ppm. Manufacturerland5.6x2.1mm/9.5mmcentres. 15pF+15pF assumes4.5pFstray; drive/startup/complete±0.1%clock requires receiving tests.",
    )
    resistors = [
        (1, "1k", "FAN5V_IN", "LED_A", "Complete±3%; feed branch includes shunt current once."),
        (
            2,
            "10k",
            "LED_A",
            "LED_K",
            "Complete±3%; across LED, not merely gate pulldown. Ioff10uA creates≤.103VLED in settled model.",
        ),
        (3, "47k", "MCU_HEALTH", "GND", "DefaultOFF duringMCUreset/input state."),
        (4, "47k", "HEARTBEAT", "GND", "No floatingWDI whileMCUreset."),
        (5, "47k", "V3V3", "WD_OK", "Open-drainwatchdog/PG pullup."),
        (
            6,
            "10k",
            "V3V3",
            "MCU_RESET_N",
            "MCURESET externalpullup; internal30..60k table at5.5V is not our full3.3V bound. ExternalwatchdogdoesNOTdriveRESET; avoidsstartupEXTRF.",
        ),
        (7, "47k", "V3V3", "WD_EN", "WDalwaysenabled; manufacturing must not leave bypass fitted."),
        (8, "68k", "WD_OK_5", "GND", "Complete±3%; 1T45off2uA+G14input5uA gives≤.49028V."),
        (9, "39k", "HW_NOFAULT_5", "GND", "Complete±3%; rawFFIoff10uA+G17input5uA gives≤.60255V."),
        (10, "10k", "FAN5V_IN", "RAW_CLEAR_N", "SupervisorOCpullup; Schmitt before ordinaryCLR input."),
        (11, "56.2k", "FAN5V_IN", "RAW_POR_SENSE", "Complete±1% receiving."),
        (12, "100k", "RAW_POR_SENSE", "GND", "Complete±1% receiving."),
        (
            13,
            "10k",
            "LEAF_PERMISSION",
            "GND",
            "LEDsinkdefaultOFF whenlogicoutputs highZ;10uAoutputIoff+5uAinputleak→≤.1545V givencomplete±3%R. Intermediatepowerstillrequirescharacterization.",
        ),
        (
            14,
            "47k",
            "FAN_L_TACH",
            "GND",
            "Receiveropen-wiredefaultLOW; sourcepullup current already inFP01ledger.",
        ),
        (15, "47k", "FAN_R_TACH", "GND", "Receiveropen-wiredefaultLOW; noextraalways-on5Vpullup."),
        (16, "1k", "TACH_L_BUF", "MCU_TACH_L", "Edge/ISR error must be measured with this actualRC."),
        (17, "1k", "TACH_R_BUF", "MCU_TACH_R", "Edge/ISR error must be measured with this actualRC."),
        (
            20,
            "20k",
            "V3V3",
            "TEMP_L_NODE",
            "Complete±.5% receiving; exact203AT-2current/thermalcoupling unqualified.",
        ),
        (
            21,
            "1k",
            "TEMP_L_NODE",
            "TEMP_L_ADC",
            "Complete±3% receiving; totalADC+capacitorleak±1.1uA receiving.",
        ),
        (22, "20k", "V3V3", "TEMP_R_NODE", "Complete±.5% receiving."),
        (23, "1k", "TEMP_R_NODE", "TEMP_R_ADC", "Complete±3% receiving."),
        (
            24,
            "100k",
            "V3V3",
            "GND",
            "Complete±3% minimum-loadbleed:≥31.4uA at3.234V keepsLDOabove10uAaccuracycondition evenifMCU/sensorsquiet.",
        ),
    ]
    for n, value, a, b, note in resistors:
        r("R" + str(n), value, a, b, note)
    c(
        "C1",
        "10uF",
        "FAN5V_IN",
        "GND",
        "RequiredlocalFRONTinputcap; effective≥.1uF (project≥3uF receiving) acrossallcorners.",
    )
    c(
        "C2",
        "10uF",
        "V3V3",
        "GND",
        "RequiredlocalFRONToutputcap; effective≥2.2uF (project≥3uF receiving). ExactESR/stability notproved bynominal10uF.",
    )
    c(
        "C3",
        "10nF",
        "LDO_DELAY",
        "GND",
        "Sameface/directground; watchdoginitialENOUTlow independentlygatesstartup.",
    )
    supplies = {
        4: "V3V3",
        5: "V3V3",
        6: "V3V3",
        8: "V3V3",
        9: "V3V3",
        10: "FAN5V_IN",
        11: "FAN5V_IN",
        12: "FAN5V_IN",
        13: "FAN5V_IN",
        15: "FAN5V_IN",
        16: "V3V3",
        17: "V3V3",
        18: "V3V3",
        19: "V3V3",
    }
    for n, supply in supplies.items():
        c("C" + str(n), "100nF", supply, "GND", "Localbypass FRONT; noPCBplacement accepted.")
    c(
        "C7",
        "2.7nF",
        "WD_CWD",
        "GND",
        "Complete±10%receiving includesalltemperature/life/assembly; tWD=(77.4*C_nF+55)ms times.905..1.095. 160msfirstHBreceivingtargethas20%margin; source-rampreference mustbeverified.",
    )
    c("C14", "10nF", "RAW_POR_CT", "GND")
    c("C20", "15pF", "XTAL1", "GND")
    c("C21", "15pF", "XTAL2", "GND")
    c("C22", "10nF", "TEMP_L_ADC", "GND", "C0G; completeADC±3LSB andfilterleak are receiving only.")
    c("C23", "10nF", "TEMP_R_ADC", "GND")
    c("C24", "100nF", "V3V3", "GND", "Localbypass for heartbeat Schmitt U16.")

    def connector(ref, nets, note):
        count = len(nets)
        add(
            ref,
            f"JST B{count}B-XH-A / XHP-{count} / SXH-001T-P0.6",
            f"Connector_JST:JST_XH_B{count}B-XH-A_1x{count:02d}_P2.50mm_Vertical",
            [
                pin(
                    n + 1,
                    name if net is not None else "NC",
                    net,
                    "passive" if net is not None else "no_connect",
                )
                for n, (name, net) in enumerate(nets)
            ],
            JST,
            note,
        )

    connector(
        "J1",
        [
            (n, net)
            for n, net in [
                ("GND", "GND"),
                ("RAW5", "FAN5V_IN"),
                ("FAULT_L_UNUSED", None),
                ("FAULT_R_UNUSED", None),
                ("TACH_L", "FAN_L_TACH"),
                ("TACH_R", "FAN_R_TACH"),
            ]
        ],
        "ExactFP01J4pinmap1GND2RAW5/3FAULTL4FAULTRunusedbyfirmware/5TACHL6TACHR. Operatingforcebranchunimplemented; TESTP03J3 forbidden.",
    )
    connector(
        "J2",
        [("SENSOR", "TEMP_L_NODE"), ("GND", "GND")],
        "RemoteSEMITEC203AT-2; lead/connectorleak/thermalattachment unqualified.",
    )
    connector(
        "J3",
        [("SENSOR", "TEMP_R_NODE"), ("GND", "GND")],
        "RemoteSEMITEC203AT-2, independentsecondthermalzone.",
    )
    connector(
        "J4",
        [("FROM_P03_J106_3", "P03_POWER_RUN"), ("TO_E28_J5_3", "E28_POWER_RUN")],
        "Only normally-openPOWER_RUNleaf. ExistingE28R93pulldownretained. DoNOTcontactP03ownRUNbranch/rawfanfeed or driveE28_MASTER_ENABLE.",
    )
    add(
        "J5",
        "AVRISP2x3 target-powered3.3V sense ONLY",
        "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical",
        [
            pin(n, net, net)
            for n, net in enumerate(["ISP_MISO", "V3V3", "ISP_SCK", "ISP_MOSI", "MCU_RESET_N", "GND"], 1)
        ],
        "https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny24A-44A-84A-Data-Sheet-DS40002269A.pdf",
        "Targetselfpoweredonly. ProgrammerVtargetsense/notpowerinjection; ISPresetforcesMCUHEALTHinput/pulldownOFF and firmwareEXTRFfault. Cleanpowercycle requiredafterprogramming. Firmware/fuses mustbe independentlyverified.",
    )
    return parts


def footprints():
    dest = ROOT / "RMX_FH02.pretty"
    dest.mkdir(exist_ok=True)

    def fp(name, pads, body, court, note):
        x, y = body
        cx, cy = court
        return f'''(footprint "{name}" (version 20241229) (generator pcbnew) (layer "F.Cu")
 (descr "{note}") (attr smd)
 (fp_rect (start {-x / 2} {-y / 2}) (end {x / 2} {y / 2}) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))
 (fp_rect (start {-cx / 2} {-cy / 2}) (end {cx / 2} {cy / 2}) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
 {"".join(f'(pad "{n}" smd rect (at {px} {py}) (size {w} {h}) (layers "F.Cu" "F.Paste" "F.Mask"))' for n, px, py, w, h in pads)}
)'''

    (dest / "ABLS_Manufacturer_Land.kicad_mod").write_text(
        fp(
            "ABLS_Manufacturer_Land",
            [(1, -4.75, 0, 5.6, 2.1), (2, 4.75, 0, 5.6, 2.1)],
            (11.6, 4.85),
            (15.6, 5.35),
            "AbraconABLSRevADp3 actual5.6x2.1lands9.5centres; PCBcaseinsulation/processunapproved.",
        )
    )
    (dest / "TLP175A_11-4M1S_Receiving.kicad_mod").write_text(
        fp(
            "TLP175A_11-4M1S_Receiving",
            [
                (1, -1.27, 3.35, 1.2, 1.8),
                (3, 1.27, 3.35, 1.2, 1.8),
                (4, 1.27, -3.35, 1.2, 1.8),
                (6, -1.27, -3.35, 1.2, 1.8),
            ],
            (3.95, 4.8),
            (4.45, 9.0),
            "Toshiba11-4M1SRev7p7package; ownreceivinglandnotmanufacturerrecommendedpattern/assemblerapproved.",
        )
    )


def selection(parts):
    values = {
        "1k": "1K00",
        "10k": "10K0",
        "20k": "20K0",
        "39k": "39K0",
        "47k": "47K0",
        "56.2k": "56K2",
        "68k": "68K0",
        "100k": "100K",
    }
    exact = {}
    for p in parts:
        if p["ref"].startswith("R"):
            value = p["part"].split()[0]
            p["part"] = value + " 0.1%25ppm TNPW0805" + values[value] + "BEEA"
        exact[p["ref"]] = dict(
            part=p["part"],
            footprint=p["footprint"],
            PCB_pose=None,
            selection_and_effective_bounds_qualified=False,
        )
    return exact


def main():
    OUT.mkdir(exist_ok=True)
    footprints()
    parts = components()
    selections = selection(parts)
    (ROOT / "selection.json").write_text(json.dumps(selections, indent=2) + "\n")
    generate(
        ROOT,
        "FH02",
        "fan_health",
        parts,
        [
            (
                20,
                1570,
                "FH02: independentRAW5faultlatch preventswatchdogautomaticretryreclosure; no physicalacceptance.",
            ),
            (
                20,
                1580,
                "Only P03J106.3-to-E28J5.3 POWER_RUN leaf. NeverdriveE28_MASTER_ENABLE. RAWfanfeedremainslive.",
            ),
            (
                20,
                1590,
                "All-current/sensor/clock/contact/partial-power/fulltemperature receivingrequirements remainunverified. NoPCBimplemented.",
            ),
        ],
        (760, 1630),
        [("FAN5V_IN", 20.32, 20.32), ("GND", 60.96, 20.32)],
    )
    cli = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/rmx-kicad-config",
        FONTCONFIG_FILE=str(REPO / "build-hardware/kicad-fonts.conf"),
    )
    commands = []
    for label, args in [
        (
            "netlist",
            ["sch", "export", "netlist", "--format", "kicadxml", "--output", str(OUT / "netlist.xml")],
        ),
        ("erc", ["sch", "erc", "--format", "json", "--output", str(OUT / "erc.json")]),
        ("svg", ["sch", "export", "svg", "--output", str(OUT / "schematic-svg")]),
    ]:
        cmd = [cli, *args, str(ROOT / "fan_health.kicad_sch")]
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        (OUT / (label + ".log")).write_text(result.stdout + result.stderr)
        commands.append(dict(command=cmd, returncode=result.returncode))
        if result.returncode:
            raise RuntimeError((label, result.returncode, result.stdout, result.stderr))
    actual, pins = netlist(OUT / "netlist.xml")
    expected = {p["ref"]: {n["number"]: n["net"] for n in p["pins"]} for p in parts}
    mismatches = {
        ref: dict(expected=m, actual=pins.get(ref)) for ref, m in expected.items() if pins.get(ref) != m
    }
    # Native no-connect nets remain distinct and are not contracted operating nets.
    for ref in list(mismatches):
        for n, net in expected[ref].items():
            if net is None and str(pins[ref].get(n, "")).startswith("unconnected-"):
                pins[ref][n] = None
        if pins[ref] == expected[ref]:
            del mismatches[ref]
    erc = json.loads((OUT / "erc.json").read_text())
    findings = [v for s in erc["sheets"] for v in s["violations"]]
    (OUT / "native.json").write_text(
        json.dumps(
            dict(
                component_count=len(parts),
                native_commands=commands,
                actual_component_set_matches=set(actual) == set(expected),
                pin_map_mismatches=mismatches,
                erc_findings=findings,
                physical_qualified=False,
                PCB_implemented=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(dict(parts=len(parts), pin_mismatches=len(mismatches), erc_findings=len(findings))))


if __name__ == "__main__":
    main()
