"""Exact pairwise-box owners for rejected receiving bounds; no physical-clash inflation."""

import json
from pathlib import Path

from .capture import ROOT, sha


def intersection(a, b, margin):
    lo = [max(a[i + 1] - margin, b[i + 1]) for i in range(3)]
    hi = [min(a[i + 1] + a[i + 4] + margin, b[i + 1] + b[i + 4]) for i in range(3)]
    delta = [v - u for u, v in zip(lo, hi)]
    if min(delta) <= 1e-8:
        return None
    return dict(mate=a[0], neighbor=b[0], low_mm=lo, high_mm=hi, volume_mm3=delta[0] * delta[1] * delta[2])


def build():
    target = ROOT / "generated/receiving-clash-owners.json"
    if target.exists():
        raise RuntimeError("New owner inventory required")
    model = ROOT / "generated/model233.json"
    d = json.loads(model.read_text())
    rows = []
    for a in d["mates"]:
        for b in d["boxes"]:
            if a[0] != b[0] and a[0].split("_")[0] == b[0].split("_")[0]:
                hit = intersection(a, b, 0.25)
                if hit:
                    rows.append(hit)
    proof = ROOT / "generated/native-matcher-fixed/verification.json"
    p = json.loads(proof.read_text())
    result = dict(
        mate_other_component_box_pairs=rows,
        actual_native_failures={n: r for n, r in p["cases"].items() if not r["clear"]},
        bounds_are_receiving_requirements_not_manufacturer_approved_maxima=True,
        bundle_failure_owner="Existing E28 growth-band PCB material Y159.1..163/Z5..6.62; opaque short-bundle box is not a routed wire",
        source_sha256={str(q): sha(q) for q in [Path(__file__), model, proof]},
        physical_qualified=False,
    )
    target.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    build()
