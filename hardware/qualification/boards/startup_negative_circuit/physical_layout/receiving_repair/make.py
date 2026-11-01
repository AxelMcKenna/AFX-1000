"""Four-cap receiving-clearance successor; preserve the captured first layout."""

import copy
import hashlib
import json
import math
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
REFS = {"C4", "C5", "C31", "C32"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(board):
    return {f.GetReference(): dict(x=f.GetPosition().x, y=f.GetPosition().y,
                                  value=f.GetValue(), FPID=str(f.GetFPIDAsString()),
                                  angle=f.GetOrientationDegrees(), flipped=f.IsFlipped(),
                                  nets={p.GetNumber(): p.GetNetname() for p in f.Pads() if p.GetNumber()})
            for f in board.GetFootprints()}


def main():
    assert not (ROOT / "negative_startup_physical.kicad_pcb").exists()
    source = PARENT / "negative_startup_physical.kicad_pcb"
    parent_sha = sha(source)
    b = pcbnew.LoadBoard(str(source))
    assert not list(b.GetTracks())
    before = identity(b)
    assert len(before) == 267
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    for ref in REFS:
        fp = fps[ref]
        assert fp.IsFlipped()
        p = fp.GetPosition()
        assert abs(p.y / 1e6 - 7.8) < 1e-6
        fp.SetPosition(pcbnew.VECTOR2I(p.x, p.y + pcbnew.FromMM(.6)))
    after = identity(b)
    for ref in before:
        expected = copy.deepcopy(before[ref])
        if ref in REFS:
            expected["y"] += pcbnew.FromMM(.6)
        assert after[ref] == expected, ref
    out = ROOT / "negative_startup_physical.kicad_pcb"
    pcbnew.SaveBoard(str(out), b)
    for name in ["negative_startup_physical.kicad_pro", "negative_startup_physical.kicad_sch",
                 "components.json", "land-inventory.json", "connector-placement.json", "fp-lib-table"]:
        shutil.copyfile(PARENT / name, ROOT / name)
    shutil.copytree(PARENT / "NF06P.pretty", ROOT / "NF06P.pretty")
    plan = json.loads((PARENT / "placement.json").read_text())
    parts = {c["ref"]: c for c in json.loads((ROOT / "components.json").read_text())}
    for ref in REFS:
        plan["placements"][ref]["anchor_mm"][1] += .6
        plan["placements"][ref]["courtyard_rect_mm"][1] += .6
    for a in plan["backside_bypass_assignments"]:
        if a["cap"] in REFS:
            cap = next(p for p in fps[a["cap"]].Pads() if p.GetNumber() == "1")
            net = next(p["net"] for p in parts[a["cap"]]["pins"] if p["number"] == "1")
            pins = [p["number"] for p in parts[a["owner"]]["pins"] if p["net"] == net
                    and p["kind"] in ["power_in", "power_out", "output"]]
            assert len(pins) == 1
            pin = next(p for p in fps[a["owner"]].Pads() if p.GetNumber() == pins[0])
            q, p = cap.GetPosition(), pin.GetPosition()
            a["projected_power_pad_separation_mm"] = math.hypot(q.x - p.x, q.y - p.y) / 1e6
    plan["maximum_projected_bypass_power_pad_distance_mm"] = max(a["projected_power_pad_separation_mm"] for a in plan["backside_bypass_assignments"])
    plan["receiving_repair"] = dict(only_refs=sorted(REFS), delta_native_v_mm=.6,
                                   nominal_TMR_pad_row_v_mm=5., tail_receiving_vmax_mm=6.7,
                                   new_cap_courtyard_vmin_mm=7.25,
                                   intended_gap_mm=.55, required_relative_plus_clearance_mm=.45,
                                   actual_native_3D_cases_required=True)
    (ROOT / "placement.json").write_text(json.dumps(plan, indent=2) + "\n")
    generated = ROOT / "generated"
    generated.mkdir(exist_ok=False)
    assert sha(source) == parent_sha
    (generated / "construction.json").write_text(json.dumps(dict(
        parent_PCB_sha256=parent_sha, output_PCB_sha256=sha(out),
        source_script_sha256=sha(Path(__file__)), exact267_identity_delta={r: dict(before=before[r], after=after[r]) for r in sorted(REFS)},
        all_other263_complete_identities_unchanged=True, component_count=265, mechanical_holes=2,
        copper_layers=6, only_four_cap_v_positions_changed_mm=.6,
        all_pin_value_FPIDs_sides_orientations_unchanged=True,
        same14_named_rear1p9_receiving_requirements=True,
        source_PCB_unchanged=True, native_DRC_required=True,
        physical_qualified=False, PDN_qualified=False, fabrication_released=False), indent=2) + "\n")
    print("New receiving repair: ONLY C4/C5/C31/C32+0.6mmv; all267 identities otherwise exact; no source changes")


if __name__ == "__main__":
    main()
