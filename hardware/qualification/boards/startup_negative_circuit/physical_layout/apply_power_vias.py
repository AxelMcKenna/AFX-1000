"""Apply a NEW literal local-via candidate; canonical placement is read-only."""

import hashlib
import json
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "routing/power-stitches"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def xy(values):
    return pcbnew.VECTOR2I(*(pcbnew.FromMM(v) for v in values))


def main():
    source = ROOT / "negative_startup_physical.kicad_pcb"
    plan = json.loads((WORK / "plan.json").read_text())
    assert sha(source) == plan["source_PCB_sha256"]
    output = WORK / "input.kicad_pcb"
    assert not output.exists()
    b = pcbnew.LoadBoard(str(source))
    before = {f.GetReference(): (f.GetPosition().x, f.GetPosition().y, f.GetValue(), str(f.GetFPIDAsString()),
                                f.GetOrientationDegrees(), f.IsFlipped()) for f in b.GetFootprints()}
    assert len(before) == 267 and not list(b.GetTracks())
    objects = []
    for v in plan["vias"]:
        via = pcbnew.PCB_VIA(b)
        via.SetPosition(xy(v["at_mm"]))
        via.SetWidth(pcbnew.FromMM(v["diameter_mm"]))
        via.SetDrill(pcbnew.FromMM(v["drill_mm"]))
        via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetNet(b.FindNet(v["net"]))
        via.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED)
        via.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
        via.SetLocked(True)
        b.Add(via)
        objects.append(via)
    for s in plan["segments"]:
        line = pcbnew.PCB_TRACK(b)
        line.SetStart(xy(s["start_mm"]))
        line.SetEnd(xy(s["end_mm"]))
        line.SetWidth(pcbnew.FromMM(s["width_mm"]))
        line.SetLayer(b.GetLayerID(s["layer"]))
        line.SetNet(b.FindNet(s["net"]))
        line.SetLocked(True)
        b.Add(line)
        objects.append(line)
    after = {f.GetReference(): (f.GetPosition().x, f.GetPosition().y, f.GetValue(), str(f.GetFPIDAsString()),
                               f.GetOrientationDegrees(), f.IsFlipped()) for f in b.GetFootprints()}
    assert before == after
    pcbnew.SaveBoard(str(output), b)
    for name in ["input", "output"]:
        shutil.copyfile(ROOT / "negative_startup_physical.kicad_pro", WORK / (name + ".kicad_pro"))
        shutil.copyfile(ROOT / "negative_startup_physical.kicad_sch", WORK / (name + ".kicad_sch"))
    (WORK / "fp-lib-table").write_text((ROOT / "fp-lib-table").read_text().replace("${KIPRJMOD}/", "${KIPRJMOD}/../../"))
    assert sha(source) == plan["source_PCB_sha256"]
    (WORK / "construction.json").write_text(json.dumps(dict(
        source_PCB_sha256=sha(source), source_plan_sha256=sha(WORK / "plan.json"),
        source_script_sha256=sha(Path(__file__)), actual_output_PCB_sha256=sha(output),
        actual_new_objects=len(objects), exact267_component_poses_values_FPIDs_sides_preserved=True,
        local_copper_locked_for_connectivity_trial=True, native_DRC_and_connectivity_required=True,
        physical_qualified=False, PDN_qualified=False, fabrication_released=False), indent=2) + "\n")
    print("New candidate only:", len(plan["vias"]), "literal vias,", len(plan["segments"]), "segments; parent untouched")


if __name__ == "__main__":
    main()
