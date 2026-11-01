"""One-shot source/artifact seal for this NEW private native receiving draft."""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

from hardware.qualification.boards.fan_health.circuit.design import REPO, ROOT, sha


def main():
    if (ROOT / "handoff.json").exists():
        raise ValueError("Preserve sealed FH02; use a new candidate instead of replacing its seal")
    out = ROOT / "generated"
    native = json.loads((out / "native.json").read_text())
    if native["erc_findings"] or native["pin_map_mismatches"] or not native["actual_component_set_matches"]:
        raise ValueError("Native failure")
    cli = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/rmx-kicad-config",
        FONTCONFIG_FILE=str(REPO / "build-hardware/kicad-fonts.conf"),
    )
    version = subprocess.run([cli, "--version"], env=env, capture_output=True, text=True, check=True)
    (out / "kicad-version.log").write_text(version.stdout + version.stderr)
    (out / "tool-identity.json").write_text(
        json.dumps(
            dict(
                binary_path=cli, sha256=sha(cli), version=version.stdout.strip(), platform=platform.platform()
            ),
            indent=2,
        )
        + "\n"
    )
    source = (
        ROOT / "sources/repository/hardware/electronics/rail_disconnect/revision28/rail_disconnect.kicad_sch"
    )
    cmd = [
        cli,
        "sch",
        "export",
        "netlist",
        "--format",
        "kicadxml",
        "--output",
        str(out / "captured-E28-netlist.xml"),
        str(source),
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
    (out / "captured-E28-export.log").write_text(result.stdout + result.stderr)
    (out / "captured-E28-export-command.json").write_text(json.dumps(cmd, indent=2) + "\n")
    provenance = {}
    special = {
        "afx-fh-attiny84a.pdf": "https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny24A-44A-84A-Data-Sheet-DS40002269A.pdf",
        "afx-fh-at_thermistor.pdf": "https://www.semitec-global.com/uploads/2022/01/P12-13-AT-Thermistor.pdf",
        "afx-fh-tlp175a.pdf": "https://toshiba.semicon-storage.com/info/TLP175A_datasheet_en_20230525.pdf?did=13665&prodName=TLP175A",
        "tlp-official-confirmation.pdf": "https://toshiba.semicon-storage.com/info/TLP175A_datasheet_en_20230525.pdf?did=13665&prodName=TLP175A",
        "afx-fh-lvc2g17.pdf": "https://www.ti.com/lit/ds/symlink/sn74lvc2g17.pdf",
        "abls.pdf": "https://abracon.com/Resonators/abls.pdf",
        "kemet-c0g.pdf": "https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf",
        "tnpw.pdf": "https://www.vishay.com/docs/28758/tnpw_e3.pdf",
    }
    for p in sorted((ROOT / "sources").glob("*.pdf")):
        provenance[str(p.relative_to(ROOT))] = dict(
            sha256=sha(p),
            primary_URL=special.get(p.name, "https://www.ti.com/lit/ds/symlink/" + p.stem + ".pdf"),
            selected=p.name not in {"sn74lv1t04.pdf", "sn74aup1g97.pdf"},
        )
    (ROOT / "primary-sources.json").write_text(json.dumps(provenance, indent=2) + "\n")
    capture = json.loads((out / "captured-inputs.json").read_text())
    for rel, digest in capture["repository_inputs_sha256"].items():
        if sha(ROOT / "sources/repository" / rel) != digest:
            raise ValueError("Captured source mutated: " + rel)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(REPO)
    testcmd = [sys.executable, str(ROOT / "test_circuit.py")]
    tests = subprocess.run(testcmd, env=env, capture_output=True, text=True)
    (out / "tests.log").write_text(tests.stdout + tests.stderr)
    if tests.returncode:
        raise ValueError(tests.stdout + tests.stderr)
    for n in ["design.py", "analyze.py", "capture.py", "package_review.py", "test_circuit.py", "seal.py"]:
        if not (ROOT / n).is_file():
            raise ValueError("Missing generator: " + n)
    own_sources = [p for p in ROOT.glob("*") if p.is_file() and p.suffix in (".py", ".md", ".json")]
    own_sources += list((ROOT / "RMX_FH02.pretty").glob("*.kicad_mod"))
    current = dict(
        scope="FH02 native schematic/ERC/export + receiving comparisons; no routedPCB",
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(own_sources)},
        native_input_schematic_sha256=sha(ROOT / "fan_health.kicad_sch"),
        artifact_sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()},
        components=native["component_count"],
        ERC_findings=0,
        native_pin_map_mismatches=0,
        actual_export_MCU_and_leaf_contract_tests_pass=True,
        portable_tests_command=testcmd,
        portable_tests_pass=True,
        source_capture_is_historical_provenance=True,
        live_parent_differences_at_seal={
            p: dict(captured=d, live=sha(REPO / p))
            for p, d in capture["repository_inputs_sha256"].items()
            if sha(REPO / p) != d
        },
        physical_qualified=False,
        PCB_implemented=False,
        fabrication_released=False,
        production_released=False,
    )
    (out / "current-native.json").write_text(json.dumps(current, indent=2) + "\n")
    files = {
        str(p.relative_to(ROOT)): sha(p)
        for p in sorted(ROOT.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.name != "handoff.json"
    }
    handoff = dict(
        scope=current["scope"],
        sealed_UTC=datetime.now(timezone.utc).isoformat(),
        files_sha256=files,
        native_receipt="generated/current-native.json",
        analysis="generated/analysis.json",
        firmware_captured=capture["firmware_host_result"],
        components=native["component_count"],
        portable_tests=13,
        native_ERC_findings=0,
        native_pin_map_mismatches=0,
        protected_DIG_new_receiving_proposal_a=2.42,
        physical_qualified=False,
        fabrication_released=False,
        production_released=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(handoff, indent=2) + "\n")
    print("FH02 READY private draft:", len(files), "files; handoff", sha(ROOT / "handoff.json"))


if __name__ == "__main__":
    main()
