"""Read-only comparison of sealed U102 thermal angle semantics; no historical edits."""

import importlib.util
import json
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha

from .u102_network_corrected import solve as corrected

ROOT = Path(__file__).resolve().parent
FROZEN = ROOT.parent / "u102/stronger"


def main():
    saved = ROOT / "sources/U102-network-frozen.py"
    spec = importlib.util.spec_from_file_location("u102_historical_audit", saved)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pcb = FROZEN / "sources/power_p03.kicad_pcb"
    orientation = json.loads((ROOT / "sources/u102-native-pad-orientation.json").read_text())
    assert orientation["pcb_sha256"] == sha(pcb)
    paths = [
        saved,
        ROOT / "u102_network_corrected.py",
        ROOT / "native_u102_orientation.py",
        ROOT / "audit_u102.py",
        pcb,
        FROZEN / "sources/construction.json",
        ROOT / "sources/u102-native-pad-orientation.json",
        REPO / "hardware/cad/a12/thermal/analyze.py",
        REPO / "hardware/electronics/common/sexpr.py",
        REPO / "hardware/electronics/output_stage/check_placement.py",
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in paths}
    results = []
    for grid in [160, 320]:
        for scenario in ["nominal", "original_sensitivity"]:
            params = dict(grid=grid, pcb_path=pcb, via_wall_um=50, power=0.961306923312642)
            params.update(
                dict(tim_gap_mm=1.22, tim_k=6, contact_c_per_w=0.8, copper_k=385)
                if scenario == "nominal"
                else dict(tim_gap_mm=1.5, tim_k=4, contact_c_per_w=2, copper_k=350)
            )
            before = module.solve([121.75, 117.5, 128.75, 122.5], **params)
            after = corrected([121.75, 117.5, 128.75, 122.5], **params)
            results.append(
                dict(
                    grid=grid,
                    scenario=scenario,
                    historical=before,
                    corrected=after,
                    total_path_change_k_per_w=after["conditional_total_junction_to_base_c_per_w"]
                    - before["conditional_total_junction_to_base_c_per_w"],
                    junction_change_c=after["conditional_junction_at_60c_base_c"]
                    - before["conditional_junction_at_60c_base_c"],
                )
            )
    contract = json.loads((FROZEN / "sources/construction.json").read_text())
    dielectrics = contract["dielectric_nominal_mm"]
    thick = corrected(
        [121.75, 117.5, 128.75, 122.5],
        grid=320,
        pcb_path=pcb,
        via_wall_um=50,
        power=0.961306923312642,
        tim_gap_mm=1.5,
        tim_k=4,
        contact_c_per_w=2,
        copper_k=350,
        dielectric_override_mm=[v * (1.76 - 0.45) / sum(dielectrics) for v in dielectrics],
    )
    assert all(sha(REPO / p) == expected for p, expected in hashes.items()), "Audit input changed"
    report = dict(
        revision="U102-absolute-angle-read-only-audit",
        source_sha256=hashes,
        frozen_pcb_sha256=sha(pcb),
        frozen_files_modified=False,
        semantic_defect="Saved PCB pad angle is absolute; adding footprint angle again double rotates native pad shapes",
        independent_reader="Native KiCad10.0.7 pcbnew, wx.App initialized, read-only PAD orientation+bbox",
        native_rotated_pad_evidence=[r for r in orientation["rows"] if r["footprint_angle_degrees"] % 180],
        isolated_change="Only angle summation removed in a separate copy; original source files remain byte-identical",
        comparisons=results,
        corrected_extra_1p76mm_sensitivity=thick,
        requirements=[
            "All actual AGND pad shapes need absolute saved angle, while pad centre still transforms by footprint pose",
            "Bind merged native PCB+construction and refill to new extraction; historical bd4765 result does not qualify a later merge",
            "Preserve actual hole/foreign-net voids, actual9EP barrels, actual six-layer85/70 copper and required50um wall; no solid resin-core copper credit",
            "Include board1.76mm/project tolerance sensitivity separately; prior U102 sensitivity left nominal1.6mm fixed",
            "Native DGN14.9 is a package reference, not a complete-path upper bound; full actual TIM/contact/solder/pressure/material uncertainty remains open",
            "Whole-base10.557757W, U13newquietvoids, U10 path and source changes require fresh independent shared thermal acceptance",
        ],
        thermal_path_qualified=False,
        physical_tests_performed=0,
        canonical_modified=False,
    )
    (ROOT / "generated").mkdir(exist_ok=True)
    (ROOT / "generated/u102-angle-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            [
                dict(
                    grid=r["grid"],
                    scenario=r["scenario"],
                    delta_c=r["junction_change_c"],
                    corrected_c=r["corrected"]["conditional_junction_at_60c_base_c"],
                )
                for r in results
            ],
            indent=2,
        )
    )
    print("1.76mm corrected sensitivity:", thick["conditional_junction_at_60c_base_c"])


if __name__ == "__main__":
    main()
