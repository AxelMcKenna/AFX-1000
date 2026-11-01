"""Lower only the two new AGND-extension priorities; preserve failed source."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u23-band-fanout-work"
WORK = ROOT / "generated/u23-band-fanout-priority-work"


def main():
    assert not WORK.exists()
    before = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    tree = read_sexpr(before.decode())
    added = json.loads((SOURCE / "generated/local-fanout.json").read_text())["added_AGND_zones"]
    identities = {str(first(read_sexpr(z), "uuid")[1]) for z in added}
    changes = []
    for zone in children(tree, "zone"):
        if str(first(zone, "uuid")[1]) not in identities:
            continue
        original = sexpr(zone)
        assert first(zone, "net_name")[1] == "/AGND"
        first(zone, "priority")[1] = a("0")
        changes.append(dict(before=original, after=sexpr(zone)))
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
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(tree) + "\n")
    (WORK / "generated/priority-repair.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(before).hexdigest(),
                candidate_pcb_sha256=hashlib.sha256((WORK / "rail_disconnect.kicad_pcb").read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                only_changes=changes,
                every_old_zone_and_all_copper_poses_rules_preserved=True,
                new_extension_priority_below_all_old_force_and_ground_zones=True,
                no_native_or_physical_qualification=True,
            ),
            indent=2,
        ) + "\n"
    )
    assert (SOURCE / "rail_disconnect.kicad_pcb").read_bytes() == before


if __name__ == "__main__":
    main()
