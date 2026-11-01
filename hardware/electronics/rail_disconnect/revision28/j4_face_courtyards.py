"""Private face-specific wire joint courtyard, with unchanged pitch9 copper.

The front retains4.7mm squares around each4.2mm land. The backside uses the
root proposal's separate2.8mm square tail envelopes (1.5mm projection), which
include the0.7mm core radius plus0.3mm relative centering allocation. Existing
nearby SMT courtyards retain their own body-clearance margins. These are
engineering assembly requirements, not accepted IPC or manufacturer patterns.
The complete3D joint/material/clearance proof remains independently required.
"""

import copy
import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import children, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE_SHA = "c69e93c1ad1992525c0fe17be781f2946b1a79fc361f48e56d20cb13b9c77d77"


def change(fp):
    pads = copy.deepcopy(children(fp, "pad"))
    fp[:] = [n for n in fp if not (isinstance(n, list) and n and n[0] == "fp_rect")]
    for layer, half in (("F.CrtYd", 2.35), ("B.CrtYd", 1.4)):
        for y in (0, 9):
            fp.append(
                read_sexpr(
                    f"(fp_rect (start {-half} {y - half}) (end {half} {y + half}) "
                    f'(stroke (width .05) (type default)) (fill none) (layer "{layer}"))'
                )
            )
    assert children(fp, "pad") == pads


def main(workspace):
    source = ROOT / "generated/j4-p9-work"
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
    original = copy.deepcopy(j4)
    change(j4)
    assert [n for n in j4 if not (isinstance(n, list) and n and n[0] == "fp_rect")] == [
        n for n in original if not (isinstance(n, list) and n and n[0] == "fp_rect")
    ]
    (workspace / pcb.name).write_text(sexpr(tree) + "\n")
    lib = workspace / "RMX_E28.pretty/AWG14_Force_2x1_P9mm_Engineering.kicad_mod"
    fp = read_sexpr(lib.read_text())
    change(fp)
    lib.write_text(sexpr(fp) + "\n")
    report = dict(
        source_pcb_sha256=SOURCE_SHA,
        candidate_pcb_sha256=hashlib.sha256((workspace / pcb.name).read_bytes()).hexdigest(),
        original_complete_j4=sexpr(original),
        candidate_complete_j4=sexpr(j4),
        actual_copper_pads_drills_tracks_vias_other_parts_unchanged=True,
        source_and_matched_library_courtyards_only_changed=True,
        front_each_pad_courtyard_mm=[4.7, 4.7],
        back_each_tail_courtyard_mm=[2.8, 2.8],
        backside_material_projection_requirement_mm=1.5,
        backside_core_radius_max_mm=0.7,
        relative_centering_requirement_mm=0.3,
        adjacent_SMT_courtyard_body_margin_retained=True,
        clearance_rules_or_exemptions_changed=False,
        native_all_severity_and_full_3d_assembly_checks_required=True,
        manufacturing_and_assembly_requirements_accepted=False,
        physical_qualified=False,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (workspace / "generated/j4-face-courtyard-proposal.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Face-specific courtyard candidate", report["candidate_pcb_sha256"])


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    args = p.parse_args()
    main(args.workspace)
