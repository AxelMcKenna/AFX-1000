#!/usr/bin/env python3
"""F04 digital-control wiring from the panel layout; no PCB/fit claim."""

import argparse
import csv
import hashlib
import io
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = "https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP23017-Data-Sheet-DS20001952.pdf"


def outputs():
    panel = runpy.run_path(str(ROOT / "hardware/cad/generate.py"))
    controls = panel["CONTROLS"]
    buttons = [c for c in controls if c["kind"] in ("button", "sector")]
    header = (ROOT / "hardware/runtime/include/rmx/controls/HardwareControls.h").read_text()
    ids = re.findall(r'"([a-z0-9_]+)"', re.search(r"buttonIds\s*\{(.*?)\};", header, re.S).group(1))
    assert ids == [c["id"] for c in buttons] and len(ids) == 29
    selectors = {c["id"]: c for c in controls if c["kind"] == "switch"}
    front = []
    for index, control in enumerate(
        buttons + [selectors["settings"], selectors["release_type"], selectors["release_type"]]
    ):
        if index < 28:
            address = 0x20 + index // 14
            offset = index % 14
            port, bit = ("A", offset) if offset < 7 else ("B", offset - 7)
        else:
            address, port, bit = 0x22, "B", index - 28
        name = (
            control["id"] if index < 30 else ("release_back_spin" if index == 30 else "release_vinyl_brake")
        )
        x, y = (
            panel["point"](control, 43.5, (control["a"] + control["b"]) / 2)
            if control["kind"] == "sector"
            else (control["x"], control["y"])
        )
        front.append(
            dict(
                kind="front",
                logical_index=index,
                id=name,
                address=address,
                gpio=f"GP{port}{bit}",
                soic_pin=21 + bit if port == "A" else 1 + bit,
                layout_x_mm=round(x, 4),
                layout_y_mm=round(y, 4),
                active="low",
                profiles=["onboard", "external"],
                receiving_pulldown_ohm=None,
            )
        )
    rear = [
        dict(
            kind="rear",
            logical_index=None,
            id=name,
            address=0x22,
            gpio=f"GPA{bit}",
            soic_pin=21 + bit,
            layout_x_mm=None,
            layout_y_mm=None,
            active=active,
            profiles=["external"],
            receiving_pulldown_ohm=pulldown,
        )
        for bit, name, active, pulldown in [
            (0, "connection_send_return", "low", None),
            (1, "manual_bypass", "low", None),
            (2, "ANALOG_OK", "high", 47000),
            (3, "INPUT_READY", "high", 270000),
        ]
    ]
    assert len({(p["address"], p["soic_pin"]) for p in front + rear}) == 36
    assert not any(p["gpio"].endswith("7") for p in front + rear)
    sources = [
        "hardware/cad/generate.py",
        "hardware/runtime/include/rmx/controls/HardwareControls.h",
        "hardware/firmware/control_map.py",
    ]
    data = dict(
        revision="F04",
        scope="Digital input wiring; not a schematic, PCB, or fit approval",
        component="MCP23017-E/SO",
        quantity_both_profiles=3,
        primary_source=SOURCE,
        datasheet_revision="DS20001952D, 2022",
        front_inputs=front,
        external_rear_inputs=rear,
        output_only_pins_unused=["GPA7 / SOIC28 pin28", "GPB7 / SOIC28 pin8"],
        fixed_soic_pins={
            "9": "V3V3_IO",
            "10": "GND",
            "11": "NC",
            "12": "SCL",
            "13": "SDA",
            "14": "NC",
            "18": "RESET_N",
            "19": "INTB unused",
            "20": "INTA unused",
        },
        address_straps={
            "0x20": {"A2": 0, "A1": 0, "A0": 0},
            "0x21": {"A2": 0, "A1": 0, "A0": 1},
            "0x22": {"A2": 0, "A1": 1, "A0": 0},
        },
        reset_seed_pin={"onboard": "D27", "external": "D0 shared CODEC_RUN"},
        input_masks={
            "0x20": {"A": 127, "B": 127},
            "0x21": {"A": 127, "B": 127},
            "0x22_external": {"A": 15, "B": 15},
            "0x22_onboard": {"A": 0, "B": 15},
        },
        notes=[
            "All front controls close to ground; internal pull-ups enabled after verified configuration.",
            "Echo selects neither release endpoint; both asserted is an invalid state.",
            "ANALOG_OK and INPUT_READY have no internal pull-up; physical receiving pull-downs required.",
            "GPA7/GPB7 and other unused pins are unconnected outputs held low after initialization.",
            "3.3V shared MCU rail; no 5V logic connection. Exact control-board placement and routing unfinished.",
            "Ten pot inputs, LED outputs, touch electrodes and angle sensor are separate interfaces.",
        ],
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
    )
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    columns = [
        "kind",
        "logical_index",
        "id",
        "address",
        "gpio",
        "soic_pin",
        "layout_x_mm",
        "layout_y_mm",
        "active",
        "profiles",
        "receiving_pulldown_ohm",
    ]
    writer.writerow(columns)
    for pin in front + rear:
        row = dict(pin, address=f"0x{pin['address']:02x}", profiles="/".join(pin["profiles"]))
        writer.writerow([row[key] for key in columns])
    return {"control-inputs.json": json.dumps(data, indent=2) + "\n", "control-inputs.csv": stream.getvalue()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, content in outputs().items():
        path = HERE / name
        if args.check:
            assert path.read_bytes() == content.encode(), f"Stale control map: {name}"
        else:
            path.write_bytes(content.encode())
    print("F04: 32 front + 4 rear inputs mapped to valid MCP23017 pins; no GPA7/GPB7 inputs.")


if __name__ == "__main__":
    main()
