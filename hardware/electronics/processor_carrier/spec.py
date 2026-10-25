"""E19 external-profile processor carrier and ten pot interfaces."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED = "https://daisy.nyc3.cdn.digitaloceanspaces.com/products/seed3/Daisy_Seed3_datasheet.pdf"
COMPONENTS = []
KNOBS = [
    "input",
    "output",
    "low",
    "mid",
    "high",
    "scene_depth",
    "x_level",
    "x_pitch",
    "scene_time",
    "scene_resonance",
]


def pin(n, name, kind, net, side="L"):
    return dict(number=str(n), name=name, kind=kind, net=net, side=side)


def part(ref, value, fp, pins, x, y, note="", source=""):
    COMPONENTS.append(
        dict(
            ref=ref,
            part=value,
            footprint=fp,
            pins=pins,
            x=round(round(x / 1.27) * 1.27, 4),
            y=round(round(y / 1.27) * 1.27, 4),
            note=note,
            source=source,
        )
    )


GPIO = [
    "CODEC_RUN",
    "SDMMC_D3_SRC",
    "SDMMC_D2_SRC",
    "SDMMC_D1_SRC",
    "SDMMC_D0_SRC",
    "SDMMC_CMD_SRC",
    "SDMMC_CLK_SRC",
    "LED_XLAT_SRC",
    "LED_SCK_SRC",
    "GAIN_REQ",
    "LED_MOSI_SRC",
    "SCL",
    "SDA",
    "HEARTBEAT",
    "LED_BLANK_SRC",
]
PINS = [
    pin(i + 1, "D" + str(i), "bidirectional" if i in (1, 2, 3, 4, 5, 11, 12) else "output", net)
    for i, net in enumerate(GPIO)
]
PINS += [
    pin(i, name, kind, net, "L")
    for i, name, kind, net in [
        (16, "AUDIO_IN_L", "input", None),
        (17, "AUDIO_IN_R", "input", None),
        (18, "AUDIO_OUT_L", "output", None),
        (19, "AUDIO_OUT_R", "output", None),
        (20, "AGND", "power_in", "AGND"),
    ]
]
PINS += [pin(21, "3V3_ANALOG", "power_out", "V3V3_ANALOG", "R")]
PINS += [pin(22 + i, "D" + str(15 + i), "input", f"POT_ADC_{i:02d}", "R") for i in range(10)]
PINS += [
    pin(i, name, kind, net, "R")
    for i, name, kind, net in [
        (32, "D25_ADC_DATA", "input", "ADC_DATA"),
        (33, "D26_DAC_DATA", "output", "DAC_DATA_SRC"),
        (34, "D27_WS", "input", "WS"),
        (35, "D28_BCLK", "input", "BCLK"),
        (36, "D29_PERMIT", "output", "MCU_PERMIT"),
        (37, "D30_ARMED", "input", "ARMED"),
        (38, "3V3_DIGITAL", "power_out", "V3V3_IO"),
        (39, "VIN", "power_in", "SEED_VIN"),
        (40, "DGND", "power_in", "AGND"),
    ]
]
part(
    "U1",
    "DaisySeed3",
    "RMX_Carrier:Seed3_Socket40",
    PINS,
    95,
    110,
    "External firmware profile only. Carrier assembly includes Seed3 and2xSSW-120-02-G-S sockets; clip socket solder tails<=3mm including solder.",
    SEED,
)


def header(ref, nets, x, y, note=""):
    part(
        ref,
        "Header" + str(len(nets)),
        f"Connector_PinHeader_2.54mm:PinHeader_1x{len(nets):02d}_P2.54mm_Vertical",
        [pin(i + 1, str(i + 1), "passive", net) for i, net in enumerate(nets)],
        x,
        y,
        note,
    )


HEADERS = [
    ("J1", ["5V_DIG", "AGND"], "Protected digital supply from E17 J4, same pin order; no raw12V input."),
    (
        "J2",
        ["AGND", "V3V3_IO", "SCL", "SDA", "CODEC_RUN"],
        "E18 J5; CODEC_RUN alias CONTROL_RESET_N; external profile only.",
    ),
    (
        "J3",
        ["AGND", "HEARTBEAT", "MCU_PERMIT", "GAIN_REQ", "ARMED", "BYPASS_SENSE"],
        "E11 J2 six-pin order; bypass sense passes to E18 rear header.",
    ),
    (
        "J4",
        ["AGND", "MODE_SEND_RETURN", "BYPASS_SENSE", "ANALOG_OK", "INPUT_READY"],
        "E18 J4; BYPASS_SENSE alias MANUAL_BYPASS.",
    ),
    ("J5", ["AGND", "BCLK", "WS", "ADC_DATA", "DAC_DATA"], "E09 J3; DAC_DATA source damping at carrier."),
    (
        "J6",
        ["AGND", "V3V3_IO", "SCL", "SDA", "CODEC_RUN", "ANALOG_OK"],
        "Split harness to E09 J4 IO power/J5 bus/status. Do not join independent3.3V outputs.",
    ),
    ("J7", ["AGND", "INPUT_READY"], "E11 J6 status."),
    ("J8", ["AGND", "MODE_SEND_RETURN"], "Rear maintained CONNECTION contact: closed=send/return."),
    (
        "J9",
        ["AGND", "V3V3_IO", "SCL", "SDA"],
        "Trill Craft bus; include module pull-ups in whole-bus budget.",
    ),
    ("J10", ["AGND", "V3V3_IO", "SCL", "SDA"], "AS5600 board bus; sensor board incomplete."),
    (
        "J11",
        ["AGND", "5V_DIG", "V3V3_IO", "LED_MOSI", "LED_SCK", "LED_XLAT", "LED_BLANK", "AGND"],
        "TLC5947 board interface; receiving BLANK pull-up still required on future LED board.",
    ),
    (
        "J12",
        ["AGND", "V3V3_IO", "SDMMC_D0", "SDMMC_D1", "SDMMC_D2", "SDMMC_D3", "SDMMC_CMD", "SDMMC_CLK"],
        "Reserved SDMMC interface. Card-power budget, socket/detect, filesystem and physical SI unfinished.",
    ),
]
for index, (ref, nets, note) in enumerate(HEADERS):
    header(ref, nets, 235 + 135 * (index % 6), 65 + 100 * (index // 6), note)


def passive(ref, value, a, b, x, y, fp=None, note=""):
    kind = "Resistor" if ref.startswith("R") else "Capacitor"
    part(
        ref,
        value,
        fp or f"{kind}_SMD:{ref[0]}_0805_2012Metric",
        [pin(1, "~", "passive", a), pin(2, "~", "passive", b, "R")],
        x,
        y,
        note,
    )


PULLS = [
    ("R1", "0.47R 1% 1W", "5V_DIG", "SEED_VIN"),
    ("R2", "10k 1%", "LED_BLANK", "V3V3_IO"),
    ("R3", "100k 1%", "MCU_PERMIT", "AGND"),
    ("R4", "100k 1%", "GAIN_REQ", "AGND"),
    ("R5", "100k 1%", "ARMED", "AGND"),
    ("R6", "100k 1%", "CODEC_RUN", "AGND"),
]
SERIES = [
    "LED_XLAT",
    "LED_SCK",
    "LED_MOSI",
    "LED_BLANK",
    "DAC_DATA",
    "SDMMC_D0",
    "SDMMC_D1",
    "SDMMC_D2",
    "SDMMC_D3",
    "SDMMC_CMD",
    "SDMMC_CLK",
]
for i, (ref, value, a, b) in enumerate(PULLS):
    passive(
        ref,
        value,
        a,
        b,
        45 + 95 * i,
        530,
        "Resistor_SMD:R_2512_6332Metric" if ref == "R1" else None,
        "Source resistor budget uses0.5A; physical load, thermal and startup qualification open."
        if ref == "R1"
        else "",
    )
for i, net in enumerate(SERIES):
    passive(
        f"R{10 + i}",
        "33R 1%",
        net + "_SRC",
        net,
        45 + 95 * (i % 10),
        565 + 35 * (i // 10),
        note="Source damping; physical edge/SI qualification unfinished.",
    )
CAPS = [
    ("22uF 25V X7R", "SEED_VIN"),
    ("100nF 16V X7R", "SEED_VIN"),
    ("1uF 16V X7R", "V3V3_ANALOG"),
    ("100nF 16V X7R", "V3V3_ANALOG"),
    ("4.7uF 16V X7R", "V3V3_IO"),
    ("100nF 16V X7R", "V3V3_IO"),
]
for i, (value, rail) in enumerate(CAPS):
    passive(
        f"C{i + 1}",
        value,
        rail,
        "AGND",
        45 + 95 * (i + 1),
        600,
        "Capacitor_SMD:C_1210_3225Metric" if i == 0 else None,
    )
for i, name in enumerate(KNOBS):
    x, y = 245 + 160 * (i % 5), 300 + 100 * (i // 5)
    header(
        f"J{20 + i}",
        ["AGND", f"POT_RAW_{i:02d}", "V3V3_ANALOG"],
        x,
        y,
        f"{name}: 10k linear pot; excitation is module analog3.3V output.",
    )
    passive(f"R{31 + i}", "1k 1%", f"POT_RAW_{i:02d}", f"POT_ADC_{i:02d}", x, y + 32)
    passive(f"C{11 + i}", "100nF 16V X7R", f"POT_ADC_{i:02d}", "AGND", x, y + 62)
    passive(
        f"R{41 + i}",
        "1M 1%",
        f"POT_ADC_{i:02d}",
        "AGND",
        x + 70,
        y + 62,
        note="Open-wiper bleed; does not provide wire-fault detection.",
    )
NOTES = [
    (
        20,
        18,
        "E19 - external-profile Seed3 processor carrier.40 module pins,10 analog pots,control-hub/codec/relay/LED/sensor/SD interfaces.",
    ),
    (
        20,
        28,
        "3.3V outputs are separate: analog pin21 excites pots; digital pin38 powers shared logic. AGND and DGND join on carrier.",
    ),
    (
        20,
        638,
        "Routed150x65mm carrier: front-slot Seed and2mm E18 daughterboard shift implemented in PCB/A05 CAD; physical assembly unverified.",
    ),
    (
        20,
        648,
        "No whole-bus/3.3V load, USB partial-power/backfeed, ADC acquisition/accuracy, SDMMC SI or physical fit approval. No fabrication release.",
    ),
]
