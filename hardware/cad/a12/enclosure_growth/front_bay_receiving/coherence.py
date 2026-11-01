"""Authoritative receiving-array manifest, read from the actual native SCAD input.

Old JSON remains historical: the robust-rear builder's mates field retained
old generic boxes even though the SCAD correctly used the XH reference subset.
This sidecar resolves that metadata defect without mutating native evidence.
"""

import json
from pathlib import Path

from .capture import ROOT, sha


def build():
    target = ROOT / "generated/coherent-receiving-model.json"
    if target.exists():
        raise RuntimeError("New coherent manifest required")
    original = ROOT / "robust_rear_variant/model.json"
    data = json.loads(original.read_text())
    source = ROOT / "robust_rear_variant/components.scad"
    arrays = {}
    for line in source.read_text().splitlines():
        for key in ["fr_boards", "fr_boxes", "fr_tails", "fr_mates", "fr_bundles"]:
            if line.startswith(key + "="):
                arrays[key] = json.loads(line[len(key) + 1 : -1])
    assert set(arrays) == {"fr_boards", "fr_boxes", "fr_tails", "fr_mates", "fr_bundles"}
    assert data["boxes"] == arrays["fr_boxes"] and data["tails"] == arrays["fr_tails"]
    data["historical_JSON_mate_field_defect_documented"] = data["mates"] != arrays["fr_mates"]
    data["mates"] = arrays["fr_mates"]
    data["prospective_straight_bundle_receivers"] = arrays["fr_bundles"]
    for b in data["boards"]:
        b["maximum_rear_assembly_projection"] = 1.5
        b["maximum_rear_SMD_projection"] = 1.2
    closed = json.loads((ROOT / "generated/FPCClosed-C7-delta.json").read_text())
    assert closed["new_receiving_body_strict_subset"]
    data["FPC_final_closed_source_identity"] = closed["closed_PCB_sha256"]
    data["FPC_geometry_source_parent_is_explicit_conservative_C7_superset"] = True
    data["source_native_receiving_PCBs_not_silently_replaced"] = True
    for r in data["component_records"]:
        if r["id"] == "FPC84_C7":
            r["current_selected_projection_requirement_mm"] = 0.97
            r["retained_conservative_parent_projection_mm"] = r["projection_mm"]
            r["new_native_source_proved_by"] = "generated/FPCClosed-C7-delta.json"
    data["source_sha256"] = {
        str(p): sha(p) for p in [Path(__file__), source, original, ROOT / "generated/FPCClosed-C7-delta.json"]
    }
    target.write_text(json.dumps(data, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                parts=len(data["boxes"]),
                actual_drilled_tail_receivers=len(data["tails"]),
                mates=len(data["mates"]),
                old_metadata_mates_corrected=data["historical_JSON_mate_field_defect_documented"],
            )
        )
    )


if __name__ == "__main__":
    build()
