"""Explicit six-hole analog outlet packing, with original terminal retained.

Replaces only the earlier five-hole outlet array and its ten spokes. All other
holes and physical connections are retained. Geometry needs fresh native DRC,
finite face-contact extraction, process acceptance and prototype validation.
"""

import argparse
import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from . import widen_analog_stems

ROOT = Path(__file__).resolve().parent
SITES = (
    (64.0, 37.5),
    (63.609327, 38.025),
    (62.175, 38.409327),
    (63.609327, 36.975),
    (61.685778, 37.77176),
    (61.790673, 36.975),
)


def main(workspace):
    source = ROOT / "generated/p9-u13-outlet-work"
    path = source / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    prior = ROOT / "generated/p9-analog-outlet-work/generated/analog-load-stitching.json"
    ids = set(json.loads(prior.read_text())["protected_ids"])
    tree = read_sexpr(before.decode())
    removed = [
        s
        for s in tree
        if isinstance(s, list)
        and s
        and s[0] in ("segment", "via")
        and children(s, "uuid")
        and str(first(s, "uuid")[1]) in ids
    ]
    assert len(removed) == 15 and len([s for s in removed if s[0] == "via"]) == 5
    assert {str(first(s, "uuid")[1]) for s in removed} == ids
    code = next(str(n[1]) for n in children(tree, "net") if str(n[2]).lstrip("/") == "V5_REG")
    assert all(str(first(s, "net")[1]) == code for s in removed)
    tree[:] = [s for s in tree if s not in removed]
    center = (62.7, 37.5)
    assert min(math.dist(p, q) for i, p in enumerate(SITES) for q in SITES[i + 1 :]) > 0.56
    assert min(math.dist(center, p) for p in SITES) > 0.91
    added = []
    for index, (x, y) in enumerate(SITES):
        uid = uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:sixload:{digest}:{index}:via")
        via = read_sexpr(
            f'(via (at {100 + x:.6f} {100 + y:.6f}) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net {code}) (uuid {uid}))'
        )
        tree.append(via)
        added.append(sexpr(via))
        for layer in ("F.Cu", "B.Cu"):
            uid = uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:sixload:{digest}:{index}:{layer}")
            line = read_sexpr(
                f'(segment (start {100 + center[0]} {100 + center[1]}) (end {100 + x:.6f} {100 + y:.6f}) (width .5) (layer "{layer}") (net {code}) (uuid {uid}))'
            )
            tree.append(line)
            added.append(sexpr(line))
    workspace = Path(workspace).resolve()
    assert workspace.is_relative_to(ROOT / "generated") and not workspace.exists()
    workspace.mkdir()
    (workspace / "generated").mkdir()
    for p in source.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, workspace / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, workspace / p.name)
    candidate = workspace / path.name
    candidate.write_text(sexpr(tree) + "\n")
    array_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
    widen_analog_stems.ROOT = workspace
    widen_analog_stems.main(0.55)
    report = dict(
        source_pcb_sha256=digest,
        predecessor_array_recipe_sha256=hashlib.sha256(prior.read_bytes()).hexdigest(),
        removed_array_objects=[sexpr(s) for s in removed],
        added_array_objects=added,
        new_sites_mm=SITES,
        actual_barrels=6,
        barrel_drill_mm=0.3,
        barrel_land_mm=0.6,
        spoke_width_mm=0.5,
        terminal_hole_and_pad_and_pose_unchanged=True,
        array_only_sha256=array_sha,
        candidate_pcb_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
        stems_width_mm=0.55,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        physical_and_process_qualified=False,
        native_and_finite_contact_checks_required=True,
    )
    (workspace / "generated/six-load-array.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Six real outlet barrels and bounded .55 mm stems emitted; all checks pending")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    main(p.parse_args().workspace)
