"""Source-derived transform instructions; no CAD mutation or fit qualification."""

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
DZ = 7.6


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_report():
    from hardware.cad.a11.integration import assignments

    other = json.loads((ROOT / "baseline-other.json").read_text())
    hashes = json.loads((ROOT / "baseline-sources.json").read_text())
    ctl = assignments(REPO / "hardware/cad/a11/generated/controls.scad")
    origins = {}
    native_findings = []
    extra_sources = [
        "hardware/cad/a12/enclosure_growth/generated/plan.json",
        "hardware/cad/a11/assembly.scad",
        "hardware/cad/a11/controls.scad",
        "hardware/cad/a11/mechanisms.scad",
        "hardware/cad/a11/housing.scad",
        "hardware/cad/a11/generated/controls.scad",
        "hardware/cad/a11/generated/layout.scad",
        "hardware/cad/a11/generated/button-fixture.scad",
        "hardware/cad/standalone.py",
        "hardware/cad/a12/integration.scad",
    ]
    board_sources = {}
    for folder, bid in [
        ("output_stage", "audio_carrier"),
        ("processor_carrier", "dsp_carrier"),
        ("control_inputs", "control_input_hub"),
        ("led_driver", "led_driver"),
    ]:
        base = REPO / "hardware/electronics" / folder
        placement = json.loads((base / "generated/placement.json").read_text())
        for body in placement["bodies"]:
            origins[body[0]] = f"hardware/electronics/{folder}/generated/placement.json#bodies"
        components = json.loads((base / "components.json").read_text())
        if isinstance(components, dict):
            components = components.get("components", components.get("parts"))
        assert isinstance(components, list)
        native_findings.append(
            dict(
                board_id=bid,
                component_count=len(components),
                native_panel_control_footprint_refs=[
                    p["ref"]
                    for p in components
                    if any(
                        w in p["footprint"].lower() for w in ["potentiometer", "switch", "rotary", "button"]
                    )
                ],
                header_refs=[p["ref"] for p in components if p["ref"].startswith("J")],
                source=f"hardware/electronics/{folder}/components.json",
            )
        )
        board_sources[bid] = f"hardware/electronics/{folder}/generated/placement.json#board"
        extra_sources += [
            f"hardware/electronics/{folder}/components.json",
            f"hardware/electronics/{folder}/README.md",
            f"hardware/electronics/{folder}/generated/placement.json",
        ]
    for rel in extra_sources:
        hashes[rel] = sha(REPO / rel)

    def entry(collection, i, row, classification, dz, origin, reason, condition=None):
        shifted = list(row)
        if dz is not None:
            shifted[3] = round(row[3] + dz, 10)
        return dict(
            collection=collection,
            index=i,
            id=row[0],
            baseline=row,
            classification=classification,
            translation_xyz_mm=None if dz is None else [0, 0, dz],
            candidate=shifted if dz is not None else None,
            source_origin=origin,
            reason=reason,
            condition=condition,
            physical_qualified=False,
        )

    board_map = []
    panel_boards = {"meter_board", "bpm_board", "settings_board", "release_select_board"}
    fixed_boards = {
        "dsp_carrier",
        "audio_carrier",
        "control_input_hub",
        "led_driver",
        "input_power",
        "disconnect_carrier",
    }
    for i, row in enumerate(other["boards"]):
        bid = row[0]
        if bid in panel_boards:
            c, dz, reason = (
                "panel_relative_candidate",
                DZ,
                "Preserve existing selector actuator or emitter/display spacing to raised panel; placement reserve, not qualified hardware.",
            )
        elif bid in fixed_boards:
            c, dz, reason = (
                "fixed_low_candidate",
                0,
                "Floor/rear/stack referenced; no native panel control is mechanically mounted on this PCB.",
            )
        else:
            assert bid == "trill_craft", bid
            c, dz, reason = (
                "unknown",
                None,
                "Controller PCB is distinct from panel touch backer/electrodes. No explicit mount or qualified electrode harness establishes required Z.",
            )
        board_map.append(
            entry(
                "boards",
                i,
                row,
                c,
                dz,
                board_sources.get(bid, "hardware/cad/standalone.py#BOARDS (A12 replaces disconnect datum)"),
                reason,
            )
        )
    env_map = []
    panel_env = {"bpm_digits", "settings_switch", "release_select_switch"} | {
        k[0] + "_pot" for k in ctl["knobs"]
    }
    lever_env = {"angle_sensor_board", "angle_sensor"}
    for i, row in enumerate(other["envelopes"]):
        name = row[0]
        if name in panel_env:
            c, dz, origin, why = (
                "panel_relative_candidate",
                DZ,
                "hardware/cad/standalone.py#ENVELOPES",
                "Preserve panel-relative actuator/shaft/display geometry; exact part engagement and mounting remain unqualified.",
            )
        elif name in lever_env:
            c, dz, origin, why = (
                "lever_coherent_candidate",
                DZ,
                "hardware/cad/standalone.py#ENVELOPES",
                "Move with pivot/magnet to preserve sensor alignment; actual magnetic gap and sensor mounting unqualified.",
            )
        elif name == "trill_components":
            c, dz, origin, why = (
                "unknown",
                None,
                "hardware/cad/standalone.py#ENVELOPES",
                "Follows unresolved Trill controller PCB, not automatically the touch backer.",
            )
        elif name in origins:
            c, dz, origin, why = (
                "fixed_low_candidate",
                0,
                origins[name],
                "Actual inherited native component/tail/fixing allocation follows unchanged low PCB.",
            )
        elif name.startswith("disconnect_"):
            c, dz, origin, why = (
                "legacy_replaced_by_native",
                0,
                "hardware/cad/a11/generated/components.scad + hardware/cad/a12/generate.py",
                "Historical E25 reserve; do not substitute for repaired E28 actual both-face body packet.",
            )
        elif name.startswith("inlet_"):
            c, dz, origin, why = (
                "fixed_rear_candidate",
                0,
                "hardware/cad/a12/inlet.py#packet",
                "Rear inlet assembly remains fixed to rear cassette.",
            )
        else:
            raise AssertionError(("Unclassified actual envelope", name))
        env_map.append(entry("envelopes", i, row, c, dz, origin, why))
    mounts = []
    for i, row in enumerate(other["board_mounts"]):
        is_lever = row[0] == "lever"
        mounts.append(
            entry(
                "board_mounts",
                i,
                row,
                "lever_coherent_candidate" if is_lever else "fixed_low_candidate",
                DZ if is_lever else 0,
                "hardware/cad/standalone.py#MOUNTS + hardware/cad/a12/generate.py#build",
                "Raise post seating plane with unchanged lever bracket."
                if is_lever
                else "Retain PCB seating plane. P03 mounts remain source-defined; no panel-height dependence.",
            )
        )
    daughters = []
    for i, row in enumerate(other["daughterboard_mounts"]):
        daughters.append(
            entry(
                "daughterboard_mounts",
                i,
                row,
                "fixed_low_candidate",
                0,
                "hardware/cad/standalone.py#DAUGHTER_MOUNTS",
                "Both lower/upper planes remain 8.1/12.1. E18 stack remains relative to fixed E19.",
            )
        )
    modules = [
        dict(
            id="front_panel",
            source="hardware/cad/a11/assembly.scad#assembled",
            behavior="panel_z driven",
            baseline_z_mm=36,
            candidate_z_mm=43.6,
        ),
        dict(
            id="guide_plate",
            source="hardware/cad/a11/assembly.scad#assembled",
            behavior="panel_z-guide_thick driven",
            baseline_z_mm=34.6,
            candidate_z_mm=42.2,
        ),
        dict(
            id="touch_backer",
            source="hardware/cad/a11/controls.scad#touch_backer",
            behavior="internal panel_z-34 translation",
            baseline_z_mm=32.6,
            candidate_z_mm=40.2,
        ),
        dict(
            id="knob_instances",
            instance_ids=[k[0] for k in ctl["knobs"]],
            source="hardware/cad/a11/assembly.scad#controls_assembly",
            behavior="shell_height+2.8 driven",
            baseline_z_mm=40.8,
            candidate_z_mm=48.4,
        ),
        dict(
            id="button_mechanisms",
            instance_ids=[b[0] for b in ctl["buttons"]],
            source="hardware/cad/a11/controls.scad#button_pose + generated/button-fixture.scad",
            behavior="panel_z driven; retain actual XY and rotations",
            switch_base_z_mm=[27.2, 34.8],
            holder_bottom_z_mm=[25.6, 33.2],
        ),
        dict(
            id="a12_switch_electronics",
            instance_ids=[b[0] for b in ctl["buttons"]],
            source="hardware/cad/a12/integration.scad#a12_switch_electronics",
            behavior="panel_z driven; 10x10 local reserve rotates with each actual switch",
            body_z_mm=[[27.2, 31.7], [34.8, 39.3]],
            lead_solder_z_mm=[[22.7, 27.2], [30.3, 34.8]],
            allocation_not_guaranteed=True,
        ),
        dict(
            id="selector_cap",
            instance_ids=["settings", "release_type"],
            source="hardware/cad/a11/assembly.scad#controls_assembly",
            behavior="panel_z driven",
            baseline_z_mm=36,
            candidate_z_mm=43.6,
        ),
        dict(
            id="ring_lens",
            source="hardware/cad/a11/assembly.scad#optics",
            behavior="shell_height driven",
            baseline_z_mm=38,
            candidate_z_mm=45.6,
        ),
        dict(
            id="touch_lens",
            source="hardware/cad/a11/assembly.scad#optics",
            behavior="panel_z driven",
            baseline_z_mm=37.2,
            candidate_z_mm=44.8,
        ),
        dict(
            id="display_lens",
            source="hardware/cad/a11/assembly.scad#optics",
            behavior="panel_z driven",
            baseline_z_mm=37.6,
            candidate_z_mm=45.2,
        ),
        dict(
            id="meter_lens",
            instance_xy_mm=[[43.9, 21.25], [43.9, 35.25]],
            source="hardware/cad/a11/assembly.scad#optics",
            behavior="panel_z driven",
            baseline_z_mm=35.2,
            candidate_z_mm=42.8,
        ),
        dict(
            id="bank_lens",
            instance_xy_mm=[[x, 103] for x in [82, 101, 120, 139]],
            source="hardware/cad/a11/assembly.scad#optics",
            behavior="panel_z driven",
            baseline_z_mm=35.2,
            candidate_z_mm=42.8,
        ),
    ]
    for row in modules:
        row["translation_xyz_mm"] = [0, 0, DZ]
        row["qualification"] = False
    lever = dict(
        source="hardware/cad/a11/mechanisms.scad",
        translation_xyz_mm=[0, 0, DZ],
        modules=["lever_bracket", "lever_arm", "lever_occupied_piece", "lever_sweep"],
        baseline_pivot_xyz_mm=[316, 82, 24],
        candidate_pivot_xyz_mm=[316, 82, 31.6],
        baseline_bracket_floor_xyz_mm=[303, 66, 7],
        candidate_bracket_floor_xyz_mm=[303, 66, 14.6],
        baseline_spring_anchor_xyz_mm=[312, 70, 28],
        candidate_spring_anchor_xyz_mm=[312, 70, 35.6],
        coupled_envelope_ids=["angle_sensor_board", "angle_sensor"],
        coupled_mount_indices=[r["index"] for r in mounts if r["id"] == "lever"],
        applies_to="Unchanged panel-relative lever kinematics; redesigned slot/lever would need separate analysis.",
        automatic_panel_z_tracking=False,
        external_bearings_magnet_spring_fasteners_mounting_and_travel_qualified=False,
    )
    headers = dict(
        E19_pots={f"J{i + 20}": k[0] for i, k in enumerate(ctl["knobs"])},
        E18_front_inputs=["J1", "J2", "J3"],
        E18_fixed_rear_status=["J4"],
        E18_E19_stack_link="E18 J5 to E19 J2",
        E20_panel_emitters=["J2", "J3", "J4", "J5"],
        E20_E19_link="E20 J1 to E19 J11; different engineering header pitches require actual adapter",
        interpretation="Pot header mapping order must be cross-checked against connector map before wiring; this ordered list alone is not an electrical pin contract.",
    )
    # Confirm actual E19 labels rather than assume list order.
    parts = json.loads((REPO / "hardware/electronics/processor_carrier/components.json").read_text())
    headers["E19_pot_native_notes"] = {
        p["ref"]: p.get("note", "") for p in parts if p["ref"] in headers["E19_pots"]
    }
    assert all(
        headers["E19_pot_native_notes"][ref].startswith(control + ":")
        for ref, control in headers["E19_pots"].items()
    )
    a = math.radians(35)
    local_z = (43.65 - 24) / math.cos(a)
    assert 0 < local_z < 24
    lever["fixed_lever_new_panel_analytic_interference_witness"] = dict(
        angle_degrees=35,
        local_stem_point_mm=[0, 0, local_z],
        world_point_mm=[316, 82 + local_z * math.sin(a), 43.65],
        original_slot_y_interval_mm=[69, 95],
        new_panel_z_interval_mm=[43.6, 45.6],
        conclusion="Point inside unchanged stem lies inside raised panel thickness beyond unchanged slot. Analytic source-geometry witness, not native or physical qualification.",
    )
    report = dict(
        schema="A12-PANEL-MOUNT-AUDIT-01",
        purpose=__doc__,
        original_shell_mm=[334, 157, 38],
        candidate_shell_mm=[334, 188.4, 45.6],
        panel_z_mm=[36, 43.6],
        panel_shift_mm=DZ,
        coordinate_rule="Original XY retained; +31.4mm depth added at front +Y. No recentering.",
        transform_semantics="Explicit source-derived candidate instructions, not adopted poses or native collision evidence. Z shifts preserve existing panel-relative geometry only.",
        boards=board_map,
        envelopes=env_map,
        board_mounts=mounts,
        daughterboard_mounts=daughters,
        panel_modules=modules,
        lever_group=lever,
        interfaces=headers,
        native_BOM_findings=native_findings,
        fixed_rear=dict(
            source="hardware/cad/a11/housing.scad#rear_panel",
            translation_xyz_mm=[0, 0, 0],
            rear_port_ids=[r[0] for r in other["rear_ports"]],
            port_envelope_ids=[r[0] for r in other["port_envelopes"]],
            reason="Rear cassette and existing I/O stay at original elevations.",
        ),
        omitted_native_groups=dict(
            P03="Use root repaired.packet actual source at unchanged datum; not a boards row in other.",
            E28="Use repaired.packet actual body and datum; legacy disconnect_ envelopes are not replacement evidence.",
            supported_E19_J13="Supported private ear has same low 6.5mm datum; preserving it retains accepted wire endpoints as a candidate, not a fresh full-route pass.",
        ),
        unresolved=[
            "Trill controller mounting/electrode harness and touch capacitance",
            "Exact panel-pot shaft/bushing/panel thickness/knob socket engagement",
            "Selector actuator travel and PCB fastening",
            "Emitter PCBs, exact lightguide/display gaps and fastening",
            "Longer switch/pot/LED/touch/sensor harness routing, strain relief and electrical performance",
            "Actual lever bearing/magnet/spring/sensor alignment and raised post structural proof",
            "New enlarged guide-plate stiffness and attachment",
            "H9 tool access still obstructed by actual DIG copper; height growth does not resolve it",
        ],
        source_sha256=hashes,
        baseline_other_sha256=sha(ROOT / "baseline-other.json"),
        native_fit_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
        shared_sources_modified=False,
    )
    (ROOT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                boards=len(board_map),
                envelopes=len(env_map),
                mounts=len(mounts),
                buttons=len(ctl["buttons"]),
                report_sha256=sha(ROOT / "report.json"),
            )
        )
    )


if __name__ == "__main__":
    write_report()
