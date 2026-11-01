"""Export the native-clean receiving candidate for a bounded routing continuation."""

import hashlib
import json
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "receiving-detour"
WORK = ROOT / "receiving-continuation-01"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    WORK.mkdir(exist_ok=False)
    source = SOURCE / "output.kicad_pcb"
    before = sha(source)
    manager = pcbnew.GetSettingsManager()
    project_path = str(SOURCE / "output.kicad_pro")
    assert manager.LoadProject(project_path)
    project = manager.GetProject(project_path)
    assert project is not None and bool(project)
    b = pcbnew.LoadBoard(str(source))
    b.SetProject(project)
    assert len(list(b.GetFootprints())) == 267
    b.BuildConnectivity()
    c = b.GetConnectivity()
    c.RecalculateRatsnest()
    assert c.GetUnconnectedCount(False) == 241
    assert pcbnew.ExportSpecctraDSN(b, str(WORK / "native-input.dsn"))
    native = (WORK / "native-input.dsn").read_text()
    modified = native
    for name in ["In1.Cu", "In4.Cu"]:
        needle = f"(layer {name}\n      (type signal)"
        assert modified.count(needle) == 1
        modified = modified.replace(needle, f"(layer {name}\n      (type power)")
    (WORK / "routing-view.dsn").write_text(modified)
    shutil.copyfile(source, WORK / "input.kicad_pcb")
    for name in ["input", "output"]:
        shutil.copyfile(SOURCE / "output.kicad_pro", WORK / (name + ".kicad_pro"))
        shutil.copyfile(SOURCE / "output.kicad_sch", WORK / (name + ".kicad_sch"))
    shutil.copyfile(SOURCE / "fp-lib-table", WORK / "fp-lib-table")
    assert sha(source) == before
    (WORK / "input-provenance.json").write_text(json.dumps(dict(
        input_PCB_sha256=before, source_script_sha256=sha(Path(__file__)),
        native_DSN_sha256=sha(WORK / "native-input.dsn"),
        routing_view_sha256=sha(WORK / "routing-view.dsn"),
        only_DSN_adapter_change_In1_In4_types_signal_to_power=True,
        uncapped_native_input_missing_connections=241,
        literal_protected_seed_geometry_not_relaxed=True,
        router_204_fixed_clearance_findings_remain_unresolved=True,
        native_output_DRC_and_seed_pose_receipt_required=True,
        physical_qualified=False, fabrication_released=False), indent=2) + "\n")


if __name__ == "__main__":
    main()
