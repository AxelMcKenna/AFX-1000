"""Tight-sample selected coarse/refined pairs without editing shared profiles."""

import json
import math
from pathlib import Path

from search import ROOT, individual, inputs, pair_gap, profile, public, sha


def run():
    coarse = json.loads((ROOT / "coarse.json").read_text())
    refined = json.loads((ROOT / "refined.json").read_text())
    candidates = [("coarse-native-candidate", coarse["recommended_pairs"][0])] + [
        (f"refined-{i + 1}", p) for i, p in enumerate(refined["recommended_pairs"][:5])
    ]
    parameters = {}
    for _, pair in candidates:
        for label in ["positive", "return"]:
            p = pair[label]
            parameters[p["id"]] = (p["pin"], p["radius_mm"], p["angle_deg"], p["endplane_mm"])
    checked = individual([profile(*args, 0.02) for args in parameters.values()], inputs())
    byid = {p["id"]: p for p in checked}
    results = []
    for name, pair in candidates:
        a, b = [byid[pair[label]["id"]] for label in ["positive", "return"]]
        gap, detail = pair_gap(a, b)
        minimum = min(
            gap, *a["clearance_lower_estimates_mm"].values(), *b["clearance_lower_estimates_mm"].values()
        )
        assert minimum > 0
        result = dict(
            name=name,
            profiles=[
                ["1", "5V_DIG", a["angle_deg"], a["radius_mm"], a["endplane_mm"]],
                ["2", "AGND", b["angle_deg"], b["radius_mm"], b["endplane_mm"]],
            ],
            positive=public(a),
            return_profile=public(b),
            pair_margin_mm=gap,
            pair_nearest=detail,
            minimum_margin_mm=minimum,
            sampled_clear=True,
            native_validation_completed=False,
        )
        results.append(result)
    paths = [
        ROOT / "search.py",
        Path(__file__),
        ROOT / "capture.json",
        ROOT / "coarse.json",
        ROOT / "refined.json",
        ROOT / "reference-check.json",
        ROOT / "outside-witness.json",
    ] + sorted((ROOT / "inputs").iterdir())
    report = dict(
        scope=__doc__,
        selected_candidates=results,
        source_evidence_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths if p.is_file()},
        tight_arc_length_sample_step_mm=0.02,
        receiver_ear_begins_world_X_mm=180,
        maximum_possible_quarter_envelope_X_mm=161
        + 16
        + (1.7526 / 2 + 0.65 + 0.25 + 0.005) / math.cos(math.pi / 64) ** 2
        + 16 * (math.pi / 240) ** 2 / 8,
        receiver_ear_body_cannot_intersect_this_bounded_quarter_search=True,
        new_whole_route_to_receiver_still_required=True,
        clipped_return_mesh_contact_topology_recorded=True,
        signed_distance_alone_not_a_manifold_certificate=True,
        outside_witness_plus_positive_surface_sample_cover_required=True,
        source_joint_bare_cut_bore_full_native_validation_required=True,
        native_geometry_pass=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (ROOT / "selected-refined-pairs.json").write_text(json.dumps(report, indent=2) + "\n")
    for r in results:
        print(
            "TIGHT",
            r["name"],
            r["profiles"],
            "min",
            r["minimum_margin_mm"],
            "pair",
            r["pair_margin_mm"],
            flush=True,
        )


if __name__ == "__main__":
    run()
