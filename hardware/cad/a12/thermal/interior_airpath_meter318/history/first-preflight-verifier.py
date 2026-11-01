"""Actual AP03 native checks, preserving all execution/mesh failures."""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh
from hardware.cad.a12.thermal.interior_airpath.verify import row_errors as parent_row_errors

from .stage import MODEL, OUT, ROOT, require_parent, sha, write


def specs():
    result = {n:dict(role="part") for n in ["base_geometry","tray_geometry","upper_gasket_geometry",
              "meter_plate_geometry","meter_gasket_geometry","new_aperture_area"]}
    result.update({n:dict(role="empty") for n in [
        "fan_baffle_collision","meter_fan_collision","pins_baffle_collision","meter_pins_collision",
        "fan_tray_collision","tray_base_collision","new_added_case_collision",
        "nominal_pressure_boundary_void_collision","feedthrough_fan_collision","feedthrough_pin_collision",
        "new_meter_to_bolt_seal_collision","new_aperture_interior_blockage"] + ["new_added_obstacle_"+str(i) for i in range(5)]})
    result.update({n:dict(role="control",expected_volume=.008) for n in [
        "approach_core_positive_control","new_meter_border_control","feedthrough_positive_control",
        "retained_pin_control","new_pin_void_collision_control"]})
    result["approach_core_solid_intersection"] = dict(role="witness")
    result["approach_top_intrusion"] = dict(role="witness")
    result["missing_feedthrough_failure_witness"] = dict(role="witness")
    return result


def row_errors(n, row, spec, folder):
    if n not in ["upper_gasket_geometry","new_aperture_area"]:
        return parent_row_errors(n,row,spec,folder)
    log = (folder/(n+".log")).read_text()
    p=folder/(n+".stl")
    if row["returncode"] or not p.exists() or "WARNING" in log or "ERROR" in log:
        return ["missing-or-failed-primitive"]
    m=mesh(p)
    expected = 2*(2*(76+51.4)-8)*.5 + 2*(2*(49+51.4)-8)*.5 if n=="upper_gasket_geometry" else (160-(4-48*math.sin(2*math.pi/96)))*.1
    bounds = [[36,137,-6.7],[278.5,188.4,-6.2]] if n=="upper_gasket_geometry" else [[0,0,0],[16,10,.1]]
    bad=[]
    if "NoError" not in log and "Top level object is a 3D object (PolySet)" not in log:
        bad.append("unrecognized-primitive-status")
    if m!=row["statistics"] or not m["closed_oriented_boundary"] or m["degenerate_triangles_excluded"]:
        bad.append("invalid-actual-primitive")
    if not math.isclose(m["volume_mm3"],expected,abs_tol=.002):
        bad.append("wrong-actual-primitive-volume")
    if any(abs(a-b)>1e-4 for x,y in zip([m["min_mm"],m["max_mm"]],bounds) for a,b in zip(x,y)):
        bad.append("wrong-actual-primitive-bounds")
    return bad


def run(runner, output, names=None):
    output=Path(output).resolve()
    if output.exists():
        raise RuntimeError("New native evidence destination required")
    require_parent()
    capture=json.loads((ROOT/"capture.json").read_text())
    if any(sha(ROOT/n)!=h for n,h in capture["source_sha256"].items()):
        raise RuntimeError("Captured candidate source changed")
    executable=Path(runner).resolve()
    sealpath=executable.parent/"handoff.json"
    seal=json.loads(sealpath.read_text())
    if not seal["fresh_controls_passed"] or any(sha(executable.parent/n)!=h for n,h in seal["files_sha256"].items()):
        raise RuntimeError("Unverified runner")
    definitions=specs()
    names=names or list(definitions)
    if any(n not in definitions for n in names):
        raise ValueError("Unknown actual native case")
    files={str(ROOT/n):h for n,h in capture["source_sha256"].items()}
    for p in [ROOT/"capture.json",ROOT/"verify.py",sealpath,executable]:
        files[str(p)]=sha(p)
    output.mkdir(parents=True)
    cases={}
    for n in names:
        target=output/(n+".stl")
        command=[str(executable),"--backend=Manifold","--hardwarnings","-o",str(target),"-D",'ap_case='+json.dumps(n),str(OUT/"checks.scad")]
        p=subprocess.run(command,capture_output=True,text=True)
        (output/(n+".log")).write_text(p.stdout+p.stderr)
        row=dict(command=command,role=definitions[n]["role"],returncode=p.returncode,
                 statistics=mesh(target) if target.exists() else None)
        row["errors"]=row_errors(n,row,definitions[n],output)
        row["clear"]=not row["errors"]
        cases[n]=row
        changed=[n for n,h in files.items() if sha(Path(n))!=h]
        result=dict(revision="AP03",required_cases=names,cases=cases,complete_set=names==list(definitions),
                    all_requested_clear=all(r["clear"] for r in cases.values()) and not changed,
                    changed_inputs=changed,input_sha256=files,
                    artifact_sha256={str(q):sha(q) for q in output.iterdir() if q.suffix in [".log",".stl"]},
                    runner_image=seal["image"],physical_qualified=False,thermal_qualified=False,
                    installed_flow_verified=False,fabrication_released=False)
        write(output/"verification.json",result)
        print(json.dumps(dict(case=n,clear=row["clear"],errors=row["errors"],volume=row["statistics"] and row["statistics"]["volume_mm3"])),flush=True)
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--openscad",required=True)
    p.add_argument("--outdir",required=True,type=Path)
    p.add_argument("--cases",nargs="+")
    args=p.parse_args()
    raise SystemExit(not run(args.openscad,args.outdir,args.cases)["all_requested_clear"])
