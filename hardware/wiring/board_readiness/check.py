"""Inventory actual design files and certificates without treating drafts as releases."""

import argparse
import hashlib
import json
from pathlib import Path

from ..system import BOARDS

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
ELECTRONICS = REPO / "hardware/electronics"
PCB_RECORDS = {
    "power_supply": ("routing/power_supply.kicad_pcb", "routing/generated/verification.json"),
    "rail_disconnect": ("routing/rail_disconnect.kicad_pcb", "routing/generated/verification.json"),
    "input_range": ("pcb/input_range.kicad_pcb", "pcb/generated/verification.json"),
    "adc_driver": ("pcb/adc_driver.kicad_pcb", "pcb/generated/verification.json"),
    "input_protection": ("input_protection.kicad_pcb", "generated/routing-verification.json"),
    "output_stage": ("output_stage.kicad_pcb", "generated/routing-verification.json"),
    "processor_carrier": ("processor_carrier.kicad_pcb", "generated/verification.json"),
    "control_inputs": ("control_inputs.kicad_pcb", "generated/verification.json"),
    "led_driver": ("led_driver.kicad_pcb", "generated/verification.json"),
}
CAD_IDS = {
    "power_supply": "power_carrier",
    "rail_disconnect": "disconnect_carrier (frozen placement)",
    "input_protection": "input_power",
    "output_stage": "audio_carrier",
    "processor_carrier": "dsp_carrier",
    "control_inputs": "control_input_hub",
    "led_driver": "led_driver",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_sources(record, path):
    base = path.parent.parent
    hashes = record.get("source_sha256", record.get("source_hashes", {}))
    matches, changed, missing = [], [], []
    for name, expected in hashes.items():
        p = (
            REPO / name
            if name.startswith(("hardware/", "tests/", "tools/", "docs/", ".github/"))
            else base / name
        )
        if not p.exists():
            missing.append(name)
        elif sha(p) != expected:
            changed.append(name)
        else:
            matches.append(name)
    return dict(
        source_hashes_checked=len(hashes),
        matching_sources=len(matches),
        changed_sources=changed,
        missing_sources=missing,
        all_recorded_sources_current=bool(hashes) and not changed and not missing,
    )


def inventory():
    sources = {}

    def track(p):
        sources[str(p.relative_to(REPO))] = sha(p)

    boards = []
    for name in BOARDS:
        folder = ELECTRONICS / name
        manifest = folder / "components.json"
        components = json.loads(manifest.read_text())
        schematic = folder / (name + ".kicad_sch")
        missing = [c["ref"] for c in components if not c.get("footprint")]
        pcb_name, record_name = PCB_RECORDS.get(name, (name + ".kicad_pcb", "generated/verification.json"))
        pcb, record_path = folder / pcb_name, folder / record_name
        record = json.loads(record_path.read_text()) if record_path.exists() else {}
        opens = (
            record.get("native_open_connections", record.get("unconnected_items")) if pcb.exists() else None
        )
        drc = (
            record.get("native_drc_violations", record.get("nonrouting_drc_violations"))
            if pcb.exists()
            else None
        )
        parity = record.get("schematic_parity_issues") if pcb.exists() else None
        native_closed = pcb.exists() and opens == 0 and drc == 0 and parity == 0
        entry = dict(
            board=name,
            circuit_components=len(components),
            assigned_footprints=len(components) - len(missing),
            missing_footprint_references=missing,
            schematic_present=schematic.exists(),
            pcb_present=pcb.exists(),
            pcb=str(pcb.relative_to(REPO)) if pcb.exists() else None,
            native_record=str(record_path.relative_to(REPO)) if record_path.exists() else None,
            native_drc_violations=drc,
            schematic_parity_issues=parity,
            native_open_connections=opens,
            recorded_native_connectivity_closed=bool(native_closed),
            record_freshness=record_sources(record, record_path) if record else None,
            a11_reference=CAD_IDS.get(name),
            new_candidate_integrated_in_a11=False if name in ("input_range", "adc_driver") else None,
            production_parts_or_stackup_qualified=False,
            electrical_performance_qualified=False,
            physical_assembly_verified=False,
            fabrication_released=False,
        )
        boards.append(entry)
        for p in [manifest, schematic, record_path, pcb]:
            if p.exists():
                track(p)
    system_path = REPO / "hardware/wiring/generated/system-interconnect.json"
    wiring = json.loads(system_path.read_text())
    track(system_path)
    required = [p for p in wiring["unused_header_pins"] if not p["optional_access"]]
    validate_boards(boards, required)
    for p in [Path(__file__), ROOT / "__init__.py", ROOT / "README.md", REPO / "hardware/wiring/system.py"]:
        if p.exists():
            track(p)
    tests = REPO / "tests/tooling/test_board_readiness.py"
    if tests.exists():
        track(tests)
    return dict(
        profile="standalone higher-headroom external converter; excludes historic E02/E03 and B1",
        boards=boards,
        board_count=len(boards),
        boards_without_pcb=[b["board"] for b in boards if not b["pcb_present"]],
        boards_with_missing_footprints=[b["board"] for b in boards if b["missing_footprint_references"]],
        required_unassigned_header_pins=required,
        required_unassigned_header_pin_count=len(required),
        unselected_distribution_fanouts=wiring["fanouts"],
        wiring_pin_pairs_checked=len(wiring["wires"]),
        blockers=[
            "Converter U1 has no assigned footprint; manufacturer package/land/stencil review required before a PCB.",
            "Native connectivity closure is not manufacturer-footprint, analog stability, noise, current/thermal or EMI qualification.",
            "SD socket, angle/touch and LED-anode assemblies remain unselected; logical terminals are not purchased-part pin numbers.",
            "E10 PCB is a separate candidate with no assigned housing datum; it must not be substituted for the existing A11 audio_carrier.",
            "E12 characterization PCB is separate from A11; its ADC force/sense stars end at J2, not the converter pins. Final co-location or a revised force/sense interface remains required.",
            "P01 is an unimplemented conditional source redesign at E25 star only; outgoing loads/fanouts, capacitor stability and late inrush remain open.",
            "E11 replaces E02/E03 for this profile; never add duplicate historic relay boards or optional-access coils.",
        ],
        board_list_complete_for_this_review=True,
        complete_unit_electronics=False,
        build_ready=False,
        source_sha256=sources,
    )


def validate_boards(boards, required):
    assert len(boards) == len(BOARDS) and {b["board"] for b in boards} == set(BOARDS)
    assert not ({"bypass", "audio_bypass"} & {b["board"] for b in boards}), (
        "Duplicate historic relay projects"
    )
    converter = next(b for b in boards if b["board"] == "converter")
    assert converter["missing_footprint_references"] == ["U1"], (
        "Converter package gap changed; review rather than suppress it"
    )
    assert len(required) == 24, "Peripheral/anode inventory changed; review source wiring"
    expected = {
        (b, h, str(p))
        for b, h, count in [
            ("processor_carrier", "J9", 4),
            ("processor_carrier", "J10", 4),
            ("processor_carrier", "J12", 8),
        ]
        for p in range(1, count + 1)
    }
    expected |= {("led_driver", f"J{h}", str(p)) for h in range(2, 6) for p in (25, 26)}
    assert {tuple(r["endpoint"]) for r in required} == expected
    for board in boards:
        assert not board["fabrication_released"] and not board["physical_assembly_verified"]
        if not board["pcb_present"]:
            assert (
                board["native_open_connections"] is None and not board["recorded_native_connectivity_closed"]
            )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    data = inventory()
    content = json.dumps(data, indent=2) + "\n"
    out = ROOT / "generated/board-readiness.json"
    if args.check:
        assert out.read_text() == content, "Stale board readiness inventory"
    else:
        out.parent.mkdir(exist_ok=True)
        out.write_text(content)
    print(
        f"{data['board_count']} external-profile boards; absent PCBs:{','.join(data['boards_without_pcb'])}; missing converter U1 footprint;24 peripheral/anodepins. Build-ready:false"
    )


if __name__ == "__main__":
    main()
