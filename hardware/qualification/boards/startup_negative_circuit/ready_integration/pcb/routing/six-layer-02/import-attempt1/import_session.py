"""Import a finished private six-layer session without moving components."""

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
    return {f.GetReference(): (f.GetValue(), f.GetFPID().Format(), f.GetPosition().x,
                              f.GetPosition().y, f.GetOrientationDegrees(), f.IsFlipped(),
                              {p.GetNumber(): p.GetNetname() for p in f.Pads() if p.GetNumber()})
            for f in board.GetFootprints()}


def main(work, surface_ground):
    assert work.parent == (ROOT / "routing").resolve()
    provenance = json.loads((work / "input-provenance.json").read_text())
    view = json.loads((work / "routing-view-provenance.json").read_text())
    original, session = work / "input.kicad_pcb", work / "output.ses"
    assert sha(original) == provenance["input_PCB_sha256"]
    assert sha(work / "routing-power-view.dsn") == view["routing_view_DSN_sha256"]
    assert session.is_file() and session.stat().st_size > 0
    name = "output-grounded" if surface_ground else "output"
    output = work / (name + ".kicad_pcb")
    assert not output.exists(), "Preserve all prior imported candidates"
    manager = pcbnew.GetSettingsManager()
    project = work / "input.kicad_pro"
    assert manager.LoadProject(str(project))
    board = pcbnew.LoadBoard(str(original))
    board.SetProject(manager.GetProject(str(project)))
    before = identity(board)
    assert pcbnew.ImportSpecctraSES(board, str(session))
    assert identity(board) == before and len(before) == 233
    assert board.GetCopperLayerCount() == 6
    foreign = []
    undersized = []
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA):
            continue
        if item.GetWidth() < pcbnew.FromMM(.16):
            undersized.append(str(item.m_Uuid))
        if item.GetLayer() in [pcbnew.In1_Cu, pcbnew.In4_Cu]:
            foreign.append(dict(layer=board.GetLayerName(item.GetLayer()), net=item.GetNetname()))
    assert not foreign, ("Dedicated inner planes contain routed tracks", foreign)
    assert not undersized, ("Imported signals below native minimum", undersized)
    if surface_ground:
        for layer in [pcbnew.F_Cu, pcbnew.B_Cu]:
            zone = pcbnew.ZONE(board)
            zone.SetLayer(layer)
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
    pcbnew.SaveBoard(str(output), board)
    shutil.copyfile(project, work / (name + ".kicad_pro"))
    assert identity(pcbnew.LoadBoard(str(output))) == before
    report = dict(scope="Imported connectivity candidate; native DRC and electrical review still required",
                  source_script_sha256=sha(Path(__file__)), input_PCB_sha256=sha(original),
                  session_sha256=sha(session), output_PCB_sha256=sha(output),
                  parts=233, copper_layers=6, all_component_poses_values_sides_FPID_and_pad_nets_preserved=True,
                  tracks_and_vias=len(list(board.GetTracks())), added_surface_ground=surface_ground,
                  tracks_on_dedicated_inner_planes=foreign, tracks_below_native_minimum=undersized,
                  native_DRC_required=True, force_copper_resistance_current_and_noise_qualified=False,
                  actual_six_layer_manufacturing_stack_qualified=False,
                  physical_qualified=False, fabrication_released=False)
    (work / (name + "-import.json")).write_text(json.dumps(report, indent=2) + "\n")
    print("Imported finished233-part session; exact component identity; native DRC required:", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--surface-ground", action="store_true")
    args = parser.parse_args()
    main(args.work.resolve(), args.surface_ground)
