"""Declared extra analog force layer using actual through-barrel attachments.

The variant preserves original force copper and adds the existing analog output
arm on In4.Cu. Its finite return-area cost must be extracted independently; no
quiet-ground, ampacity, stackup or process qualification follows.
"""

import copy
import hashlib
import json
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .repair import ROOT


def main():
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    added = []
    sources = []
    nets = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    for zone in list(children(tree, "zone")):
        if nets[str(first(zone, "net")[1])] != "V5_REG":
            continue
        if str(first(zone, "layer")[1]) != "In3.Cu":
            continue
        sources.append(sexpr(first(zone, "polygon")))
        new = copy.deepcopy(zone)
        new[:] = [
            n
            for n in new
            if not (
                isinstance(n, list)
                and n
                and n[0] in ("filled_polygon", "filled_areas_thickness", "fill_segments", "uuid", "priority")
            )
        ]
        first(new, "layer")[1] = "In4.Cu"
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:E28:parallel-analog-force:" + sexpr(new)))
        new.append([a("uuid"), a(uid)])
        new.append([a("priority"), a(str(20 + len(added)))])
        if uid in added:
            continue
        assert not any(
            children(z, "uuid") and str(first(z, "uuid")[1]) == uid for z in children(tree, "zone")
        ), "Parallel arm already present"
        tree.append(new)
        added.append(uid)
    assert added
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/parallel-analog-force-arm.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(before).hexdigest(),
                output_pcb_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                added_zone_ids=added,
                actual_source_zone_outlines=sources,
                source_layer="In3.Cu",
                additional_layer="In4.Cu",
                zone_priorities=list(range(20,20+len(added))),
                original_force_geometry_retained=True,
                existing_all_layer_barrels_used=True,
                added_ideal_interlayer_connections=False,
                actual_return_area_removed_requires_extraction=True,
                all_layer_thickness_and_process_accepted=False,
                native_verification_required=True,
                resistance_upper_bound_qualified=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Added", len(added), "actual In4.Cu analog force zones; return extraction required")


if __name__ == "__main__":
    main()
