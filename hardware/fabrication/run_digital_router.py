"""Bounded digital routing with explicit outer-layer constraints."""

import argparse
import json
import subprocess
import time
import uuid
from pathlib import Path

from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
WORK = ROOT/"staging/digital-signal-routing-03"
IMAGE = "ghcr.io/freerouting/freerouting@sha256:146ab8ecfe78a6c21ba017218d7c0e89a02fbf7018243b562b0794c740f3de9f"


def run():
    global WORK
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace",default=WORK.name)
    parser.add_argument("--passes",type=int,default=16)
    args = parser.parse_args()
    assert args.workspace and all(c.isalnum() or c in "-_" for c in args.workspace)
    assert 1 <= args.passes <= 64
    WORK = WORK.parent/args.workspace
    receipt = WORK/"router-command.json"
    assert not receipt.exists()
    source = json.loads((WORK/"export.json").read_text())
    assert sha(WORK/"routing-view.dsn") == source["routing_DSN_sha256"]
    name = "afx-dc-router-"+uuid.uuid4().hex[:12]
    command = ["docker","run","--rm","--pull=never","--name",name,"--platform","linux/arm64",
        "--network","none","--read-only","--cap-drop","ALL","--security-opt","no-new-privileges=true",
        "--memory","2g","--cpus","2","--pids-limit","192","--user","501:20",
        "--tmpfs","/tmp:rw,nosuid,size=256m,mode=1777","--env","HOME=/tmp",
        "--mount","type=bind,source="+str(WORK)+",target=/work","--workdir","/work",
        "--entrypoint","java",IMAGE,"-Xmx1024m","-XX:ActiveProcessorCount=2",
        "-Djava.awt.headless=true","-Duser.home=/tmp","-Djava.util.prefs.userRoot=/tmp/prefs",
        "-jar","/app/freerouting-executable.jar","-de","/work/routing-view.dsn","-do","/work/routed.ses",
        "--user_data_path=/work/config","-da","--gui.enabled=false","--api_server.enabled=false",
        "--router.autorouter.enabled=true","--router.autorouter.max_passes="+str(args.passes),
        "--router.autorouter.max_items=10000","--router.fanout.enabled=true",
        "--router.fanout.max_passes=4","--router.optimizer.enabled=false",
        "--router.automatic_neckdown=false","--router.neck_width_um=0",
        "--router.copper_to_edge_clearance_um=500","--router.hole_clearance_um=250",
        "--router.strict_drc=true","--router.plane_as_obstacle=false",
        "--router.layers.routable=true,false,false,true",
        "--router.layers.preferred_direction_horizontal=true,false,true,false",
        "--router.autorouter.ignore_net_classes=AFX_MANUAL",
        "--router.result_json=/work/router-result.json"]
    record = dict(image=IMAGE,command=command,container=name,source_DSN_sha256=sha(WORK/"routing-view.dsn"),
        recipe_sha256=sha(Path(__file__)),started_unix=time.time(),timeout_seconds=225,
        native_acceptance_pending=True,fabrication_released=False)
    with (WORK/"router-console.log").open("w") as log:
        child = subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        record["pid"] = child.pid
        receipt.write_text(json.dumps(record,indent=2)+"\n")
        print("Started named isolated router",name,flush=True)
        try:
            code = child.wait(timeout=225)
        except subprocess.TimeoutExpired:
            record["bounded_timeout_reached"] = True
            subprocess.run(["docker","rm","-f",name],capture_output=True,timeout=15)
            code = child.wait(timeout=15)
    record.update(returncode=code,finished_unix=time.time(),session_exists=(WORK/"routed.ses").is_file())
    if record["session_exists"]:
        record["session_sha256"] = sha(WORK/"routed.ses")
    receipt.write_text(json.dumps(record,indent=2)+"\n")
    print("Router terminal",code,"session",record["session_exists"],flush=True)


if __name__ == "__main__":
    run()
