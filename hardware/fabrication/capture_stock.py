"""Capture a selected circuit's used stock lands from the pinned Linux image."""

import argparse
import json
import shutil
import sys
from pathlib import Path

from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def run():
    assert sys.platform == "linux"
    parser = argparse.ArgumentParser()
    parser.add_argument("circuit")
    parser.add_argument("label")
    args = parser.parse_args()
    assert all(s and all(c.isalnum() or c in "-_" for c in s) for s in (args.circuit,args.label))
    source = REPO/"hardware/electronics"/args.circuit/"components.json"
    parts = json.loads(source.read_text())
    output = ROOT/"staging"/args.label
    output.mkdir(exist_ok=False)
    hashes = {str(source):sha(source)}
    for identifier in sorted({p["footprint"] for p in parts}):
        library,name = identifier.split(":")
        path = Path("/usr/share/kicad/footprints")/(library+".pretty")/(name+".kicad_mod")
        target = output/(library+".pretty")/path.name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(path,target)
        hashes[str(path)] = sha(path)
    (output/"capture.json").write_text(json.dumps(dict(source_sha256=hashes,circuit=args.circuit,
        recipe_sha256=sha(Path(__file__)),part_count=len(parts),fabrication_released=False),indent=2)+"\n")
    print("Captured used stock lands for",args.circuit,len(parts),"parts")


if __name__ == "__main__":
    run()
