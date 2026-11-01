"""Check proposed nominal bolt-seat masks against every actual raw facet."""

import json
import math
import struct

from .stage import OUT, ROOT, sha, write


def build():
    output = OUT / "raw-mating-bolt-domain-audit.json"
    if (ROOT / "handoff.json").exists() or output.exists():
        raise RuntimeError("Guard-domain audit is immutable")
    result = {}
    for name, axes, r, centres in [
        (
            "M3_hardware_nominal_mates",
            (0, 1),
            3.71,
            [(p[0] + x, p[1] + y) for p in [[80, 165.5], [254, 165.5]] for x in [-16, 16] for y in [-16, 16]],
        ),
        ("M2_hardware_nominal_mates", (0, 2), 2.73, [(x + dx, -8.9) for x in [80, 254] for dx in [-7, 7]]),
    ]:
        p = OUT / "mating-raw" / (name + ".stl")
        b = p.read_bytes()
        n = struct.unpack_from("<I", b, 80)[0]
        worst = 0
        bad = []
        for i in range(n):
            raw = struct.unpack_from("<12fH", b, 84 + 50 * i)
            tri = [raw[3:6], raw[6:9], raw[9:12]]
            actual = min(max(math.hypot(v[axes[0]] - cx, v[axes[1]] - cy) for v in tri) for cx, cy in centres)
            worst = max(worst, actual)
            if actual > r:
                bad.append(i)
        result[name] = dict(
            raw_triangles=n,
            proposed_guard_radius=r,
            max_actual_triangle_radius=worst,
            uncontained_triangles=bad,
            raw_STL_sha256=sha(p),
        )
    write(
        output,
        dict(
            cases=result,
            all_raw_bolt_facets_inside_proposed_local_masks=all(
                not r["uncontained_triangles"] for r in result.values()
            ),
            source_sha256={
                "guard_domain_audit.py": sha(ROOT / "guard_domain_audit.py"),
                "mating.scad": sha(ROOT / "mating.scad"),
            },
            physical_qualified=False,
        ),
    )
    print(json.dumps(result))


if __name__ == "__main__":
    build()
