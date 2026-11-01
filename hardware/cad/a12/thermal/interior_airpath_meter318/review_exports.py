"""Fresh moved-family exports; unchanged review families remain AP02-bound."""

import json
import subprocess
from pathlib import Path

from .stage import OUT, ROOT, sha, write
from .verify import mesh, row_errors

NAMES=["assembly_all_gaskets","assembly_meter_hardware","feedthrough_receiving_geometry"]


def build():
    folder=OUT/"review-exports"
    if folder.exists() or (ROOT/"handoff.json").exists():
        raise RuntimeError("New export destination required")
    main=json.loads((OUT/"current-native/verification.json").read_text())
    if not main["all_requested_clear"] or not main["complete_set"]:
        raise RuntimeError("Complete actual source checks required")
    bindings=dict(main["input_sha256"])
    for p in [ROOT/"review_exports.py",OUT/"current-native/verification.json"]:
        bindings[str(p)]=sha(p)
    if any(sha(Path(p))!=v for p,v in bindings.items()):
        raise RuntimeError("Changed source")
    base=main["cases"]["tray_geometry"]["command"]
    base=base[:base.index("-o")]
    folder.mkdir()
    rows={}
    for n in NAMES:
        command=list(base)
        command[command.index('ap_case="tray_geometry"')]='ap_case='+json.dumps(n)
        target=folder/(n+".stl")
        command += ["-o",str(target),str(OUT/"current-checks.scad")]
        p=subprocess.run(command,capture_output=True,text=True)
        (folder/(n+".log")).write_text(p.stdout+p.stderr)
        row=dict(role="review",returncode=p.returncode,command=command,statistics=mesh(target) if target.exists() else None)
        row["errors"]=row_errors(n,row,dict(role="review"),folder)
        row["clear"]=not row["errors"]
        rows[n]=row
        result=dict(cases=rows,input_sha256=bindings,
                    artifact_sha256={str(q):sha(q) for q in folder.iterdir() if q.suffix in [".log",".stl"]},
                    changed_inputs=[n for n,v in bindings.items() if sha(Path(n))!=v],
                    all_requested_clear=all(r["clear"] for r in rows.values()),
                    full_native_replay_of_unchanged_AP02_families_claimed=False)
        write(folder/"verification.json",result)
        print(json.dumps(dict(case=n,clear=row["clear"],errors=row["errors"])),flush=True)
    if result["changed_inputs"] or not result["all_requested_clear"]:
        raise RuntimeError("Failed/stale review export")


if __name__=="__main__":
    build()
