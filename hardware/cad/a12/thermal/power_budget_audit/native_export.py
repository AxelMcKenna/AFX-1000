"""Native read-only exports of immutable E19/E20 copies for the provenance audit."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kicad-cli", required=True)
    args = parser.parse_args()
    sources = {}
    artifacts = {}
    rows = []
    with tempfile.TemporaryDirectory(prefix="afx-native-power-audit-") as directory:
        temp = Path(directory)
        font = temp / "fonts.conf"
        font.write_text(
            f"<fontconfig><dir>/System/Library/Fonts</dir><cachedir>{temp}/fontcache</cachedir></fontconfig>"
        )
        env = dict(os.environ, KICAD_CONFIG_HOME=str(temp / "config"), FONTCONFIG_FILE=str(font))
        version = subprocess.run(
            [args.kicad_cli, "version"], env=env, capture_output=True, text=True, check=True
        ).stdout.strip()
        for name, folder, file in [
            ("E20", "led_driver", "led_driver"),
            ("E19", "processor_carrier", "processor_carrier"),
        ]:
            path = ROOT / "sources/repository/hardware/electronics" / folder / (file + ".kicad_sch")
            target = OUT / (name + "-netlist.xml")
            sources[str(path.relative_to(REPO))] = sha(path)
            command = [
                args.kicad_cli,
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadxml",
                "-o",
                str(target),
                str(path),
            ]
            run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=45)
            log = OUT / (name + "-export.log")
            log.write_text(run.stdout + run.stderr)
            assert run.returncode == 0 and target.exists()
            artifacts.update({str(p.relative_to(REPO)): sha(p) for p in [target, log]})
            rows.append(dict(name=name, command=command, returncode=run.returncode, source_sha256=sha(path)))
        assert all(sha(REPO / p) == h for p, h in sources.items())
    report = dict(
        native_tool=version,
        exports=rows,
        source_sha256=sources,
        artifact_sha256=artifacts,
        export_is_current_pin_contract_only=True,
        full_new_ERC_DRC_claimed=False,
        canonical_modified=False,
        current_or_thermal_qualified=False,
    )
    (OUT / "native-export.json").write_text(json.dumps(report, indent=2) + "\n")
    print(version, "two native exports; no original writes")


if __name__ == "__main__":
    main()
