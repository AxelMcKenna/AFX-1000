"""Read-only strict native checks and immutable handoff for FPC01-M1."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import read_sexpr

from .validate import ROOT, validate

REPO = Path(__file__).resolve().parents[5]
PARENT = ROOT.parent / "composite"
FR = REPO / "hardware/cad/a12/enclosure_growth/front_bay_receiving"
CLI = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
PY39 = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_seal(root):
    handoff = json.loads((root / "handoff.json").read_text())
    for name, expected in handoff["files_sha256"].items():
        assert sha(root / name) == expected, (root, name)
    return len(handoff["files_sha256"])


def selected_inputs():
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(ROOT.rglob("*"))
            if p.is_file() and not any(s in p.parts for s in ("__pycache__", "generated"))
            and not p.name.endswith((".lck", ".kicad_prl"))
            and p.name not in ("handoff.json", "native-reference-check.json")}


def main():
    assert not (ROOT / "handoff.json").exists(), "Sealed packets are read-only"
    out = ROOT / "generated"
    out.mkdir(exist_ok=False)
    before = selected_inputs()
    parent_count = verify_seal(PARENT)
    fr_count = verify_seal(FR)
    manifest = json.loads((ROOT / "sources/parent-manifest.json").read_text())
    assert sha(PARENT / "handoff.json") == manifest["parent_handoff_sha256"]
    for name, digest in manifest["captured_input_sha256"].items():
        assert sha(ROOT / "sources" / name) == digest, name
    env = dict(os.environ, KICAD_CONFIG_HOME="/private/tmp/afx-fpc-mount-final",
               FONTCONFIG_FILE=str(REPO / "build-hardware/kicad-fonts.conf"))
    commands = []

    def run(args, label):
        p = subprocess.run(args, text=True, capture_output=True, env=env, cwd=REPO, timeout=180)
        (out / (label + ".log")).write_text(p.stdout + p.stderr)
        commands.append(dict(command=args, returncode=p.returncode))
        assert p.returncode == 0, (label, p.stdout, p.stderr)

    sch = str(ROOT / "fan_power_health.kicad_sch")
    pcb = str(ROOT / "fan_power_health.kicad_pcb")
    run([CLI, "--version"], "version")
    run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "--output", str(out / "netlist.xml"), sch], "netlist")
    run([CLI, "sch", "erc", "--format", "json", "--output", str(out / "erc.json"), sch], "erc")
    run([CLI, "pcb", "drc", "--format", "json", "--all-track-errors", "--schematic-parity", "--severity-all", "--refill-zones", "--exit-code-violations", "--output", str(out / "drc.json"), pcb], "drc")
    run([sys.executable, "-m", "hardware.qualification.boards.fan_health.composite_mount.test_mount"], "portable")
    run([PY39, str(ROOT / "native_measure.py")], "native-reference")
    invariant = validate(read_sexpr(Path(pcb).read_text()))
    parts = json.loads((ROOT / "components.json").read_text())
    actual, pins = netlist(out / "netlist.xml")
    nc = []
    for c in parts:
        for p in c["pins"]:
            if p["net"] is None:
                value = pins[c["ref"]].pop(p["number"])
                assert value.startswith("unconnected-("), value
                nc.append([c["ref"], p["number"], value])
    expected = {c["ref"]: {p["number"]: p["net"] for p in c["pins"] if p["net"] is not None} for c in parts}
    assert pins == expected and set(actual) == set(expected) and len(actual) == 84
    for c in parts:
        assert actual[c["ref"]].findtext("value") == c["part"]
        assert actual[c["ref"]].findtext("footprint") == c["footprint"]
    drc = json.loads((out / "drc.json").read_text())
    assert all(not drc[k] for k in ("violations", "unconnected_items", "schematic_parity", "ignored_checks"))
    erc = json.loads((out / "erc.json").read_text())
    assert not [v for s in erc["sheets"] for v in s["violations"]]
    assert selected_inputs() == before, "Package inputs changed during native/portable checks"
    assert verify_seal(PARENT) == parent_count and verify_seal(FR) == fr_count
    (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    report = dict(revision="FPC01-M1-clip-keepouts", PCB_sha256=sha(Path(pcb)), parts=84,
                  exact_native_pin_value_footprint_differences=0, explicit_no_connects=nc,
                  ERC_errors=0, ERC_warnings=0, DRC_errors=0, DRC_warnings=0,
                  opens=0, parity=0, ignored_checks=[], portable_tests=6,
                  native_reference_check=json.loads((ROOT / "native-reference-check.json").read_text()),
                  geometry_invariants=invariant, package_inputs_verified_before_and_after=before,
                  selected_inputs_only=True, all_transitive_dependencies_instrumented=False,
                  immutable_parent_files_verified_before_and_after=parent_count,
                  immutable_FR01_files_verified_before_and_after=fr_count,
                  FR01_handoff_sha256=sha(FR / "handoff.json"),
                  physical_qualified=False, mounting_material_and_process_qualified=False,
                  full_unit_geometry_adopted=False, PDN_qualified=False, noise_qualified=False,
                  installed_cooling_qualified=False, fabrication_released=False)
    (out / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    report["files_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in sorted(ROOT.rglob("*"))
                              if p.is_file() and "__pycache__" not in p.parts
                              and not p.name.endswith((".lck", ".kicad_prl")) and p.name != "handoff.json"}
    (ROOT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print("FPC01-M1: native ERC/DRC/parity/opens/warnings0; 6 mutation tests; sealed", len(report["files_sha256"]), "files")


if __name__ == "__main__":
    main()
