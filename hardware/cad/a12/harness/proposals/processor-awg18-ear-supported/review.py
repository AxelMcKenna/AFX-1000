"""Exact source preservation, mechanical package and current native/copper proof."""

import hashlib
import json
import math
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-ear"
REPO = ROOT.parents[5]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def reference(fp):
    return next(p[2] for p in children(fp, "property") if p[1] == "Reference")


def run(write=True):
    old = read_sexpr((SOURCE / "processor_carrier.kicad_pcb").read_text())
    new = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    before = {reference(f): f for f in children(old, "footprint")}
    after = {reference(f): f for f in children(new, "footprint")}
    assert len(before) == 85 and len(after) == 86 and set(after) - set(before) == {"H9"}
    assert all(sexpr(after[k]) == sexpr(v) for k, v in before.items())
    h9 = after["H9"]
    assert h9[1] == "RMX_Carrier:M2_Insert_Clearance"
    assert first(h9, "layer")[1] == "F.Cu"
    assert list(map(float, first(h9, "at")[1:])) == [252, 155.2]
    assert set(first(h9, "attr")[1:]) == {"board_only", "exclude_from_pos_files", "exclude_from_bom"}
    pads = children(h9, "pad")
    assert len(pads) == 1
    p = pads[0]
    assert p[1] == "" and p[2:4] == ["np_thru_hole", "circle"]
    assert list(map(float, first(p, "size")[1:])) == [2.4, 2.4] and float(first(p, "drill")[1]) == 2.4
    assert not children(p, "net")
    circles = {first(c, "layer")[1]: float(first(c, "end")[1]) for c in children(h9, "fp_circle")}
    assert circles == {"F.CrtYd": 2.8, "B.CrtYd": 3.7}
    original_zone_ids = {str(first(z, "uuid")[1]) for z in children(old, "zone")}
    zones = [z for z in children(new, "zone") if str(first(z, "uuid")[1]) not in original_zone_ids]
    assert len(zones) == 1
    z = zones[0]
    assert set(first(z, "layers")[1:]) == {"F.Cu", "In1.Cu", "In2.Cu", "B.Cu"}
    ko = first(z, "keepout")
    assert all(first(ko, k)[1] == "not_allowed" for k in ["tracks", "vias", "copperpour"])
    assert first(ko, "pads")[1] == "allowed"
    assert first(ko, "footprints")[1] == "allowed"
    stripped = [q for q in new if q is not h9 and q is not z]
    assert sexpr(stripped) == sexpr(old), "An original board object changed"
    points = [tuple(map(float, q[1:3])) for q in first(first(z, "polygon"), "pts")[1:]]
    assert len(points) == 64
    distances = []
    for a, b in zip(points, points[1:] + points[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        distances.append(abs(dx * (155.2 - a[1]) - dy * (252 - a[0])) / math.hypot(dx, dy))
    assert min(distances) >= 3.801 - 1e-8
    for name in [
        "processor_carrier.kicad_sch",
        "components.json",
        "bom.csv",
        "fp-lib-table",
        "sym-lib-table",
        "RMX_E19.kicad_sym",
    ]:
        assert (ROOT / name).read_bytes() == (SOURCE / name).read_bytes(), name
    pa, na = netlist(SOURCE / "generated/netlist.xml")
    pb, nb = netlist(ROOT / "generated/netlist.xml")
    assert len(pa) == len(pb) == 77 and na == nb
    native = json.loads((ROOT / "generated/native.json").read_text())
    assert native["candidate_pcb_sha256"] == sha(ROOT / "processor_carrier.kicad_pcb")
    assert all(type(v) is int and v == 0 for v in native["counts"].values())
    for group in ["source_sha256", "artifact_sha256"]:
        for name, digest in native[group].items():
            assert sha(REPO / name) == digest, ("Stale native evidence", name)
    copper = json.loads((ROOT / "generated/native-metal-clearance.json").read_text())
    assert copper["source_pcb_sha256"] == sha(ROOT / "processor_carrier.kicad_pcb") and copper[
        "actual_filled_pcb_sha256"
    ] == sha(ROOT / "generated/filled.kicad_pcb")
    assert copper["source_code_sha256"] == sha(ROOT / "native_copper.py")
    assert copper["actual_all_four_layer_copper_clear"]
    assert len(copper["rows"]) == 4
    assert all(
        r[k] <= 1e-8
        for r in copper["rows"]
        for k in ["pad_intersection_mm2", "track_via_intersection_mm2", "filled_copper_intersection_mm2"]
    )
    assert (
        copper["inside_positive_control_area_mm2"] > 0.78 and copper["outside_negative_control_area_mm2"] == 0
    )
    report = dict(
        source_parent_pcb_sha256=sha(SOURCE / "processor_carrier.kicad_pcb"),
        candidate_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
        actual_filled_pcb_sha256=sha(ROOT / "generated/filled.kicad_pcb"),
        native_counts=native["counts"],
        old85_footprints_and_all_original_board_objects_exact=True,
        total_footprints=86,
        schematic_components_unchanged=77,
        J13_all_pads_courtyards_poses_unchanged=True,
        new_only_board_H9_world_mm=[182, 97.2],
        new_H9_native_mm=[252, 155.2],
        NPTH_mm=2.4,
        front_head_mm=5.6,
        back_boss_class_mm=7.2,
        metal_exclusion_required_min_radius_mm=3.8,
        actual_keepout_min_radius_mm=min(distances),
        numerical_construction_guard_mm=0.001,
        pad_rule_exception_requires_native_copper_polygon_audit=True,
        all_actual_four_layer_copper_clear=True,
        solder_mask_insulation_credit=False,
        nominal_hole_to_top_ear_edge_mm=1.0,
        nominal_J13_service_bbox_to_H9_head_gap_mm=0.75,
        shared_input_target_a=2.4,
        unassigned_other_branch_or_reserve_a=0.636,
        source_J1_unfitted_service_role_preserved=True,
        source_parent_PDN_result_inherited=False,
        full_tensor_started=False,
        root_boss_support_strain_material_and_insert_engagement_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    if write:
        (ROOT / "generated/package-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Verified", report["candidate_pcb_sha256"], native["counts"])
    return report


if __name__ == "__main__":
    run()
