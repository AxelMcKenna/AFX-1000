"""Independent mechanical/interface facts from externally held official Craft C3.

No manufacturer PCB, datasheet, logo or vendor STEP is redistributed here.
"""

import hashlib
import json
import math
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
VENDOR = Path("/private/tmp/afx-trill-vendor")
COMMIT = "537ebd6bb9c1de736aa0fc65c66fc1115b7875ef"
X0, Y0 = 125.984, 94.107
WORLD = [82, 123.5, 30.6]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    path = VENDOR / "trill-craft-C3.kicad_pcb"
    pcb = read_sexpr(path.read_text())
    netnames = {int(n[1]): n[2] for n in children(pcb, "net")}
    mounts = []
    ports = []
    bodies = []
    tails = []

    def world(xy):
        return [round(WORLD[0] + xy[0] - X0, 7), round(WORLD[1] + xy[1] - Y0, 7)]

    for fp in children(pcb, "footprint"):
        props = {p[1]: p[2] for p in children(fp, "property")}
        ref = props["Reference"]
        pads = children(fp, "pad")
        if not pads:
            continue
        points = []
        for p in pads:
            xy = world(transform(fp, first(p, "at")[1:3]))
            size = list(map(float, first(p, "size")[1:3]))
            radius = math.hypot(*size) / 2
            points.append([*xy, radius])
            net = children(p, "net")
            netname = (
                net[0][2] if net and len(net[0]) > 2 else netnames.get(int(net[0][1]), "") if net else ""
            )
            if ref in ["H1", "H2"]:
                mounts.append(
                    dict(
                        ref=ref,
                        world_xy_mm=xy,
                        drill_mm=float(first(p, "drill")[1]),
                        pad_size_mm=size,
                        net=netname,
                    )
                )
                continue
            if ref == "J1" and p[3] == "circle":
                ports.append(
                    dict(pin=p[1], net=netname, world_xy_mm=xy, drill_mm=float(first(p, "drill")[1]))
                )
            if p[2] == "thru_hole" and p[3] == "circle":
                tails.append(
                    dict(
                        id=ref + "_" + p[1],
                        xy_mm=xy,
                        radius_requirement_mm=0.8,
                        z_mm=[27.6, 30.6],
                        qualification=False,
                    )
                )
        if ref not in ["H1", "H2"]:
            lo = [min(p[i] - p[2] for p in points) for i in [0, 1]]
            hi = [max(p[i] + p[2] for p in points) for i in [0, 1]]
            bodies.append(
                dict(
                    id=ref,
                    box_mm=[*lo, 32.2, hi[0] - lo[0], hi[1] - lo[1], 6.4],
                    meaning="Circumscribed actual terminal group; entire6.4mm above-face project allocation, not verified component height.",
                )
            )
    assert len(mounts) == 2 and all(
        m["drill_mm"] == 3.2 and m["pad_size_mm"] == [5.5, 5.5] and m["net"].startswith("unconnected")
        for m in mounts
    )
    assert [p["net"] for p in ports] == ["/XRES", "/EVENT", "GND", "VCC", "/I2C_SDA", "/I2C_SCL"]
    evidence = {}
    for name in ["trill-craft-C3.kicad_pcb", "trill-craft-A3.kicad_pcb", "trill_datasheet.pdf", "README.md"]:
        p = VENDOR / name
        evidence[str(p)] = sha(p)
    sources = {}
    for rel in [
        "hardware/cad/a12/panel_mount_audit/report.json",
        "hardware/cad/a11/controls.scad",
        "hardware/cad/a11/mechanisms.scad",
        "hardware/cad/standalone.py",
        "hardware/electronics/processor_carrier/spec.py",
        "hardware/electronics/processor_carrier/components.json",
        "firmware/daisy/main.cpp",
        "hardware/firmware/BoardIO.h",
        "hardware/firmware/full_engine/main.cpp",
        "hardware/firmware/README.md",
    ]:
        sources[rel] = sha(REPO / rel)
        dest = ROOT / "sources" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((REPO / rel).read_bytes())
    report = dict(
        schema="TC01",
        manufacturer="Bela / Augmented Instruments Ltd",
        official_commit=COMMIT,
        primary_sources=[
            dict(
                url="https://github.com/BelaPlatform/Trill/blob/"
                + COMMIT
                + "/hardware/craft/REV_C3_KiCad/trill-craft.kicad_pcb",
                facts="Exact C3 outline, hole positions/pin map",
            ),
            dict(
                url="https://github.com/BelaPlatform/Trill/blob/" + COMMIT + "/trill_datasheet.pdf",
                revision="1.3 / RevC /2025-02-03",
                pages={
                    "6": "RevA vsC footprint; pads",
                    "7": "1.71..5.5V,4mA and50/100/400kHz rows",
                    "26": "53.8x21.8,1.6PCB,37mm mounting pitch; holes not ground",
                },
            ),
            dict(
                url="https://learn.bela.io/tutorials/trill-sensors/working-with-trill-craft/",
                facts="Electrode cables are part of sensor; sequential pads forcentroid; ground unused channels; actual tuning/cover/grounding needed",
            ),
        ],
        external_vendor_sha256=evidence,
        source_sha256=sources,
        vendor_hardware_license="CC BY-SA4.0 stated in current officialREADME; vendorfiles remainexternal; no copiedvendorPCB/logo/STEP in this kit.",
        original_project_reserve_mm=[82, 123.5, 23, 52, 21, 1.6],
        candidate_datum_mm=WORLD,
        candidate_orientation="Official C3 X/Y untranslated orientation; component face upward.",
        native_board_bounds_mm=[125.984, 94.107, 179.832, 115.951],
        actual_width_depth_mm=[53.848, 21.844],
        native_thickness_mm=1.6,
        dimensions_are_nominal_not_fabrication_tolerance=True,
        candidate_conservative_outline_box_mm=[82, 123.5, 30.6, 53.848, 21.844, 1.6],
        old_reserve_undersizes_current_C3_mm=[1.848, 0.844],
        mounts=mounts,
        actual_mount_centre_distance_mm=math.dist(mounts[0]["world_xy_mm"], mounts[1]["world_xy_mm"]),
        communication_pads=ports,
        component_terminal_reserves=bodies,
        tail_reserves=tails,
        design=dict(
            attachment="Insulating saddle carried by four existing touch-backer corner interfaces; no post through central foil/lens aperture.",
            backer_corner_interfaces_xy_mm=[[x, y] for x in [73, 143] for y in [123, 145]],
            backer_existing_pilot_mm=1.6,
            backer_attachment_fastener_and_thread_qualified=False,
            upper_mating_z_mm=42.2,
            saddle_floor_z_mm=[24.6, 26.2],
            board_seat_z_mm=30.6,
            mounting_seat_OD_mm=5.4,
            mounting_clearance_mm=3.4,
            construction_material="Electrically insulating machined or printed polymer: grade/process/creep/fire/tolerance remain UNSELECTED.",
            M3_retention="Actual3.2mm boardholes permit nominalM3; screwhead/washer project envelopeOD6.4/H3.2. Exact fastener length/threadengagement/torque unresolved.",
            wire_configuration="Direct soldered I2C/electrode leads; no unsourced 90degree headerbody assumed. Solder/strain/endgeometry and insulating loom remain unqualified.",
        ),
        host_interface=dict(
            E19="J9",
            mapping={"1 AGND": "J1.3 GND", "2 V3V3_IO": "J1.4 VCC", "3 SCL": "J1.6", "4 SDA": "J1.5"},
            unused_reset_event="J1.1/J1.2 not routed by existingE19J9; select reset/event policy before integration.",
            operating_voltage_datasheet_row_V=[1.71, 5.5],
            operating_current_datasheet_row_mA=4,
            current_row_is_guaranteed_assembly_max=False,
            electrode_plan="Eight sequential channels0..7 candidate, remainingchannelsground permanufacturercentroidguide; exact foil/wire mapping not implemented.",
            firmware_profile_context="Legacy firmware/daisy/main.cpp is the B1/5V MPR121 profile, not current high-end. Current hardware/firmware/BoardIO.h and full_engine/main.cpp use Trill0x30 identify/DIFF protocol. Physical C3 command/scan/tuning/startup compatibility remains unmeasured; no firmware failure inferred from legacy profile.",
        ),
        model_limits=[
            "Nominal vendorCAD outline/thickness without lot/tolerance limits",
            "Project6.4mm above-face allocation lacks actual all-part height proof",
            "3mm tail reserve/radius.8 is assembly requirement, not measured soldergeometry",
            "No complete wire/insulation/strain or capacitance/noise/touch proof",
            "Backer1.4mm cornerflange strength and exact mountinghardware unresolved",
            "Native local fit does not prove whole enlargedunit fit or adjacent wire/thermal/positive-link closure",
        ],
        native_fit_qualified=False,
        physical_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
    )
    (ROOT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(mounts=mounts, bodies=len(bodies), tails=len(tails))))


if __name__ == "__main__":
    run()
