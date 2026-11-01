"""Capture the NF physical project's external symbol-library dependency."""

import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    source=ROOT.parent/"startup_negative_circuit/physical_layout"
    target=ROOT/"generated/NF"
    out=ROOT/"generated/symbol-dependency-capture.json"
    assert not out.exists()
    rows=[]
    for name in ("RMX_NF06P.kicad_sym","sym-lib-table"):
        before=sha(source/name)
        assert not (target/name).exists()
        shutil.copyfile(source/name,target/name)
        assert sha(target/name)==sha(source/name)==before
        rows.append(dict(source=str(source/name),target=str(target/name),sha256=before))
    out.write_text(json.dumps(dict(recipe_sha256=sha(Path(__file__)),copied_dependencies=rows,
        no_schematic_symbols_pin_maps_or_nets_changed=True,source_files_unchanged=True),indent=2)+"\n")


if __name__=="__main__":
    run()
