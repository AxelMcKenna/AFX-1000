"""E02 watchdog/relay-driver schematic specification. Pins follow cited datasheets."""

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
        pin(4, "GND", "power_in", "L", "GND"),
        pin(9, "EP", "power_in", "L", "GND"),
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
        pin(3, "1Y", "output", "R", "HEALTH_A"),
        pin(4, "2A", "input", "L", "HEALTH_A"),
        pin(5, "2B", "input", "L", "PROCESS_OK"),
        pin(6, "2Y", "output", "R", "CLEAR_N"),
        pin(9, "3A", "input", "L", "ARMED"),
        pin(10, "3B", "input", "L", "PERMIT_CLEAN"),
        pin(8, "3Y", "output", "R", "COIL_ENABLE"),
        pin(12, "4A", "input", "L", "MCU_PERMIT"),
        pin(13, "4B", "input", "L", "MCU_PERMIT"),
        pin(11, "4Y", "output", "R", "PERMIT_CLEAN"),
        pin(14, "VCC", "power_in", "R", "3V3"),
        pin(7, "GND", "power_in", "R", "GND"),
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
        pin(4, "GND", "power_in", "R", "GND"),
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
            pin(2, "GND", "power_in", "R", "GND"),
            pin(1, "RESET_N", "open_collector", "R", "LOCAL_OK"),
            pin(4, "CT", "passive", "R", None),
        ],
        x,
        60.96,
        "https://www.ti.com/lit/ds/symlink/tps3808.pdf",
        "CT intentionally open: 20ms nominal reset release delay",
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


connector("J1", ["5V", "GND", "3V3"], 419.1, 60.96, "Regulated inputs only; common ground")
connector(
    "J2",
    ["GND", "HEARTBEAT", "MCU_PERMIT", "GAIN_REQ", "ARMED", "BYPASS_SENSE"],
    299.72,
    157.48,
    "Seed D13/D26/D9/D28/D0 respectively; GND pin 1",
)
connector(
    "J3",
    ["3V3", "PROCESS_OK", "ANALOG_OK", "GND", "BYPASS_SENSE"],
    419.1,
    157.48,
    "Process contact must close to 3V3; missing loop/analog-good wire fails low",
)
connector(
    "J4", ["5V", "BYPASS_LOW"], 299.72, 248.92, "Two parallel 5V bypass coils; contacts on audio carrier"
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
            pin(2, "S", "passive", "L", "GND"),
            pin(3, "D", "passive", "R", drain),
        ],
        x,
        248.92,
        "https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf",
    )

PASSIVES = [
    ("C1", "150pF C0G 5%", "CWD", "GND", "C_0805_2012Metric"),
    *[(f"C{i}", "100nF X7R", "3V3", "GND", "C_0805_2012Metric") for i in range(2, 7)],
    ("C7", "1uF 16V X7R", "3V3", "GND", "C_0805_2012Metric"),
    ("C8", "22uF 16V X7R", "5V", "GND", "C_1206_3216Metric"),
    ("R1", "10k 1%", "3V3", "LOCAL_OK", "R_0805_2012Metric"),
    ("R2", "100k 1%", "HEARTBEAT", "GND", "R_0805_2012Metric"),
    ("R3", "47k 1%", "MCU_PERMIT", "GND", "R_0805_2012Metric"),
    ("R4", "47k 1%", "PROCESS_OK", "GND", "R_0805_2012Metric"),
    ("R5", "47k 1%", "ANALOG_OK", "GND", "R_0805_2012Metric"),
    ("R6", "10k 1%", "3V3", "BYPASS_SENSE", "R_0805_2012Metric"),
    ("R7", "47k 1%", "GAIN_REQ", "GND", "R_0805_2012Metric"),
    ("R8", "4.7k 1%", "COIL_ENABLE", "BYPASS_GATE", "R_0805_2012Metric"),
    ("R9", "270k 1%", "BYPASS_GATE", "GND", "R_0805_2012Metric"),
    ("R10", "4.7k 1%", "GAIN_REQ", "GAIN_GATE", "R_0805_2012Metric"),
    ("R11", "270k 1%", "GAIN_GATE", "GND", "R_0805_2012Metric"),
    ("D1", "SMF9.0A", "BYPASS_LOW", "GND", "D_SOD-123F"),
    ("D2", "SMF9.0A", "GAIN_LOW", "GND", "D_SOD-123F"),
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
