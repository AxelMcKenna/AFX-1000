"""Isolate saved receiving collisions without changing tested geometry."""

import json
import math

from .capture import ROOT, sha, write


def intersection(a, b, margin=0):
    lo = [max(a[i + 1] - margin, b[i + 1]) for i in range(3)]
    hi = [min(a[i + 1] + a[i + 4] + margin, b[i + 1] + b[i + 4]) for i in range(3)]
    if any(hi[i] <= lo[i] + 1e-10 for i in range(3)):
        return None
    return dict(min_mm=lo, max_mm=hi, volume_mm3=math.prod(hi[i] - lo[i] for i in range(3)))


def build():
    path = ROOT / "generated/pair-audit.json"
    if path.exists():
        raise RuntimeError("New diagnostic output required")
    data = json.loads((ROOT / "generated/model.json").read_text())
    pairs = []
    for family in ["mates", "tails"]:
        for a in data[family]:
            for b in data["boxes"]:
                if (
                    a[0].split("_")[0] != b[0].split("_")[0]
                    or (family == "mates" and a[0] == b[0])
                    or (family == "tails" and b[2] <= 180.5)
                ):
                    continue
                hit = intersection(a, b, 0.25)
                if hit:
                    pairs.append(
                        dict(
                            family=family,
                            a=a,
                            b=b,
                            nominal_intersection=intersection(a, b),
                            receiving_margin_mm=0.25,
                            receiving_intersection=hit,
                            meaning="conservative declared courtyard/pad-and-fillet receiving envelopes; not direct measured body collision",
                        )
                    )
    write(
        path,
        dict(
            pairs=pairs,
            source_sha256={
                str(ROOT / "generated/model.json"): sha(ROOT / "generated/model.json"),
                str(__file__): sha(__import__("pathlib").Path(__file__)),
            },
            geometry_changed=False,
            physical_qualified=False,
        ),
    )
    print(
        json.dumps(
            dict(pairs=len(pairs), nominal_nonempty=sum(p["nominal_intersection"] is not None for p in pairs))
        )
    )


if __name__ == "__main__":
    build()
