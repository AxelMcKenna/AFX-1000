"""Locate recorded repository inputs after a checkout moves to another machine.

Receipts retain their original path strings and hashes. Only recognized checkout
roots are relocated; external manufacturer inputs keep their external paths.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHECKOUT_NAMES = frozenset(("rmx-publish","AFX-1000","afx-1000"))


def recorded_path(name):
    path = Path(name)
    if not path.is_absolute():
        candidate = (REPO/path).resolve()
        if not candidate.is_relative_to(REPO):
            raise ValueError("Recorded repository path escapes the checkout")
        return candidate
    if path.is_relative_to(REPO):
        return path
    for index in range(len(path.parts)-1,-1,-1):
        part = path.parts[index]
        if part not in CHECKOUT_NAMES:
            continue
        suffix = Path(*path.parts[index+1:])
        candidate = (REPO/suffix).resolve()
        if not candidate.is_relative_to(REPO):
            raise ValueError("Recorded repository path escapes the checkout")
        return candidate
    return path
