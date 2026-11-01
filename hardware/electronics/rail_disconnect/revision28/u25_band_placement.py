"""Declare a separate U25/assigned-bypass relocation; preserve the 21-open source."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u24g-band-ground-repair-work"
WORK = ROOT / "generated/u25-band-placement-work"


def main():
    assert not WORK.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    tree = read_sexpr(original.decode())
    changes = []
    poses = {"U25": (141.5, 148.0, 0), "C70": (144.4, 152.2, 0)}
    for f in children(tree, "footprint"):
        ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
        if ref not in poses:
            continue
        assert first(f, "layer")[1] == "B.Cu"
        before = sexpr(f)
        first(f, "at")[1:] = [a(str(v)) for v in poses[ref]]
        changes.append(dict(ref=str(ref), before=before, after=sexpr(f)))
    assert len(changes) == 2
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
    candidate = WORK / source.name
    candidate.write_text(sexpr(tree) + "\n")
    report = dict(
        source_board_sha256=hashlib.sha256(original).hexdigest(),
        candidate_board_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_opens=21,
        source_warnings=92,
        changes=changes,
        assigned_bypass_owner="C70 -> U25",
        all_other_footprints_copper_zones_edges_rules_unchanged=True,
        all_ports_bulk_mounts_studs_fixed=True,
        J8_and_PB02_not_adopted=True,
        physical_native_and_electrical_checks_pending=True,
        qualified=False,
    )
    (WORK / "generated/placement-proposal.json").write_text(json.dumps(report, indent=2) + "\n")
    assert source.read_bytes() == original


if __name__ == "__main__":
    main()
