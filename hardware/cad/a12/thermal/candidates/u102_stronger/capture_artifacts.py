"""Copy exact source/actual-native-artifact bytes named by an owner's sealed receipt."""

import argparse
import json
import shutil
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha


def capture(source, destination):
    source = source.resolve()
    destination = destination.resolve()
    receipt = json.loads((source / "generated/current-native.json").read_text())
    assert (
        receipt["pcb_sha256"]
        == sha(source / "power_p03.kicad_pcb")
        == sha(destination / "power_p03.kicad_pcb")
    )
    copied = {}
    unavailable = []
    for group in ["source_sha256", "artifact_sha256"]:
        for name, expected in receipt[group].items():
            original = (REPO / name).resolve()
            if not original.exists() or sha(original) != expected:
                unavailable.append(dict(group=group, original=name, expected_sha256=expected))
                continue
            if original.is_relative_to(source):
                target = destination / original.relative_to(source)
            else:
                target = destination / "source-dependencies" / original.relative_to(REPO)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
            assert sha(target) == expected == sha(original)
            copied[str(target.relative_to(REPO))] = dict(original=name, sha256=expected, group=group)
    report = dict(
        pcb_sha256=receipt["pcb_sha256"],
        captured_native_receipt_sha256=sha(destination / "generated/current-native.json"),
        captured=copied,
        unavailable_current_bytes=unavailable,
        original_files_modified=False,
    )
    (destination / "evidence-capture.json").write_text(json.dumps(report, indent=2) + "\n")
    print(destination.relative_to(REPO), "captured", len(copied), "unavailable", len(unavailable))
    if unavailable:
        print(json.dumps(unavailable, indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--destination", required=True, type=Path)
    a = p.parse_args()
    capture(a.source, a.destination)


if __name__ == "__main__":
    main()
