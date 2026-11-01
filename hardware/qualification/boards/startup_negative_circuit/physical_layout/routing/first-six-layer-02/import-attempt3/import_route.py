"""Import one connectivity trial; enforce actual poses, pads and copper limits."""

import faulthandler
import hashlib
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "routing/first-six-layer-02"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(board):
    return {f.GetReference(): dict(value=f.GetValue(), footprint=str(f.GetFPIDAsString()),
                                  x=f.GetPosition().x, y=f.GetPosition().y,
                                  angle=f.GetOrientationDegrees(), flipped=f.IsFlipped(),
                                  pads={p.GetNumber(): p.GetNetname() for p in f.Pads() if p.GetNumber()})
            for f in board.GetFootprints()}


def main():
    faulthandler.enable()
    output = WORK / "output.kicad_pcb"
    assert not output.exists(), "Never overwrite a reviewed or rejected import"
    provenance = json.loads((WORK / "input-provenance.json").read_text())
    source = WORK / "input.kicad_pcb"
    assert sha(source) == provenance["input_PCB_sha256"]
    manager = pcbnew.GetSettingsManager()
    path = str(WORK / "input.kicad_pro")
    assert manager.LoadProject(path)
    project = manager.GetProject(path)
    assert project is not None and bool(project)
    board = pcbnew.LoadBoard(str(source))
    board.SetProject(project)
    before = identity(board)
    assert len(before) == 267
    session = WORK / "adapted-output.ses"
    assert session.is_file() and pcbnew.ImportSpecctraSES(board, str(session))
    after = identity(board)
    assert before.keys() == after.keys()
    quantization = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        old, new = dict(before[ref]), dict(after[ref])
        dx, dy = new.pop("x") - old.pop("x"), new.pop("y") - old.pop("y")
        # An equivalent360-degree representation carries no physical move.
        da = (new.pop("angle") - old.pop("angle") + 180) % 360 - 180
        assert old == new and abs(da) < 1e-9, (ref, old, new, da)
        # Specctra resolution um10 is a100nm position lattice. The analog
        # centroid planner has native1nm coordinates: rounding can differ by
        # at most50nm plus1nm serialization. Every such position is restored
        # EXACTLY, not accepted as a physical component move.
        assert abs(dx) <= 51 and abs(dy) <= 51, (ref, dx, dy)
        if dx or dy:
            quantization.append(dict(ref=ref, dX_nm=dx, dY_nm=dy))
            fp.SetPosition(pcbnew.VECTOR2I(before[ref]["x"], before[ref]["y"]))
    widths = {}
    vias = 0
    for track in board.GetTracks():
        if isinstance(track, pcbnew.PCB_VIA):
            assert track.GetDrill() >= pcbnew.FromMM(.3)
            assert track.GetWidth(pcbnew.F_Cu) >= pcbnew.FromMM(.65)
            track.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED)
            track.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
            vias += 1
        else:
            assert track.GetLayer() not in [pcbnew.In1_Cu, pcbnew.In4_Cu], "Signal on reserved plane"
            width = track.GetWidth()
            widths[width] = widths.get(width, 0) + 1
            assert width >= pcbnew.FromMM(.2), (width, "Unexpected neckdown")
    assert identity(board) == before
    pcbnew.SaveBoard(str(output), board)
    assert sha(source) == provenance["input_PCB_sha256"]
    report = dict(source_PCB_sha256=sha(source), session_sha256=sha(session),
                  original_router_session_sha256=sha(WORK / "output.ses"),
                  one_empty_mechanical_component_ID_quote_restored=True,
                  output_PCB_sha256=sha(output), source_script_sha256=sha(Path(__file__)),
                  all267_exact_poses_values_sides_FPIDs_and_actual_pad_nets_preserved=True,
                  DSN_position_lattice_nm=100,
                  maximum_position_quantization_before_exact_restoration_nm=51,
                  restored_DSN_position_rounding=quantization,
                  track_widths_nm=widths, vias=vias, all_imported_vias_front_back_tented=True,
                  reserved_In1_In4_signal_tracks=0, full_native_DRC_and_parity_required=True,
                  routing_complete=False, force_Kelvin_voltage_drop_qualified=False,
                  PDN_noise_physical_or_fabrication_qualified=False)
    (WORK / "import.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Imported connectivity trial:", sum(widths.values()), "tracks,", vias,
          "vias; all267 exact identities restored; native DRC/connectivity required")


if __name__ == "__main__":
    main()
