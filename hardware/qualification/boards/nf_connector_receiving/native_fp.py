"""Native footprint-parser receipt only; not a PCB, ERC or routing pass."""

import json
import sys
from pathlib import Path

import pcbnew

from .study import ROOT, sha


def run():
    target = ROOT / "generated/native-footprints.json"
    if target.exists():
        raise RuntimeError("New receipt required")
    sources = {}
    rows = {}
    paths = [
        ROOT / "sources/repository/KiCad/JST_PHD_B30B-PHDSS_2x15_P2.00mm_Vertical.kicad_mod",
        ROOT / "ForcePigtail.pretty/NF_Force_18AWG_P5_2p1Drill_Receiving.kicad_mod",
    ]
    for p in paths:
        sources[str(p)] = sha(p)
        f = pcbnew.FootprintLoad(str(p.parent), p.stem)
        assert f is not None
        pads = {
            str(q.GetNumber()): dict(
                XY_mm=[pcbnew.ToMM(q.GetPosition().x), pcbnew.ToMM(q.GetPosition().y)],
                land_mm=[pcbnew.ToMM(q.GetSize().x), pcbnew.ToMM(q.GetSize().y)],
                drill_mm=[pcbnew.ToMM(q.GetDrillSize().x), pcbnew.ToMM(q.GetDrillSize().y)],
            )
            for q in f.Pads()
        }
        if "PHD" in p.stem:
            assert len(pads) == 30
            for n, q in pads.items():
                i = int(n)
                assert q["XY_mm"] == [2 * ((i - 1) // 2), 2 * ((i - 1) % 2)] and q["drill_mm"] == [0.75, 0.75]
        else:
            assert len(pads) == 2 and pads["1"]["XY_mm"] == [0, 0] and pads["2"]["XY_mm"] == [5, 0]
            assert all(q["drill_mm"] == [2.1, 2.1] and q["land_mm"] == [3.4, 3.4] for q in pads.values())
        rows[p.stem] = dict(pads=pads, native_load_passed=True)
    sources[str(Path(__file__))] = sha(Path(__file__))
    target.write_text(
        json.dumps(
            dict(
                KiCad_version=pcbnew.GetBuildVersion(),
                Python_version=sys.version,
                source_sha256=sources,
                footprints=rows,
                parser_only=True,
                PCB_native_DRC_performed=False,
                actual_assembly_qualified=False,
                force_pad_strain_design_complete=False,
                fabrication_released=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(dict(footprints=2, pads=32, parser_only=True)))


if __name__ == "__main__":
    run()
