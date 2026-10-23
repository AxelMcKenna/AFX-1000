"""E11 independent input qualification and stereo relay schematic specification. Pins follow cited datasheets."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPONENTS = []


def pin(number, name, kind, side, net):
    return dict(number=str(number), name=name, kind=kind, side=side, net=net)


def component(ref, part, footprint, pins, x, y, source="", note=""):
    COMPONENTS.append(
        dict(ref=ref, part=part, footprint=footprint, pins=pins, x=x, y=y, source=source, note=note)
    )


component(
    "U1",
    "TPS3431SDRBR",
    "Package_SON:VSON-8-1EP_3x3mm_P0.65mm_EP1.65x2.4mm",
    [
        pin(1, "VDD", "power_in", "L", "3V3"),
        pin(3, "EN", "input", "L", "3V3"),
        pin(5, "SET1", "input", "L", "3V3"),
        pin(6, "WDI", "input", "L", "HEARTBEAT"),
        pin(4, "AGND", "power_in", "L", "AGND"),
        pin(9, "EP", "power_in", "L", "AGND"),
        pin(2, "CWD", "passive", "R", "CWD"),
        pin(7, "WDO_N", "open_collector", "R", "LOCAL_OK"),
        pin(8, "ENOUT", "open_collector", "R", "LOCAL_OK"),
    ],
    60.96,
    60.96,
    "https://www.ti.com/lit/ds/symlink/tps3431.pdf",
    "150pF timing; EN/SET1 permanently high",
)

component(
    "U2",
    "SN74HCS08DR",
    "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    [
        pin(1, "1A", "input", "L", "LOCAL_OK"),
        pin(2, "1B", "input", "L", "ANALOG_OK"),
        pin(3, "1Y", "output", "R", "INPUT_ENABLE"),
        pin(4, "2A", "input", "L", "INPUT_ENABLE"),
        pin(5, "2B", "input", "L", "PROCESS_OK"),
        pin(6, "2Y", "output", "R", "PROCESS_HEALTH"),
        pin(9, "3A", "input", "L", "ARMED"),
        pin(10, "3B", "input", "L", "PERMIT_CLEAN"),
        pin(8, "3Y", "output", "R", "COIL_ENABLE"),
        pin(12, "4A", "input", "L", "MCU_PERMIT"),
        pin(13, "4B", "input", "L", "MCU_PERMIT"),
        pin(11, "4Y", "output", "R", "PERMIT_CLEAN"),
        pin(14, "VCC", "power_in", "R", "3V3"),
        pin(7, "AGND", "power_in", "R", "AGND"),
    ],
    60.96,
    157.48,
    "https://www.ti.com/lit/ds/symlink/sn74hcs08.pdf",
    "All gate inputs are Schmitt-trigger; no unused gates",
)

component(
    "U3",
    "SN74LVC1G74DCTR",
    "Package_TO_SOT_SMD:SOT-23-8",
    [
        pin(1, "CLK", "input", "L", "PERMIT_CLEAN"),
        pin(2, "D", "input", "L", "3V3"),
        pin(6, "CLR_N", "input", "L", "CLEAR_N"),
        pin(7, "PRE_N", "input", "L", "3V3"),
        pin(8, "VCC", "power_in", "L", "3V3"),
        pin(3, "Q", "output", "R", "ARMED"),
        pin(5, "Q_N", "output", "R", None),
        pin(4, "AGND", "power_in", "R", "AGND"),
    ],
    180.34,
    157.48,
    "https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf",
    "Positive edge arms Q; asynchronous clear prevents WDO recovery from rearming",
)

for ref, part, sense, x in [("U4", "TPS3808G33DBVR", "3V3", 180.34), ("U5", "TPS3808G50DBVR", "5V", 299.72)]:
    component(
        ref,
        part,
        "Package_TO_SOT_SMD:SOT-23-6",
        [
            pin(6, "VDD", "power_in", "L", "3V3"),
            pin(5, "SENSE", "input", "L", sense),
            pin(3, "MR_N", "input", "L", "3V3"),
            pin(2, "AGND", "power_in", "R", "AGND"),
            pin(1, "RESET_N", "open_collector", "R", "LOCAL_OK"),
            pin(4, "CT", "passive", "R", "STARTUP_CT" if ref == "U4" else None),
        ],
        x,
        60.96,
        "https://www.ti.com/lit/ds/symlink/tps3808.pdf",
        "U4: CT via100k to3V3 selects180..420ms startup guard; U5: CT open,20ms nominal release",
    )


def connector(ref, nets, x, y, note):
    component(
        ref,
        "Conn_01x" + str(len(nets)).zfill(2),
        f"Connector_PinHeader_2.54mm:PinHeader_1x{len(nets):02d}_P2.54mm_Vertical",
        [pin(i + 1, str(i + 1), "passive", "L", net) for i, net in enumerate(nets)],
        x,
        y,
        note=note,
    )


connector("J1", ["5V", "AGND", "3V3"], 419.1, 60.96, "Regulated inputs only; common ground")
connector(
    "J2",
    ["AGND", "HEARTBEAT", "MCU_PERMIT", "GAIN_REQ", "ARMED", "BYPASS_SENSE"],
    299.72,
    157.48,
    "External F02: D13 heartbeat / D29 permit / D9 gain / D30 Q; bypass sense to MCP0x22 GPA1",
)
connector(
    "J3",
    ["3V3", "PROCESS_OK", "ANALOG_OK", "AGND", "BYPASS_SENSE"],
    419.1,
    157.48,
    "Process contact must close to 3V3; missing loop/analog-good wire fails low",
)
connector(
    "J4",
    ["5V", "BYPASS_LOW", "5V", "INPUT_LOW"],
    299.72,
    248.92,
    "Optional coil access for included K1/K2; do not duplicate relays on another board",
)
connector("J5", ["5V", "GAIN_LOW"], 419.1, 248.92, "Two parallel 5V gain coils; contacts on audio carrier")

for ref, drain, gate, x in [
    ("Q1", "BYPASS_LOW", "BYPASS_GATE", 60.96),
    ("Q2", "GAIN_LOW", "GAIN_GATE", 180.34),
]:
    component(
        ref,
        "AO3400A",
        "Package_TO_SOT_SMD:SOT-23",
        [
            pin(1, "G", "input", "L", gate),
            pin(2, "S", "passive", "L", "AGND"),
            pin(3, "D", "passive", "R", drain),
        ],
        x,
        248.92,
        "https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf",
    )

PASSIVES = [
    ("C1", "150pF C0G 5%", "CWD", "AGND", "C_0805_2012Metric"),
    *[(f"C{i}", "100nF X7R", "3V3", "AGND", "C_0805_2012Metric") for i in range(2, 7)],
    ("C7", "1uF 16V X7R", "3V3", "AGND", "C_0805_2012Metric"),
    ("C8", "22uF 16V X7R", "5V", "AGND", "C_1206_3216Metric"),
    ("R1", "10k 1%", "3V3", "LOCAL_OK", "R_0805_2012Metric"),
    ("R2", "100k 1%", "HEARTBEAT", "AGND", "R_0805_2012Metric"),
    ("R3", "47k 1%", "MCU_PERMIT", "AGND", "R_0805_2012Metric"),
    ("R4", "47k 1%", "PROCESS_OK", "AGND", "R_0805_2012Metric"),
    ("R5", "47k 1%", "ANALOG_OK", "AGND", "R_0805_2012Metric"),
    ("R6", "10k 1%", "3V3", "BYPASS_SENSE", "R_0805_2012Metric"),
    ("R7", "47k 1%", "GAIN_REQ", "AGND", "R_0805_2012Metric"),
    ("R8", "4.7k 1%", "FINAL_ENABLE", "BYPASS_GATE", "R_0805_2012Metric"),
    ("R9", "270k 1%", "BYPASS_GATE", "AGND", "R_0805_2012Metric"),
    ("R10", "4.7k 1%", "GAIN_REQ", "GAIN_GATE", "R_0805_2012Metric"),
    ("R11", "270k 1%", "GAIN_GATE", "AGND", "R_0805_2012Metric"),
    ("D1", "SMF9.0A", "BYPASS_LOW", "AGND", "D_SOD-123F"),
    ("D2", "SMF9.0A", "GAIN_LOW", "AGND", "D_SOD-123F"),
]
for index, (ref, part, a, b, fp) in enumerate(PASSIVES):
    library = {"C": "Capacitor_SMD", "R": "Resistor_SMD", "D": "Diode_SMD"}[ref[0]]
    names = ("K", "A") if ref.startswith("D") else ("1", "2")
    note = ("Local bypass for U" + str(int(ref[1:]) - 1)) if ref in ["C2", "C3", "C4", "C5", "C6"] else ""
    if ref == "C8":
        note = "Select effective capacitance >=10uF at 5V; confirm DC-bias curve"
    component(
        ref,
        part,
        library + ":" + fp,
        [pin(1, names[0], "passive", "L", a), pin(2, names[1], "passive", "R", b)],
        40.64 + index % 6 * 101.6,
        309.88 + index // 6 * 25.4,
        source="https://www.mouser.com/datasheet/2/240/Littelfuse_TVS_Diode_SMF_Datasheet.pdf-1698977.pdf"
        if ref.startswith("D")
        else "",
        note=note,
    )

component(
    "U6",
    "SN74HCS08DR",
    "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    [
        pin(1, "1A", "input", "L", "TIMER_ENABLE"),
        pin(2, "1B", "input", "L", "TIMER_INPUT_OK"),
        pin(3, "1Y", "output", "R", "INPUT_READY"),
        pin(4, "2A", "input", "L", "COIL_ENABLE"),
        pin(5, "2B", "input", "L", "CLEAR_N"),
        pin(6, "2Y", "output", "R", "FINAL_ENABLE"),
        pin(9, "3A", "input", "L", "INPUT_READY"),
        pin(10, "3B", "input", "L", "PROCESS_HEALTH"),
        pin(8, "3Y", "output", "R", "CLEAR_N"),
        pin(12, "4A", "input", "L", "INPUT_ENABLE"),
        pin(13, "4B", "input", "L", "GAIN_STABLE"),
        pin(11, "4Y", "output", "R", "TIMER_ENABLE"),
        pin(14, "VCC", "power_in", "R", "3V3"),
        pin(7, "GND", "power_in", "R", "AGND"),
    ],
    0,
    0,
    "https://www.ti.com/lit/ds/symlink/sn74hcs08.pdf",
    "Direct health/gain qualification, asynchronous latch clear and final output gate.",
)

component(
    "U7",
    "LTC6994HS6-1#TRMPBF",
    "Package_TO_SOT_SMD:TSOT-23-6",
    [
        pin(1, "IN", "input", "L", "TIMER_ENABLE"),
        pin(2, "GND", "power_in", "L", "AGND"),
        pin(3, "SET", "passive", "L", "TIMER_SET"),
        pin(4, "DIV", "input", "R", "TIMER_DIV"),
        pin(5, "V+", "power_in", "R", "3V3"),
        pin(6, "OUT", "output", "R", "TIMER_INPUT_OK"),
    ],
    0,
    0,
    "https://www.analog.com/media/en/technical-documentation/data-sheets/LTC6994-1-6994-2.pdf",
    "LTC6994-1 only: DIVCODE6/POL0; rising delay ~2.008s, falling edge immediate. No external CT charge memory.",
)

component(
    "U8",
    "SN74HCS86DR",
    "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    [
        pin(1, "1A", "input", "L", "GAIN_REQ"),
        pin(2, "1B", "input", "L", "GAIN_DELAY"),
        pin(3, "1Y", "output", "R", "GAIN_EDGE"),
        pin(4, "2A", "input", "L", "GAIN_EDGE"),
        pin(5, "2B", "input", "L", "3V3"),
        pin(6, "2Y", "output", "R", "GAIN_STABLE"),
        pin(9, "3A", "input", "L", "AGND"),
        pin(10, "3B", "input", "L", "AGND"),
        pin(8, "3Y", "output", "R", None),
        pin(12, "4A", "input", "L", "AGND"),
        pin(13, "4B", "input", "L", "AGND"),
        pin(11, "4Y", "output", "R", None),
        pin(14, "VCC", "power_in", "R", "3V3"),
        pin(7, "GND", "power_in", "R", "AGND"),
    ],
    0,
    0,
    "https://www.ti.com/lit/ds/symlink/sn74hcs86.pdf",
    "Schmitt XOR detects both gain edges; second gate inverts pulse. Unused inputs grounded, outputs NC.",
)

component(
    "Q3",
    "AO3400A",
    "Package_TO_SOT_SMD:SOT-23",
    [
        pin(1, "G", "input", "L", "INPUT_GATE"),
        pin(2, "S", "passive", "L", "AGND"),
        pin(3, "D", "passive", "R", "INPUT_LOW"),
    ],
    0,
    0,
    "https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf",
    "Input relay follows local/analog health, independent of manual bypass and MCU permit.",
)

for ref, nets, note in [
    (
        "K1",
        {
            "1": "5V",
            "8": "BYPASS_LOW",
            "3": "OUT_L",
            "2": "IN_L",
            "4": "PROC_OUT_L",
            "6": "OUT_R",
            "7": "IN_R",
            "5": "PROC_OUT_R",
        },
        "Released output selector is dry; energized is processed.",
    ),
    (
        "K2",
        {
            "1": "5V",
            "8": "INPUT_LOW",
            "3": "PROC_IN_L",
            "2": None,
            "4": "IN_L",
            "6": "PROC_IN_R",
            "7": None,
            "5": "IN_R",
        },
        "Input isolation has a separate driver; open NC contacts.",
    ),
]:
    names = {
        "1": "COIL+",
        "8": "COIL-",
        "3": "L_COM",
        "2": "L_NC",
        "4": "L_NO",
        "6": "R_COM",
        "7": "R_NC",
        "5": "R_NO",
    }
    component(
        ref,
        "G6K-2F-Y DC5",
        "Relay_SMD:Relay_DPDT_Omron_G6K-2F-Y",
        [
            pin(n, names[n], "passive", "L" if n in ("1", "8", "3", "6") else "R", net)
            for n, net in nets.items()
        ],
        0,
        0,
        "https://omronfs.omron.com/en_US/ecb/products/pdf/en-g6k.pdf",
        note,
    )

connector(
    "J6", ["AGND", "INPUT_READY"], 0, 0, "MCP0x22 GPA3; active high; receiving-end 270k pull-down required"
)
connector("J7", ["IN_L", "AGND", "IN_R"], 0, 0, "Line input after RCA/TS source selection/normalling")
connector("J8", ["OUT_L", "AGND", "OUT_R"], 0, 0, "Stereo line output; common audio/logic reference")
connector(
    "J9",
    ["PROC_IN_L", "AGND", "PROC_IN_R", "PROC_OUT_L", "AGND", "PROC_OUT_R"],
    0,
    0,
    "Pins1..3 -> E10 J1; pins4..6 <- E05 J2. Not raw converter pins.",
)

for ref, value, a, b, fp, note in [
    (
        "R12",
        "4.7k 1%",
        "INPUT_ENABLE",
        "INPUT_GATE",
        "R_0805_2012Metric",
        "Independent input coil gate series resistor",
    ),
    ("R13", "270k 1%", "INPUT_GATE", "AGND", "R_0805_2012Metric", "Input gate defaults off"),
    (
        "R14",
        "383k 0.1% 25ppm",
        "TIMER_SET",
        "AGND",
        "R_0805_2012Metric",
        "Allocate total RSET error <=1% including temperature/aging",
    ),
    (
        "R15",
        "47k 1%",
        "GAIN_REQ",
        "GAIN_DELAY",
        "R_0805_2012Metric",
        "Both-edge RC reset; 3.3V Schmitt thresholds require qualification",
    ),
    (
        "R16",
        "147k 1%",
        "3V3",
        "TIMER_DIV",
        "R_0805_2012Metric",
        "DIVCODE6/POL0; allocate total resistor error <=1.5% each",
    ),
    (
        "R17",
        "100k 1%",
        "TIMER_DIV",
        "AGND",
        "R_0805_2012Metric",
        "Protect DIV from fast edges; total capacitance <100pF",
    ),
    (
        "R18",
        "100k 1%",
        "3V3",
        "STARTUP_CT",
        "R_0805_2012Metric",
        "U4 selects300ms nominal release; require timer startup <=100ms before input enable",
    ),
    (
        "C9",
        "1uF 16V X7R 10%",
        "GAIN_DELAY",
        "AGND",
        "C_0805_2012Metric",
        "Require effective 0.7..1.3uF over bias/temp/aging",
    ),
    ("C10", "100nF 16V X7R", "3V3", "AGND", "C_0805_2012Metric", "Local U6 bypass"),
    ("C11", "100nF 16V X7R", "3V3", "AGND", "C_0805_2012Metric", "Local U7 bypass"),
    ("C12", "100nF 16V X7R", "3V3", "AGND", "C_0805_2012Metric", "Local U8 bypass"),
    (
        "D3",
        "SMF9.0A",
        "INPUT_LOW",
        "AGND",
        "D_SOD-123F",
        "Input coil TVS; transient release/overshoot unmeasured",
    ),
]:
    library = {"R": "Resistor_SMD", "C": "Capacitor_SMD", "D": "Diode_SMD"}[ref[0]]
    names = ("K", "A") if ref.startswith("D") else ("1", "2")
    component(
        ref,
        value,
        library + ":" + fp,
        [pin(1, names[0], "passive", "L", a), pin(2, names[1], "passive", "R", b)],
        0,
        0,
        note=note,
    )

# Independent native review sheet, preserving historical E02/E03 projects.
positions = {
    "U1": (60, 60),
    "U4": (200, 60),
    "U5": (340, 60),
    "U2": (60, 160),
    "U3": (200, 160),
    "U6": (340, 160),
    "U7": (480, 60),
    "U8": (480, 160),
    "Q1": (60, 270),
    "Q2": (200, 270),
    "Q3": (340, 270),
    "K1": (480, 270),
    "K2": (620, 270),
    "J1": (760, 60),
    "J2": (760, 160),
    "J3": (760, 270),
    "J4": (60, 365),
    "J5": (200, 365),
    "J6": (340, 365),
    "J7": (480, 365),
    "J8": (620, 365),
    "J9": (760, 365),
}
passive_index = 0
for c in COMPONENTS:
    if c["ref"] in positions:
        x, y = positions[c["ref"]]
    else:
        x, y = 40 + 90 * (passive_index % 9), 450 + 30 * (passive_index // 9)
        passive_index += 1
    c["x"] = round(round(x / 1.27) * 1.27, 4)
    c["y"] = round(round(y / 1.27) * 1.27, 4)

NOTES = [
    (
        20.32,
        17.78,
        "E11: independent input precharge and edge-armed wet output. All blocks show physical package pin numbers.",
    ),
    (
        20.32,
        25.4,
        "Replaces E02+E03 for the external F02 profile; do not assemble all three projects together. No PCB or physical validation.",
    ),
    (
        20.32,
        596.9,
        "K2 closes on LOCAL_OK & ANALOG_OK; manual bypass clears K1 only. Gain edges restart U7, holding K1 dry for ~2s.",
    ),
    (
        20.32,
        604.52,
        "INPUT_READY -> MCP0x22 GPA3, no pull-up, receiving 270k pull-down. Firmware adds 1.25s quiet + 350ms stable rearm.",
    ),
    (
        20.32,
        612.14,
        "Common AGND reference; keep coil returns away from audio paths. Rail monitors, complete integrated PCB, harnesses and bench tests remain open.",
    ),
]
