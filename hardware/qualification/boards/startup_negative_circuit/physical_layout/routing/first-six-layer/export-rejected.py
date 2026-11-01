"""Export a new immutable six-layer connectivity trial using actual rules."""

import faulthandler
import hashlib
import json
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    faulthandler.enable()
    work = ROOT / "routing/first-six-layer"
    work.mkdir(parents=True, exist_ok=False)
    source = ROOT / "negative_startup_physical.kicad_pcb"
    project_path = ROOT / "negative_startup_physical.kicad_pro"
    source_sha = sha(source)
    manager = pcbnew.GetSettingsManager()
    assert manager.LoadProject(str(project_path)), "Never attach an unloaded PROJECT"
    project = manager.GetProject(str(project_path))
    assert project is not None and bool(project.this), "Never attach a null PROJECT"
    board = pcbnew.LoadBoard(str(source))
    assert board is not None and len(list(board.GetFootprints())) == 267
    # Both owning manager and actual project stay strongly referenced throughout
    # the export. No GUI is initialized; no footprint is flipped or mutated.
    board.SetProject(project)
    assert board.GetProject() is not None
    assert pcbnew.ExportSpecctraDSN(board, str(work / "native-input.dsn"))
    assert sha(source) == source_sha
    shutil.copyfile(source, work / "input.kicad_pcb")
    for name in ["input", "output"]:
        shutil.copyfile(project_path, work / (name + ".kicad_pro"))
        shutil.copyfile(ROOT / "negative_startup_physical.kicad_sch", work / (name + ".kicad_sch"))
    (work / "fp-lib-table").write_text((ROOT / "fp-lib-table").read_text().replace("${KIPRJMOD}/", "${KIPRJMOD}/../../"))
    report = dict(scope="NF06P265 six-layer connectivity trial; default traces do not qualify force/Kelvin/PDN",
                  input_PCB_sha256=sha(work / "input.kicad_pcb"),
                  input_DSN_sha256=sha(work / "native-input.dsn"),
                  source_script_sha256=sha(Path(__file__)),
                  input_project_sha256=sha(work / "input.kicad_pro"),
                  input_schematic_sha256=sha(work / "input.kicad_sch"),
                  native_source_PCB_unchanged=True, parts=265, additional_mechanical_footprints=2,
                  routing_layers=["F.Cu", "In2.Cu", "In3.Cu", "B.Cu"],
                  reserved_planes={"In1.Cu": "/AGND", "In4.Cu": "/AUX2V6"},
                  stackup_and_force_current_voltage_drop_qualified=False,
                  physical_qualified=False, fabrication_released=False)
    (work / "input-provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Exported exact267-footprint source; strongly owned loaded project; original PCB unchanged")


if __name__ == "__main__":
    main()
