"""Independent actual native-pad check after footprint flips and rotations."""

import hashlib
import json
import math
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path = ROOT / "negative_startup_placement.kicad_pcb"
    plan = json.loads((ROOT / "generated/placement.json").read_text())
    manager = pcbnew.GetSettingsManager()
    project = ROOT / "negative_startup_placement.kicad_pro"
    assert manager.LoadProject(str(project))
    board = pcbnew.LoadBoard(str(path))
    board.SetProject(manager.GetProject(str(project)))
    parts = {f.GetReference(): f for f in board.GetFootprints()}
    rows = []
    for assignment in plan["AUX_backside_bypass_assignments"]:
        ic, cap = parts[assignment["ic"]], parts[assignment["capacitor"]]
        power = next(p for p in ic.Pads() if p.GetNumber() == assignment["power_pin"])
        bypass = next(p for p in cap.Pads() if p.GetNumber() == "1")
        ground = next(p for p in cap.Pads() if p.GetNumber() == "2")
        assert not ic.IsFlipped() and cap.IsFlipped()
        assert power.GetNetname() == bypass.GetNetname() == "AUX2V6"
        assert ground.GetNetname() == "AGND"
        a, b = power.GetPosition(), bypass.GetPosition()
        distance = math.hypot(a.x - b.x, a.y - b.y) / 1e6
        error = abs(distance - assignment["projected_pad_distance_mm"])
        assert error <= 2e-6, (assignment, distance, "Native flip/rotation disagrees with plan")
        rows.append(dict(ic=ic.GetReference(), capacitor=cap.GetReference(),
                         native_IC_power_pad_mm=[a.x / 1e6, a.y / 1e6],
                         native_capacitor_VCC_pad_mm=[b.x / 1e6, b.y / 1e6],
                         native_projected_separation_mm=distance, plan_difference_mm=error))
    assert len(rows) == 32
    report = dict(scope="Actual native pads, not pre-flip placement arithmetic", assignments=rows,
                  maximum_native_projected_pad_separation_mm=max(r["native_projected_separation_mm"] for r in rows),
                  source_sha256={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), path, ROOT / "generated/placement.json"]},
                  actual_copper_return_and_via_inductance_qualified=False,
                  physical_qualified=False, fabrication_released=False)
    (ROOT / "generated/native-bypass-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(len(rows), "native bypass assignments checked; maximum", report["maximum_native_projected_pad_separation_mm"], "mm")


if __name__ == "__main__":
    main()
