"""Real zero-drill negative source attachments in a separate candidate.

Four lowest-priority same-net zones join existing header, bus, drain lands and
legacy physical barrels. Original factory pads, masks, paste, drilled objects,
force primitives and every original track/via remain unchanged.
"""

import copy
import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u28-selective-analog-batch2-work"
WORK = ROOT / "generated/u28-negative-force-arms-work"


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    preflight_path = SOURCE / "generated/negative-force-arm-preflight.json"
    preflight = json.loads(preflight_path.read_text())
    assert (
        preflight["source_sha256"]
        == hashlib.sha256((SOURCE / "generated/filled-selective-analog2.kicad_pcb").read_bytes()).hexdigest()
    )
    assert all(not row["foreign_filled_overlap"] for row in preflight["proposed_patches"])
    tree = read_sexpr(original.decode())
    added = []
    for row in preflight["proposed_patches"]:
        net, layer = row["net"], row["layer"]
        assert net in ("N12_SRC", "N19_SRC") and layer in ("F.Cu", "B.Cu")
        source_zone = next(
            z
            for z in children(tree, "zone")
            if children(z, "net_name") and str(first(z, "net_name")[1]).lstrip("/") == net
        )
        zone = copy.deepcopy(source_zone)
        zone[:] = [
            n for n in zone if not (isinstance(n, list) and n and n[0] in ("filled_polygon", "fill_segments"))
        ]
        first(zone, "uuid")[1] = a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:negativeArm:{digest}:{row}")))
        first(zone, "layer")[1] = layer
        first(zone, "priority")[1] = a("0")
        first(zone, "min_thickness")[1] = a(".2")
        x0, y0, x1, y1 = row["rectangle_mm"]
        first(zone, "polygon")[:] = read_sexpr(
            f"(polygon (pts (xy {100 + x0} {100 + y0}) (xy {100 + x1} {100 + y0}) (xy {100 + x1} {100 + y1}) (xy {100 + x0} {100 + y1})))"
        )
        tree.append(zone)
        added.append(sexpr(zone))
    assert len(added) == 4
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
    result = dict(
        source_pcb_sha256=digest,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        preflight_sha256=hashlib.sha256(preflight_path.read_bytes()).hexdigest(),
        added_force_primitives=added,
        original_copper_parts_ports_and_drills_all_preserved=True,
        no_new_drilled_or_component_objects=True,
        source_pads_masks_and_paste_unchanged=True,
        fresh_native_negative_copper_and_return_matrix_required=True,
        physical_startup_SOA_fabrication_and_voltage_qualified=False,
    )
    (WORK / "generated/negative-force-arm-repair.json").write_text(json.dumps(result, indent=2) + "\n")
    assert path.read_bytes() == original


if __name__ == "__main__":
    main()
