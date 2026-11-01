"""Private Specctra round trip for an unrated NF03 connectivity proposal."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import pcbnew

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "routing/initial-connectivity"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export():
    WORK.mkdir(parents=True, exist_ok=True)
    target = WORK / "input.dsn"
    assert not target.exists(), "Preserve router inputs; use a new candidate directory"
    project_path = ROOT / "negative_startup_placement.kicad_pro"
    manager = pcbnew.GetSettingsManager()
    assert manager.LoadProject(str(project_path))
    board = pcbnew.LoadBoard(str(ROOT / "negative_startup_placement.kicad_pcb"))
    board.SetProject(manager.GetProject(str(project_path)))
    zone = pcbnew.ZONE(board)
    zone.SetLayer(pcbnew.In1_Cu)
    zone.SetNet(board.FindNet("AGND"))
    zone.SetLocalClearance(pcbnew.FromMM(.2))
    zone.SetMinThickness(pcbnew.FromMM(.2))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetThermalReliefGap(pcbnew.FromMM(.25))
    zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(.3))
    polygon = zone.Outline()
    polygon.NewOutline()
    for x, y in [(.5, .5), (148.5, .5), (148.5, 38.5), (.5, 38.5)]:
        polygon.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(zone)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(WORK / "input.kicad_pcb"), board)
    assert pcbnew.ExportSpecctraDSN(board, str(target))
    for name in ["input", "output"]:
        shutil.copyfile(project_path, WORK / (name + ".kicad_pro"))
    table = (ROOT / "fp-lib-table").read_text().replace("${KIPRJMOD}/", "${KIPRJMOD}/../../")
    (WORK / "fp-lib-table").write_text(table)
    report = dict(
        scope="Initial connectivity experiment, not force/quiet-ground/startup acceptance",
        placement_pcb_sha256=sha(ROOT / "negative_startup_placement.kicad_pcb"),
        input_pcb_sha256=sha(WORK / "input.kicad_pcb"), input_dsn_sha256=sha(target),
        initial_ground_plane="In1.Cu AGND; other three layers available to routing",
        force_copper_voltage_drop_qualified=False, reference_noise_qualified=False,
        whole_unit_fit_verified=False, physical_qualified=False, fabrication_released=False,
    )
    (WORK / "input-provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Exported private connectivity proposal", target)


def import_session():
    original = WORK / "input.kicad_pcb"
    session = WORK / "output.ses"
    assert session.is_file()
    board = pcbnew.LoadBoard(str(original))
    before = {f.GetReference(): (f.GetValue(), f.GetPosition().x, f.GetPosition().y,
                               f.GetOrientationDegrees(), f.IsFlipped(),
                               {p.GetNumber(): p.GetNetname() for p in f.Pads() if p.GetNumber()})
              for f in board.GetFootprints()}
    assert pcbnew.ImportSpecctraSES(board, str(session))
    after = {f.GetReference(): (f.GetValue(), f.GetPosition().x, f.GetPosition().y,
                              f.GetOrientationDegrees(), f.IsFlipped(),
                              {p.GetNumber(): p.GetNetname() for p in f.Pads() if p.GetNumber()})
             for f in board.GetFootprints()}
    assert before == after, "Router changed component pose/value/pin mapping"
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    result = WORK / "output.kicad_pcb"
    pcbnew.SaveBoard(str(result), board)
    report = dict(
        source_pcb_sha256=sha(original), session_sha256=sha(session), output_pcb_sha256=sha(result),
        exact_component_pose_value_and_pin_maps_preserved=True,
        tracks_and_vias=len(list(board.GetTracks())), native_DRC_required=True,
        force_copper_voltage_drop_qualified=False, physical_qualified=False, fabrication_released=False,
    )
    (WORK / "import-provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Imported routing experiment; native DRC and electrical review required")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["export", "import"])
    parser.add_argument("--work", type=Path, default=WORK)
    args = parser.parse_args()
    WORK = args.work.resolve()
    assert WORK.parent == (ROOT / "routing").resolve()
    export() if args.stage == "export" else import_session()
