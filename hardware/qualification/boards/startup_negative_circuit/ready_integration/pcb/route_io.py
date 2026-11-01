"""Fresh six-layer connectivity experiment; parent four-layer PCB unchanged."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(board):
    return {f.GetReference(): (f.GetValue(), f.GetPosition().x, f.GetPosition().y,
                              f.GetOrientationDegrees(), f.IsFlipped(),
                              {p.GetNumber(): p.GetNetname() for p in f.Pads() if p.GetNumber()})
            for f in board.GetFootprints()}


def main(work):
    assert work.parent == (ROOT / "routing").resolve()
    work.mkdir(parents=True, exist_ok=False)
    original = ROOT / "negative_startup_ready.kicad_pcb"
    project = ROOT / "negative_startup_ready.kicad_pro"
    manager = pcbnew.GetSettingsManager()
    assert manager.LoadProject(str(project))
    board = pcbnew.LoadBoard(str(original))
    board.SetProject(manager.GetProject(str(project)))
    before = identity(board)
    assert len(before) == 233 and not list(board.GetTracks()) and board.GetAreaCount() == 0
    board.SetCopperLayerCount(6)
    for layer, netname in [(pcbnew.In1_Cu, "AGND"), (pcbnew.In4_Cu, "AUX2V6")]:
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(board.FindNet(netname))
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
    assert identity(board) == before
    assert board.GetCopperLayerCount() == 6
    pcbnew.SaveBoard(str(work / "input.kicad_pcb"), board)
    assert pcbnew.ExportSpecctraDSN(board, str(work / "input.dsn"))
    for name in ["input", "output"]:
        shutil.copyfile(project, work / (name + ".kicad_pro"))
    (work / "fp-lib-table").write_text((ROOT / "fp-lib-table").read_text().replace("${KIPRJMOD}/", "${KIPRJMOD}/../../"))
    report = dict(scope="NF04R233 six-layer connectivity trial; not physical stackup acceptance",
                  parent_PCB_sha256=sha(original), exact233_component_poses_values_sides_and_pad_nets_preserved=True,
                  input_PCB_sha256=sha(work / "input.kicad_pcb"), input_DSN_sha256=sha(work / "input.dsn"),
                  source_script_sha256=sha(Path(__file__)), copper_layers=6,
                  planes={"In1.Cu": "AGND", "In4.Cu": "AUX2V6"},
                  routing_layers=["F.Cu", "In2.Cu", "In3.Cu", "B.Cu"],
                  nominal_total_board_thickness_mm=1.6, receiving_total_board_max_mm=1.76,
                  actual_manufacturer_six_layer_stack_Cu_dielectric_and_tolerance_accepted=False,
                  force_copper_voltage_drop_qualified=False, reference_noise_qualified=False,
                  native_DRC_required=True, physical_qualified=False, fabrication_released=False)
    (work / "input-provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Exported233-part six-layer trial, component identity preserved:", work)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    main(args.work.resolve())
