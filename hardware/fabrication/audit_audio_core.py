"""Independently check the shared audio-core native export and interface joins."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.fabrication.audit_candidate import sha

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "hardware/fabrication/staging/audio-core-integration-01"
# Physical source pins, independent of the renderer's reference/net-map logic.
ADC_STARS = {
    "ADC_LP": dict(codec_pin="15", force=[("R105", "2"), ("C103", "1"), ("C104", "1")], sense=[("R104", "1"), ("R110", "1")]),
    "ADC_LN": dict(codec_pin="16", force=[("R106", "2"), ("C103", "2"), ("C105", "1")], sense=[("R103", "1"), ("R111", "1")]),
    "ADC_RP": dict(codec_pin="20", force=[("R121", "2"), ("C117", "1"), ("C118", "1")], sense=[("R120", "1"), ("R126", "1")]),
    "ADC_RN": dict(codec_pin="19", force=[("R122", "2"), ("C117", "2"), ("C119", "1")], sense=[("R119", "1"), ("R127", "1")]),
}
DAC_PINS = {
    "DAC_LP": [("U201", "5"), ("U301", "2"), ("R301", "1"), ("C301", "1")],
    "DAC_LN": [("U201", "4"), ("U301", "6"), ("R302", "1"), ("C302", "1")],
    "DAC_RP": [("U201", "8"), ("U302", "2"), ("R313", "1"), ("C306", "1")],
    "DAC_RN": [("U201", "7"), ("U302", "6"), ("R314", "1"), ("C307", "1")],
}
EXPECTED_SHARED = {"AGND", "P12", "N12", "V5_REG", "REF_ADC1", "REF_ADC2", "CHIP_EN", *ADC_STARS, *DAC_PINS}


def joins(pins):
    by_net = defaultdict(set)
    for ref, terminals in pins.items():
        for pin, net in terminals.items():
            by_net[net].add((ref, pin))
    for net, star in ADC_STARS.items():
        required = {("U201", star["codec_pin"]), *star["force"], *star["sense"]}
        assert by_net[net] == required, ("Wrong ADC force/sense or codec polarity", net, sorted(by_net[net] ^ required))
    for net, required in DAC_PINS.items():
        assert by_net[net] == set(required), ("Wrong raw-DAC polarity or I/V connection", net)
    for net, required in {
        "REF_ADC1": {("U201", "14"), ("R108", "1")},
        "REF_ADC2": {("U201", "21"), ("R124", "1")},
        "CHIP_EN": {("U201", "1"), ("R143", "1"), ("U207", "6"), ("U207", "12")},
    }.items():
        assert required <= by_net[net], ("Missing reference or enable connection", net)
    return by_net


def check():
    native_path, construction_path = OUT / "native-review.json", OUT / "construction.json"
    native, construction = [json.loads(p.read_text()) for p in (native_path, construction_path)]
    for record in (native, construction):
        assert all(sha(REPO / p) == digest for p, digest in record["source_sha256"].items())
    assert all(sha(OUT / p) == digest for p, digest in native["raw_export_sha256"].items())
    assert all(sha(OUT / p) == digest for p, digest in native["captured_library_sha256"].items())
    erc = json.loads((OUT / "erc.json").read_text())
    assert len(erc["sheets"]) == 4 and erc["ignored_checks"] == []
    assert not any(s["violations"] for s in erc["sheets"]) and native["ERC_findings"] == 0
    assert all(c["returncode"] == 0 for c in native["complete_native_commands"])
    parts, pins = netlist(OUT / "netlist.xml")
    expected = json.loads((OUT / "expected-circuit.json").read_text())
    assert set(parts) == set(expected) and len(parts) == 210
    assert sum(len(v) for v in pins.values()) == 613
    domain = {}
    for ref, part in expected.items():
        assert parts[ref].findtext("value") == part["value"], ref
        assert (parts[ref].findtext("footprint") or "") == part["footprint"], ref
        assert set(pins[ref]) == set(part["pins"]), ref
        for pin, net in part["pins"].items():
            actual = pins[ref][pin]
            assert (actual.startswith("unconnected-") if net is None else actual == net), (ref, pin, net, actual)
        domain[ref] = part["source_domain"]
    by_net = joins(pins)
    shared = {net for net, nodes in by_net.items() if len({domain[r] for r, p in nodes}) > 1}
    assert shared == EXPECTED_SHARED, ("Unexpected cross-sheet connection", shared ^ EXPECTED_SHARED)
    assert {r for r in parts if r.startswith("J")} == {"J101", "J103", "J104", "J203", "J204", "J205", "J302", "J303"}
    unassigned = [r for r in parts if not parts[r].findtext("footprint")]
    assert unassigned == ["U201"] and parts["U201"].findtext("value") == "ES9292QPRO"
    assert len(pins["U201"]) == 49
    assert not (OUT / "audio_core.kicad_pcb").exists()
    inputs = [Path(__file__), native_path, construction_path, OUT / "netlist.xml", OUT / "erc.json", OUT / "expected-circuit.json"]
    return dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in inputs},
        electrical_parts=210, exported_physical_terminals=613,
        original_component_values_and_assigned_footprints_preserved=True,
        declared_cross_sheet_nets=sorted(shared), removed_internal_analog_headers=4,
        original_circuit_reference_traceability=construction["reference_map"],
        exact_ADC_star_terminals={net: {k: ([list(p) for p in v] if isinstance(v, list) else v) for k, v in spec.items()} for net, spec in ADC_STARS.items()},
        ADC_physical_requirement="Actual U201 input land must be the first common copper of force and independent feedback/sense branches; removing that land must disconnect the branches",
        physical_star_copper_checked=False, native_ERC_findings=0,
        all_native_ERC_categories_enabled=True, native_PCB_DRC_performed=False,
        missing_footprint_refs=unassigned, final_audio_PCB_routed=False,
        driver_enable_reference_timing_qualified=False, actual_ADC_load_and_partial_power_limits_resolved=False,
        actual_DAC_output_scale_resolved=False, final_power_connectors_and_harness_selected=False,
        enclosure_fit_verified=False, fabrication_released=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check()
    output = OUT / "integration-handoff.json"
    if args.check:
        assert json.loads(output.read_text()) == result
    else:
        with output.open("x") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    print("Shared audio core:210 parts/613 terminals;15 declared cross-sheet nets; exact four ADC stars and four DAC pin groups; ERC0")
