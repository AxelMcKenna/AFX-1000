"""Measured local new-route nudges after enforcing the native0.2mm minimum.

No footprint, original protected copper, hole, rule or exemption is changed.
Every candidate still requires full native clearance/connectivity verification.
"""

import hashlib
import json
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .repair import ROOT

MOVES = {
    ("AGND", "F.Cu"): {
        (141.1607, 140.7263): (141.1607, 140.6963),
        (141.3634, 140.7263): (141.3634, 140.6963),
    },
    ("REF_HIGH_OK", "B.Cu"): {
        (182.2448, 126.3407): (182.2748, 126.3707),
        (182.2448, 126.4199): (182.2748, 126.4499),
        (182.3903, 126.1952): (182.4203, 126.2252),
    },
    ("E28_RESET", "B.Cu"): {
        (221.5873, 114.1058): (221.5873, 114.0858),
        (219.8412, 114.1058): (219.8412, 114.0858),
    },
}


def main(contract_path):
    pcb = ROOT / "rail_disconnect.kicad_pcb"
    before = pcb.read_bytes()
    tree = read_sexpr(before.decode())
    protected = {r["uuid"] for r in json.loads(Path(contract_path).read_text())["locked_copper"]}
    changed = []
    for node in children(tree, "segment"):
        net = str(first(node, "net")[-1]).lstrip("/")
        layer = str(first(node, "layer")[1])
        moves = MOVES.get((net, layer), {})
        literal = sexpr(node)
        for end in ("start", "end"):
            point = first(node, end)
            xy = tuple(map(float, point[1:3]))
            if xy in moves:
                assert str(first(node, "uuid")[1]) not in protected
                point[1:3] = [a(f"{v:.4f}") for v in moves[xy]]
        if sexpr(node) != literal:
            changed.append(dict(before=literal, after=sexpr(node)))
    assert changed
    pcb.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/router-clearance-repair.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(before).hexdigest(),
                output_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
                changed_native_objects=changed,
                new_route_vertex_moves_file_mm={str(k): str(v) for k, v in MOVES.items()},
                protected_original_copper_changed=False,
                parts_and_holes_moved=False,
                rules_relaxed=False,
                raw_native_all_track_check_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Nudged", len(changed), "actual new trace objects; native recheck required")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("contract_path")
    args = p.parse_args()
    main(args.contract_path)
