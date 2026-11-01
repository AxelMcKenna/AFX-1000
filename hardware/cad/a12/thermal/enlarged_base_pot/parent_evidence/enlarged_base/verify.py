"""EB01 exact native artifacts, source freshness and fail-closed roles."""

import argparse
import json
import math
import struct
import subprocess
from collections import Counter

from .stage import OUT, ROOT, sha, write

SOLIDS = ["metal_geometry", "standalone_metal_geometry", "feet_geometry", "feet_assembly_geometry", "carrier_geometry", "attachment_geometry", "interface_geometry"]
REVIEW = ["retained_controls_review", "retained_electronics_review", "retained_wire_review", "retained_power_review", "lid_rear_review"]
EMPTY = [
    "metal_carrier_collision", "metal_electronics_collision", "metal_native_0p25_collision",
    "metal_controls_ports_collision", "metal_wire_collision", "metal_return_positive_collision",
    "lower_carrier_collision", "lower_metal_collision", "lower_electronics_collision",
    "lower_native_0p25_collision", "lower_controls_ports_collision", "lower_wire_collision",
    "lower_other_hardware_collision", "foot_screw_base_collision", "foot_screw_feet_collision",
    "foot_screw_carrier_collision", "foot_screw_other_collision", "feet_pin_collision",
    "interface_carrier_collision", "interface_components_collision", "interface_PCB_seat_collision",
    "interface_other_hardware_collision", "interface_wire_controls_collision",
]
EXACT_CONTROLS = ["front_material_positive_control", "new_bolt_material_positive_control", "foot_screw_positive_control", "interface_positive_control"]
CONTROLS = EXACT_CONTROLS + ["missing_new_bore_positive_control", "unrelieved_carrier_positive_control", "undersized_foot_countersink_positive_control"]
ALL = SOLIDS + EMPTY + CONTROLS + REVIEW


def mesh(path):
    data = path.read_bytes()
    assert len(data) >= 84, "Missing STL header"
    count = struct.unpack_from("<I", data, 80)[0]
    assert count > 0 and len(data) == 84 + 50 * count
    edges, terms, points = Counter(), [], []
    zero = 0
    for i in range(count):
        row = struct.unpack_from("<12fH", data, 84 + 50*i)
        a,b,c = (tuple(row[j:j+3]) for j in (3,6,9))
        assert all(math.isfinite(v) for p in (a,b,c) for v in p)
        cross = tuple((b[(k+1)%3]-a[(k+1)%3])*(c[(k+2)%3]-a[(k+2)%3])-(b[(k+2)%3]-a[(k+2)%3])*(c[(k+1)%3]-a[(k+1)%3]) for k in range(3))
        if sum(v*v for v in cross) < 1e-24:
            zero += 1
            continue
        for x,y in ((a,b),(b,c),(c,a)):
            edges[(x,y)] += 1
        points.extend([a,b,c])
        terms.append(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))
    assert points
    bad = sum(n != 1 or edges[(b,a)] != 1 for (a,b),n in edges.items())
    return dict(triangles=count, degenerate_triangles_excluded=zero, bad_directed_edges=bad,
        closed_oriented_boundary=bad==0, volume_mm3=abs(math.fsum(terms))/6,
        min_mm=[min(p[k] for p in points) for k in range(3)],max_mm=[max(p[k] for p in points) for k in range(3)])


def row_errors(name, row, output=OUT):
    errors = []
    target = output / (name + ".stl")
    logpath = output / (name + ".log")
    if not logpath.exists():
        return [name + ": missing log"]
    log = logpath.read_text()
    if "WARNING" in log or "ERROR" in log:
        errors.append(name + ": native warning/error")
    if name in EMPTY:
        if not (row["returncode"] == 1 and "Current top level object is empty." in log and not target.exists() and row.get("statistics") is None):
            errors.append(name + ": collision artifact not empty")
    elif name in SOLIDS + CONTROLS + REVIEW:
        if row["returncode"] != 0 or "NoError" not in log or not target.exists():
            errors.append(name + ": required NoError solid missing")
        else:
            m = mesh(target)
            if m != row.get("statistics"):
                errors.append(name + ": actual mesh disagrees with row")
            if m["volume_mm3"] <= .001 or (name not in REVIEW and (not m["closed_oriented_boundary"] or m["degenerate_triangles_excluded"] != 0)):
                errors.append(name + ": invalid/empty solid")
            if name in EXACT_CONTROLS and not math.isclose(m["volume_mm3"],.008,abs_tol=2e-6):
                errors.append(name + ": positive control is wrong volume")
            if name in CONTROLS and name not in EXACT_CONTROLS and m["volume_mm3"] < .1:
                errors.append(name + ": missing failure witness")
    else:
        errors.append(name + ": unknown role")
    return errors


def input_hashes():
    files = [ROOT / n for n in ["stage.py","geometry.scad","verify.py","capture.json","design.json"]]
    files += [OUT / n for n in ["analysis.json","scene.json","checks.scad","parts.scad"]]
    c = json.loads((ROOT / "capture.json").read_text())
    files += [ROOT / n for n in c["derived_context_sha256"]]
    files += [ROOT / "sources" / n for n in c["original_sha256"]]
    return {str(p.relative_to(ROOT)):sha(p) for p in files}


def run(executable, selected=None):
    names = selected or ALL
    assert all(n in ALL for n in names)
    inputs = input_hashes()
    scene = json.loads((OUT / "scene.json").read_text())
    rows = {}
    for name in names:
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        values = dict(part="eb_only",thermal_part="eb_only",positive_part="eb_only",candidate_case="eb_only",trial="eb_only",ui_case="eb_only",eb_case=name,
            body_width=334,body_depth=188.4,shell_height=45.6,panel_z=43.6,
            fasteners=scene["fasteners"],board_mounts=scene["mounts"],rear_ports=scene["rear_ports"])
        cmd = [str(executable),"--hardwarnings","--backend","Manifold","--export-format","binstl"]
        for k,v in values.items():
            cmd += ["-D",k+"="+json.dumps(v)]
        cmd += ["-o",str(target),str(OUT / "checks.scad")]
        p = subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        (OUT/(name+".log")).write_text(p.stdout+p.stderr)
        row = dict(returncode=p.returncode,statistics=mesh(target) if p.returncode==0 and target.exists() else None,command=cmd,
            role="retained-review-only-group" if name in REVIEW else "empty-collision" if name in EMPTY else "positive-control" if name in CONTROLS else "production-part",
            inherited_group_is_manufacturable_part=False if name in REVIEW else None)
        row["errors"] = row_errors(name,row)
        row["clear"] = not row["errors"]
        rows[name] = row
        changed = [n for n,h in inputs.items() if sha(ROOT/n)!=h]
        result = dict(scope=__doc__,cases=rows,requested_cases=names,complete_required_case_set=names==ALL,
            input_sha256=inputs,changed_inputs=changed,all_requested_native_checks_clear=not changed and all(r["clear"] for r in rows.values()),
            artifact_sha256={str(p.relative_to(ROOT)):sha(p) for n in rows for p in [OUT/(n+".log"),OUT/(n+".stl")] if p.exists()},
            physical_qualified=False,thermal_qualified=False,fabrication_released=False,structural_qualified=False)
        write(OUT / "verification.json",result)
        print(json.dumps(dict(case=name,clear=row["clear"],errors=row["errors"],volume=row["statistics"]["volume_mm3"] if row["statistics"] else None)),flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad",required=True)
    parser.add_argument("--cases",nargs="*")
    args = parser.parse_args()
    result = run(args.openscad,args.cases)
    raise SystemExit(0 if result["all_requested_native_checks_clear"] else 1)
