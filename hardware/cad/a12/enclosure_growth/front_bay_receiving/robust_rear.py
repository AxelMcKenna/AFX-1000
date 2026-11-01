"""Separate ROOT-requested rear-SMD1.2/tail1.5 receiving sensitivity."""

import json
from pathlib import Path

from .capture import ROOT, sha


def build():
    folder = ROOT / "robust_rear_variant"
    if folder.exists():
        raise RuntimeError("New receiving sensitivity required")
    original = ROOT / "generated/model233.json"
    data = json.loads(original.read_text())
    records = data["component_records"]
    B = {r["id"] for r in records if r["native_side"] == "B"}
    for row in data["boxes"]:
        if row[0] in B:
            row[5] = 1.2
    for row in data["tails"]:
        row[5] = 1.5
    for r in records:
        if r["id"] in B:
            r["projection_mm"] = 1.2
            r["world_box_mm"][4] = 1.2
            r["basis"] = "NEW PROJECT robust rear-SMD1.2 receiving, supplier/seat approval pending"
    folder.mkdir()
    old = json.loads(original.read_text())
    scad = (ROOT / "xh_reference_variant/components.scad").read_text()
    for key, tag in [("boxes", "fr_boxes"), ("tails", "fr_tails")]:
        a = tag + "=" + json.dumps(old[key]) + ";"
        b = tag + "=" + json.dumps(data[key]) + ";"
        assert a in scad
        scad = scad.replace(a, b)
    (folder / "components.scad").write_text(scad)
    checks = (ROOT / "xh_reference_variant/checks.scad").read_text()
    (folder / "checks.scad").write_text(checks)
    data["rear_SMD_requirement_mm"] = 1.2
    data["rear_THT_requirement_mm"] = 1.5
    data["rear_ref_maximum_Z_mm"] = {
        r["id"]: r["world_box_mm"][2] + r["world_box_mm"][5] for r in records if r["id"] in B
    }
    data["rear_tail_maximum_Z_mm"] = {b[0]: b[3] + b[6] for b in data["tails"]}
    data["all_rear_receivers_below_upper_seat_start_Z41p6"] = all(
        v < 41.6
        for v in list(data["rear_ref_maximum_Z_mm"].values()) + list(data["rear_tail_maximum_Z_mm"].values())
    )
    data["source_sha256"] = {
        str(p): sha(p) for p in [Path(__file__), original, ROOT / "xh_reference_variant/components.scad"]
    }
    (folder / "model.json").write_text(json.dumps(data, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                rear_SMD=len(B),
                rear_drilled_pads=len(data["tails"]),
                SMD_maxZ=max(data["rear_ref_maximum_Z_mm"].values()),
                tail_maxZ=max(data["rear_tail_maximum_Z_mm"].values()),
                all_below_seat=data["all_rear_receivers_below_upper_seat_start_Z41p6"],
            )
        )
    )


if __name__ == "__main__":
    build()
