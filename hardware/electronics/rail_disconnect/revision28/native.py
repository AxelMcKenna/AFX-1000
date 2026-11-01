"""Fresh unfiltered KiCad checks on scratch copies; never save over source."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .native_profile import summarize

ROOT = Path(__file__).resolve().parent
REPOSITORY = Path(__file__).resolve().parents[4]
DEFAULT_CLI = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


def check(cli=DEFAULT_CLI, label="latest", require_closed=False, source_pcb=None):
    out = ROOT / "generated"
    with tempfile.TemporaryDirectory(prefix="rmx-e28-native-") as directory:
        temp = Path(directory)
        for path in ROOT.iterdir():
            if path.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym") or path.name in (
                "sym-lib-table",
                "fp-lib-table",
            ):
                shutil.copy2(path, temp / path.name)
            elif path.suffix == ".pretty":
                shutil.copytree(path, temp / path.name)
        source_pcb = ROOT / "rail_disconnect.kicad_pcb" if source_pcb is None else Path(source_pcb)
        if source_pcb.resolve() != (ROOT / "rail_disconnect.kicad_pcb").resolve():
            assert source_pcb.resolve().is_relative_to((ROOT / "generated").resolve()), (
                "Candidate source must stay in E28 generated directory"
            )
            shutil.copy2(source_pcb, temp / "rail_disconnect.kicad_pcb")
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR="/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints",
            FONTCONFIG_FILE=str(REPOSITORY / "build-hardware/kicad-fonts.conf"),
        )
        input_hashes = {
            str(path.relative_to(temp)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in temp.rglob("*")
            if path.is_file()
        }
        input_pcb_hash = input_hashes["rail_disconnect.kicad_pcb"]
        logs = []

        def run(*args):
            result = subprocess.run([str(cli), *map(str, args)], capture_output=True, text=True, env=env)
            logs.append(
                {
                    "args": [str(a) for a in args],
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
            assert result.returncode == 0, (args, result.stdout, result.stderr)

        run(
            "sch",
            "erc",
            "--severity-all",
            "--format",
            "json",
            "-o",
            out / f"erc-{label}.json",
            temp / "rail_disconnect.kicad_sch",
        )
        run(
            "pcb",
            "drc",
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--refill-zones",
            "--save-board",
            "--format",
            "json",
            "-o",
            out / f"drc-{label}.json",
            temp / "rail_disconnect.kicad_pcb",
        )
        shutil.copy2(temp / "rail_disconnect.kicad_pcb", out / f"filled-{label}.kicad_pcb")
        raw = json.loads((out / f"drc-{label}.json").read_text())
        erc = json.loads((out / f"erc-{label}.json").read_text())
        status = summarize(raw, erc)
        counts = status["counts"]
        receipt = {
            "revision": "E28",
            **status,
            "physical_qualification": False,
            "pcb_sha256": input_pcb_hash,
            "source_pcb_path": str(source_pcb),
            "source_hashes": input_hashes,
            "source_unchanged_after_check": input_pcb_hash
            == hashlib.sha256(source_pcb.read_bytes()).hexdigest(),
            "drc_sha256": hashlib.sha256((out / f"drc-{label}.json").read_bytes()).hexdigest(),
            "commands": logs,
        }
        (out / f"native-{label}.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(label, counts, flush=True)
        if require_closed:
            assert receipt["native_closed"], "Native findings or unchecked rule categories remain"
            assert receipt["source_unchanged_after_check"], "Source changed while checking scratch snapshot"
        return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", default=DEFAULT_CLI)
    parser.add_argument("--label", default="latest")
    parser.add_argument("--require-closed", action="store_true")
    parser.add_argument("--source-pcb", type=Path)
    args = parser.parse_args()
    check(args.cli, args.label, args.require_closed, args.source_pcb)
