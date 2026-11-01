"""Repair one C83 return diagonal exposed by the deliberate bypass move."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..revision26 import router as aid
from .focused import legal_line
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/c83-aux-branch-repair-work"
WORK = ROOT / "generated/c83-cap-return-clear-work"
UID = "813034d3-7fe3-5f88-ad6d-41701322efa2"


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    original = path.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    assert digest == "59bb659ef7d4b8941e19b6563749716845f13b4acd90ebdc8b90ea9d3e8c9b21"
    tree = read_sexpr(original.decode())
    node = next(n for n in children(tree, "segment") if str(first(n, "uuid")[1]) == UID)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    assert names[str(first(node, "net")[1])] == "AGND"
    assert [float(v) for v in first(node, "start")[1:3]] == [237.25, 147.1]
    assert [float(v) for v in first(node, "end")[1:3]] == [238.1, 146.25]
    before = sexpr(node)
    tree.remove(node)
    rt = Router(tree)
    points = [(137.25, 47.1), (138.1, 47.1), (138.1, 46.25)]
    assert all(legal_line(rt, "AGND", 0, p, q, 0.2) for p, q in zip(points, points[1:]))
    ids = {id(n) for n in tree}
    aid.STEP = 0.025
    rt.path("AGND", 0, points, 0.2)
    added = []
    for index, n in enumerate(tree):
        if id(n) not in ids and isinstance(n, list) and n and n[0] in ("segment", "via"):
            n.append([a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:C83return:{digest}:{index}:{sexpr(n)}")))])
            added.append(sexpr(n))
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for source in SOURCE.iterdir():
        if source.is_file() and (source.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym") or source.name in ("components.json", "fp-lib-table", "sym-lib-table")):
            shutil.copy2(source, WORK / source.name)
        elif source.suffix == ".pretty":
            shutil.copytree(source, WORK / source.name)
    (WORK / path.name).write_text(sexpr(tree) + "\n")
    (WORK / "generated/cap-return-repair.json").write_text(json.dumps(dict(source_pcb_sha256=digest, recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), removed_one_local_C83_GND_diagonal=before, added_local_GND_route=added, original_GND_annulus_and_all_other_objects_fixed=True, deliberate_local_return_geometry_change_requires_new_PDN_and_noise_review=True, failed_native_clearance_and_mask_report_preserved_at_source=True, actual_native_checks_pending=True, physical_qualified=False), indent=2) + "\n")
    assert path.read_bytes() == original


if __name__ == "__main__":
    main()
