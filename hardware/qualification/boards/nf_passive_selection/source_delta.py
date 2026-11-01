"""Reproducible passive-only NF249 to provisional NF261 identity delta."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build(output):
    if output.exists():
        raise RuntimeError("Refusing to replace historical delta")
    files = [ROOT / f"sources/{name}/components.json" for name in ["NF249", "NF261"]]
    sources = [
        {p["ref"]: p for p in json.loads(f.read_text()) if p["ref"].startswith(("R", "C"))} for f in files
    ]
    a, b = sources
    changed = {}
    for ref in sorted(a.keys() & b.keys()):
        delta = {
            key: [a[ref].get(key), b[ref].get(key)]
            for key in ["part", "footprint", "pins"]
            if a[ref].get(key) != b[ref].get(key)
        }
        if delta:
            changed[ref] = delta
    data = dict(
        revision="NP01-passive-input-delta",
        parent_passive_count=len(a),
        provisional_passive_count=len(b),
        added=[b[ref] for ref in sorted(b.keys() - a.keys())],
        removed=sorted(a.keys() - b.keys()),
        changed=changed,
        source_sha256={str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
        provisional_261_pre_TPS3890_pin_correction=True,
        electrical_adopted=False,
        no_future_READY_source_or_pin_contract_inherited=True,
    )
    output.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(dict(added=len(data["added"]), changed=len(changed), removed=len(data["removed"]))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
