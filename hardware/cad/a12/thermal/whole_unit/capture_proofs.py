"""Capture remaining exact report inputs, retaining known stale comparison evidence."""

import json
import shutil
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha

from .ledger import OUT, P03, ROOT, SOURCES, read


def main():
    capture = read(ROOT / "capture.json")
    reports = [
        P03 / "generated/analysis.json",
        P03 / "generated/bipolar-ledger.json",
        SOURCES / "hardware/electronics/rail_disconnect/revision28/generated/local-loads-partial.json",
        P03 / "generated/heatmap.json",
    ]
    lineage = []
    for report_path in reports:
        report = read(report_path)
        rows = []
        for original, expected in report["source_sha256"].items():
            source = Path(original) if Path(original).is_absolute() else REPO / original
            relative = source.relative_to(REPO)
            target = SOURCES / relative
            if not target.exists() and source.exists() and sha(source) == expected:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                capture["captured"][str(relative)] = dict(
                    captured=str(target.relative_to(REPO)), sha256=sha(target)
                )
            rows.append(
                dict(
                    original=str(relative),
                    expected_sha256=expected,
                    captured=str(target.relative_to(REPO)) if target.exists() else None,
                    actual_captured_sha256=sha(target) if target.exists() else None,
                    captured_matches_report=target.exists() and sha(target) == expected,
                )
            )
        lineage.append(
            dict(
                report=str(report_path.relative_to(REPO)),
                report_sha256=sha(report_path),
                inputs=rows,
                used_as_historical_comparison_only=report_path.name == "heatmap.json",
            )
        )
    (ROOT / "capture.json").write_text(json.dumps(capture, indent=2) + "\n")
    result = dict(
        source_sha256={str(Path(__file__).resolve().relative_to(REPO)): sha(Path(__file__).resolve())},
        reports=lineage,
        actual_physical_source_bounds_established=False,
    )
    (OUT / "source-lineage.json").write_text(json.dumps(result, indent=2) + "\n")
    for report in lineage:
        print(
            report["report"],
            "unmatched:",
            [r["original"] for r in report["inputs"] if not r["captured_matches_report"]],
        )


if __name__ == "__main__":
    main()
