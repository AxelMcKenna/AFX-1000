"""Per-component OCC diagnostics for native-positive collision investigation."""

import json

from .generate import OUT


def main():
    import cadquery as cq

    p = json.loads((OUT / "obstacles.json").read_text())
    findings = []
    bars = {
        n: cq.importers.importStep(str(OUT / (n + "-COVERED-ENVELOPE.step"))).val() for n in ("ANA", "DIG")
    }
    for name, bar in bars.items():
        bb = bar.BoundingBox()
        rows = (
            [("native", r) for r in p["boxes"]]
            + [("other", r) for r in p["other_boxes"]]
            + [("switch conservative diagnostic AABB", r) for r in p.get("switch_diagnostic_boxes", [])]
        )
        for group, r in rows:
            _, x, y, z, w, h, t, *_ = r
            if (
                x - 0.35 > bb.xmax
                or x + w + 0.35 < bb.xmin
                or y - 0.35 > bb.ymax
                or y + h + 0.35 < bb.ymin
                or z - 0.35 > bb.zmax
                or z + t + 0.35 < bb.zmin
            ):
                continue
            body = cq.Solid.makeBox(w + 0.7, h + 0.7, t + 0.7, cq.Vector(x - 0.35, y - 0.35, z - 0.35))
            hit = bar.intersect(body)
            v = hit.Volume()
            if v > 1e-6:
                findings.append(dict(bar=name, ref=r[0], group=group, volume_mm3=v, box=r[:7]))
        for r in p["cylinders"]:
            _, x, y, z, d, h = r
            if (
                x - d / 2 - 0.35 > bb.xmax
                or x + d / 2 + 0.35 < bb.xmin
                or y - d / 2 - 0.35 > bb.ymax
                or y + d / 2 + 0.35 < bb.ymin
                or z - 0.35 > bb.zmax
                or z + h + 0.35 < bb.zmin
            ):
                continue
            hit = bar.intersect(cq.Solid.makeCylinder(d / 2 + 0.35, h + 0.7, cq.Vector(x, y, z - 0.35)))
            if hit.Volume() > 1e-6:
                findings.append(
                    dict(bar=name, ref=r[0], group="native cylinder", volume_mm3=hit.Volume(), cylinder=r)
                )
    (OUT / "component-diagnostics.json").write_text(json.dumps(findings, indent=2) + "\n")
    print(json.dumps(findings, indent=2))


if __name__ == "__main__":
    main()
