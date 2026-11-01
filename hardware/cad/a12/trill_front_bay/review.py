"""Independent standard-library evidence and fit-contract checks for TC02."""

import hashlib
import json
import math
import struct
from collections import Counter

from .build import OUT, REPO, ROOT
from .verify import CONTROL, EMPTY, SOLIDS, WITNESS


def mesh(data):
    n = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84 + 50 * n:
        raise ValueError("STL size")
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    vol = 0.0
    edges = Counter()
    vertices = set()
    collapsed = 0
    for i in range(n):
        row = struct.unpack_from("<12fH", data, 84 + 50 * i)
        v = [tuple(row[j : j + 3]) for j in [3, 6, 9]]
        if not all(math.isfinite(x) for p in v for x in p):
            raise ValueError("nonfinite vertex")
        collapsed += len(set(v)) != 3
        vertices.update(v)
        for p in v:
            for k in range(3):
                lo[k] = min(lo[k], p[k])
                hi[k] = max(hi[k], p[k])
        a, b, c = v
        vol += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + a[1] * (b[2] * c[0] - b[0] * c[2])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6
        for a, b in zip(v, v[1:] + v[:1]):
            edges[tuple(sorted([a, b]))] += 1
    return dict(
        triangles=n,
        min_mm=lo,
        max_mm=hi,
        volume_mm3=abs(vol),
        edges_not_two=sum(v != 2 for v in edges.values()),
        collapsed=collapsed,
        vertex_count=len(vertices),
    )


def errors(meta=None, native=None, overrides=None, check_live=True):
    m = meta if meta is not None else json.loads((OUT / "analysis.json").read_text())
    n = native if native is not None else json.loads((OUT / "verification.json").read_text())
    override = overrides or {}
    out = []

    def read(p):
        rel = str(p.relative_to(REPO))
        return override[rel] if rel in override else p.read_bytes() if p.is_file() else None

    def hashok(p, h):
        b = read(p)
        return b is not None and hashlib.sha256(b).hexdigest() == h

    for name, h in n["source_sha256"].items():
        if not hashok(ROOT / "sources" / name, h):
            out.append("captured source " + name)
        if check_live and not hashok(REPO / name, h):
            out.append("live source " + name)
    for group in ["execution_inputs_sha256", "artifact_sha256"]:
        for name, h in n[group].items():
            if not hashok(REPO / name, h):
                out.append(group + " " + name)
    expected = SOLIDS + EMPTY + WITNESS + CONTROL
    if set(n.get("cases", {})) != set(expected):
        out.append("case coverage")
    if n.get("changed_inputs"):
        out.append("stale native run")
    for name, row in n.get("cases", {}).items():
        logbytes = read(OUT / (name + ".log"))
        b = read(OUT / (name + ".stl"))
        if logbytes is None:
            out.append("missing log " + name)
            continue
        log = logbytes.decode()
        clean = not any(s in log for s in ["WARNING", "ERROR"])
        if not clean:
            out.append("unclean " + name)
        if name in EMPTY:
            if (
                b is not None
                or not row["empty"]
                or row["returncode"] != 1
                or "Current top level object is empty." not in log
                or not row["geometry_clear"]
            ):
                out.append("empty collision " + name)
        else:
            if b is None:
                out.append("missing mesh " + name)
                continue
            a = mesh(b)
            saved = row.get("statistics")
            if not isinstance(saved, dict):
                out.append("missing metadata " + name)
                continue
            if (
                not math.isclose(a["volume_mm3"], saved["volume_mm3"], abs_tol=1e-6)
                or a["triangles"] != saved["triangles"]
                or a["min_mm"] != saved["min_mm"]
                or a["max_mm"] != saved["max_mm"]
            ):
                out.append("actual mesh metadata " + name)
            if row["empty"] or row["returncode"] != 0 or row["geometry_clear"]:
                out.append("nonempty row " + name)
            if name == "growth_slab_geometry":
                good = (
                    "3D object (PolySet)" in log
                    and any(l.strip().split() == ["Convex:", "yes"] for l in log.splitlines())
                    and a["edges_not_two"] == 0
                    and a["collapsed"] == 0
                    and a["vertex_count"] == 8
                    and math.isclose(a["volume_mm3"], 151 * 9.25 * 2.1, abs_tol=0.001)
                    and all(
                        math.isclose(x, y, abs_tol=0.00003) for x, y in zip(a["min_mm"], [13, 153.75, 4.8])
                    )
                    and all(math.isclose(x, y, abs_tol=0.00003) for x, y in zip(a["max_mm"], [164, 163, 6.9]))
                )
                if not good or not row.get("named_primitive_topology_and_dimensions_verified"):
                    out.append("named primitive proof")
            elif "NoError" not in log or not row["native_NoError"]:
                out.append("missing NoError " + name)
            if name in CONTROL and not math.isclose(a["volume_mm3"], 0.008, abs_tol=1e-6):
                out.append("control " + name)
            if a["volume_mm3"] <= 0.001:
                out.append("missing volume " + name)
        if not row.get("evidence_valid"):
            out.append("rejected evidence " + name)
    if m.get("origin_mm") != [82, 158, 20] or m.get("mount_centres_mm") != [
        [130.0871, 168.922],
        [93.0871, 168.9352],
    ]:
        out.append("pose")
    if (
        m.get("proposed_minimum_bore_acceptance_requirement_mm") != 3.1
        or m.get("minimum_bore_manufacturer_guaranteed") is not False
    ):
        out.append("bore requirement provenance")
    if not math.isclose(m.get("nominal_requirement_radial_margin_mm", 0), 0.095, abs_tol=1e-12):
        out.append("primary fit margin")
    if not math.isclose(m.get("rejected_sensitivity_radial_margin_mm", 0), -0.005, abs_tol=1e-12):
        out.append("sensitivity margin")
    if (
        n.get("relative_0p3_sensitivity_accepted") is not False
        or n.get("panel_and_guide_installed_tool_access_clear") is not False
    ):
        out.append("adverse cases falsely accepted")
    if not n.get("all_required_evidence_valid") or not n.get("all_primary_empty_checks_clear"):
        out.append("primary evidence failed")
    for key in ["physical_qualified", "thermal_qualified", "electrical_qualified", "fabrication_released"]:
        if m.get(key) is not False or n.get(key) is not False:
            out.append("false claim " + key)
    return out


if __name__ == "__main__":
    found = errors()
    print(
        json.dumps(
            dict(
                errors=found,
                primary_geometry_screen_clear=not found,
                relative_0p3_accepted=False,
                guide_installed_tool_access=False,
                physical_qualified=False,
            )
        )
    )
    raise SystemExit(bool(found))
