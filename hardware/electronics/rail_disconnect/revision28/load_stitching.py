"""Actual parallel plated paths from the analog force planes to the load face."""

import hashlib
import json
import math
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..revision26.layout import Layout
from .repair import ROOT, Router


def main(count=6, width=1.0):
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    rt = Router(tree)
    pad = next(p for p in rt.by_ref["J3"] if p["pin"] == "6")
    assert pad["net"] == "V5_REG" and pad["through"]
    footprint = next(
        fp
        for fp in children(tree, "footprint")
        if next(p[2] for p in children(fp, "property") if p[1] == "Reference") == "J3"
    )
    native_pad = next(p for p in children(footprint, "pad") if p[1] == "6")
    drill = float(first(native_pad, "drill")[1])
    judge = Layout.__new__(Layout)
    judge.router = rt
    recipe_path = ROOT / "generated/analog-load-stitching.json"
    prior = json.loads(recipe_path.read_text()) if recipe_path.exists() else None
    old_ids = set(prior.get("protected_ids", [])) if prior else set()
    retained_ids = {
        str(first(node, "uuid")[1])
        for node in tree
        if isinstance(node, list)
        and node
        and node[0] in ("via", "segment")
        and children(node, "uuid")
        and str(first(node, "uuid")[1]) in old_ids
    }
    sites = [
        tuple(float(v) - 100 for v in first(node, "at")[1:3])
        for node in children(tree, "via")
        if str(first(node, "uuid")[1]) in retained_ids
    ]
    previous_count = len(sites)
    for radius in (1.05, 1.15, 1.3, 1.5, 1.7, 1.9, 2.1, 2.5, 3.1):
        if len(sites) >= count:
            break
        for angle in range(0, 360, 15):
            point = tuple(
                round(
                    pad["xy"][i]
                    + radius * (math.cos(math.radians(angle)) if i == 0 else math.sin(math.radians(angle))),
                    6,
                )
                for i in (0, 1)
            )
            saved = rt.geometry
            # Keep each foreign PTH's complete copper bounding box. That box
            # plus the normal .51mm via-to-foreign-copper reserve already
            # exceeds its drill-to-drill requirement; the inherited extra
            # 1.7mm square is not the physical hole. Own-net copper may overlap,
            # so this selected PTH instead gets an explicit full-size drill
            # edge check: .15 via radius + .25 hole spacing + .01 guard.
            rt.geometry = [dict(g, through=False) if g.get("through") else g for g in saved if g is not pad]
            clear = math.dist(point, pad["xy"]) >= drill / 2 + 0.15 + 0.25 + 0.01 and judge.free_via(
                pad["net"], point
            )
            rt.geometry = saved
            if not clear or not all(
                judge.free_line(pad["net"], face, pad["xy"], point, width) for face in (0, 5)
            ):
                continue
            rt.via(pad["net"], point)
            actual = next(
                (
                    via
                    for via in children(tree, "via")
                    if math.dist(tuple(float(v) - 100 for v in first(via, "at")[1:3]), point) < 1e-7
                ),
                None,
            )
            if actual is None:
                # The inherited emitter can refuse a location inside a PTH's
                # rectangular reserve. Never count or draw a pretend barrel.
                continue
            for face in (0, 5):
                rt.path(pad["net"], face, [pad["xy"], point], width)
            sites.append(point)
            if len(sites) == count:
                break
        if len(sites) == count:
            break
    assert sites, "No physical analog output stitching site found"
    ids = sorted(retained_ids)
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:load-stitch:{index}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    actual_barrels = [
        str(first(node, "uuid")[1]) for node in children(tree, "via") if str(first(node, "uuid")[1]) in ids
    ]
    assert len(actual_barrels) == len(sites)
    path.write_text(sexpr(tree) + "\n")
    recipe_path.write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                target_terminal="J3.6",
                actual_pad_center_mm=pad["xy"],
                actual_pth_drill_mm=drill,
                requested_extra_barrels=count,
                actual_extra_barrels=len(sites),
                newly_added_barrels=len(sites) - previous_count,
                actual_sites_mm=sites,
                barrel_drill_mm=0.3,
                barrel_land_mm=0.6,
                selected_pth_to_via_hole_edge_minimum_mm=0.25,
                additional_nominal_drill_spacing_guard_mm=0.01,
                actual_drill_tolerance_and_registration_accepted=False,
                spoke_width_mm=width,
                spoke_layers=["F.Cu", "B.Cu"],
                protected_ids=ids,
                actual_barrel_ids=actual_barrels,
                each_barrel_must_tolerate_entire_analog_load=True,
                native_verification_required=True,
                finite_face_contact_extraction_required=True,
                filled_capped_planarity_accepted=False,
                physical_qualified=False,
                prior_recipe=prior,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "Analog load array:",
        len(sites),
        "actual barrels;",
        len(sites) - previous_count,
        "new in this pass; sites",
        sites,
    )


if __name__ == "__main__":
    main()
