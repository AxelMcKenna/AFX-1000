"""Byte-replay the frozen E26 pilot; this does not approve its native findings."""

import argparse
import hashlib
import json
from pathlib import Path

from ...common.reports import sha
from ...common.sexpr import read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent


def replay_bytes(recipe):
    return (sexpr([read_sexpr(item) for item in recipe["ordered_root_items"]]) + "\n").encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Verify replay and baseline hashes without writing"
    )
    args = parser.parse_args()
    recipe = json.loads((ROOT / "reviewed-pilot.json").read_text())
    for name, expected in recipe["baseline_sha256"].items():
        assert sha(ROOT / name) == expected, ("Changed source baseline", name)
    data = replay_bytes(recipe)
    assert hashlib.sha256(data).hexdigest() == recipe["candidate_pcb_sha256"]
    pcb = ROOT / "rail_disconnect.kicad_pcb"
    if args.check:
        assert data == pcb.read_bytes(), "Current board differs from the frozen pilot"
    else:
        (ROOT / "generated/verification.json").unlink(missing_ok=True)
        pcb.write_bytes(data)
    print("E26 pilot replay matches; 21 opens and 30 DRC warnings remain; not build-ready")


if __name__ == "__main__":
    main()
