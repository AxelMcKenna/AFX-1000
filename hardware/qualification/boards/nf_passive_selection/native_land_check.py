"""Optional real KiCad parser check of NP01 candidate manufacturing lands."""

import argparse
import hashlib
import json
import platform
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(output):
    if output.exists():
        raise RuntimeError("Refusing to overwrite native evidence")
    lib = ROOT / "analyses/NP01.pretty"
    rows = []
    for path in sorted(lib.glob("*.kicad_mod")):
        f = pcbnew.FootprintLoad(str(lib), path.stem)
        if f is None:
            raise ValueError(f"Native load failed: {path}")
        pads = []
        for p in f.Pads():
            xy = p.GetPosition()
            size = p.GetSize()
            pads.append(
                dict(
                    number=p.GetNumber(),
                    xy_mm=[pcbnew.ToMM(xy.x), pcbnew.ToMM(xy.y)],
                    size_mm=[pcbnew.ToMM(size.x), pcbnew.ToMM(size.y)],
                )
            )
        if sorted(p["number"] for p in pads) != ["1", "2"]:
            raise ValueError("Native pin count mismatch")
        rows.append(dict(file=str(path), sha256=sha(path), pads=pads))
    if len(rows) != 9:
        raise ValueError("Missing required land candidates")
    data = dict(
        scope="KiCad actual footprint parser/2padgeometry only, no PCB placement/DRC/fabrication approval",
        KiCad_version=pcbnew.Version(),
        python_version=platform.python_version(),
        source_sha256={str(Path(__file__)): sha(Path(__file__))},
        rows=rows,
        physical_qualified=False,
        fabrication_released=False,
    )
    output.write_text(json.dumps(data, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                native_footprints=len(rows),
                native_pads=sum(len(x["pads"]) for x in rows),
                KiCad_version=pcbnew.Version(),
            )
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
