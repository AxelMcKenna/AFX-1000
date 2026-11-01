"""Separate exact native rectangular-pad tail receiving correction.

The earlier FR max(sizeX,sizeY) square is retained in the initial trial. This
variant keeps the complete actual rectangular pad bounding box plus 0.2 mm on
EACH side, actual absolute pad rotation and 1.5 mm rear trim/fillet allowance.
No PCB pose, copper, selected body or allowance is changed.
"""

import json
import math
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

from .capture import ROOT, closure, sha, write
from .model import world_box


def build():
    out = ROOT / "tail_shape"
    if out.exists():
        raise RuntimeError("New variant required")
    d = json.loads((ROOT / "generated/model.json").read_text())
    base = ROOT / "inputs/hardware/qualification/boards"
    tails = []
    audit = []
    for ident, folder, pcbname, origin in [
        (
            "NF265",
            "startup_negative_circuit/physical_layout",
            "negative_startup_physical.kicad_pcb",
            [172, 180.5, 3.5],
        ),
        ("FPC91", "fan_health/composite_nf_branch", "fan_power_health.kicad_pcb", [14, 180.5, 3.5]),
    ]:
        tree = read_sexpr((base / folder / pcbname).read_text())
        for fp in children(tree, "footprint"):
            ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
            for pad in children(fp, "pad"):
                if str(pad[2]) != "thru_hole":
                    continue
                xy = transform(fp, first(pad, "at")[1:3])
                size = list(map(float, first(pad, "size")[1:3]))
                angle = float(first(pad, "at")[3]) if len(first(pad, "at")) > 3 else 0
                rad = math.radians(angle)
                width = abs(math.cos(rad)) * (size[0] + 0.4) + abs(math.sin(rad)) * (size[1] + 0.4)
                depth = abs(math.sin(rad)) * (size[0] + 0.4) + abs(math.cos(rad)) * (size[1] + 0.4)
                bb = [xy[0] - width / 2, xy[1] - depth / 2, xy[0] + width / 2, xy[1] + depth / 2]
                row = [ident + "_" + ref + "." + str(pad[1]), *world_box(origin, bb, -3.26, -1.76)]
                old = next(b for b in d["tails"] if b[0] == row[0])
                assert all(
                    old[i + 1] - 1e-8 <= row[i + 1]
                    and row[i + 1] + row[i + 4] <= old[i + 1] + old[i + 4] + 1e-8
                    for i in range(3)
                ), row[0]
                tails.append(row)
                audit.append(
                    dict(
                        id=row[0],
                        actual_native_pad_size_mm=size,
                        absolute_native_pad_angle_deg=angle,
                        native_pad_center_mm=list(xy),
                        receiving_xy_per_side_mm=0.2,
                        rear_trim_fillet_mm=1.5,
                        old_square_row=old,
                        new_rectangular_row=row,
                        new_conservative_receiver_subset_old=True,
                    )
                )
    assert len(tails) == len(d["tails"]) == 106
    sources = closure(ROOT / "checks.scad")
    out.mkdir()
    derived = {}
    for p in sources:
        if p == ROOT / "checks.scad":
            dst = out / "checks.scad"
        else:
            dst = out / p.relative_to(ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == ".scad":
            text = p.read_text().replace(str(ROOT / "context"), str(out / "context"))
            if p.name == "components.scad" and p.parent.name == "robust_rear_variant":
                old = "fr_tails=" + json.dumps(d["tails"]) + ";"
                assert old in text
                text = text.replace(old, "fr_tails=" + json.dumps(tails) + ";")
            dst.write_text(text)
        else:
            dst.write_bytes(p.read_bytes())
        derived[str(dst.relative_to(ROOT))] = sha(dst)
    d["tails"] = tails
    write(out / "model.json", d)
    write(
        out / "audit.json",
        dict(
            source_sha256={str(p): sha(p) for p in [Path(__file__), ROOT / "generated/model.json", *sources]},
            derived_sha256=derived,
            pad_receiving_corrections=audit,
            all106_new_receivers_subset_old=True,
            actual_Cu_pads_PCB_poses_components_and_mates_changed=False,
            physical_qualified=False,
        ),
    )
    print(
        json.dumps(
            dict(
                rectangular_receivers=len(tails),
                changed=sum(a["new_rectangular_row"] != a["old_square_row"] for a in audit),
            )
        )
    )


if __name__ == "__main__":
    build()
