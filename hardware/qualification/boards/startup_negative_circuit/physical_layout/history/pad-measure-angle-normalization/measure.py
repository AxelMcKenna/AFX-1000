"""Read actual native pad poses and explicit local rear-height requirements."""

import hashlib
import json
import math
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    pcb = ROOT / "negative_startup_physical.kicad_pcb"
    before = sha(pcb)
    board = pcbnew.LoadBoard(str(pcb))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    parts = {c["ref"]: c for c in json.loads((ROOT / "components.json").read_text())}
    plan = json.loads((ROOT / "placement.json").read_text())
    assert len(parts) == 265 and len(fps) == 267
    for ref, pose in plan["placements"].items():
        fp = fps[ref]
        assert ("B" if fp.IsFlipped() else "F") == pose["side"]
        assert abs(fp.GetOrientationDegrees() - pose["rotation_deg"]) < 1e-9
        assert math.dist([fp.GetPosition().x / 1e6, fp.GetPosition().y / 1e6], pose["anchor_mm"]) <= 2e-6
    assignments = []
    for a in plan["backside_bypass_assignments"]:
        cap, owner = a["cap"], a["owner"]
        net = next(p["net"] for p in parts[cap]["pins"] if p["number"] == "1")
        pins = [p["number"] for p in parts[owner]["pins"] if p["net"] == net
                and p["kind"] in ["power_in", "power_out", "output"]]
        assert len(pins) == 1
        power = next(p for p in fps[owner].Pads() if p.GetNumber() == pins[0])
        pad = next(p for p in fps[cap].Pads() if p.GetNumber() == "1")
        assert power.GetNetname() == pad.GetNetname() == "/" + net
        x, y = power.GetPosition(), pad.GetPosition()
        distance = math.hypot(x.x - y.x, x.y - y.y) / 1e6
        assert abs(distance - a["projected_power_pad_separation_mm"]) <= 3e-6, (cap, distance, a)
        assignments.append(dict(cap=cap, owner=owner, owner_power_pin=pins[0], net=power.GetNetname(),
                                actual_native_projected_power_pad_separation_mm=distance,
                                via_and_complete_return_loop_inductance_qualified=False))
    assert len(assignments) == 58
    rear = []
    for ref in plan["local_rear_1p9_mm_receiving_caps"]:
        p = plan["placements"][ref]
        assert p["side"] == "B"
        u, v, width, height = p["courtyard_rect_mm"]
        # Courtyards conservatively bound plan bodies; these arithmetic tests
        # do not replace new3D contact/lead/wire/assembly checks.
        ymax = 180.5 + 1.76 + 1.9 + .2
        zmax = 3.5 + v + height + .2
        x_bands_clear = all(u + width <= x - 4.2 - .25 or u >= x + 4.2 + .25 for x in [38, 138])
        assert ymax + .25 < 185.6 and zmax + .25 < 41.6 and x_bands_clear, ref
        rear.append(dict(ref=ref, complete_height_receiving_mm=1.9,
                         maximum_FR4_receiving_mm=1.76, additional_frame_displacement_sensitivity_mm=.2,
                         Y_high_sensitivity_mm=ymax, inner_wall_Y_mm=185.6,
                         Z_high_courtyard_sensitivity_mm=zmax, upper_seat_Z_low_mm=41.6,
                         outside_declared_carrier_X_bands=True,
                         actual_body_tail_mount_wire_native_intersections_verified=False))
    assert sha(pcb) == before
    report = dict(parts=265, extra_mechanical=2, all_actual_native_component_poses_match_plan=True,
                  PCB_sha256=before, source_script_sha256=sha(Path(__file__)),
                  source_plan_sha256=sha(ROOT / "placement.json"),
                  native_supply_pad_assignments=assignments,
                  worst_native_projected_supply_pad_distance_mm=max(a["actual_native_projected_power_pad_separation_mm"] for a in assignments),
                  named_local_rear_1p9_receiving_analytical_checks=rear,
                  actual_assembled_height_accepted=False, full_unit_geometry_qualified=False,
                  PDN_and_reference_noise_qualified=False, physical_qualified=False, fabrication_released=False)
    out = ROOT / "generated/native-pad-measurements.json"
    assert not out.exists(), "Preserve earlier measurements"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print("Actual native58 supply-pad placements agree;14 taller rear receiving arithmetic checks pass; real loops/fullfit unqualified")


if __name__ == "__main__":
    main()
