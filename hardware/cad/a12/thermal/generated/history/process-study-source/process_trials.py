"""Immutable, declared U13 process scenarios; no fabrication/thermal approval."""

import argparse
import gzip
import json
from pathlib import Path

from .generate import OUT, REPO, ROOT, load, sha
from .u13_path import solve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcb", required=True)
    args = parser.parse_args()
    pcb = Path(args.pcb)
    origin = sha(pcb)
    d = load()
    heavy = dict(
        via_wall_um=50, outer_copper_override_um=85, dielectric_override_mm=[0.10, 0.34, 0.27, 0.34, 0.10]
    )
    specifications = [
        ("native_1p6_wall25", 160, {}),
        ("proposed_1p0_wall25", 160, dict(dielectric_override_mm=[0.10, 0.12, 0.14, 0.12, 0.10])),
        ("wall35_current_stack", 160, dict(via_wall_um=35)),
        ("wall50_outer85", 160, heavy),
        ("wall50_outer85_fine", 320, heavy),
        ("wall50_gap1p5_contact0p8", 160, dict(heavy, tim_gap_mm=1.5, contact_c_per_w=0.8)),
        (
            "wall50_illustrative_lower_k",
            160,
            dict(heavy, tim_gap_mm=1.5, contact_c_per_w=0.8, copper_k=350, tim_k=4),
        ),
        (
            "wall50_bore0p2_illustrative",
            160,
            dict(heavy, finished_bore_override_mm=0.20, tim_gap_mm=1.5, contact_c_per_w=0.8),
        ),
    ]
    rows = {}
    for name, grid, options in specifications:
        rows[name] = solve(d, grid=grid, pcb_path=pcb, **options)
        assert sha(pcb) == origin, "Native input changed during process screen"
    snapshot = OUT / "native-inputs" / ("p03-" + origin + ".kicad_pcb.gz")
    snapshot.write_bytes(gzip.compress(pcb.read_bytes(), mtime=0))
    report = dict(
        scope="Actual saved native XY/fills; explicit process/stack overrides are conditional design candidates. Capability is not a board-specific DFM approval. No material/contact sensitivity is a guaranteed bound.",
        native_origin_sha256=origin,
        compressed_native_input=str(snapshot.relative_to(REPO)),
        scenarios=rows,
        source_sha256={
            str((ROOT / f).relative_to(REPO)): sha(ROOT / f)
            for f in [
                "process_trials.py",
                "process-candidates.json",
                "u13_path.py",
                "generate.py",
                "analyze.py",
                "design.json",
            ]
        },
        guardbanded_85c_acceptance=False,
        source_routing_or_manufacturing_approved=False,
        physical_tests_performed=0,
        fabrication_released=False,
        thermal_qualified=False,
    )
    (OUT / "u13-process-trials.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
