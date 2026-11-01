"""Capture only E11's used stock lands for package review; no Mac CAD import."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parents[1]/"hardware/electronics/sequenced_bypass"
OUT = ROOT/"staging/bypass-stock-library"


def run():
    assert sys.platform == "linux", "Use the pinned Linux CAD image"
    OUT.mkdir(exist_ok=False)
    parts = json.loads((SOURCE/"components.json").read_text())
    rows, hashes = [], {}
    for identifier in sorted({p["footprint"] for p in parts}):
        lib, name = identifier.split(":")
        path = Path("/usr/share/kicad/footprints")/(lib+".pretty")/(name+".kicad_mod")
        target = OUT/(lib+".pretty")/path.name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(path,target)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[str(path)] = digest
        tree = read_sexpr(path.read_text())
        pads = [dict(number=str(p[1]),at=list(first(p,"at")[1:]),size=list(first(p,"size")[1:]),
                     layers=list(first(p,"layers")[1:])) for p in children(tree,"pad")]
        rows.append(dict(footprint=identifier,sha256=digest,pads=pads))
        if identifier in {p["footprint"] for p in parts if p["ref"] in ("U1","U3")}:
            print(identifier,pads,flush=True)
    (OUT/"inventory.json").write_text(json.dumps(dict(source_sha256=hashes,footprints=rows,
        original_E11_sources_unchanged=True,fabrication_released=False),indent=2)+"\n")


if __name__ == "__main__":
    run()
