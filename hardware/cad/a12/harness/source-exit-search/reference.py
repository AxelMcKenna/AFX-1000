"""Reproduce the known east-pair failure before trusting the ranking screen."""

import json
from pathlib import Path

from search import ROOT, individual, inputs, pair_gap, profile, public, sha


def run():
    a, b = individual([profile("1", 10, 0, 18, 0.02), profile("2", 10, -30, 24, 0.02)], inputs())
    gap, detail = pair_gap(a, b)
    native = json.loads((ROOT / "inputs/formed-verification.json").read_text())
    assert native["cases"]["hardware_collision"]["volume_mm3"] > 28
    report = dict(
        reference_positive=public(a),
        reference_return=public(b),
        pair_margin_mm=gap,
        pair_nearest=detail,
        known_native_hardware_hit_volume_mm3=native["cases"]["hardware_collision"]["volume_mm3"],
        screen_detects_known_hardware_failure=min(
            a["clearance_lower_estimates_mm"]["return"],
            a["clearance_lower_estimates_mm"]["positive"],
            b["clearance_lower_estimates_mm"]["return"],
            b["clearance_lower_estimates_mm"]["positive"],
        )
        < 0,
        screen_does_not_introduce_component_or_case_failure=min(
            a["clearance_lower_estimates_mm"]["case"],
            a["clearance_lower_estimates_mm"]["components"],
            b["clearance_lower_estimates_mm"]["case"],
            b["clearance_lower_estimates_mm"]["components"],
        )
        > 0,
        screen_pair_clear=gap > 0,
        source_code_sha256={p.name: sha(p) for p in [ROOT / "search.py", Path(__file__)]},
        input_capture_sha256=sha(ROOT / "capture.json"),
        physical_fit_verified=False,
    )
    assert report["screen_detects_known_hardware_failure"]
    (ROOT / "reference-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "REFERENCE",
        report["screen_detects_known_hardware_failure"],
        report["screen_does_not_introduce_component_or_case_failure"],
        gap,
    )


if __name__ == "__main__":
    run()
