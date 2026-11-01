"""Generate a conservative P03 packaging reserve, preserving the A11 source kit.

This is an interface allocation until the actual repaired native PCBs and their
complete component heights replace it. It cannot establish electrical or physical
qualification. The positive-control geometry deliberately removes the boss reliefs.
"""

import hashlib
import json
from pathlib import Path

from hardware.cad.a11.integration import assignments, overlap

from .inlet import INLET
from .inlet import packet as inlet_packet

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
OUT = ROOT / "generated"
A11 = ROOT.parent / "a11"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    contract = json.loads((ROOT / "interface.json").read_text())
    power = contract["power_candidate"]
    data = assignments(A11 / "generated/components.scad")
    # A12 raises the disconnect internally to provide real underside assembly
    # clearance. Retain A11 unchanged and move every inherited reserve and its
    # printed mounting plane together. Actual repaired component shapes have a
    # separate source-bound packet in repaired.py.
    disconnect_datum = contract["disconnect_terminals"]["board_datum"]
    old_disconnect = next(board for board in data["boards"] if board[0] == "disconnect_carrier")
    assert old_disconnect[1:3] == disconnect_datum[:2], "XY relocation needs independent integration"
    disconnect_dz = disconnect_datum[2] - old_disconnect[3]
    old_disconnect[3] = disconnect_datum[2]
    for row in data["envelopes"] + data["disconnect_cylinders"]:
        if row[0].startswith("disconnect_"):
            row[3] += disconnect_dz
    for mount in data["board_mounts"]:
        if mount[0] == "disconnect_carrier":
            mount[3] = disconnect_datum[2]
    inlet = inlet_packet(data)
    data["boards"] = [inlet["board"] if b[0] == "input_power" else b for b in data["boards"]]
    data["envelopes"] = [e for e in data["envelopes"] if not e[0].startswith("e23_")] + inlet["bodies"]
    # P03 replaces the complete original supply. It cannot occupy that bay while
    # also retaining the original board as an unallocated source for its ± rails.
    data["boards"] = [b for b in data["boards"] if b[0] != "power_carrier"]
    data["envelopes"] = [e for e in data["envelopes"] if not e[0].startswith("power_")]
    data["board_mounts"] = [m for m in data["board_mounts"] if m[0] != "power_carrier"]
    x, y, z = power["datum"]
    for mx, my in power["mounts"]:
        data["board_mounts"].append(["power_carrier", x + mx, y + my, z, power["mount_drill"]])
    z_min, z_max = power["adjustable_bottom_z_range"]
    assert z_min <= z <= z_max
    thickness_min, thickness_max = power["fabrication_thickness_range"]
    assert 0 < thickness_min <= power["thickness"] <= thickness_max
    bounds = [
        "P03_conservative_top",
        x,
        y,
        z_min,
        160,
        45,
        z_max - z_min + thickness_max + power["top_assembly_height_limit"],
    ]
    collisions = [b[:7] for b in data["boards"] + data["envelopes"] if overlap(bounds, b)]
    assert not collisions, ("Candidate bay collides with other electronics", collisions)
    bottom_gap = z_min - power["bottom_assembly_height_limit"] - 2.8
    assert bottom_gap >= power["minimum_external_clearance"]
    sources = [ROOT / "interface.json", ROOT / "generate.py", ROOT / "integration.scad"]
    sources += [
        ROOT / "inlet.py",
        ROOT.parent / "input_power.py",
        ROOT.parent / "standalone.py",
        A11 / "integration.py",
        REPO / "hardware/electronics/common/sexpr.py",
        REPO / "hardware/electronics/output_stage/check_placement.py",
        INLET / "rear_inlet.kicad_pcb",
        INLET / "components.json",
    ]
    sources += list(A11.glob("*.scad")) + list((A11 / "generated").glob("*.scad"))
    report = dict(
        revision=contract["revision"],
        scope="Conservative new supply bay allocation, not actual component integration",
        power_candidate=power,
        disconnect_mount_plane_z_mm=disconnect_datum[2],
        electronics_box_collisions=collisions,
        bottom_assembly_to_floor_gap_mm=bottom_gap,
        top_assembly_maximum_z_mm=z_max + thickness_max + power["top_assembly_height_limit"],
        old_supply_retained=False,
        inlet_integration=inlet,
        native_repaired_pcb_bound=False,
        terminal_fastener_stack_approved=False,
        physical_fit_verified=False,
        fabrication_released=False,
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(set(sources))},
    )
    return contract, data, report


def main():
    contract, data, report = build()
    OUT.mkdir(exist_ok=True)
    (OUT / "components.scad").write_text(
        "// A12 reserve: actual A11 obstacles, original supply removed.\n"
        + "\n".join(f"{k} = {json.dumps(v)};" for k, v in data.items())
        + "\n"
    )
    p = contract["power_candidate"]
    (OUT / "interface.scad").write_text(
        "// Generated conditional A12 supply interface; no physical approval.\n"
        + "\n".join(f"p03_{k} = {json.dumps(v)};" for k, v in p.items())
        + "\n"
        + "\n".join(
            "a12_switch_" + name + " = " + json.dumps(contract["switch_assembly"][key]) + ";"
            for name, key in [
                ("body_xy", "local_body_terminal_reserve_xy_mm"),
                ("body_height", "body_projection_maximum_mm"),
                ("lead_drop", "lead_solder_projection_requirement_mm"),
            ]
        )
        + "\n"
    )
    (OUT / "allocation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("A12: new P03 supply bay allocated; native geometry checks still required")


if __name__ == "__main__":
    main()
