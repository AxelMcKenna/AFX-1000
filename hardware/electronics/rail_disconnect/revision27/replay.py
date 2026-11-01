"""Restore the exact reviewed E27 copper additions over frozen E26."""

import argparse
import hashlib
import json
from pathlib import Path

from ...common.sexpr import read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent


def replay_bytes(recipe):
    source = (ROOT.parent / "revision26/rail_disconnect.kicad_pcb").read_bytes()
    assert hashlib.sha256(source).hexdigest() == recipe["parent_pcb_sha256"], "Parent board changed"
    tree = read_sexpr(source.decode())
    additions = [read_sexpr(n) for n in recipe["added_copper"]]
    assert all(n[0] in ("segment", "via") for n in additions)
    tree.extend(additions)
    result = (sexpr(tree) + "\n").encode()
    assert hashlib.sha256(result).hexdigest() == recipe["candidate_pcb_sha256"], (
        "Replay differs from reviewed candidate"
    )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    recipe = json.loads((ROOT / "reviewed-additions.json").read_text())
    raw = replay_bytes(recipe)
    board = ROOT / "rail_disconnect.kicad_pcb"
    if args.check:
        assert raw == board.read_bytes(), "Current PCB differs from reviewed candidate"
    else:
        board.write_bytes(raw)
    print("E27 byte-identical replay; native and physical qualification remain separate")


if __name__ == "__main__":
    main()
