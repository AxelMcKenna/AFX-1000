"""Same real land/TIM envelope on stronger actual copper, with captured full-context obstacles."""

import json
import shutil
from pathlib import Path

from hardware.cad.a12.thermal.candidates.u10.candidate import geometry_inventory
from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.sexpr import read_sexpr

from .synthesize import BASE, ROOT

OUT = ROOT / "generated"


def main():
    OUT.mkdir(exist_ok=True)
    source = BASE / "variant/power_p03.kicad_pcb"
    pcb = ROOT / "variant/power_p03.kicad_pcb"
    source_fp = geometry_inventory(read_sexpr(source.read_text()))["footprints"]
    current_fp = geometry_inventory(read_sexpr(pcb.read_text()))["footprints"]
    assert source_fp == current_fp, "Component/pad pose changed; must rebuild full actual obstacle packet"
    before = json.loads((BASE / "generated/geometry.json").read_text())
    for path, expected in before["reference_shared_source_sha256"].items():
        assert sha(REPO / path) == expected, "Captured obstacle context changed"
    for name in ["LAND.step", "LAND.stl", "TIM.step", "TIM.stl", "obstacles.json"]:
        shutil.copy2(BASE / "generated" / name, OUT / name)
    scad = (
        (BASE / "generated/checks.scad")
        .read_text()
        .replace("../sources/context/", "../../u10/sources/context/")
    )
    (OUT / "checks.scad").write_text(scad)
    paths = [
        Path(__file__).resolve(),
        ROOT / "synthesize.py",
        pcb,
        ROOT / "variant/receipt.json",
        BASE / "generated/checks.scad",
        BASE / "generated/geometry.json",
        BASE / "generated/obstacles.json",
        BASE / "candidate.py",
        REPO / "hardware/electronics/common/sexpr.py",
    ]
    before.update(
        dict(
            revision="U10-eight-via-unchanged-land-envelope",
            candidate_pcb_sha256=sha(pcb),
            footprints_and_native_pads_identical_to_sealed_u10=True,
            source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
            declared_mechanical_envelope_unchanged=True,
            physical_fit_verified=False,
            thermal_path_qualified=False,
        )
    )
    (OUT / "geometry.json").write_text(json.dumps(before, indent=2) + "\n")


if __name__ == "__main__":
    main()
