"""Finish the source-bound U37 corridor with a physically screened bypass pose."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-u37-backbone-clear-work"
WORK = ROOT / "generated/schmitt-u37-short-barrel-pose-work"


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    f = next(
        f
        for f in children(t, "footprint")
        if any(p[1] == "Reference" and p[2] == "C80" for p in children(f, "property"))
    )
    before = sexpr(f)
    assert tuple(map(float, first(f, "at")[1:3])) == (122.8, 108.0)
    first(f, "at")[1:3] = [a("123.8"), a("108.0")]
    after = sexpr(f)
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for p in SOURCE.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, WORK / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, WORK / p.name)
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(t) + "\n")
    (WORK / "generated/bypass-pose.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                only_changed_footprint="C80",
                before=before,
                after=after,
                all_Cu_and_other_parts_unchanged=True,
                nominal_component_values_unchanged=True,
                all_native_MCAD_PDN_and_decoupling_proof_pending=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
