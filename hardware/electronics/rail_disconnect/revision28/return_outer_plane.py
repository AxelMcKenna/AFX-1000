"""Separate physical B.Cu return reinforcement trial; no resistance pass implied."""

import copy
import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u28-band-reconnect1-work"
WORK = ROOT / "generated/u28-return-outer-plane-work"


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    tree = read_sexpr(original.decode())
    candidates = [
        z
        for z in children(tree, "zone")
        if children(z, "net_name") and str(first(z, "net_name")[1]).lstrip("/") == "AGND"
    ]
    assert candidates and not any(first(z, "layer")[1] == "B.Cu" for z in candidates)
    zone = copy.deepcopy(candidates[0])
    zone[:] = [
        n for n in zone if not (isinstance(n, list) and n and n[0] in ("filled_polygon", "fill_segments"))
    ]
    first(zone, "uuid")[1] = a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:outer-return:{digest}")))
    first(zone, "layer")[1] = "B.Cu"
    first(zone, "priority")[1] = a("0")
    first(zone, "min_thickness")[1] = a(".2")
    first(zone, "polygon")[:] = read_sexpr(
        "(polygon (pts (xy 220 116) (xy 254 116) (xy 254 140) (xy 220 140)))"
    )
    tree.append(zone)
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
    (WORK / path.name).write_text(sexpr(tree) + "\n")
    report = dict(
        source_pcb_sha256=digest,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        only_new_object=sexpr(zone),
        all_existing_copper_parts_ports_rules_zones_unchanged=True,
        actual_J4_ground_to_J8_current_path_must_be_reextracted=True,
        C24_to_J8_dynamic_loop_not_removed=True,
        J8_lug_and_PB02_not_adopted=True,
        unapproved_ground_parasitics_soldering_and_process_review_required=True,
        native_and_electrical_checks_pending=True,
        physical_and_fabrication_qualified=False,
    )
    (WORK / "generated/return-plane-trial.json").write_text(json.dumps(report, indent=2) + "\n")
    assert path.read_bytes() == original


if __name__ == "__main__":
    main()
