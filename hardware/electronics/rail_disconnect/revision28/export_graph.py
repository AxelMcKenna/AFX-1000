"""Bind the native component export to the exact checked editable source."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from .repair import ROOT

KICAD_PYTHON = (
    "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9"
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(label):
    output = ROOT / "generated"
    receipt_path = output / f"native-{label}.json"
    receipt = json.loads(receipt_path.read_text())
    source = ROOT / "rail_disconnect.kicad_pcb"
    assert receipt["source_unchanged_after_check"]
    assert sha(source) == receipt["pcb_sha256"], "Editable source changed since native check"
    filled = output / f"filled-{label}.kicad_pcb"
    drc = output / f"drc-{label}.json"
    assert sha(drc) == receipt["drc_sha256"], "Raw native report changed"
    graph = output / "open-components.json"
    command = [
        KICAD_PYTHON,
        "-m",
        "hardware.electronics.rail_disconnect.revision27.native_graph",
        str(filled),
        str(drc),
        str(graph),
    ]
    subprocess.run(
        command, check=True, env=dict(os.environ, KICAD_CONFIG_HOME="/private/tmp/rmx-kicad-config")
    )
    assert sha(source) == receipt["pcb_sha256"], "Editable source changed while exporting"
    (output / "native-open-components-binding.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=sha(source),
                filled_pcb_sha256=sha(filled),
                drc_sha256=sha(drc),
                native_receipt_sha256=sha(receipt_path),
                graph_sha256=sha(graph),
                exporter_sha256=sha(Path(__file__)),
                native_label=label,
                command=command,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    main(parser.parse_args().label)
