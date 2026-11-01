"""Independent OCC fit checks for intentional terminal/saddle assemblies."""

import json

from .caps import pieces
from .generate import OUT, ROOT, fasteners, load, sha, shape
from .support import parts


def main():
    d = load()
    checks = []
    for name in d["paths"]:
        cu = shape(d, name)
        for end in (0, 1):
            cap = pieces(d, name, end)
            main = fasteners(d, name, end)
            for half in ("HALF-A", "HALF-B"):
                for label, obj in [
                    ("copper", cu),
                    ("main-M3", main),
                    ("cross-screw", cap["CROSS-SCREW"]),
                    ("nut", cap["NUT"]),
                ]:
                    v = cap[half].intersect(obj).Volume()
                    checks.append(dict(id=f"{name}{end}-{half}-{label}", volume_mm3=v, clear=v < 1e-7))
            v = cap["HALF-A"].intersect(cap["HALF-B"]).Volume()
            checks.append(dict(id=f"{name}{end}-cap-halves", volume_mm3=v, clear=v < 1e-7))
    support = parts(d)
    for name in d["paths"]:
        keeper = support[name + "-SADDLE-KEEPER"]
        for i in (0, 1):
            v = keeper.intersect(support[name + "-SADDLE-SCREW" + str(i)]).Volume()
            checks.append(dict(id=name + "keeper-clearance-hole" + str(i), volume_mm3=v, clear=v < 1e-7))
        for i in (0, 1):
            v = shape(d, name).intersect(support[name + "-SADDLE-SCREW" + str(i)]).Volume()
            checks.append(
                dict(id=name + "saddle-metal-screw" + str(i) + "-copper", volume_mm3=v, clear=v < 1e-7)
            )
        for label, obj in [("pedestal", support["BONDED-PEDESTAL"]), ("keeper", keeper)]:
            v = shape(d, name).intersect(obj).Volume()
            checks.append(dict(id=name + label + "-copper", volume_mm3=v, clear=v < 1e-7))
    report = dict(
        source_sha256={
            q.name: sha(q)
            for q in [
                ROOT / "design.json",
                ROOT / "generate.py",
                ROOT / "caps.py",
                ROOT / "support.py",
                ROOT / "self_check.py",
            ]
        },
        checks=checks,
        all_declared_nominal_fits_clear=all(r["clear"] for r in checks),
        excluded_intersections="M1.6 male threads into PEEK tapped1.3mm minor bores and nuts are intentional nominal threaded mates; no helical/thread strength simulation",
        physical_fit_verified=False,
    )
    (OUT / "self-fit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
