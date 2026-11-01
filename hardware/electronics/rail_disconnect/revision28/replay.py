"""Byte-replay the closed E28 native PCB from frozen foundation and explicit edits.

The recipe stores native S-expression object replacements, not router seeds or
an assertion that a screenshot is a PCB. Freezing requires an independently
closed native receipt tied to these exact source bytes. Replay alone never
confers electrical, physical or manufacturing qualification.
"""

import argparse
import hashlib
import json
from pathlib import Path

from ...common.sexpr import read_sexpr, sexpr
from .manufacturer import ROOT


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(receipt_path):
    receipt = json.loads(receipt_path.read_text())
    board = ROOT / "rail_disconnect.kicad_pcb"
    assert receipt["native_closed"] and not any(receipt["counts"].values()), (
        "Do not freeze a partial routing/DRC result"
    )
    assert receipt["pcb_sha256"] == digest(board), "Native receipt must check these exact source bytes"
    foundation = ROOT / "generated/foundation.kicad_pcb"
    parent = read_sexpr(foundation.read_text())
    tree = read_sexpr(board.read_text())
    known = {sexpr(n): i for i, n in enumerate(parent[1:], 1)}
    recipe = []
    for node in tree[1:]:
        literal = sexpr(node)
        recipe.append(
            dict(foundation_node=known[literal]) if literal in known else dict(native_literal=literal)
        )
    package = dict(
        revision="E28",
        foundation_sha256=digest(foundation),
        target_pcb_sha256=digest(board),
        native_receipt_file=str(receipt_path.relative_to(ROOT)),
        native_receipt_sha256=digest(receipt_path),
        ordered_native_objects=recipe,
        physical_qualified=False,
        manufacturing_accepted=False,
    )
    (ROOT / "generated/closed-native-recipe.json").write_text(json.dumps(package, indent=2) + "\n")
    return package


def replay(output):
    recipe = json.loads((ROOT / "generated/closed-native-recipe.json").read_text())
    foundation = ROOT / "generated/foundation.kicad_pcb"
    assert digest(foundation) == recipe["foundation_sha256"]
    parent = read_sexpr(foundation.read_text())
    tree = [parent[0]]
    for node in recipe["ordered_native_objects"]:
        tree.append(
            parent[node["foundation_node"]]
            if "foundation_node" in node
            else read_sexpr(node["native_literal"])
        )
    rendered = (sexpr(tree) + "\n").encode()
    assert hashlib.sha256(rendered).hexdigest() == recipe["target_pcb_sha256"]
    output.write_bytes(rendered)
    return recipe


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--freeze", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if args.freeze:
        result = freeze(args.freeze)
    else:
        assert args.output, "An explicit replay output path is required"
        result = replay(args.output)
    print(result["target_pcb_sha256"])


if __name__ == "__main__":
    main()
