"""Preserve exact native-attempt input bytes before any prospective repair."""

import argparse
import json
import shutil
from pathlib import Path

from .stage import ROOT, sha, write


def archive(receipt, name):
    receipt = Path(receipt).resolve()
    target = ROOT / "history" / name
    if (ROOT / "handoff.json").exists() or target.exists() or not receipt.is_relative_to(ROOT):
        raise RuntimeError("Trial archive requires a fresh unsealed local destination")
    report = json.loads(receipt.read_text())
    known = {}
    for p in (ROOT / "history").rglob("reconstruction-map.json"):
        for row in json.loads(p.read_text())["input_bytes"].values():
            original = ROOT / row["copy"]
            if sha(original) != row["sha256"]:
                raise RuntimeError("An archived source copy has changed")
            known[row["sha256"]] = row["copy"]
    target.mkdir(parents=True)
    result = {}
    for i, (n, expected) in enumerate(report["input_sha256"].items()):
        p = Path(n)
        if sha(p) != expected:
            raise RuntimeError("Native input was changed before preservation: " + n)
        if expected in known:
            copy = ROOT / known[expected]
        else:
            copy = target / "files" / ("%04d-" % i + p.name)
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, copy)
        result[n] = dict(sha256=expected, copy=str(copy.relative_to(ROOT)))
    write(
        target / "reconstruction-map.json",
        dict(
            original_receipt=str(receipt),
            original_receipt_sha256=sha(receipt),
            input_bytes=result,
            original_logs_and_artifacts_preserved=True,
            source_byte_reconstruction_only=True,
        ),
    )
    print(json.dumps(dict(inputs=len(result), destination=str(target))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    archive(args.receipt, args.name)
