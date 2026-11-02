"""Replay DC01 against the three original exported circuits and critical pins."""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.fabrication.audit_candidate import sha

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "hardware/fabrication/staging/digital-core-integration-01"

# Kept independent of the constructor's map and expected-circuit manifest.
CONTRACT = (
    ("PROCESSOR", "processor-carrier-native-01", "processor_carrier", 1000, {"J2", "J11"}),
    ("CONTROLS", "control-inputs-native-01", "control_inputs", 2000, {"J4", "J5"}),
    ("LED", "led-driver-native-01", "led_driver", 3000, {"J1"}),
)
SHARED = {"AGND", "V3V3_IO", "5V_DIG", "SCL", "SDA", "CODEC_RUN", "BYPASS_SENSE",
          "MODE_SEND_RETURN", "ANALOG_OK", "INPUT_READY", "LED_MOSI", "LED_SCK", "LED_XLAT", "LED_BLANK"}


def expected_circuit():
    result = {}
    for domain, folder, name, offset, removed in CONTRACT:
        parts, pins = netlist(OUT.parent / folder / "netlist.xml")
        for ref in parts.keys() - removed:
            prefix, number = re.fullmatch(r"([A-Z]+)([0-9]+)", ref).groups()
            new = prefix + str(int(number) + offset)
            mapped = {}
            for pin, net in pins[ref].items():
                if domain == "CONTROLS":
                    net = {"CONTROL_RESET_N": "CODEC_RUN", "MANUAL_BYPASS": "BYPASS_SENSE"}.get(net, net)
                mapped[pin] = None if net.startswith("unconnected-") else net if net in SHARED else domain + "/" + net
            result[new] = dict(source_domain=domain, source_ref=ref, value=parts[ref].findtext("value"),
                               footprint=parts[ref].findtext("footprint") or "", pins=mapped)
    return result


def verify_export(parts, pins):
    expected = expected_circuit()
    assert len(parts) == 138 and set(parts) == set(expected), "Wrong retained component set"
    by_net = defaultdict(set)
    for ref, spec in expected.items():
        assert parts[ref].findtext("value") == spec["value"], ("Component value changed", ref)
        assert parts[ref].findtext("footprint") == spec["footprint"], ("Land changed", ref)
        assert set(pins[ref]) == set(spec["pins"]), ("Terminal set changed", ref)
        for pin, net in spec["pins"].items():
            actual = pins[ref][pin]
            assert (actual.startswith("unconnected-") if net is None else actual == net), ("Pin net changed", ref, pin, net, actual)
            by_net[actual].add((ref, pin))
    shared = {net for net, nodes in by_net.items() if len({expected[r]["source_domain"] for r, _ in nodes}) > 1}
    assert shared == SHARED, ("Unexpected cross-domain net", shared ^ SHARED)
    for net, nodes in {
        "CODEC_RUN": {("U1001", "1"), ("U2001", "18"), ("U2002", "18"), ("U2003", "18"), ("J1006", "5")},
        "SCL": {("U1001", "12"), ("U2001", "12"), ("U2002", "12"), ("U2003", "12")},
        "SDA": {("U1001", "13"), ("U2001", "13"), ("U2002", "13"), ("U2003", "13")},
        "BYPASS_SENSE": {("J1003", "6"), ("J1004", "3"), ("U2003", "22")},
        "LED_MOSI": {("U3005", "3")}, "LED_SCK": {("U3005", "4")},
        "LED_XLAT": {("U3005", "5")}, "LED_BLANK": {("U3005", "6")},
    }.items():
        assert nodes <= by_net[net], ("Missing critical interface", net)
    assert pins["U1001"]["11"] == "PROCESSOR/LED_MOSI_SRC"
    assert pins["U1001"]["9"] == "PROCESSOR/LED_SCK_SRC"
    assert pins["U3005"]["21"] == "LED/DATA_5V_SRC"
    assert pins["U3001"]["4"] == "LED/DATA_5V"
    assert all(parts[r].findtext("footprint") for r in parts)
    return expected, sorted(shared)


def check():
    construction = json.loads((OUT / "construction.json").read_text())
    native = json.loads((OUT / "native-review.json").read_text())
    for record in (construction, native):
        assert all(sha(REPO / p) == h for p, h in record["source_sha256"].items()), "Source changed"
    for field in ("raw_export_sha256", "captured_library_sha256"):
        assert all(sha(OUT / p) == h for p, h in native[field].items())
    erc = json.loads((OUT / "erc.json").read_text())
    assert len(erc["sheets"]) == 4 and erc["ignored_checks"] == []
    assert not any(s["violations"] for s in erc["sheets"]) and native["ERC_findings"] == 0
    assert all(c["returncode"] == 0 for c in native["complete_native_commands"])
    parts, pins = netlist(OUT / "netlist.xml")
    expected, shared = verify_export(parts, pins)
    assert expected == json.loads((OUT / "expected-circuit.json").read_text())
    assert not (OUT / "digital_core.kicad_pcb").exists()
    paths = [Path(__file__), OUT / "construction.json", OUT / "native-review.json", OUT / "erc.json", OUT / "netlist.xml"]
    return dict(revision="DC01", source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
                electrical_parts=len(parts), exported_physical_terminals=sum(len(v) for v in pins.values()),
                independently_replayed_original_values_lands_and_pin_nets=True,
                removed_internal_headers=5, declared_cross_sheet_nets=shared,
                control_reset_profile="E18 external codec / Seed D0 CODEC_RUN",
                native_ERC_findings=0, all_native_ERC_categories_enabled=True,
                native_PCB_DRC_performed=False, PCB_layout_present=False,
                power_return_thermal_and_enclosure_qualified=False, fabrication_released=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check()
    path = OUT / "integration-handoff.json"
    if args.check:
        assert result == json.loads(path.read_text())
    else:
        with path.open("x") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    print(f"DC01: {result['electrical_parts']} parts/{result['exported_physical_terminals']} terminals; source circuits preserved; ERC 0")
