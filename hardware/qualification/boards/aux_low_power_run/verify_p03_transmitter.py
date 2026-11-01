"""Full isolated Linux checks of an integrated P03 AX03 prototype."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pcbnew

from hardware.electronics.common.netlists import netlist
from hardware.electronics.rail_disconnect.revision28 import native_pad_geometry
from hardware.electronics.rail_disconnect.revision28.native_profile import summarize

REPO = Path(__file__).resolve().parents[4]
WORK = REPO / "hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    assert args.label and all(c.isalnum() or c in "-_" for c in args.label)
    candidate = args.candidate.resolve()
    assert candidate.is_relative_to(WORK)
    output = WORK / "generated" / args.label
    output.mkdir(exist_ok=False)
    sources = [WORK / ("power_p03" + suffix) for suffix in (".kicad_sch", ".kicad_pro", ".kicad_dru")]
    sources += [candidate, WORK / "components.json", WORK / "RMX_P03.kicad_sym"]
    sources += sorted((WORK / "RMX_AX03_P03.pretty").glob("*.kicad_mod"))
    before = {str(p): sha(p) for p in sources}
    for p in sources[:3]:
        shutil.copyfile(p, output / p.name)
    shutil.copyfile(candidate, output / "power_p03.kicad_pcb")
    for name in ("sym-lib-table", "fp-lib-table"):
        (output / name).write_text((WORK / name).read_text().replace("${KIPRJMOD}/", "${KIPRJMOD}/../../"))
    project = output / "power_p03.kicad_pro"
    settings = json.loads(project.read_text())
    strict = json.loads((REPO / "hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work/rail_disconnect.kicad_pro").read_text())
    settings["board"]["design_settings"]["rule_severities"] = strict["board"]["design_settings"]["rule_severities"]
    settings["erc"] = strict["erc"]
    project.write_text(json.dumps(settings, indent=2)+"\n")
    commands = []
    for label, options in (
        ("netlist", ["sch", "export", "netlist", "--format", "kicadxml", "-o", str(output/"netlist.xml"), str(output/"power_p03.kicad_sch")]),
        ("erc", ["sch", "erc", "--severity-all", "--format", "json", "-o", str(output/"erc.json"), str(output/"power_p03.kicad_sch")]),
        ("drc", ["pcb", "drc", "--all-track-errors", "--schematic-parity", "--severity-all", "--refill-zones", "--save-board", "--format", "json", "-o", str(output/"drc.json"), str(output/"power_p03.kicad_pcb")]),
    ):
        command = ["kicad-cli", *options]
        p = subprocess.run(command, capture_output=True, text=True, timeout=120)
        (output/(label+".log")).write_text(p.stdout+p.stderr)
        commands.append(dict(command=command, returncode=p.returncode))
        assert p.returncode == 0, (label, p.returncode, p.stdout, p.stderr)
    actual, pins = netlist(output/"netlist.xml")
    declared = json.loads((WORK/"components.json").read_text())
    assert len(actual) == len(declared) == 264
    mismatch = []
    for c in declared:
        if actual[c["ref"]].findtext("value") != c["part"]:
            mismatch.append([c["ref"], "value"])
        for p in c["pins"]:
            value = pins[c["ref"]].get(p["number"])
            if p["net"] is not None and value != p["net"]:
                mismatch.append([c["ref"], p["number"], value, p["net"]])
    assert not mismatch, mismatch
    parent = json.loads((WORK/"generated/integration.json").read_text())
    for c in parent["original_parts"]:
        for p in c["pins"]:
            expected = "POWER_RUN_E28_LEAF" if (c["ref"], p["number"]) == ("J106", "3") else p["net"]
            assert expected is None or pins[c["ref"]][p["number"]] == expected
    assert pins["R113"] == {"1": "V2V5_AUX", "2": "SWITCH_SUPPLY"}
    assert pins["U102"]["3"] == pins["J104"]["2"] == pins["U201"]["1"] == "POWER_RUN"
    assert pins["R403"] == {"1": "AX03_RUN_DRIVE", "2": "POWER_RUN_E28_LEAF"}
    board = pcbnew.LoadBoard(str(output/"power_p03.kicad_pcb"))
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    connection.RecalculateRatsnest()
    missing = connection.GetUnconnectedCount(False)
    drc, erc = [json.loads((output/name).read_text()) for name in ("drc.json", "erc.json")]
    assert len(drc["unconnected_items"]) == min(missing, 499)
    status = summarize(drc, erc)
    native_pad_geometry.LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")
    (output/"pads.json").write_text(json.dumps(native_pad_geometry.export(output/"power_p03.kicad_pcb"), indent=2)+"\n")
    assert all(sha(Path(p)) == digest for p, digest in before.items())
    result = dict(source_sha256=before, native_commands=commands, declared_pin_value_mismatches=mismatch,
        electrical_parts=264, native_footprints=len(list(board.GetFootprints())),
        uncapped_missing_connections=missing, status=status,
        original_R113_and_internal_RUN_PG_topology_preserved=True,
        only_original_pin_net_change="J106.3: POWER_RUN -> POWER_RUN_E28_LEAF",
        checked_PCB_sha256=sha(output/"power_p03.kicad_pcb"), checked_project_sha256=sha(project),
        recipe_sha256=sha(Path(__file__)), all_sources_unchanged=True,
        native_Mac_CAD_launches=0, physical_qualified=False, fabrication_released=False)
    (output/"review.json").write_text(json.dumps(result, indent=2)+"\n")
    print("P03 AX03:", missing, "uncapped opens;", status["counts"], flush=True)


if __name__ == "__main__":
    run()
