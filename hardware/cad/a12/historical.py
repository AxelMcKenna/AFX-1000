"""Resolve exact historical bytes without claiming live inputs are current.

This helper is for regression tests of explicitly superseded baseline packets.
New native acceptance must continue to check its actual current input hashes.
"""

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
INDEX = REPO / "hardware/cad/a12/qualification_reviews/historical_sources/manifest.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_hashes(hashes, base=REPO):
    entries = json.loads(INDEX.read_text())["entries"]
    index = {(e["original_path"], e["expected_sha256"]): e for e in entries}
    statuses = []
    for name, expected in hashes.items():
        path = Path(base) / name
        relative = str(path.relative_to(REPO))
        if path.is_file() and sha(path) == expected:
            statuses.append(dict(original_path=relative, status="current", resolved_path=str(path)))
            continue
        entry = index.get((relative, expected))
        if entry is None:
            raise AssertionError(f"Unrecognized stale/missing historical source: {relative} {expected}")
        if entry["status"] == "exact_captured_bytes":
            captured = REPO / entry["captured_path"]
            assert sha(captured) == expected, f"Changed captured evidence: {captured}"
            statuses.append(dict(original_path=relative, status="captured", resolved_path=str(captured)))
        else:
            assert entry["status"] == "historical_capture_missing"
            statuses.append(dict(original_path=relative, status="historical_capture_missing", resolved_path=None))
    return dict(
        sources=statuses,
        applies_to_current_inputs=all(e["status"] == "current" for e in statuses),
        historical_capture_complete=all(e["resolved_path"] is not None for e in statuses),
        fabrication_released=False,
    )


def resolve(name, expected, base=REPO):
    result = inspect_hashes({name: expected}, base)
    path = result["sources"][0]["resolved_path"]
    if path is None:
        raise AssertionError(f"Historical evidence cannot be reconstructed: {name}")
    return Path(path)
