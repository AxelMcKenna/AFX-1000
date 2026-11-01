"""Declare a separate U27/assigned-bypass relocation; preserve the 39-open source."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u26-band-leaf-cleanup6-work"
WORK = ROOT / "generated/u27-band-placement-work"


def main():
    assert not WORK.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    tree = read_sexpr(original.decode())
    changes = []
    backside_template = next(
        f
        for f in children(tree, "footprint")
        if any(p[1] == "Reference" and p[2] == "C71" for p in children(f, "property"))
    )
    poses = {"U27": (197, 147.5, 0), "C72": (199.8625, 152.3, 270)}
    for f in children(tree, "footprint"):
        ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
        if ref not in poses:
            continue
        before = sexpr(f)
        if ref == "C72":
            assert first(f, "layer")[1] == "F.Cu"
            template = copy.deepcopy(backside_template)
            first(template, "uuid")[1] = first(f, "uuid")[1]
            for property_node in children(template, "property"):
                original_property = [p for p in children(f, "property") if p[1] == property_node[1]]
                if original_property:
                    property_node[2] = original_property[0][2]
            assert {str(p[1]): str(first(p, "net")[-1]) for p in children(f, "pad")} == {
                str(p[1]): str(first(p, "net")[-1]) for p in children(template, "pad")
            }
            f[:] = template
        assert first(f, "layer")[1] == "B.Cu"
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
        source_opens=39,
        source_warnings=70,
        changes=changes,
        assigned_bypass_owner="C72 -> U27",
        explicit_C72_F_to_B_standard_0805_pattern_from_existing_C71=True,
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
