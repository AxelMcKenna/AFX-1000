"""Bounded cubic-return alternatives; sampled radius is ranking only until certified."""

import json
import math

import numpy as np

from . import search
from .bezier import certificate


def main():
    positive = [
        r
        for r in json.loads((search.OUT / "lift-individual-1.json").read_text())["screened"]
        if r["sample_cover_clear"]
    ]
    source = json.loads((search.OUT / "lift-search-7mm.json").read_text())["source_profiles"]
    p = source["2"]
    p0 = np.array(p["endpoint_mm"])
    phi = math.radians(p["angle_deg"])
    heading = np.array([math.cos(phi), math.sin(phi), 0])
    p3 = np.array([188, 104, 15.1])
    t = np.linspace(0, 1, 161)[:, None]
    rows = []
    for s in np.arange(6, 25.01, 0.5):
        for r in np.arange(6, 20.01, 0.5):
            cp = np.array([p0, p0 + s * heading, p3 + [0, 0, r], p3])
            v = 3 * (
                (1 - t) ** 2 * (cp[1] - cp[0]) + 2 * (1 - t) * t * (cp[2] - cp[1]) + t * t * (cp[3] - cp[2])
            )
            a = 6 * ((1 - t) * (cp[2] - 2 * cp[1] + cp[0]) + t * (cp[3] - 2 * cp[2] + cp[1]))
            k = np.linalg.norm(np.cross(v, a), axis=1) / np.linalg.norm(v, axis=1) ** 3
            radius = 1 / k.max()
            if radius > 9.85:
                rows.append(
                    dict(
                        kind="cubic_bezier",
                        control_points_mm=cp.tolist(),
                        start=p0.tolist(),
                        finish=p3.tolist(),
                        initial_handle_mm=float(s),
                        final_handle_mm=float(r),
                        sampled_radius_estimate_mm=float(radius),
                        continuous_radius_certified=False,
                        analytic_length_upper_mm=float(
                            np.linalg.norm(np.diff(cp, axis=0), axis=1).sum() + 1e-9
                        ),
                    )
                )
    print("Cubic return analytic-control candidates", len(rows), flush=True)
    screened = search.individual(rows, search.obstacles(), 0.15)
    clear = [r for r in screened if r["sample_cover_clear"]]
    (search.OUT / "cubic-return-individual.json").write_text(
        json.dumps(dict(screened=screened, clear=len(clear)), indent=2) + "\n"
    )
    print("Cubic return clear", len(clear), flush=True)
    pairs = []
    best = None
    for a in positive:
        for b in clear:
            gap, nearest = search.pair(a, b, source, 0.1)
            if best is None or gap > best["pair_margin_mm"]:
                best = dict(pair_margin_mm=gap, positive=a, return_profile=b, pair_nearest=nearest)
            if gap > 0:
                pairs.append(
                    dict(
                        positive=a,
                        return_profile=b,
                        pair_margin_mm=gap,
                        pair_nearest=nearest,
                        minimum_margin_mm=min(
                            gap,
                            *a["clearance_lower_estimates_mm"].values(),
                            *b["clearance_lower_estimates_mm"].values(),
                        ),
                    )
                )
    pairs.sort(key=lambda r: -r["minimum_margin_mm"])
    for row in pairs[:16]:
        proof = certificate(row["return_profile"]["control_points_mm"], search.MIN_R)
        row["return_profile"]["curvature_certificate"] = proof
        row["return_profile"]["continuous_radius_certified"] = proof["certified"]
        row["return_profile"]["minimum_continuous_radius_lower_mm"] = proof["radius_lower_mm"]
    report = dict(
        positive_candidates=len(positive),
        cubic_return_clear=len(clear),
        clear_pairs=len(pairs),
        recommended_pairs=pairs[:16],
        best_pair=best,
        source_profiles=source,
        native_route_verified=False,
        physical_fit_verified=False,
    )
    (search.OUT / "cubic-pairs.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "clear pairs",
        len(pairs),
        "best",
        pairs[0]["minimum_margin_mm"] if pairs else best["pair_margin_mm"],
        flush=True,
    )


if __name__ == "__main__":
    main()
