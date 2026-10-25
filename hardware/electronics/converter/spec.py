"""E09 converter core, local supplies and hardware qualification prototype.

The codec footprint is deliberately unassigned: the public v0.1 document gives
7x7mm/48QFN but omits the referenced dimensioned land pattern/EP drawing.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPONENTS = []
ESS = "https://www.esstech.com/wp-content/uploads/2026/08/ES9292_DS_v0.1.pdf"
LDO = "https://www.ti.com/lit/ds/symlink/tps7a20.pdf"
SUP = "https://www.ti.com/lit/ds/symlink/tps3890.pdf"
XO = "https://ecsxtal.com/store/pdf/ECS-2520MVLC.pdf"


def pin(number, name, kind, side, net):
    return dict(number=str(number), name=name, kind=kind, side=side, net=net)


def component(ref, part, footprint, pins, x, y, source="", note=""):
    COMPONENTS.append(
        dict(
            ref=ref,
            part=part,
            footprint=footprint,
            pins=pins,
            x=round(round(x / 1.27) * 1.27, 4),
            y=round(round(y / 1.27) * 1.27, 4),
            source=source,
            note=note,
        )
    )


analog = [
    (3, "AGND_DAC1", "power_in", "AGND"),
    (4, "DAC1B", "output", "DAC_LN"),
    (5, "DAC1", "output", "DAC_LP"),
    (6, "VREF_BUF_DAC", "power_out", "REF_DAC_BUF"),
    (7, "DAC2B", "output", "DAC_RN"),
    (8, "DAC2", "output", "DAC_RP"),
    (9, "AGND_DAC2", "power_in", "AGND"),
    (10, "VREF_LN_DAC", "power_out", "REF_DAC_LN"),
    (11, "REXT", "passive", None),
    (12, "AVCCH", "power_in", "A4V5"),
    (13, "VREF_LN_ADC", "power_out", "REF_ADC_LN"),
    (14, "VREF_BUF_ADC1", "power_out", "REF_ADC1"),
    (15, "IN_P1", "input", "ADC_LP"),
    (16, "IN_M1", "input", "ADC_LN"),
    (17, "AGND_ADC1", "power_in", "AGND"),
    (18, "AGND_ADC2", "power_in", "AGND"),
    (19, "IN_M2", "input", "ADC_RN"),
    (20, "IN_P2", "input", "ADC_RP"),
    (21, "VREF_BUF_ADC2", "power_out", "REF_ADC2"),
    (22, "AGND", "power_in", "AGND"),
    (23, "PLL_LN_REF", "power_out", "REF_PLL_LN"),
    (24, "PLL_REG", "power_out", "REF_PLL"),
]
digital = [
    (1, "CHIP_EN", "input", "CHIP_EN"),
    (2, "MODE_I2C", "input", "AGND"),
    (25, "AVCC_3V3", "power_in", "A3V3"),
    (26, "ACLK1", "input", "MCLK"),
    (27, "ACLK2", "input", "AGND"),
    (28, "DVDD", "power_out", "DVDD_CORE"),
    (29, "DGND", "power_in", "AGND"),
    (30, "AVDD", "power_in", "V3V3_IO"),
    (31, "DATA_CLK", "output", "BCLK_SRC"),
    (32, "DATA1_WS", "output", "WS_SRC"),
    (33, "DATA2_ADC", "output", "ADC_DATA_SRC"),
    (34, "GPIO1", "bidirectional", None),
    (35, "DATA4_DAC", "input", "DAC_DATA"),
    (36, "GPIO2", "bidirectional", None),
    (37, "GPIO3_CLK_VALID", "bidirectional", "CLK_VALID"),
    (38, "GPIO4_RAMP_DONE", "bidirectional", "RAMP_DONE"),
    (39, "GPIO5", "bidirectional", None),
    (40, "GPIO6", "bidirectional", None),
    (41, "GPIO7", "bidirectional", None),
    (42, "GPIO8", "bidirectional", None),
    (43, "GPIO9", "bidirectional", None),
    (44, "SDA", "bidirectional", "SDA"),
    (45, "SCL", "input", "SCL"),
    (46, "ADDR1", "input", "AGND"),
    (47, "ADDR0", "input", "AGND"),
    (48, "RT1", "input", "AGND"),
    (49, "PAD_DGND", "power_in", "AGND"),
]
component(
    "U1",
    "ES9292QPRO",
    "",
    [pin(n, name, kind, "L", net) for n, name, kind, net in analog]
    + [pin(n, name, kind, "R", net) for n, name, kind, net in digital],
    100,
    110,
    ESS,
    "Unassigned footprint: manufacturer dimensioned QFN/EP drawing required. REXT NC = internal fixed 3.3V references with AVCCH4.5. I2C 7-bit0x18 (wire0x30/0x31).",
)
for ref, value, rail, x in [("U2", "TPS7A2033PDBVR", "A3V3", 280), ("U3", "TPS7A2045PDBVR", "A4V5", 420)]:
    component(
        ref,
        value,
        "Package_TO_SOT_SMD:SOT-23-5",
        [
            pin(1, "IN", "power_in", "L", "V5_REG"),
            pin(3, "EN", "input", "L", "V5_REG"),
            pin(2, "GND", "power_in", "L", "AGND"),
            pin(5, "OUT", "power_out", "R", rail),
            pin(4, "NC", "passive", "R", None),
        ],
        x,
        65,
        LDO,
        "V5_REG must remain4.90..5.10V; enables tied to input. Output capacitance/bias and reverse-current behavior require qualification.",
    )
component(
    "Y1",
    "ECS-2520MVLC-245.7-BN-TR",
    "Oscillator:Oscillator_SMD_ECS_2520MV-xxx-xx-4Pin_2.5x2.0mm",
    [
        pin(1, "ENABLE", "input", "L", "V3V3_IO"),
        pin(2, "GND", "power_in", "L", "AGND"),
        pin(4, "VDD", "power_in", "L", "V3V3_IO"),
        pin(3, "OUT_24M576", "output", "R", "MCLK_SRC"),
    ],
    560,
    65,
    XO,
    "24.576MHz; 50ppm plus3ppm first-year aging screen. MVLC package land matches MV family drawing. Frequency/order availability and loaded clock timing unverified.",
)
for ref, value, sense, reset, x in [
    ("U4", "TPS389033DSET", "V3V3_IO", "CODEC_PGOOD", 280),
    ("U5", "TPS389033DSET", "A3V3", "CODEC_PGOOD", 420),
    ("U6", "TPS389001DSET", "SENSE_4V5", "CODEC_PGOOD", 560),
    ("U8", "TPS389033DSET", "V3V3_IO", "TIMER_OK", 420),
]:
    component(
        ref,
        value,
        "RMX_Converter:TI_DSE0006A_TPS3890",
        [
            pin(1, "SENSE", "input", "L", sense),
            pin(3, "MR_N", "input", "L", "SETTLE_ENABLE" if ref == "U8" else "V3V3_IO"),
            pin(4, "VDD", "power_in", "L", "V3V3_IO"),
            pin(2, "GND", "power_in", "R", "AGND"),
            pin(5, "CT", "passive", "R", "CT_SETTLE" if ref == "U8" else None),
            pin(6, "RESET_N", "open_collector", "R", reset),
        ],
        x,
        260 if ref == "U8" else 155,
        SUP,
        "U8:2.2uF CT, require effective>=1.5uF and total injected leakage<=100nA; qualification after flags/rails stable."
        if ref == "U8"
        else "CT open. Open-drain PG wire-AND; precision thresholds include hysteresis and sense current. No rail-overvoltage protection.",
    )
component(
    "U7",
    "SN74HCS08DR",
    "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    [
        pin(1, "1A", "input", "L", "CODEC_PGOOD"),
        pin(2, "1B", "input", "L", "PRE_ANALOG_OK"),
        pin(3, "1Y", "output", "R", "SUPPLY_OK"),
        pin(4, "2A", "input", "L", "SUPPLY_OK"),
        pin(5, "2B", "input", "L", "CODEC_RUN"),
        pin(6, "2Y", "output", "R", "CHIP_EN"),
        pin(9, "3A", "input", "L", "CLK_VALID"),
        pin(10, "3B", "input", "L", "RAMP_DONE"),
        pin(8, "3Y", "output", "R", "CODEC_FLAGS"),
        pin(12, "4A", "input", "L", "CHIP_EN"),
        pin(13, "4B", "input", "L", "CODEC_FLAGS"),
        pin(11, "4Y", "output", "R", "SETTLE_ENABLE"),
        pin(14, "VCC", "power_in", "R", "V3V3_IO"),
        pin(7, "GND", "power_in", "R", "AGND"),
    ],
    280,
    260,
    "https://www.ti.com/lit/ds/symlink/sn74hcs08.pdf",
    "Schmitt gates hold CHIP_EN and timer low unless qualified rails/run/codec flags are high.",
)
component(
    "U9",
    "SN74LVC1G08DCKR",
    "Package_TO_SOT_SMD:SOT-353_SC-70-5",
    [
        pin(1, "A", "input", "L", "SETTLE_ENABLE"),
        pin(2, "B", "input", "L", "TIMER_OK"),
        pin(3, "GND", "power_in", "L", "AGND"),
        pin(4, "Y", "output", "R", "ANALOG_OK"),
        pin(5, "VCC", "power_in", "R", "V3V3_IO"),
    ],
    560,
    260,
    "https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf",
    "Direct qualification AND drops ANALOG_OK independently of timer discharge latency.",
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


connector(
    "J1",
    ["DAC_LP", "DAC_LN", "AGND", "DAC_RP", "DAC_RN"],
    100,
    240,
    "Same order as E08 J1. Short converter-board connections; not a long raw-DAC harness.",
)
connector(
    "J2",
    ["ADC_LP", "ADC_LN", "AGND", "ADC_RP", "ADC_RN", "REF_ADC1", "REF_ADC2"],
    100,
    310,
    "ADC/input driver incomplete. Reference outputs are for high-impedance bias inputs only; reference load unqualified.",
)
connector(
    "J3",
    ["AGND", "BCLK", "WS", "ADC_DATA", "DAC_DATA"],
    700,
    155,
    "Codec master; MCU SAI2 dual-slave,32bit I2S,64 BCLK/frame. DAC_DATA needs source series resistor on MCU carrier.",
)
connector(
    "J4",
    ["V5_REG", "AGND", "V3V3_IO"],
    700,
    65,
    "4.90..5.10V regulated input; IO rail must be same3.3V as MCU. Do not join independent3.3V regulator outputs.",
)
connector(
    "J5",
    ["AGND", "SCL", "SDA", "CODEC_RUN", "PRE_ANALOG_OK", "ANALOG_OK", "CODEC_PGOOD", "CHIP_EN"],
    700,
    260,
    "PRE_ANALOG_OK from all +/-19V,+/-12V hardware monitors. ANALOG_OK -> E02 J3.3; firmware must wait for it before permit.",
)

PASSIVES = []


def passive(ref, value, a, b, note="", footprint=None, source=""):
    kind = ref[0]
    PASSIVES.append(
        (
            ref,
            value,
            a,
            b,
            note,
            footprint or f"{'Resistor' if kind == 'R' else 'Capacitor'}_SMD:{kind}_0805_2012Metric",
            source,
        )
    )


for ref, rail in [("R1", "SCL"), ("R2", "SDA")]:
    passive(
        ref,
        "2k 1%",
        rail,
        "V3V3_IO",
        "One fitted pullup pair for the total bus; include module pullups in parallel/load budget.",
    )
for ref, node, value in [("R3", "CODEC_PGOOD", "10k 1%"), ("R4", "TIMER_OK", "10k 1%")]:
    passive(ref, value, node, "V3V3_IO")
for ref, node, value in [
    ("R5", "CODEC_RUN", "47k 1%"),
    ("R6", "PRE_ANALOG_OK", "47k 1%"),
    ("R7", "CLK_VALID", "100k 1%"),
    ("R8", "RAMP_DONE", "100k 1%"),
    ("R9", "CHIP_EN", "100k 1%"),
    ("R10", "ANALOG_OK", "100k 1%"),
]:
    passive(ref, value, node, "AGND", "Missing drive/power fails low.")
passive(
    "R11",
    "27.7k 0.1%",
    "A4V5",
    "SENSE_4V5",
    "TPS389001 divider upper; include reference/hysteresis/input-current bounds.",
)
passive("R12", "10k 0.1%", "SENSE_4V5", "AGND")
for ref, a, b in [
    ("R13", "MCLK_SRC", "MCLK"),
    ("R14", "BCLK_SRC", "BCLK"),
    ("R15", "WS_SRC", "WS"),
    ("R16", "ADC_DATA_SRC", "ADC_DATA"),
]:
    passive(ref, "33 1%", a, b, "Place at the clock/data source; actual edge/load/SI qualification pending.")

reference_caps = [
    ("C1", "1uF 10V X7R 10%", "V3V3_IO"),
    ("C2", "1uF 10V X7R 10%", "DVDD_CORE"),
    ("C3", "100nF 50V C0G 5%", "REF_DAC_BUF"),
    ("C4", "1uF 10V tantalum 10%", "REF_DAC_BUF"),
    ("C5", "1uF 10V X7R 10%", "A3V3"),
    ("C6", "1uF 10V tantalum 10%", "REF_DAC_LN"),
    ("C7", "1uF 10V tantalum 10%", "A4V5"),
    ("C8", "1uF 10V tantalum 10%", "REF_ADC_LN"),
    ("C9", "1uF 10V tantalum 10%", "REF_PLL_LN"),
    ("C10", "100nF 50V C0G 5%", "REF_PLL"),
    ("C11", "1uF 10V tantalum 10%", "REF_PLL"),
    ("C12", "100nF 50V C0G 5%", "REF_ADC1"),
    ("C13", "1uF 10V tantalum 10%", "REF_ADC1"),
    ("C14", "100nF 50V C0G 5%", "REF_ADC2"),
    ("C15", "1uF 10V tantalum 10%", "REF_ADC2"),
]
for ref, value, net in reference_caps:
    passive(
        ref,
        value,
        net,
        "AGND",
        "ESS reference capacitor; tantalum positive pad1, ground pad2. Final MPN/ESR and effective values unselected.",
        footprint="Capacitor_Tantalum_SMD:CP_EIA-3216-18_Kemet-A"
        if "tantalum" in value
        else "Capacitor_SMD:C_1210_3225Metric"
        if "C0G" in value
        else None,
        source=ESS,
    )
for ref, net, value in [
    ("C16", "V5_REG", "2.2uF 25V X7R 10%"),
    ("C17", "A3V3", "10uF 16V X7R 10%"),
    ("C18", "V5_REG", "2.2uF 25V X7R 10%"),
    ("C19", "A4V5", "10uF 16V X7R 10%"),
]:
    passive(
        ref,
        value,
        net,
        "AGND",
        "Input effective>=1uF; output effective>=4.7uF; qualify bias/temperature/ESR.",
        footprint="Capacitor_SMD:C_1210_3225Metric",
    )
for i, ref in enumerate(("U4", "U5", "U6", "U7", "U8", "U9", "Y1"), 20):
    passive("C" + str(i), "100nF 50V X7R", "V3V3_IO", "AGND", f"Local bypass for {ref}")
passive(
    "C27",
    "2.2uF 25V X7R 10%",
    "CT_SETTLE",
    "AGND",
    "Required effective1.5..2.8uF over bias/temperature/aging; total CT injected leakage<=100nA. Exact MPN unselected.",
    footprint="Capacitor_SMD:C_1210_3225Metric",
)
passive("C28", "100nF 50V X7R", "V3V3_IO", "AGND", "Additional local codec AVDD bypass")
passive("C29", "100nF 50V X7R", "A3V3", "AGND", "Additional local AVCC_3V3 bypass")
for i, (ref, value, a, b, note, footprint, source) in enumerate(PASSIVES):
    component(
        ref,
        value,
        footprint,
        [pin(1, "1", "passive", "L", a), pin(2, "2", "passive", "R", b)],
        40 + 80 * (i % 9),
        360 + 35 * (i // 9),
        source,
        note,
    )

NOTES = [
    (
        20,
        15,
        "E09 - standalone converter core / local rails / clock / hardware qualification. Circuit prototype; not routed or physically validated.",
    ),
    (
        20,
        24,
        "ES9292QPRO footprint UNASSIGNED pending manufacturer QFN/EP drawing. IO is shared MCU3.3V; V5_REG4.90..5.10V.",
    ),
    (
        20,
        550,
        "I2C default7bit0x18 (wire0x30/0x31). Codec master24.576MHz -> BCLK3.072MHz, WS48kHz. ADC and external-MCU firmware adapter remain incomplete.",
    ),
]
