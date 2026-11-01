"""Add real all-copper-layer edge-clip keepouts; retain every component pose."""

import hashlib
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (ROOT / "handoff.json").exists()
    source = ROOT / "sources/parent-fan_power_health.kicad_pcb"
    manifest = json.loads((ROOT / "sources/parent-manifest.json").read_text())
    assert sha(source) == manifest["captured_input_sha256"][source.name]
    output = ROOT / "fan_power_health.kicad_pcb"
    assert not output.exists(), "Preserve prior candidates"
    manager = pcbnew.GetSettingsManager()
    project = ROOT / "fan_power_health.kicad_pro"
    assert manager.LoadProject(str(project))
    board = pcbnew.LoadBoard(str(source))
    board.SetProject(manager.GetProject(str(project)))
    before = {f.GetReference(): f.GetPosition() for f in board.GetFootprints()}
    layers = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
    assert board.GetCopperLayerCount() == len(layers)
    areas = []
    for center in [17., 54.5]:
        for edge, y0, y1 in [("BOTTOM", 0., 1.65), ("TOP", 36.35, 38.)]:
            box = [center - 3.6, y0, center + 3.6, y1]
            for layer in layers:
                zone = pcbnew.ZONE(board)
                zone.SetLayer(layer)
                zone.SetIsRuleArea(True)
                zone.SetZoneName("MOUNT_CLIP_" + str(center) + "_" + edge + "_" + board.GetLayerName(layer))
                zone.SetDoNotAllowTracks(True)
                zone.SetDoNotAllowVias(True)
                zone.SetDoNotAllowZoneFills(True)
                zone.SetDoNotAllowPads(True)
                zone.SetDoNotAllowFootprints(False)
                polygon = zone.Outline()
                polygon.NewOutline()
                for x, y in [(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])]:
                    polygon.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
                board.Add(zone)
                areas.append(dict(name=zone.GetZoneName(), layer=board.GetLayerName(layer), box_mm=box))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    assert all(f.GetPosition() == before[f.GetReference()] for f in board.GetFootprints())
    pcbnew.SaveBoard(str(output), board)
    report = dict(scope="Real PCB edge-contact keepout successor; not clip material/structural qualification",
                  parent_pcb_sha256=sha(source), output_pcb_sha256=sha(output), source_script_sha256=sha(Path(__file__)),
                  added_all_layer_keepout_records=areas, component_count=len(before), all84_component_poses_preserved=True,
                  clip_contact_width_mm=6., keepout_width_mm=7.2, keepout_width_factor=1.2,
                  contact_depth_mm=1.2, keepout_depth_mm=1.65,
                  rear_SMD_complete_height_receiving_mm=1.2, rear_THT_tail_plus_fillet_receiving_mm=1.5,
                  mounting_polymer_interface_and_process_selected=False, soldermask_as_clip_insulation_credited=False,
                  native_DRC_required=True, physical_qualified=False, fabrication_released=False)
    (ROOT / "construction.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Added16realall-layerclipkeepouts; all84componentposespreserved; nativeDRCrequired")


if __name__ == "__main__":
    main()
