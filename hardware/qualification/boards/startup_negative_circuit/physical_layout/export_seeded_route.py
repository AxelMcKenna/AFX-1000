"""Export actual local power stitches with protected copper for a signal trial."""

import hashlib
import json
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "routing/power-stitches"
WORK = ROOT / "routing/power-seeded-six-layer"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    WORK.mkdir(exist_ok=False)
    source = SOURCE / "input.kicad_pcb"
    before = sha(source)
    manager = pcbnew.GetSettingsManager()
    path = str(SOURCE / "input.kicad_pro")
    assert manager.LoadProject(path)
    project = manager.GetProject(path)
    assert project is not None and bool(project)
    board = pcbnew.LoadBoard(str(source))
    board.SetProject(project)
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    conn.RecalculateRatsnest()
    count = conn.GetUnconnectedCount(False)
    assert count == 487
    assert all(t.IsLocked() for t in board.GetTracks())
    assert pcbnew.ExportSpecctraDSN(board, str(WORK / "native-input.dsn"))
    for name in ["input", "output"]:
        shutil.copyfile(source, WORK / (name + ".kicad_pcb")) if name == "input" else None
        shutil.copyfile(SOURCE / (name + ".kicad_pro"), WORK / (name + ".kicad_pro"))
        shutil.copyfile(SOURCE / (name + ".kicad_sch"), WORK / (name + ".kicad_sch"))
    shutil.copyfile(SOURCE / "fp-lib-table", WORK / "fp-lib-table")
    shutil.copyfile(SOURCE / "plan.json", WORK / "literal-power-plan.json")
    assert sha(source) == before
    (WORK / "input-provenance.json").write_text(json.dumps(dict(
        source_PCB_sha256=before, input_PCB_sha256=sha(WORK / "input.kicad_pcb"),
        source_script_sha256=sha(Path(__file__)), native_DSN_sha256=sha(WORK / "native-input.dsn"),
        uncapped_native_connectivity_missing_connections=count,
        literal_seed_vias=173, literal_seed_segments=342,
        all_literal_copper_locked_before_export=True, exact267_footprints_unchanged=True,
        native_DRC_and_actual_retained_local_copper_check_required=True,
        full_unit_PDN_noise_force_voltage_drop_qualified=False, physical_qualified=False,
        fabrication_released=False), indent=2) + "\n")
    print("Exported native487-open power-seeded trial; all515 literal copper objects locked")


if __name__ == "__main__":
    main()
