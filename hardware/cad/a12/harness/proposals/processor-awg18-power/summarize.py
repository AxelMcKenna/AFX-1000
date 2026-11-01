"""Source-bound cold/hot/grid and retained-budget handoff, never an endpoint pass."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    retained = ROOT / "generated/inputs/retained-output-electrical-analysis.json"
    old = json.loads(retained.read_text())
    rows = []
    inputs = [retained, ROOT / "construction-requirements.json", ROOT / "summarize.py"]
    groups = {}
    for label, folder in [("fills", ROOT), ("six_stitch", ROOT / "stitch_trial")]:
        for p in sorted((folder / "generated").glob("*-grid*.json")):
            d = json.loads(p.read_text())
            if "local_simultaneous_sharing_corners" not in d:
                continue
            for rel, digest in d["source_sha256"].items():
                assert sha(folder / rel) == digest, ("Stale model source", p, rel)
            inputs.append(p)
            kind = "baseline" if d["baseline"] else label
            key = (kind, d["scenario"]["name"])
            groups.setdefault(key, []).append(d)
            for temp, case in d["local_simultaneous_sharing_corners"].items():
                rows.append(
                    dict(
                        case=kind,
                        scenario=d["scenario"]["name"],
                        grid_mm=d["grid_mm"],
                        temperature_c=int(temp),
                        positive_LED_drop_v=case[0]["positive_only_drop_v"]["led"],
                        local_LED_positive_plus_return_drop_v=[
                            min(r["led_local_loop_drop_v"] for r in case),
                            max(r["led_local_loop_drop_v"] for r in case),
                        ],
                        local_Seed_path_before_R1_drop_v=[
                            min(r["seed_local_loop_drop_before_R1_v"] for r in case),
                            max(r["seed_local_loop_drop_before_R1_v"] for r in case),
                        ],
                        maximum_absolute_front_filter_to_Seed_ground_offset_v=max(
                            abs(v) for r in case for v in r["quiet_front_filter_to_seed_offset_v"].values()
                        ),
                        missing_remote_return_contributions_remain_symbolic=True,
                    )
                )
    refinement = []
    for key, models in groups.items():
        models.sort(key=lambda d: d["grid_mm"], reverse=True)
        for coarse, fine in zip(models, models[1:]):
            for temp in ["20", "100"]:
                a, b = [
                    max(r["led_local_loop_drop_v"] for r in d["local_simultaneous_sharing_corners"][temp])
                    for d in [coarse, fine]
                ]
                refinement.append(
                    dict(
                        case=key[0],
                        scenario=key[1],
                        temperature_c=int(temp),
                        coarse_grid_mm=coarse["grid_mm"],
                        fine_grid_mm=fine["grid_mm"],
                        LED_maximum_corner_drop_difference_v=b - a,
                        relative_to_fine_fraction=abs(b - a) / b,
                        convergence_is_not_a_certified_geometry_or_material_bound=True,
                    )
                )
    oldend = {
        k: v
        for k, v in old["chosen_limit_result"]["endpoints"].items()
        if k in ["processor_5v", "led_5v"] or k.startswith("led_anode_")
    }
    report = dict(
        scope=__doc__,
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in inputs},
        cases=rows,
        grid_refinement=refinement,
        retained_lumped_baseline=dict(
            report=str(retained.relative_to(REPO)),
            report_sha256=sha(retained),
            endpoints=oldend,
            LED_anode_headroom_v=oldend["led_anode_1"]["minimum_v"] - 4.9,
            E19_port_escape_already_in_each_processor_lead_ohm=0.0005,
            source_and_destination_joint_allowances_retained_separately=True,
            actual_E19_matrix_must_replace_escape_inside_full_network=True,
            subtracting_local_drop_from_old_minimum_is_not_a_new_voltage_bound=True,
            canonical42_lumped_proof_is_not_combineddb83_copper_proof=True,
        ),
        current_ledger=dict(
            Seed_input_a=1.0,
            LED5V_a=0.764,
            nested_3v3_export_a=0.075,
            Seed_local_return_after_known_exports_a=0.925,
            unknown_export_return_path_sharing_not_zeroed=True,
            old_E19_passive_screen_assumes_Seed_a=0.5,
            older_legacy_screen_assumes_Seed_a=0.6,
            current_targets_not_reduced=True,
        ),
        R1=dict(
            native_ohm=0.47,
            initial_tolerance_fraction=0.01,
            initial_only_drop_at_1a_v=0.4747,
            initial_only_dissipation_at_1a_w=0.4747,
            MPN_TCR_hot_rating_aging_thermal_and_dynamic_qualified=False,
        ),
        remaining_holds=[
            "Complete P03/E28/E19/source-reference and externalAGND network embedding",
            "Actual external0.075Areturn sharing and GPIO/LED/SD/sensor currents",
            "Accepted copper/stack/material/wall/drill/etch/registration/tolerance bounds",
            "MeasuredB-face solderwire/joint and real J11/Seed contact resistance",
            "Real local effectiveC/ESR/PDNimpedance/loadstep/noise/EM/ampacity/temperature",
            "DownstreamLEDdriver/anode copper/header/wire and 20mVdynamic/2mVspread bounds",
        ],
        complete_endpoint_qualified=False,
        full_PDN_qualified=False,
        ampacity_noise_thermal_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (ROOT / "generated/summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print("SUMMARY", len(rows), "cases", len(refinement), "refinement comparisons")
    return report


if __name__ == "__main__":
    run()
