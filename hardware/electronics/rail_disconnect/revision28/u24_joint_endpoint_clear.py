"""Remove one new route's off-grid overshoot; retain the actual target endpoint."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u24-oc-joint-reconnect-work"
WORK = ROOT / "generated/u24-oc-endpoint-clear-work"


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    assert hashlib.sha256(original).hexdigest() == "0db5bbd9306666604d78f1fdb4f6dae852376ef6c4ab9dd448f9cc25859013f7"
    tree = read_sexpr(original.decode())
    objects = {str(first(n, "uuid")[1]): n for n in children(tree, "segment")}
    stem = objects["c05b4e9d-9bfb-5d02-9cd7-840a4ac44757"]
    backtrack = objects["4218b75f-2139-54a7-955d-66c79b3a3045"]
    before = [sexpr(stem), sexpr(backtrack)]
    assert [float(x) for x in first(stem, "start")[1:3]] == [151.9, 146.6]
    assert [float(x) for x in first(stem, "end")[1:3]] == [152.1, 146.6]
    assert [float(x) for x in first(backtrack, "end")[1:3]] == [152.05, 146.6]
    # The actual existing target was152.05,146.6. The0.1mm planning grid
    # went50um past it and doubled back toward a foreign signal corner.
    first(stem, "end")[1:3] = [a("152.05"), a("146.6")]
    tree.remove(backtrack)
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for source in SOURCE.iterdir():
        if source.is_file() and (source.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym") or source.name in ("components.json", "fp-lib-table", "sym-lib-table")):
            shutil.copy2(source, WORK / source.name)
        elif source.suffix == ".pretty":
            shutil.copytree(source, WORK / source.name)
    (WORK / path.name).write_text(sexpr(tree) + "\n")
    report = dict(source_pcb_sha256=hashlib.sha256(original).hexdigest(), recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), before=before, after=sexpr(stem), exactly_one_new_POS_OUTPUT_READY_segment_shortened_and_one_new_backtrack_removed=True, original_native_target_unchanged=True, all_other_objects_unchanged=True, native_checks_required=True, physical_qualified=False)
    (WORK / "generated/endpoint-repair.json").write_text(json.dumps(report, indent=2) + "\n")
    assert path.read_bytes() == original


if __name__ == "__main__":
    main()
