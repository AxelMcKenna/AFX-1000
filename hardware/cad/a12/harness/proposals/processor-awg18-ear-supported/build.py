"""Private board-only H9 support; no original ear part/copper/outline edits."""

import copy
import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-ear"
SOURCE_SHA = "d55f9e48899b336df4cead960c96c8cadecaf9fc01a273906221c8d419eb0e21"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def clone_ids(node):
    if not isinstance(node, list):
        return
    if node and node[0] == "uuid":
        node[1] = str(uuid.uuid5(uuid.NAMESPACE_URL, "afx-ear-support-H9-" + str(node[1])))
    else:
        for q in node:
            clone_ids(q)


def run():
    assert sha(SOURCE / "processor_carrier.kicad_pcb") == SOURCE_SHA
    assert not (ROOT / "processor_carrier.kicad_pcb").exists()
    for p in SOURCE.iterdir():
        if p.is_dir() and p.suffix == ".pretty":
            shutil.copytree(p, ROOT / p.name)
        elif p.is_file() and (
            p.suffix in [".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_sym"]
            or p.name in ["components.json", "bom.csv", "fp-lib-table", "sym-lib-table"]
        ):
            shutil.copy2(p, ROOT / p.name)
    out = ROOT / "generated"
    out.mkdir()
    tree = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    assert len(children(tree, "footprint")) == 85
    h4 = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "H4"] for p in children(f, "property"))
    )
    h9 = copy.deepcopy(h4)
    clone_ids(h9)
    first(h9, "at")[1:] = [a(252), a(155.2)]
    for prop in children(h9, "property"):
        if prop[1] == "Reference":
            prop[2] = "H9"
    assert "board_only" in first(h9, "attr") and "exclude_from_bom" in first(h9, "attr")
    tree.append(h9)
    count = 64
    radius = 3.801 / math.cos(math.pi / count)
    points = [
        (252 + radius * math.cos(i * 2 * math.pi / count), 155.2 + radius * math.sin(i * 2 * math.pi / count))
        for i in range(count)
    ]
    pts = " ".join(f"(xy {x:.9f} {y:.9f})" for x, y in points)
    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, "afx-ear-H9-all-layer-metal-keepout"))
    zone = read_sexpr(
        f'(zone(layers "F.Cu" "In1.Cu" "In2.Cu" "B.Cu")(uuid "{uid}")(hatch edge .5)(connect_pads(clearance 0))(min_thickness .15)(keepout(tracks not_allowed)(vias not_allowed)(pads allowed)(copperpour not_allowed)(footprints allowed))(fill(thermal_gap .3)(thermal_bridge_width .5))(polygon(pts {pts})))'
    )
    tree.append(zone)
    (ROOT / "processor_carrier.kicad_pcb").write_text(sexpr(tree) + "\n")
    ledger = dict(
        source_parent_pcb_sha256=SOURCE_SHA,
        candidate_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
        original_85_footprints_and_all_original_board_nodes_required_exact=True,
        new_H9_footprint=sexpr(h9),
        new_metal_keepout=sexpr(zone),
        native_centre_mm=[252, 155.2],
        world_centre_mm=[182, 97.2],
        nominal_NPTH_bore_mm=2.4,
        front_head_diameter_mm=5.6,
        back_boss_class_diameter_mm=7.2,
        full_circle_metal_keepout_minimum_radius_mm=3.8,
        circumscribed_polygon_vertices=64,
        circumscribed_vertex_radius_mm=radius,
        only_new_keepout_may_change_native_fills=True,
        J13_and_original77_parts_pins_traces_poses_outline_unchanged=True,
        nominal_bore_to_ear_top_edge_mm=1.0,
        nominal_J13_service_bbox_to_H9_head_X_gap_mm=0.75,
        root_additive_case_boss_required=True,
        root_boss_geometry=dict(
            world_centre_mm=[182, 97.2], OD_mm=7.2, blind_insert_bore_mm=3.2, seat_z_mm=6.5, floor_z_mm=2.8
        ),
        shared_input_target_a=2.4,
        known_Seed_LED_branches_a=[1.0, 0.764],
        unassigned_other_branches_or_reserve_a=0.636,
        no_parent_PDN_result_inherited=True,
        full_tensor_started=False,
        native_verification_pending=True,
        source_parent_modified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (out / "design-change.json").write_text(json.dumps(ledger, indent=2) + "\n")
    print("Added H9", ledger["candidate_pcb_sha256"])


if __name__ == "__main__":
    run()
