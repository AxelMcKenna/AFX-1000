"""Shared provenance utilities for generated verification reports."""

import hashlib
import os
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes(root, paths):
    sources = {Path(path) if Path(path).is_absolute() else Path(root) / path for path in paths}
    sources.update(Path(__file__).parent.glob("*.py"))
    return {
        os.path.relpath(path, root): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(sources)
    }
