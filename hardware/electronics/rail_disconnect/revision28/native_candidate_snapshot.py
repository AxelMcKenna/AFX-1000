"""Run KiCad checks plus read-only uncapped connectivity and pad export.

Run with the KiCad-bundled Python, on an explicit private candidate folder.
Unresolved native findings are retained verbatim; no qualification is inferred.
"""

import argparse
import contextlib
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

from . import native, native_pad_geometry, native_uncapped, u14_residual_inventory


def snapshot(work, label):
    work = Path(work).resolve()
    root = Path(__file__).resolve().parent
    assert work.is_relative_to(root / "generated")
    source = work / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    native.ROOT = work
    native.check(label=label)
    output = work / "generated"
    filled = output / ("filled-" + label + ".kicad_pcb")
    drc = output / ("drc-" + label + ".json")
    coverage = output / ("native-" + label + ".json")
    uncapped = native_uncapped.check(source, filled, drc, output / "uncapped-native.json")
    with contextlib.redirect_stdout(io.StringIO()):
        u14_residual_inventory.main(source, filled, drc, output / "residual-components.json")
    (output / "native-pads.json").write_text(json.dumps(native_pad_geometry.export(filled), indent=2) + "\n")
    raw = json.loads(drc.read_text())
    native_report = json.loads(coverage.read_text())
    report = dict(
        source_pcb_sha256=hashlib.sha256(original).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        native_coverage_sha256=hashlib.sha256(coverage.read_bytes()).hexdigest(),
        native_severity_counts=dict(Counter(x["severity"] for x in raw["violations"])),
        native_reported_opens=len(raw["unconnected_items"]),
        native_uncapped_opens=uncapped["uncapped_unconnected_count"],
        ERC=native_report["counts"]["erc"],
        parity=len(raw["schematic_parity"]),
        DRC_ignored_checks=native_report["ignored_checks"],
        ERC_ignored_checks=native_report["erc_ignored_checks"],
        all_rule_checks_explicitly_enabled=native_report["all_native_rule_checks_enabled"],
        input_track_via_geometry_and_nets_preserved_during_fill=uncapped["source_track_via_geometry_and_nets_preserved"],
        source_unchanged=source.read_bytes() == original,
        native_closed=native_report["native_closed"],
        physical_qualified=False,
    )
    assert report["source_unchanged"]
    (output / "snapshot-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("label")
    args = parser.parse_args()
    snapshot(args.work, args.label)
