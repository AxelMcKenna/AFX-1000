"""Independent read-only audit of sealed NF03C; fresh exports stay here."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

from hardware.electronics.common.netlists import netlist

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
SOURCE = REPO / "hardware/qualification/boards/startup_negative_circuit/compact"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit():
    handoff = json.loads((SOURCE / "handoff.json").read_text())
    hashes = handoff["files_sha256"]
    for name, digest in hashes.items():
        assert sha(SOURCE / name) == digest, name
    out = ROOT / "generated"
    out.mkdir(parents=True, exist_ok=True)
    cli = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    commands = [
        [cli, "--version"],
        [cli, "sch", "export", "netlist", "--format", "kicadxml", "--output",
         str(out / "netlist.xml"), str(SOURCE / "negative_startup.kicad_sch")],
        [cli, "sch", "erc", "--format", "json", "--output", str(out / "erc.json"),
         str(SOURCE / "negative_startup.kicad_sch")],
    ]
    records = []
    for argv in commands:
        result = subprocess.run(argv, env=dict(os.environ, KICAD_CONFIG_HOME="/private/tmp/rmx-kicad-config"),
                                text=True, capture_output=True, timeout=120, check=False)
        records.append(dict(argv=argv, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
        (out / "commands.json").write_text(json.dumps(records, indent=2) + "\n")
        assert result.returncode == 0, argv
    fresh_parts, fresh_pins = netlist(out / "netlist.xml")
    original_parts, original_pins = netlist(SOURCE / "generated/netlist.xml")
    assert fresh_pins == original_pins
    assert {r: p.findtext("value") for r, p in fresh_parts.items()} == {
        r: p.findtext("value") for r, p in original_parts.items()
    }
    issues = [v for s in json.loads((out / "erc.json").read_text())["sheets"] for v in s["violations"]]
    expected = json.loads((SOURCE / "generated/erc-review.json").read_text())["reviewed"]
    assert sorted(issues, key=lambda v: v["items"][0]["uuid"]) == sorted(
        expected, key=lambda v: v["items"][0]["uuid"]
    )
    for name, digest in hashes.items():
        assert sha(SOURCE / name) == digest, name
    report = dict(
        handoff_sha256=sha(SOURCE / "handoff.json"), sealed_files_verified=len(hashes),
        fresh_native_parts=len(fresh_parts), fresh_pin_and_value_parity=True,
        fresh_erc_errors=sum(v["severity"] == "error" for v in issues),
        fresh_erc_warnings=sum(v["severity"] == "warning" for v in issues),
        exact_reviewed_warning_inventory_matches=True,
        documentation_errata=[{
            "file": "integration.json", "field": "power_interfaces.bias_input",
            "description": "Narrative says two499ohm resistors; actual circuit, parameters and controller_feed_nominal_ohm use two392ohm, total784ohm.",
            "source_files_modified": False,
        }],
        scope="File integrity, independent native netlist/value parity and exact ERC inventory only",
        e28_integration_implemented=False, pcb_implemented=False, physical_qualified=False,
        fabrication_released=False,
        artifact_sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(out.iterdir()) if p.is_file()},
    )
    (ROOT / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ["artifact_sha256", "documentation_errata"]}, indent=2))


if __name__ == "__main__":
    audit()
