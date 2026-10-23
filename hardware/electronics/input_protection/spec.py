"""E16 fast-OV adaptation of the E15 DC inlet/eFuse and enable guard.

Input protection only. Final rail OV disconnects, layout and bench proof remain
separate work; no mains circuitry or external messages/orders are involved.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPONENTS = []
TI = "https://www.ti.com/lit/ds/symlink/"
NXP = "https://assets.nexperia.com/documents/data-sheet/"


def pin(n, name, kind, side, net):
    return dict(number=str(n), name=name, kind=kind, side=side, net=net)


def component(ref, part, footprint, pins, x=0, y=0, source="", note=""):
    COMPONENTS.append(
        dict(ref=ref, part=part, footprint=footprint, pins=pins, x=x, y=y, source=source, note=note)
    )


def resistor(ref, a, b, value, precision=True, note=""):
    component(
        ref,
        value + (" 0.1% 10ppm" if precision else " 1%"),
        "Resistor_SMD:R_0805_2012Metric",
        [pin(1, "1", "passive", "L", a), pin(2, "2", "passive", "R", b)],
        note=note,
    )


def capacitor(ref, a, b, value, large=False, fp=None, note=""):
    component(
        ref,
        value,
        fp or ("Capacitor_SMD:" + ("C_1210_3225Metric" if large else "C_0805_2012Metric")),
        [pin(1, "+", "passive", "L", a), pin(2, "-", "passive", "R", b)],
        note=note,
    )


component(
    "J1",
    "PJ-102AH",
    "Connector_BarrelJack:BarrelJack_CUI_PJ-102AH_Horizontal",
    [
        pin(1, "CENTER+", "passive", "L", "DC_IN"),
        pin(2, "SLEEVE", "passive", "L", "AGND"),
        pin(3, "SWITCH", "passive", "L", None),
    ],
    80,
    70,
    "https://www.sameskydevices.com/product/resource/pj-102ah.pdf",
    "5A24V inlet; center positive. Adapter target12V3A +/-5% delivered at inlet; exact adapter unselected.",
)
component(
    "F1",
    "0451004.MRL 4A 125V",
    "Fuse:Fuse_Littelfuse-NANO2-451_453",
    [pin(1, "1", "passive", "L", "DC_IN"), pin(2, "2", "passive", "R", "VIN_SYS")],
    source="https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1",
    note="Backup fuse, nominal cold resistance16mOhm/I2t3.152A2s. Clearing/adapter/TVS coordination remains unverified; 30mOhm hot allocation is not a datasheet maximum.",
)
component(
    "D1",
    "SMBJ33CA-E3/52",
    "Diode_SMD:D_SMB",
    [pin(1, "1", "passive", "L", "VIN_SYS"), pin(2, "2", "passive", "R", "AGND")],
    source="https://www.vishay.com/docs/88392/smbj.pdf",
    note="Bidirectional33V TVS tolerates24V DC misplug without normal avalanche. No surge-class or TVS/fuse coordination approval.",
)
component(
    "Q1",
    "PSMN012-100YS,115",
    "Package_TO_SOT_SMD:LFPAK56",
    [
        *[pin(i, "SOURCE", "passive", "L", "VIN_SYS") for i in (1, 2, 3)],
        pin(4, "GATE", "input", "L", "BLOCK_GATE"),
        pin(5, "DRAIN/MB", "passive", "R", "VIN_IC"),
    ],
    350,
    70,
    NXP + "PSMN012-100YS.pdf",
    "Source is INPUT, drain is eFuse IN. Body diode permits cold positive startup; external blocking FET opposes internal pass-FET body diode.",
)
component(
    "Q2",
    "BSS138-7-F",
    "Package_TO_SOT_SMD:SOT-23",
    [
        pin(1, "GATE", "input", "L", "BLOCK_DRV"),
        pin(2, "SOURCE", "passive", "L", "VIN_SYS"),
        pin(3, "DRAIN", "passive", "R", "BLOCK_GATE"),
    ],
    620,
    70,
    "https://www.diodes.com/datasheet/download/BSS138.pdf",
    "Fast gate discharge as manufacturer Fig8-7. Ciss50pF max at10V; source follows raw input, never connect source to AGND.",
)
component(
    "U1",
    "TPS26630RGER",
    "Package_DFN_QFN:Texas_RGE0024H_VQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm",
    [
        pin(1, "IN", "power_in", "L", "VIN_IC"),
        pin(2, "IN", "power_in", "L", "VIN_IC"),
        pin(3, "B_GATE", "output", "R", "BLOCK_GATE"),
        pin(4, "DRV", "output", "R", "BLOCK_DRV"),
        pin(5, "IN_SYS", "power_in", "L", "VIN_SYS"),
        pin(6, "UVLO", "input", "L", "INPUT_UV"),
        pin(7, "OVP", "input", "L", "INPUT_OV"),
        pin(8, "GND", "power_in", "L", "AGND"),
        pin(9, "dVdT", "passive", "L", "INPUT_SLEW"),
        pin(10, "ILIM", "passive", "L", "INPUT_ILIM"),
        pin(11, "MODE", "input", "L", None),
        pin(12, "SHDN", "input", "L", "POWER_RUN"),
        pin(13, "IMON", "output", "R", None),
        pin(14, "FLT", "open_collector", "R", None),
        pin(15, "PGTH", "input", "L", "INPUT_PGTH"),
        pin(16, "PGOOD", "open_collector", "R", "POWER_READY"),
        pin(17, "OUT", "power_out", "R", "VIN_PROTECTED"),
        pin(18, "OUT", "passive", "R", "VIN_PROTECTED"),
        *[pin(i, "NC", "no_connect", "L", None) for i in range(19, 25)],
        pin(25, "EP/GND", "power_in", "L", "AGND"),
    ],
    350,
    230,
    TI + "tps2663.pdf",
    "TPS26630 has no2x overload-pulse feature. MODE left open selects latch-off; power switch cycles SHDN to clear a fault.",
)

# Always-on auxiliary supply is fed BEFORE the eFuse internal pass FET. Its
# startup path is the external Q1 body diode, even with POWER_RUN low.
component(
    "U2",
    "TPS7A1601DGNR",
    "Package_SO:MSOP-8-1EP_3x3mm_P0.65mm_EP1.68x1.88mm",
    [
        pin(1, "OUT", "power_out", "R", "V2V5_AUX"),
        pin(2, "FB", "input", "L", "AUX_FB"),
        pin(3, "PG", "open_collector", "R", "POWER_RUN"),
        pin(4, "GND", "power_in", "L", "AGND"),
        pin(5, "EN", "input", "L", "VIN_IC"),
        pin(6, "NC", "no_connect", "L", None),
        pin(7, "DELAY", "passive", "L", "AUX_START_DELAY"),
        pin(8, "IN", "power_in", "L", "VIN_IC"),
        pin(9, "EP/GND", "power_in", "L", "AGND"),
    ],
    80,
    230,
    TI + "tps7a16.pdf",
    "Independent~2.5V for power switch and enable pull-up. Never connect to Seed3 3V3 output.",
)
resistor(
    "R1",
    "VIN_SYS",
    "INPUT_UV",
    "309k",
    note="Total error<=0.3%; minimum actual input resistor must exceed300k for reverse-input protection",
)
resistor("R2", "INPUT_UV", "AGND", "40.2k")
resistor(
    "R3",
    "VIN_SYS",
    "INPUT_OV",
    "309k",
    note="Total error<=0.3%; limit input current during reversed/misplugged supply",
)
resistor("R4", "INPUT_OV", "AGND", "28k")
resistor("R5", "VIN_PROTECTED", "INPUT_PGTH", "73.2k")
resistor("R6", "INPUT_PGTH", "AGND", "10k")
resistor(
    "R7",
    "INPUT_ILIM",
    "AGND",
    "6.49k",
    note="Nominal18kOhm*A/R=2.77A; allocate10% programming error, not a guarantee at an unlisted resistor value",
)
resistor("R8", "V2V5_AUX", "AUX_FB", "110k")
resistor("R9", "AUX_FB", "AGND", "100k")
resistor(
    "R10",
    "V2V5_AUX",
    "POWER_READY",
    "1k",
    False,
    "Pull-up independent of Seed3 power; output goes to E14 guarded enable divider",
)
resistor(
    "R11",
    "V2V5_AUX",
    "AGND",
    "10k",
    False,
    "Auxiliary bleeder exceeds positive OVP clamp injection under declared input envelope",
)
resistor(
    "R12",
    "POWER_RUN",
    "AGND",
    "47k",
    False,
    "Missing switch remains OFF with10uA internal source plus1uA auxiliary-PG leakage; load for PG and fast OV sinks",
)
resistor(
    "R13",
    "V2V5_AUX",
    "SWITCH_SUPPLY",
    "3.3k",
    False,
    "Limits auxiliary PG sink current below1mA; receiving high level still exceeds2V",
)
resistor(
    "R14",
    "VIN_PROTECTED",
    "AGND",
    "47k",
    False,
    "Bus bleed; not a fast discharge or power-isolation guarantee",
)
component(
    "D2",
    "BAS116,215",
    "Package_TO_SOT_SMD:SOT-23",
    [
        pin(1, "ANODE", "passive", "L", "INPUT_OV"),
        pin(2, "NC", "no_connect", "L", None),
        pin(3, "CATHODE", "passive", "R", "V2V5_AUX"),
    ],
    620,
    230,
    NXP + "BAS116.pdf",
    "Low-leakage positive OVP clamp; allocate1.3V forward drop over intended operating temperatures; verify physically.",
)
component(
    "D3",
    "SS16-E3/61T",
    "Diode_SMD:D_SMA",
    [pin(1, "CATHODE", "passive", "L", "VIN_PROTECTED"), pin(2, "ANODE", "passive", "R", "AGND")],
    source="https://www.vishay.com/docs/88746/ss12.pdf",
    note="Output negative-spike provision per eFuse recommendations; actual undershoot/current/pulse bounds unverified.",
)
capacitor(
    "C1",
    "VIN_SYS",
    "AGND",
    "2.2uF 100V X7R",
    True,
    note="Effective>=0.1uF; reverse-polarity capable nonpolar MLCC",
)
capacitor("C2", "VIN_IC", "AGND", "2.2uF 100V X7R", True, note="Effective>=0.1uF before internal pass FET")
capacitor(
    "C3",
    "VIN_PROTECTED",
    "AGND",
    "220uF 35V electrolytic 20% (EEUFR1V221)",
    fp="Capacitor_THT:CP_Radial_D8.0mm_P3.50mm",
    note="Positive lead atVIN_PROTECTED. Manufacturer body8x11.5mm/pitch3.5mm;950mArms and56mOhm impedance at100kHz. Actual waveform/ripple/lifetime and placement unverified.",
)
capacitor(
    "C4", "VIN_PROTECTED", "AGND", "1uF 50V X7R", True, note="Effective>=0.1uF at protected input boundary"
)
capacitor(
    "C5",
    "INPUT_SLEW",
    "AGND",
    "100nF 16V X7R",
    note="Effective80..120nF allocation; output ramp and full-temperature behavior require measurement",
)
capacitor("C6", "V2V5_AUX", "AGND", "10uF 16V X7R", True, note="Effective>=2.2uF for LDO stability")
capacitor("C7", "V2V5_AUX", "AGND", "100nF 16V X7R")

# Sense after the reverse blocker. Fail-safe comparator inputs tolerate5.5V
# independently of VCC; no positive input clamp may backfeed the aux supply.
component(
    "U3",
    "TLV7011DBVR",
    "Package_TO_SOT_SMD:SOT-23-5",
    [
        pin(1, "OUT", "output", "R", "FAST_OV_OUT"),
        pin(2, "VEE", "power_in", "L", "AGND"),
        pin(3, "IN+", "input", "L", "FAST_OV_SENSE"),
        pin(4, "IN-", "input", "L", "FAST_OV_REF"),
        pin(5, "VCC", "power_in", "L", "V2V5_AUX"),
    ],
    source="https://www.ti.com/document-viewer/TLV7011/datasheet",
    note="Independent fast OV comparator; push-pull high turns Q3 ON to pull SHDN low. Delay/drive/bias budget includes allocations, not full-temperature manufacturer guarantees.",
)
component(
    "Q3",
    "DMN2056U-7",
    "Package_TO_SOT_SMD:SOT-23",
    [
        pin(1, "GATE", "input", "L", "FAST_OV_GATE"),
        pin(2, "SOURCE", "passive", "L", "AGND"),
        pin(3, "DRAIN", "passive", "R", "POWER_RUN"),
    ],
    source="https://www.diodes.com/datasheet/download/DMN2056U.pdf",
    note="Low-voltage gate NFET.85mOhm max at1.5V/25C; allocate250mOhm hot. Sinks current-limited switch signal, not load current. Place locally at SHDN.",
)
resistor("R15", "VIN_IC", "FAST_OV_SENSE", "30.9k")
resistor("R16", "FAST_OV_SENSE", "AGND", "3.09k")
resistor(
    "R17",
    "FAST_OV_OUT",
    "FAST_OV_SENSE",
    "309k",
    note="Positive feedback adds hysteresis; no sense capacitor that could hide a fast input fault",
)
resistor("R18", "V2V5_AUX", "FAST_OV_REF", "10k")
resistor("R19", "FAST_OV_REF", "AGND", "10k")
resistor(
    "R20",
    "FAST_OV_GATE",
    "AGND",
    "100k",
    False,
    "Gate pulldown when comparator is unpowered; internal eFuse OVP remains independent",
)
resistor(
    "R21",
    "FAST_OV_OUT",
    "FAST_OV_GATE",
    "100",
    False,
    "Local gate damping; place Q3 by SHDN, not across the panel harness",
)
capacitor("C8", "V2V5_AUX", "AGND", "100nF 16V X7R")
capacitor(
    "C9",
    "FAST_OV_REF",
    "AGND",
    "1nF 16V C0G 5%",
    note="Reference bypass only; roughly5us RC. Comparator startup/reference settling requires qualification.",
)
capacitor(
    "C10",
    "AUX_START_DELAY",
    "AGND",
    "10nF 16V C0G 5%",
    note="Auxiliary PG delays eFuse startup until comparator/reference settle. Delay threshold and comparator startup maxima require qualification; no MCU dependency.",
)
for ref, nets, y in [
    ("J2", ["VIN_PROTECTED", "AGND"], 70),
    ("J3", ["AGND", "POWER_READY"], 170),
    ("J4", ["SWITCH_SUPPLY", "POWER_RUN", "AGND"], 300),
    ("J5", ["V2V5_AUX", "AGND"], 400),
    ("J6", ["V2V5_AUX", "AGND", "POWER_RUN"], 450),
]:
    component(
        ref,
        "Header" + str(len(nets)),
        "Connector_PinHeader_2.54mm:PinHeader_1x" + f"{len(nets):02d}" + "_P2.54mm_Vertical",
        [pin(i + 1, n, "passive", "L", n) for i, n in enumerate(nets)],
        900,
        y,
        note="Engineering header only; use keyed rated production connector. J2 carries full input current; J3 is required for startup.",
    )
# The actual panel switch is a separate low-current component/harness boundary.
component(
    "S1",
    "JS102011SAQN",
    "Button_Switch_SMD:SW_SPDT_CK_JS102011SAQN",
    [
        pin(1, "ON", "passive", "L", "SWITCH_SUPPLY"),
        pin(2, "COMMON", "passive", "R", "POWER_RUN"),
        pin(3, "OFF", "passive", "L", "AGND"),
    ],
    620,
    400,
    "https://www.ckswitches.com/media/1422/js.pdf",
    "Low-current shutdown/reset switch. Physical placement/actuator and orientation must be verified; it does not carry load current.",
)

positions = {
    "J1": (60, 140),
    "U2": (60, 70),
    "U1": (220, 110),
    "Q1": (390, 65),
    "Q2": (390, 105),
    "S1": (390, 155),
    "J2": (540, 60),
    "J3": (540, 100),
    "J4": (540, 140),
    "J5": (540, 180),
    "J6": (540, 215),
    "U3": (60, 185),
    "Q3": (390, 195),
}
for c in COMPONENTS:
    if c["ref"] in positions:
        c["x"], c["y"] = positions[c["ref"]]
passives = [c for c in COMPONENTS if c["ref"].startswith(("R", "C", "D", "F"))]
for i, c in enumerate(passives):
    c["x"] = 48 + (i % 7) * 75
    c["y"] = 240 + (i // 7) * 40
for c in COMPONENTS:
    c["x"] = round(round(c["x"] / 1.27) * 1.27, 4)
    c["y"] = round(round(c["y"] / 1.27) * 1.27, 4)
NOTES = [
    (
        20.32,
        20.32,
        "E16: E15 DC inlet/eFuse + independent TLV7011 fast OV shutdown. Auxiliary supply powers comparison and PGOOD guard; no MCU or main-rail dependency.",
    ),
    (
        20.32,
        30.48,
        "Conditional schematic prototype. No IEC surge claim, PCB/enclosure placement or physical startup/fault validation. Final analog/digital rail OV disconnects remain open.",
    ),
    (
        20.32,
        425.45,
        "FAST_OV_OUT high -> Q3 grounds POWER_RUN/SHDN. R17 provides hysteresis. Local wiring, comparator delay/drive and transferred fault charge require qualification.",
    ),
    (
        20.32,
        434.34,
        "Auxiliary PG/C10 holds SHDN low during startup. S1 missing -> OFF via47k. AUX starts through external FET body diode before the internal pass FET.",
    ),
    (
        20.32,
        443.23,
        "TVS standoff33V permits24V DC misplug. Fuse/TVS coordination, transient clamp voltage and final rail disconnects remain open; no physical protection approval.",
    ),
]
