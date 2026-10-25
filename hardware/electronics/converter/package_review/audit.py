"""Check pin/register facts without manufacturing a missing codec footprint."""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
PARENT = ROOT.parent
OUT = ROOT / "generated"
NAME_ALIASES = {
    "MODE_I2C": "MODE",
    "DATA1_WS": "DATA1",
    "DATA2_ADC": "DATA2",
    "DATA4_DAC": "DATA4",
    "GPIO3_CLK_VALID": "GPIO3",
    "GPIO4_RAMP_DONE": "GPIO4",
    "PAD_DGND": "PACKAGE_PAD",
}
CRITICAL_VALUES = {
    0: (1, 0xBF, 0x2F),
    1: (1, 0x17, 2),
    2: (1, 0xFF, 0x11),
    5: (1, 0x7F, 3),
    6: (1, 0x10, 0),
    7: (1, 0xFF, 7),
    8: (1, 0x0F, 0x0D),
    9: (1, 0xBF, 0x25),
    10: (1, 0x5F, 1),
    11: (1, 0x7F, 0),
    12: (2, 0x1F1F, 0x0100),
    14: (2, 0x1F1F, 0x0100),
    62: (1, 0xFF, 0x62),
    68: (2, 0x01FF, 0),
    77: (1, 0x7F, 4),
    83: (2, 0x3C00, 0x3000),
    110: (2, 0xFFFF, 0x0202),
    116: (1, 0x33, 0x33),
    117: (1, 0x6F, 3),
    136: (1, 0x7C, 0),
    137: (1, 0x0F, 0),
    147: (1, 0xEF, 0),
    148: (1, 0x33, 0x33),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def allowed_mask(fields, reg, count):
    first = fields[str(reg)]
    width = first["last_register"] - reg + 1
    if width == count:
        return first["writable_mask"]
    assert width == 1 and count == 2, "Register width requires explicit source review"
    second = fields[str(reg + 1)]
    assert second["last_register"] == reg + 1
    return first["writable_mask"] | (second["writable_mask"] << 8)


def audit(header=None, components=None, contract=None):
    contract = json.loads((ROOT / "source-contract.json").read_text()) if contract is None else contract
    components = json.loads((PARENT / "components.json").read_text()) if components is None else components
    codec = next(p for p in components if p["ref"] == "U1")
    assert codec["part"] == "ES9292QPRO"
    assert codec["footprint"] == "", "Do not assign a generic QFN in place of manufacturer package review"
    actual = {p["number"]: NAME_ALIASES.get(p["name"], p["name"]) for p in codec["pins"]}
    assert actual == contract["pin_names"], "Codec pin names/numbers differ from ESS Table1"
    pins = {p["number"]: p.get("net") for p in codec["pins"]}
    for pin, net in {
        "1": "CHIP_EN",
        "2": "AGND",
        "11": None,
        "12": "A4V5",
        "25": "A3V3",
        "26": "MCLK",
        "27": "AGND",
        "28": "DVDD_CORE",
        "29": "AGND",
        "30": "V3V3_IO",
        "44": "SDA",
        "45": "SCL",
        "46": "AGND",
        "47": "AGND",
        "48": "AGND",
        "49": "AGND",
    }.items():
        assert pins[pin] == net, (pin, net)
    text = (REPO / "hardware/firmware/Es9292.h").read_text() if header is None else header
    table = text.split("inline static constexpr auto settings", 1)[1].split("explicit Es9292", 1)[0]
    settings = [
        tuple(int(v, 0) for v in row)
        for row in re.findall(r"\{(\d+),\s*(\d+),\s*(0x[0-9a-f]+|\d+),\s*(0x[0-9a-f]+|\d+)\}", table)
    ]
    assert len(settings) == 45 and len({r[0] for r in settings}) == 45, "Missing/duplicated codec settings"
    checked = []
    for reg, count, mask, value in settings:
        allowed = allowed_mask(contract["register_fields"], reg, count)
        assert mask & ~allowed == 0 and value & ~mask == 0, (
            "Reserved/undefined bits",
            reg,
            mask,
            allowed,
            value,
        )
        if reg in CRITICAL_VALUES:
            assert (count, mask, value) == CRITICAL_VALUES[reg], (
                "Changed clock/format/qualifier setting",
                reg,
            )
        checked.append(
            dict(register=reg, count=count, mask=mask, value=value, published_writable_mask=allowed)
        )
    assert re.search(r"address\s*=\s*0x18", text)
    assert "codecRead(225, id)" in text and "id != 0xaf" in text
    assert "!apply({116, 1, 0x33, 0x30})" in text and "!apply({68, 2, 0x01ff, 0x000c})" in text
    assert "ramp == 0x30" in text, (
        "GPIO ramp-done alone also goes high when ramped down; require live ramp-up"
    )
    assert "(clock & 0xe0) == 0x80" in text
    package = contract["package"]
    assert package["body_nominal_mm"] == [7, 7] and package["exposed_pad_pin"] == 49
    assert (
        not package["approved_for_layout"]
        and package["perimeter_pitch_mm"] is None
        and package["exposed_pad_width_mm"] is None
    )
    adc_parts = json.loads((REPO / "hardware/electronics/adc_driver/components.json").read_text())
    adc_header = next(p for p in adc_parts if p["ref"] == "J2")
    adc_header_nets = {p["number"]: p.get("net") for p in adc_header["pins"]}
    assert adc_header_nets == {
        "1": "ADC_LP",
        "2": "ADC_LN",
        "3": "AGND",
        "4": "ADC_RP",
        "5": "ADC_RN",
        "6": "REF_ADC1",
        "7": "REF_ADC2",
    }
    return dict(
        pin_table_entries_checked=len(actual),
        firmware_setting_entries_checked=len(checked),
        register_mask_checks=checked,
        critical_clock_format_and_qualifier_values_checked=len(CRITICAL_VALUES),
        gpio_63_64_are_independent_byte_registers=True,
        readback_id_register=225,
        readback_id=175,
        i2c_seven_bit_address=24,
        package_release_blocked=True,
        missing_manufacturer_data=[
            "Dimensioned ES9292QPRO outline with revision and tolerances: pin pitch/width/length, body thickness/standoff and exposed-pad dimensions",
            "Recommended land, mask/paste and thermal-via geometry or manufacturer assembly approval for an engineered land pattern",
        ],
        firmware_register_policy_matches_reviewed_public_document=True,
        actual_codec_sai_interoperability_verified=False,
        physical_clock_edge_and_mclk_ratio_verified=False,
        footprint_assigned=False,
        adc_driver_header_pin_contract=adc_header_nets,
        separate_force_and_sense_conductors_to_converter=False,
        header_sensing_is_converter_pin_kelvin=False,
        final_system_architecture_requirement="Co-locate ADC driver with converter, or revise force/sense interface; separate-board characterization does not close the converter loop",
        build_ready=False,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    p.add_argument("--pdf", type=Path)
    args = p.parse_args()
    report = audit()
    contract = json.loads((ROOT / "source-contract.json").read_text())
    report["primary_document"] = contract["source"]
    report["package"] = contract["package"]
    report["manufacturer_resource_search"] = contract["manufacturer_resource_search"]
    if args.pdf:
        assert sha(args.pdf) == contract["source"]["sha256"], "Different ESS document; requires review"
    files = [
        ROOT / "source-contract.json",
        ROOT / "audit.py",
        ROOT / "README.md",
        ROOT / "__init__.py",
        PARENT / "components.json",
        PARENT / "converter.kicad_sch",
        PARENT / "dependencies.json",
        REPO / "hardware/electronics/adc_driver/components.json",
        REPO / "hardware/firmware/Es9292.h",
        REPO / "tests/tooling/test_converter_package.py",
    ]
    report["source_sha256"] = {str(q.relative_to(REPO)): sha(q) for q in files if q.exists()}
    out = OUT / "review.json"
    content = json.dumps(report, indent=2) + "\n"
    if args.check:
        assert out.read_text() == content, "Stale converter source review"
    else:
        OUT.mkdir(exist_ok=True)
        out.write_text(content)
    print(
        "ESS:49pins and45settings checked; manufacturer dimensioned package/land data still missing. Layout release:false."
    )


if __name__ == "__main__":
    main()
