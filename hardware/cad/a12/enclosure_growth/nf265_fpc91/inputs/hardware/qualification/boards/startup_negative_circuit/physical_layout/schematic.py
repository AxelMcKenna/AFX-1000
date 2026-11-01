"""Pair the new physical footprint IDs with the captured NF05R circuit."""

import copy
import json
import os
import subprocess

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.netlists import netlist

from .capture import ROOT, sha


def main():
    assert not (ROOT / "handoff.json").exists()
    assert not (ROOT / "negative_startup_physical.kicad_sch").exists()
    rows = json.loads((ROOT / "land-inventory.json").read_text())["rows"]
    by = {r["ref"]: r for r in rows}
    parts = copy.deepcopy(json.loads((ROOT / "sources/NF05R/components.json").read_text()))
    for c in parts:
        c["footprint"] = by[c["ref"]]["proposed_footprint"]
        path = ROOT / "NF06P.pretty" / (c["footprint"].split(":")[1] + ".kicad_mod")
        assert sha(path) == by[c["ref"]]["library_sha256"], c["ref"]
        c["note"] = c.get("note", "") + " NF06P physical-land proposal only; complete tolerance, process and assembly acceptance remains false."
    generate(ROOT, "NF06P", "negative_startup_physical", parts,
             [(20, 45, "NF06P: captured265-part NF05R circuit with explicit physical-land/connector proposals."),
              (20, 55, "Actual primitive/MPN heights, complete tolerances, routing, return coupling and installed assembly require fresh review."),
              (20, 65, "Prototype only; physical/partial-power/faultenergy/fabrication acceptance FALSE.")],
             (1100, 4550),
             [(name, x, 20.32) for name, x in [
                 ("AGND", 20.32), ("GUARDED_12V_FORCE", 91.44), ("DIG5_FORCE", 172.72),
                 ("AUX2V6", 254), ("N19_P03_SRC", 330.2), ("N12_P03_SRC", 411.48),
                 ("N19_VIN", 490.22), ("N12_VIN", 568.96), ("MODULE_INPUT_GND", 650.24)]])
    (ROOT / "fp-lib-table").write_text('(fp_lib_table (version 7) (lib (name "NF06P") (type "KiCad") (uri "${KIPRJMOD}/NF06P.pretty") (options "") (descr "Explicit captured/proposed physical lands; unaccepted process")))\n')
    rules = dict(min_clearance=.16, min_track_width=.16, min_copper_edge_clearance=.5,
                 min_hole_clearance=.25, min_through_hole_diameter=.3, min_via_annular_width=.1)
    severities = {name: "error" for name in ["missing_courtyard", "track_not_centered_on_via",
                  "tuning_profile_track_geometries", "footprint_filters_mismatch", "footprint_type_mismatch"]}
    project = dict(meta=dict(filename="negative_startup_physical.kicad_pro", version=1),
                   board=dict(design_settings=dict(rules=rules, rule_severities=severities)),
                   net_settings=dict(classes=[dict(name="Default", clearance=.2, track_width=.2,
                                                    via_diameter=.65, via_drill=.3)]))
    (ROOT / "negative_startup_physical.kicad_pro").write_text(json.dumps(project, indent=2) + "\n")
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    cli = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    env = dict(os.environ, KICAD_CONFIG_HOME="/private/tmp/afx-nf06p-native")
    commands = []
    for label, args in [
        ("netlist", ["sch", "export", "netlist", "--format", "kicadxml", "--output", str(out / "netlist.xml"), str(ROOT / "negative_startup_physical.kicad_sch")]),
        ("erc", ["sch", "erc", "--format", "json", "--output", str(out / "erc.json"), str(ROOT / "negative_startup_physical.kicad_sch")]),
    ]:
        run = subprocess.run([cli, *args], capture_output=True, text=True, env=env, timeout=120)
        (out / (label + ".log")).write_text(run.stdout + run.stderr)
        commands.append(dict(label=label, command=[cli, *args], returncode=run.returncode))
        assert run.returncode == 0, (label, run.stdout, run.stderr)
    actual, pins = netlist(out / "netlist.xml")
    assert len(actual) == 265
    for c in parts:
        assert actual[c["ref"]].findtext("value") == c["part"]
        assert actual[c["ref"]].findtext("footprint") == c["footprint"]
        for p in c["pins"]:
            name = pins[c["ref"]][p["number"]]
            assert name == p["net"] if p["net"] is not None else name.startswith("unconnected-")
    issues = [v for s in json.loads((out / "erc.json").read_text())["sheets"] for v in s["violations"]]
    assert len(issues) == 2 and all(v["severity"] == "warning" and v["type"] == "ground_pin_not_ground" for v in issues), issues
    assert {v["items"][0]["description"].split()[1] for v in issues} == {"U19", "U24"}
    (out / "schematic-check.json").write_text(json.dumps(dict(
        commands=commands, exact_captured265_pin_value_differences=0, physical_footprint_ids_synchronized=True,
        ERC_errors=0, ERC_warnings=2, warnings=issues, PCB_native_parity_required=True,
        source_script_sha256=sha(ROOT / "schematic.py"), physical_qualified=False), indent=2) + "\n")
    print("NF06P265 schematic: exact original pin/value contracts, synchronized physical footprint IDs; ERC0+two inherited warnings")


if __name__ == "__main__":
    main()
