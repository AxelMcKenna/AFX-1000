"""Stage a portable, exact-library project and run isolated strict native checks.

Only explicitly named staging directories are written. Inputs and original
projects stay read-only. A review is not an order or a fabrication release.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.electronics.rail_disconnect.revision28.native_profile import summarize

if sys.platform == "linux":
    import pcbnew

REPO = Path(__file__).resolve().parents[2]
STAGING = REPO/"hardware/fabrication/staging"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-project",type=Path,required=True)
    parser.add_argument("--candidate",type=Path,required=True)
    parser.add_argument("--label",required=True)
    parser.add_argument("--source-schematic",type=Path)
    parser.add_argument("--symbol-table",type=Path)
    args = parser.parse_args()
    assert args.label and all(c.isalnum() or c in "-_" for c in args.label)
    source, candidate = args.source_project.resolve(), args.candidate.resolve()
    assert source.is_relative_to(REPO) and candidate.is_relative_to(STAGING)
    name, parent = source.stem, source.parent
    schematic = (args.source_schematic or parent/(name+".kicad_sch")).resolve()
    symbol_table = (args.symbol_table or parent/"sym-lib-table").resolve()
    assert schematic.is_relative_to(REPO) and symbol_table.is_relative_to(REPO)
    assert schematic.name == name+".kicad_sch"
    output = STAGING/args.label
    output.mkdir(exist_ok=False)
    driver = output/"applied-native-review.py.txt"
    shutil.copyfile(Path(__file__),driver)
    inputs = [source,schematic,parent/"fp-lib-table",symbol_table,candidate]
    dru = parent/(name+".kicad_dru")
    if dru.exists():
        inputs.append(dru)
    hashes = {str(p):sha(p) for p in inputs}
    for p in inputs:
        if p.suffix in (".kicad_pro",".kicad_sch",".kicad_dru"):
            shutil.copyfile(p,output/p.name)
    pcb = output/(name+".kicad_pcb")
    shutil.copyfile(candidate,pcb)
    tree = read_sexpr(pcb.read_text())
    used = {str(f[1]) for f in children(tree,"footprint")}
    libraries = output/"libraries"
    libraries.mkdir()
    library_files = {}
    for table_name in ("fp-lib-table","sym-lib-table"):
        table_path = symbol_table if table_name == "sym-lib-table" else parent/table_name
        table = read_sexpr(table_path.read_text())
        for library in children(table,"lib"):
            nickname = str(first(library,"name")[1])
            uri = str(first(library,"uri")[1]).replace("${KIPRJMOD}",str(table_path.parent))
            uri = uri.replace("${KICAD10_FOOTPRINT_DIR}",os.environ["KICAD10_FOOTPRINT_DIR"])
            uri = uri.replace("${KICAD10_SYMBOL_DIR}","/usr/share/kicad/symbols")
            original = Path(uri).resolve()
            assert original.is_relative_to(REPO) or original.is_relative_to(Path("/usr/share/kicad")), original
            destination = libraries/original.name
            if table_name == "fp-lib-table":
                destination.mkdir(exist_ok=True)
                files = [original/(item.split(":",1)[1]+".kicad_mod") for item in sorted(used) if item.startswith(nickname+":")]
                for p in files:
                    assert p.is_file(),p
                    library_files[str(p)] = sha(p)
                    shutil.copyfile(p,destination/p.name)
            else:
                assert original.is_file(),original
                library_files[str(original)] = sha(original)
                shutil.copyfile(original,destination)
            first(library,"uri")[1] = "${KIPRJMOD}/libraries/"+original.name
        (output/table_name).write_text(sexpr(table)+"\n")
    project = output/source.name
    settings = json.loads(project.read_text())
    rules = dict(settings["board"]["design_settings"]["rules"])
    drc_profile = settings["board"]["design_settings"].setdefault("rule_severities",{})
    erc_profile = settings.setdefault("erc",{}).setdefault("rule_severities",{})
    promoted = []
    for severity,keys in ((drc_profile,("missing_courtyard","track_not_centered_on_via","tuning_profile_track_geometries","footprint_filters_mismatch","footprint_type_mismatch")),
                          (erc_profile,("single_global_label","four_way_junction","simulation_model_issue","footprint_filter"))):
        for key in keys:
            if severity.get(key) != "error":
                promoted.append(dict(rule=key,before=severity.get(key,"native_default"),after="error"))
            severity[key] = "error"
    assert rules == settings["board"]["design_settings"]["rules"]
    project.write_text(json.dumps(settings,indent=2)+"\n")
    commands = []
    for label,options in (
        ("netlist",["sch","export","netlist","--format","kicadxml","-o",str(output/"netlist.xml"),str(output/(name+".kicad_sch"))]),
        ("erc",["sch","erc","--severity-all","--format","json","-o",str(output/"erc.json"),str(output/(name+".kicad_sch"))]),
        ("drc",["pcb","drc","--all-track-errors","--schematic-parity","--severity-all","--refill-zones","--save-board","--format","json","-o",str(output/"drc.json"),str(pcb)]),
    ):
        p = subprocess.run(["kicad-cli",*options],capture_output=True,text=True,timeout=120)
        (output/(label+".log")).write_text(p.stdout+p.stderr)
        commands.append(dict(command=["kicad-cli",*options],returncode=p.returncode))
        assert p.returncode == 0,(label,p.stdout,p.stderr)
    actual,pins = netlist(output/"netlist.xml")
    baseline = parent/"netlist.xml"
    parity = None
    if baseline.is_file():
        old,old_pins = netlist(baseline)
        parity = (pins == old_pins and set(old) == set(actual) and all(
            old[r].findtext("value") == actual[r].findtext("value") and
            old[r].findtext("footprint") == actual[r].findtext("footprint") for r in old))
        assert parity,"Circuit differs from paired baseline export"
        hashes[str(baseline)] = sha(baseline)
    board = pcbnew.LoadBoard(str(pcb))
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    connection.RecalculateRatsnest()
    missing = connection.GetUnconnectedCount(False)
    drc,erc = [json.loads((output/p).read_text()) for p in ("drc.json","erc.json")]
    assert len(drc["unconnected_items"]) == min(499,missing)
    status = summarize(drc,erc)
    assert all(sha(Path(p)) == digest for p,digest in {**hashes,**library_files}.items())
    record = dict(source_sha256=hashes,captured_library_source_sha256=library_files,
        copied_used_library_files_only=True,complete_native_commands=commands,electrical_parts=len(actual),
        uncapped_open_connections=missing,status=status,baseline_circuit_pin_value_footprint_parity=parity,
        geometry_rule_values_unchanged=True,rule_severities_promoted=promoted,
        source_projects_unchanged=True,checked_PCB_sha256=sha(pcb),checked_project_sha256=sha(project),
        checked_schematic_sha256=sha(output/(name+".kicad_sch")),
        raw_report_sha256={p.name:sha(p) for p in (output/"drc.json",output/"erc.json",output/"netlist.xml")},
        captured_project_library_sha256={str(p.relative_to(output)):sha(p) for p in libraries.rglob("*") if p.is_file()},
        captured_library_table_sha256={p.name:sha(p) for p in (output/"fp-lib-table",output/"sym-lib-table")},
        applied_driver_sha256=sha(driver),native_version=pcbnew.GetBuildVersion(),
        native_Mac_CAD_launches=0,physical_qualified=False,fabrication_released=False)
    (output/"review.json").write_text(json.dumps(record,indent=2)+"\n")
    print("Strict native review:",status["counts"],"uncapped opens",missing,"all checks enabled",status["all_native_rule_checks_enabled"])


if __name__ == "__main__":
    run()
