"""Remove only natively dangling ordinary objects on already-closed logic nets.

Force, timing, reference, power, every open net and all latch-incident nets stay
fixed. Fresh native checks must prove that actual package pads stay connected.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .ordinary_joint_ripup7 import ORDINARY
from .schmitt_cone_candidate import GROUPS

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/pg-master-local-repair-work"
WORK = ROOT / "generated/closed-logic-cleanup-work"


def run(source_dir, work, label, expected_sha256):
    source_dir, work = Path(source_dir).resolve(), Path(work).resolve()
    assert source_dir.is_relative_to(ROOT / "generated") and work.is_relative_to(ROOT / "generated")
    assert not work.exists()
    source = source_dir / "rail_disconnect.kicad_pcb"
    blob = source.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    assert digest == expected_sha256
    tree = read_sexpr(blob.decode())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    objects = {str(first(n, "uuid")[1]): n for k in ("segment", "via") for n in children(tree, k)}
    parts = json.loads((source_dir / "components.json").read_text())
    protected = {p["net"] for c in parts if c["ref"] in ("U21", "U22") for p in c["pins"]}
    graph_path = source_dir / "generated/residual-components.json"
    graph = json.loads(graph_path.read_text())
    assert graph["source_sha256"][str(source.resolve())] == digest
    signals = {n for group in GROUPS for n in group if n}
    allowed = (ORDINARY | signals | {n + "_SCHMITT" for n in signals}) - protected - set(graph["inventory"])
    raw = source_dir / ("generated/drc-" + label + ".json")
    drc = json.loads(raw.read_text())
    assert not drc["unconnected_items"] == []
    removed = []
    seen = set()
    for violation in drc["violations"]:
        if violation["type"] not in ("track_dangling", "via_dangling"):
            continue
        for item in violation["items"]:
            uid = item["uuid"]
            node = objects.get(uid)
            if node is None or uid in seen:
                continue
            net = names[str(first(node, "net")[1])]
            if net not in allowed:
                continue
            seen.add(uid)
            removed.append(
                dict(uuid=uid, net=net, exact_original_object=sexpr(node), raw_native_finding=violation)
            )
            tree.remove(node)
    assert removed, "No eligible closed-net ordinary dangling copper remains"
    work.mkdir()
    (work / "generated").mkdir()
    for path in source_dir.iterdir():
        if path.is_file() and (
            path.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or path.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(path, work / path.name)
        elif path.suffix == ".pretty":
            shutil.copytree(path, work / path.name)
    (work / source.name).write_text(sexpr(tree) + "\n")
    report = dict(
        source_pcb_sha256=digest,
        native_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(),
        raw_DRC_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        protected_latch_incident_nets=sorted(n for n in protected if n),
        removed_ordinary_dangling_objects=removed,
        actual_pad_connectivity_must_remain_unchanged=True,
        all_force_timing_reference_power_open_nets_and_part_geometry_fixed=True,
        fresh_native_and_finite_copper_checks_required=True,
        physical_qualified=False,
    )
    (work / "generated/closed-logic-cleanup.json").write_text(json.dumps(report, indent=2) + "\n")
    assert source.read_bytes() == blob
    print("Removed", len(removed), "literal dangling ordinary objects on closed nets", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("label")
    parser.add_argument("expected_sha256")
    args = parser.parse_args()
    run(args.source, args.work, args.label, args.expected_sha256)
