"""Byte-replay the three isolated J4 proposal steps from sealed R58 inputs.

Project/session preferences (.kicad_prl), logs and generated reports are not
native design inputs. Every PCB/schematic/project/symbol/library/table and
components.json byte in the final candidate is compared independently.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from . import j4_face_courtyards, j4_mask_proposal, j4_pitch_proposal

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def source_paths(folder):
    for p in folder.rglob("*"):
        if not p.is_file() or "generated" in p.relative_to(folder).parts:
            continue
        if p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_mod") or p.name in (
            "components.json",
            "sym-lib-table",
            "fp-lib-table",
        ):
            yield p


def main(workspace):
    workspace = Path(workspace).resolve()
    assert workspace.is_relative_to(ROOT / "generated") and not workspace.exists()
    source = ROOT / "generated/r58-joint-work"
    mirrored = workspace / "generated/r58-joint-work"
    mirrored.mkdir(parents=True)
    for p in source_paths(source):
        destination = mirrored / p.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, destination)
    steps = [
        (j4_pitch_proposal, "j4-p9-work"),
        (j4_face_courtyards, "j4-p9-face-work"),
        (j4_mask_proposal, "j4-p9-mask-work"),
    ]
    for module, name in steps:
        module.ROOT = workspace
        module.main(workspace / "generated" / name)
    final = ROOT / "generated/j4-p9-mask-work"
    repeated = workspace / "generated/j4-p9-mask-work"
    paths = list(source_paths(final))
    assert {p.relative_to(final) for p in paths} == {p.relative_to(repeated) for p in source_paths(repeated)}
    hashes = {}
    for p in paths:
        assert p.read_bytes() == (repeated / p.relative_to(final)).read_bytes(), str(p)
        hashes[str(p.relative_to(REPO))] = hashlib.sha256(p.read_bytes()).hexdigest()
    report = dict(
        source_sha256=hashes,
        all_native_project_source_bytes_equal=True,
        native_source_files_verified=len(hashes),
        replay_recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        excluded_non_design_inputs=[".kicad_prl session preferences", "generated evidence/logs"],
        physical_qualified=False,
    )
    (final / "generated/byte-replay.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Every final native design input byte matches replay:", len(hashes), "files")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    args = p.parse_args()
    main(args.workspace)
