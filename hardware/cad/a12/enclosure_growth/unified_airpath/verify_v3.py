"""Pinned native checks of the new captured source32 unit and GND129 route."""

import argparse
import json
import subprocess
from pathlib import Path

from hardware.cad.a12.enclosure_growth.r1_local.stage import closure
from hardware.cad.a12.thermal.interior_airpath.verify import mesh, row_errors as boolean_row_errors
from .part_import import NAMES as IMPORT_NAMES, errors as import_errors

from .ground_route import ROOT, sha, write

def row_errors(n,row,spec,folder):
    return import_errors(n,row,folder) if n in IMPORT_NAMES else boolean_row_errors(n,row,spec,folder)


RUNNER=ROOT.parents[0]/"r1_local/linux_runner/openscad.py"


def specs():
    d={"new_ANA_return_geometry":dict(role="part"),"new_ANA_retention_geometry":dict(role="review"),
       "new_wire_pair_geometry":dict(role="review")}
    d.update({n:dict(role="empty") for n in ["ANA_return_C24_clearance_collision",
        "new_return_new_ground_collision","new_wire_pair_collision","new_wire_source_bore_collision",
        "new_wire_receiver_bore_collision","return_vs_PB_ANA_collision","return_vs_PB_DIG_collision",
        "return_vs_PB_support_collision","new_wire_components_collision","new_wire_controls_collision",
        "new_wire_case_collision","new_wire_return_hardware_collision","new_wire_PB_ANA_collision",
        "new_wire_PB_DIG_collision","new_wire_PB_support_collision","native_component_case_0p25_collision",
        "native_component_other_0p25_collision","native_boards_mutual_0p25_collision"]})
    d.update({n:dict(role="witness") for n in ["old_return_new_ground_failure","old_ground_source_bore_failure"]})
    d.update({n:dict(role="control",expected_volume=.008) for n in ["new_R1_control","new_ground_control","new_ANA_shift_control"]})
    d.update({"part_"+n:dict(role="part") for n in ["ANA_POST","ANA_CAP","DIG_POST","DIG_CAP"]})
    return d


def run(out,names=None):
    out=Path(out).resolve()
    if out.exists():
        raise RuntimeError("New native output destination required")
    cap=json.loads((ROOT/"capture.json").read_text())
    assert all(sha(ROOT/n)==h for n,h in cap["copied_input_sha256"].items())
    deriv=json.loads((ROOT/"generated/derivation.json").read_text())
    assert all(sha(ROOT/n)==h for n,h in deriv["derived_source_sha256"].items())
    runner_seal=json.loads((RUNNER.parent/"handoff.json").read_text())
    assert runner_seal["fresh_controls_passed"] and all(sha(RUNNER.parent/n)==h for n,h in runner_seal["files_sha256"].items())
    source=closure(ROOT/"generated/entry_v3.scad")
    for p in list((ROOT/"inputs/PB02-generated").glob("*.stl"))+list((ROOT/"return_variant2/generated").glob("*.stl")):
        source[p]=sha(p)
    for p in [ROOT/"capture.json",ROOT/"generated/derivation.json",ROOT/"generated/ground-route.json",
              Path(__file__),ROOT/"ground_route.py",ROOT/"derive.py",ROOT/"variant2_stage.py",ROOT/"part_import.py",ROOT/"generated/variant2-coverage.json",RUNNER.parent/"handoff.json"]:
        source[p]=sha(p)
    for n,h in runner_seal["files_sha256"].items():
        source[RUNNER.parent/n]=h
    assert all(p.is_relative_to(ROOT) or p.is_relative_to(RUNNER.parent) for p in source)
    cfg=json.loads((ROOT/"model/config.json").read_text())
    source[ROOT/"model/config.json"]=sha(ROOT/"model/config.json")
    definitions=specs();names=names or list(definitions)
    if any(n not in definitions for n in names):raise ValueError("Unknown case")
    out.mkdir(parents=True)
    rows={}
    for n in names:
        variables={k:"cp_only" for k in ["part","thermal_part","positive_part","candidate_case","trial","ui_case","eb_case","ps_case","cp_case"]}
        variables.update(fi_case="fi_only",fi_fa_case="fi_only",ht_case="none",ap_case="none",ua_case=n,
            body_width=334,body_depth=188.4,shell_height=45.6,panel_z=43.6,
            fasteners=cfg["fasteners"],board_mounts=cfg["mounts"],rear_ports=cfg["rear_ports"],openings=cfg["openings"])
        command=[str(RUNNER),"--hardwarnings","--backend","Manifold","--export-format","binstl"]
        for k,v in variables.items():command += ["-D",k+"="+json.dumps(v)]
        target=out/(n+".stl")
        command += ["-o",str(target),str(ROOT/"generated/entry_v3.scad")]
        result=subprocess.run(command,capture_output=True,text=True)
        (out/(n+".log")).write_text(result.stdout+result.stderr)
        row=dict(command=command,role=definitions[n]["role"],returncode=result.returncode,
                 statistics=mesh(target) if target.exists() else None)
        row["errors"]=row_errors(n,row,definitions[n],out);row["clear"]=not row["errors"]
        rows[n]=row
        changed=[str(p) for p,h in source.items() if sha(p)!=h]
        data=dict(revision="UA01-private-partial32",required_cases=names,cases=rows,
             complete_set=names==list(definitions),input_sha256={str(p):h for p,h in source.items()},
             artifact_sha256={str(p):sha(p) for p in out.iterdir() if p.suffix in [".log",".stl"]},
             changed_inputs=changed,all_requested_clear=all(r["clear"] for r in rows.values()) and not changed,
             E28_electrical_opens=32,latest_E28_development_adopted=False,
             new_groundroute_and_return_not_priorproof_inheritance=True,
             physical_qualified=False,thermal_qualified=False,electrical_qualified=False,fabrication_released=False,
             full_wiring_qualified=False,actual_NF_FH_boards_adopted=False)
        write(out/"verification.json",data)
        print(json.dumps(dict(case=n,clear=row["clear"],errors=row["errors"],volume=row["statistics"] and row["statistics"]["volume_mm3"])),flush=True)
    return data


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--outdir",required=True,type=Path);p.add_argument("--cases",nargs="+")
    args=p.parse_args();raise SystemExit(not run(args.outdir,args.cases)["all_requested_clear"])
