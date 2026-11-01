"""Execute real native mask/plot contract negative controls in private copies."""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .j4_mask_review import main as review


def main(before, workspace):
    before, workspace = Path(before), Path(workspace)
    root = workspace / "generated/mask-contract-mutations"
    assert not root.exists(), "Keep earlier mutation evidence immutable"
    root.mkdir()
    cases = (
        "ground_B_pad_opening_restored",
        "ground_drill_changed",
        "positive_pad_moved",
        "ground_mask_circle_offcenter",
        "actual_back_Gerber_aperture_enlarged",
    )
    rows = []
    for label in cases:
        case = root / label
        case.mkdir()
        (case / "generated").mkdir()
        shutil.copytree(workspace / "generated/mask-gerbers", case / "generated/mask-gerbers")
        pcb = case / "rail_disconnect.kicad_pcb"
        shutil.copy2(workspace / pcb.name, pcb)
        tree = read_sexpr(pcb.read_text())
        f = next(
            f
            for f in children(tree, "footprint")
            if any(p[1] == "Reference" and p[2] == "J4" for p in children(f, "property"))
        )
        pads = {p[1]: p for p in children(f, "pad")}
        if label == "ground_B_pad_opening_restored":
            first(pads["2"], "layers").append("B.Mask")
        elif label == "ground_drill_changed":
            first(pads["2"], "drill")[1] = a("2.3")
        elif label == "positive_pad_moved":
            first(pads["1"], "at")[1] = a(".1")
        elif label == "ground_mask_circle_offcenter":
            first(first(f, "fp_circle"), "center")[1] = a(".2")
        else:
            gerber = case / "generated/mask-gerbers/rail_disconnect-B_Mask.gbs"
            text, count = re.subn(r"(%ADD\d+C,)1\.300000(\*%)", r"\g<1>1.500000\2", gerber.read_text())
            assert count == 1
            gerber.write_text(text)
        if not label.startswith("actual_back"):
            pcb.write_text(sexpr(tree) + "\n")
        rejected = False
        try:
            review(before, case)
        except AssertionError:
            rejected = True
        assert rejected, "Broken native/actual-plot contract was accepted: " + label
        inputs = [pcb, *sorted((case / "generated/mask-gerbers").iterdir())]
        rows.append(
            dict(
                mutation=label,
                rejected=True,
                source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
            )
        )
    report = dict(
        source_pcb_sha256=hashlib.sha256((workspace / "rail_disconnect.kicad_pcb").read_bytes()).hexdigest(),
        review_source_sha256=hashlib.sha256(
            Path(__file__).with_name("j4_mask_review.py").read_bytes()
        ).hexdigest(),
        mutation_recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        cases=rows,
        all_five_defects_rejected=True,
        physical_qualified=False,
    )
    (workspace / "generated/native-mask-mutations.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Five actual native/Gerber mask defects rejected")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("before")
    p.add_argument("workspace")
    args = p.parse_args()
    main(args.before, args.workspace)
