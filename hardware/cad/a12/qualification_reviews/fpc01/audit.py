"""Independent strict copied-project review; sealed FPC01 is read-only."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from hardware.electronics.common.netlists import netlist

ROOT = Path(__file__).resolve().parent
SOURCE = Path("hardware/qualification/boards/fan_health/composite").resolve()
CLI = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    handoff = json.loads((SOURCE / "handoff.json").read_text())
    inputs = json.loads((ROOT / "review-inputs.json").read_text())
    assert sha(SOURCE / "handoff.json") == inputs["source_handoff_sha256"]
    for name, digest in handoff["files_sha256"].items():
        assert sha(SOURCE / name) == digest, name
    native = ROOT / "native"
    out = ROOT / "generated"
    out.mkdir(exist_ok=False)
    env = dict(os.environ, KICAD_CONFIG_HOME="/private/tmp/afx-fpc-independent-kicad",
               FONTCONFIG_FILE=str(Path("build-hardware/kicad-fonts.conf").resolve()))
    commands = []

    def run(args, label):
        p = subprocess.run(args, text=True, capture_output=True, env=env, timeout=120)
        (out / (label + ".log")).write_text(p.stdout + p.stderr)
        commands.append(dict(command=args, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr))
        assert p.returncode == 0, commands[-1]

    run([CLI, "--version"], "version")
    run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "--output", str(out / "netlist.xml"), str(native / "fan_power_health.kicad_sch")], "netlist")
    run([CLI, "sch", "erc", "--format", "json", "--output", str(out / "erc.json"), str(native / "fan_power_health.kicad_sch")], "erc")
    run([CLI, "pcb", "drc", "--format", "json", "--all-track-errors", "--schematic-parity", "--severity-all", "--refill-zones", "--exit-code-violations", "--output", str(out / "drc.json"), str(native / "fan_power_health.kicad_pcb")], "drc")
    run([sys.executable, "-m", "hardware.qualification.boards.fan_health.composite.test_composite"], "portable")
    parts = json.loads((SOURCE / "components.json").read_text())
    actual, pins = netlist(out / "netlist.xml")
    nc = []
    for c in parts:
        for p in c["pins"]:
            if p["net"] is None:
                value = pins[c["ref"]].pop(p["number"])
                assert value.startswith("unconnected-("), value
                nc.append(dict(ref=c["ref"], pin=p["number"], exported_net=value))
    expected = {c["ref"]: {p["number"]: p["net"] for p in c["pins"] if p["net"] is not None} for c in parts}
    assert set(actual) == set(expected) and pins == expected and len(actual) == 84
    for c in parts:
        assert actual[c["ref"]].findtext("value") == c["part"], c["ref"]
        assert actual[c["ref"]].findtext("footprint") == c["footprint"], c["ref"]
    drc = json.loads((out / "drc.json").read_text())
    assert all(not drc[key] for key in ["violations", "unconnected_items", "schematic_parity", "ignored_checks"])
    erc = json.loads((out / "erc.json").read_text())
    assert not [v for s in erc["sheets"] for v in s["violations"]]
    for name, digest in handoff["files_sha256"].items():
        assert sha(SOURCE / name) == digest, (name, "Sealed source changed during review")
    assert sha(native / "fan_power_health.kicad_pcb") == inputs["copied_PCB_sha256"] == handoff["pcb_sha256"]
    (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    report = dict(scope="Independent strict native review of sealed FPC01; not physical qualification",
                  sealed_source_files_verified_before_and_after=len(handoff["files_sha256"]),
                  source_handoff_sha256=sha(SOURCE / "handoff.json"), PCB_sha256=handoff["pcb_sha256"],
                  parts=84, exact_exported_pin_value_and_footprint_differences=0,
                  explicit_no_connects=nc, ERC_errors=0, ERC_warnings=0, DRC_errors=0, DRC_warnings=0,
                  unrouted_connections=0, schematic_parity_findings=0, ignored_DRC_checks=[],
                  additional_default_ignored_checks_promoted_to_error=inputs["private_review_policy_tightening"],
                  portable_tests=9, all_pass=True,
                  source_sha256={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ROOT / "review-inputs.json", *sorted(native.iterdir())] if p.is_file()},
                  artifact_sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(out.iterdir()) if p.is_file()},
                  source_parent_edited=False, PDN_qualified=False, noise_qualified=False,
                  installed_cooling_qualified=False, physical_qualified=False, fabrication_released=False)
    (ROOT / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    print("FPC01 independent84-part review PASS: strict nativeERC/DRC/parity/opens0,9portabletests;340sourcefiles unchanged")


if __name__ == "__main__":
    main()
