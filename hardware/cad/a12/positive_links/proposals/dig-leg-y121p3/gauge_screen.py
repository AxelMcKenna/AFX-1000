"""Equivalent empty-intersection test, moving box dilation to the simple lug.

For symmetric axis-aligned boxes C(a), C(b):
(A+C(a)) intersects (B+C(b)) iff (A+C(a+b)) intersects B.
This equivalence concerns existence only, not the volume of intersections.
The .9 mm attachment allocation and .1 mm positive position are both retained.
"""

import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]


def main():
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("pb_capture", ROOT / "native.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    sha = module.sha
    a = json.loads((ROOT / "native/inputs.json").read_text())
    out = ROOT / "gauge-screen"
    assert not out.exists()
    out.mkdir()
    sources = {**a["source_sha256"], **a["context_sha256"]}
    for p in [
        Path(__file__),
        ROOT / "native/checks.scad",
        ROOT / "native/gauge-derived.scad",
        ROOT / "native/inputs.json",
    ]:
        sources[str(p.relative_to(REPO))] = sha(p)
    assert all(sha(REPO / n) == h for n, h in sources.items())
    scene = "include <" + str(ROOT / "native/checks.scad") + ">\n"
    scene += """
gs_case="none";
module gs_gauge(m){let($fn=96)minkowski(){union(){lug();washer_head();}cube([2*m,2*m,2*m],center=true);}}
if(gs_case=="complete_attachment_positive_collision")intersection(){gs_gauge(1);pb_all();}
if(gs_case=="complete_attachment_original_positive_witness")intersection(){gs_gauge(.9);let($fn=96)positive_hardware();}
if(gs_case=="attachment_control")intersection(){gs_gauge(1);translate([131.9,136.4,15.5])cube([.2,.2,.2]);}
"""
    source = out / "checks.scad"
    source.write_text(scene)
    sources[str(source.relative_to(REPO))] = sha(source)
    cases = {}
    for name in [
        "complete_attachment_original_positive_witness",
        "complete_attachment_positive_collision",
        "attachment_control",
    ]:
        target = out / (name + ".stl")
        cmd = [
            "/private/tmp/rmx-openscad-mounted/OpenSCAD.app/Contents/MacOS/OpenSCAD",
            "--hardwarnings",
            "--backend",
            "Manifold",
            "--export-format",
            "binstl",
        ]
        for definition in a["definitions"] + ['pb_case="none"', "gs_case=" + json.dumps(name)]:
            cmd += ["-D", definition]
        cmd += ["-o", str(target), str(source)]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        log = run.stdout + run.stderr
        (out / (name + ".log")).write_text(log)
        stats = binary_stl(target) if target.exists() else None
        empty = run.returncode == 1 and "Current top level object is empty." in log and stats is None
        expected_empty = name.endswith("_collision")
        ok = "ERROR" not in log and "WARNING" not in log
        ok &= (
            empty
            if expected_empty
            else run.returncode == 0 and "NoError" in log and stats and stats["volume_mm3"] > 0
        )
        if name.endswith("_control") and stats:
            ok &= math.isclose(stats["volume_mm3"], 0.008, abs_tol=2e-6)
        if name.endswith("_witness") and stats:
            ok &= math.isclose(stats["volume_mm3"], 2.1002543527357744, abs_tol=2e-5)
        cases[name] = dict(
            passed=bool(ok),
            expected_empty=expected_empty,
            empty=empty,
            returncode=run.returncode,
            statistics=stats,
            command=cmd,
        )
        print(name, bool(ok), stats and stats["volume_mm3"], flush=True)
    changed = [n for n, h in sources.items() if sha(REPO / n) != h]
    result = dict(
        scope=__doc__,
        source_sha256=sources,
        cases=cases,
        changed_inputs=changed,
        complete_attachment_positive_geometric_screen_passed=not changed
        and all(x["passed"] for x in cases.values()),
        intersection_volume_equivalence_claimed=False,
        all_remaining_PB02_context_screens_complete=False,
        physical_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
        artifact_sha256={
            str(p.relative_to(REPO)): sha(p) for p in out.iterdir() if p.suffix in [".stl", ".log"]
        },
    )
    (out / "verification.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
