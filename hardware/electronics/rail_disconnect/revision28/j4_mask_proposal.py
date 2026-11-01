"""Separate pitch9 ground-terminal mask/fillet process candidate, not release.

Only the ground terminal gets a2.6mm B.Mask opening. Positive copper/drill/mask
stay unchanged, with its original4.7mm B courtyard restored. The ground2.8mm
tail/solder bound requires total radial mask registration+edge error<=0.1mm.
Small exposed annulus and solder wetting require actual fabricator/assembler
approval and inspected process coupons; a mask aperture is not a solder proof.
"""

import copy
import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE_SHA = "5ee253eedb5a2e5babf1e774ceeeb59a9f296f1984586119006afac05524f7c8"


def change(fp):
    positive = copy.deepcopy(next(p for p in children(fp, "pad") if p[1] == "1"))
    ground = next(p for p in children(fp, "pad") if p[1] == "2")
    assert list(map(float, first(ground, "at")[1:])) == [0, 9]
    assert first(ground, "layers")[1:] == ["*.Cu", "*.Mask"]
    first(ground, "layers")[1:] = ["*.Cu", "F.Mask"]
    ground.append(read_sexpr("(solder_mask_margin 0)"))
    fp.append(
        read_sexpr(
            "(fp_circle (center 0 9) (end 1.3 9) (stroke (width 0) (type default)) "
            '(fill solid) (layer "B.Mask"))'
        )
    )
    for rect in children(fp, "fp_rect"):
        if first(rect, "layer")[1] == "B.CrtYd" and float(first(rect, "start")[2]) < 0:
            first(rect, "start")[1:] = [a("-2.35"), a("-2.35")]
            first(rect, "end")[1:] = [a("2.35"), a("2.35")]
    assert next(p for p in children(fp, "pad") if p[1] == "1") == positive


def main(workspace):
    source = ROOT / "generated/j4-p9-face-work"
    workspace = Path(workspace).resolve()
    assert workspace.is_relative_to(ROOT / "generated") and not workspace.exists()
    pcb = source / "rail_disconnect.kicad_pcb"
    assert hashlib.sha256(pcb.read_bytes()).hexdigest() == SOURCE_SHA
    workspace.mkdir()
    for p in source.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("sym-lib-table", "fp-lib-table", "components.json")
        ):
            shutil.copy2(p, workspace / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, workspace / p.name)
    (workspace / "generated").mkdir()
    tree = read_sexpr(pcb.read_text())
    j4 = next(
        f
        for f in children(tree, "footprint")
        if any(p[1] == "Reference" and p[2] == "J4" for p in children(f, "property"))
    )
    old = copy.deepcopy(j4)
    change(j4)
    (workspace / pcb.name).write_text(sexpr(tree) + "\n")
    lib = workspace / "RMX_E28.pretty/AWG14_Force_2x1_P9mm_Engineering.kicad_mod"
    fp = read_sexpr(lib.read_text())
    change(fp)
    lib.write_text(sexpr(fp) + "\n")
    report = dict(
        source_pcb_sha256=SOURCE_SHA,
        candidate_pcb_sha256=hashlib.sha256((workspace / pcb.name).read_bytes()).hexdigest(),
        original_complete_j4=sexpr(old),
        candidate_complete_j4=sexpr(j4),
        positive_pad_copper_drill_and_all_mask_unchanged=True,
        ground_copper_and_drill_unchanged_from_pitch9=True,
        ground_F_mask_nominal_diameter_mm=4.2,
        ground_B_mask_nominal_diameter_mm=2.6,
        ground_backside_tail_and_solder_max_width_requirement_mm=2.8,
        combined_radial_mask_edge_and_registration_requirement_mm=0.1,
        finished_plated_hole_requirement_mm=[2.1, 2.3],
        minimum_centered_exposed_B_annular_width_mm=0.15,
        minimum_B_annular_width_with_full_radial_offset_mm=0.05,
        backside_tail_projection_requirement_mm=1.5,
        positive_back_courtyard_mm=[4.7, 4.7],
        ground_back_courtyard_mm=[2.8, 2.8],
        fabricator_mask_and_hole_process_accepted=False,
        assembler_fillets_wetting_and_mask_adherence_accepted=False,
        joint_resistance_0p5mohm_verified=False,
        all_native_mask_and_full_3d_assembly_checks_required=True,
        actual_copper_tracks_vias_other_parts_or_rules_changed=False,
        physical_qualified=False,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (workspace / "generated/j4-mask-proposal.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Ground mask process candidate", report["candidate_pcb_sha256"])


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    args = p.parse_args()
    main(args.workspace)
