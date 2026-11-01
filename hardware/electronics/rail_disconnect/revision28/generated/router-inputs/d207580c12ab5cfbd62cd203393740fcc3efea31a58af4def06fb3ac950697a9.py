"""Bounded, isolated official Java router execution; native acceptance is separate."""

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JAVA = Path("/private/tmp/afx-temurin25-runtime/jdk-25.0.5+8-jre/Contents/Home/bin/java")
JAR = Path("/private/tmp/afx-freerouting-2.5.0/freerouting-2.5.0.jar")


def main(
    workspace, mode="baseline", passes=4, timeout=600, max_items=100, fanout_passes=3, skip_fanout=False
):
    workspace = Path(workspace).resolve()
    assert workspace.is_relative_to((ROOT / "generated").resolve())
    metadata = json.loads((workspace / "export.json").read_text())
    dsn = workspace / metadata["dsn_filename"]
    assert hashlib.sha256(dsn.read_bytes()).hexdigest() == metadata["dsn_sha256"]
    destination = workspace / (mode + ".ses")
    assert not destination.exists(), "Never overwrite a prior routing session"
    config = workspace / (mode + "-config")
    config.mkdir()
    template = Path("/private/tmp/afx-e28-force-guard-router-v3/config/freerouting.json")
    shutil.copy2(template, config / "freerouting.json")
    enabled = "false" if mode == "baseline" else "true"
    args = [
        str(JAVA),
        "-Xmx4g",
        "-XX:ActiveProcessorCount=4",
        "-Djava.awt.headless=true",
        "-Djava.util.prefs.userRoot=" + str(workspace / (mode + "-prefs")),
        "-jar",
        str(JAR),
        "-de",
        str(dsn),
        "-do",
        str(destination),
        "--router.autorouter.enabled=" + enabled,
        "--router.fanout.enabled=" + ("false" if skip_fanout else enabled),
        "--router.optimizer.enabled=false",
        "--router.fanout.max_passes=" + str(fanout_passes),
        "--router.autorouter.max_items=" + str(max_items),
        "--router.autorouter.save_intermediate_stages=true",
        "--router.job_timeout=00:08:00",
        "--router.automatic_neckdown=false",
        "--router.neck_width_um=0",
        "--router.copper_to_edge_clearance_um=500",
        "--router.hole_clearance_um=250",
        "--router.strict_drc=true",
        "--router.plane_as_obstacle=false",
        "-da",
        "--user_data_path=" + str(config),
        "--gui.enabled=false",
        "--api_server.enabled=false",
        "--logging.file.location=" + str(workspace / (mode + "-router.log")),
        "--router.autorouter.max_passes=" + str(passes),
        "--router.result_json=" + str(workspace / (mode + "-result.json")),
    ]
    receipt = dict(
        args=args,
        source_dsn_sha256=metadata["dsn_sha256"],
        router_jar_sha256=hashlib.sha256(JAR.read_bytes()).hexdigest(),
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        timeout_seconds=timeout,
        started_unix=time.time(),
        native_accepted=False,
        physical_qualified=False,
    )
    record = workspace / (mode + "-command.json")
    with (workspace / (mode + "-console.log")).open("w") as output:
        child = subprocess.Popen(args, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        receipt["pid"] = child.pid
        record.write_text(json.dumps(receipt, indent=2) + "\n")
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            receipt["bounded_timeout_reached"] = True
            os.killpg(child.pid, signal.SIGINT)
            try:
                code = child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGTERM)
                code = child.wait(timeout=30)
    receipt.update(returncode=code, finished_unix=time.time(), ses_exists=destination.exists())
    if destination.exists():
        receipt["ses_sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
    record.write_text(json.dumps(receipt, indent=2) + "\n")
    print(mode, "exit", code, "SES", destination.exists(), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    p.add_argument("--mode", choices=("baseline", "routed", "routed-chunk"), default="baseline")
    p.add_argument("--passes", type=int, default=4)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--max-items", type=int, default=100)
    p.add_argument("--fanout-passes", type=int, default=3)
    p.add_argument("--skip-fanout", action="store_true")
    a = p.parse_args()
    main(a.workspace, a.mode, a.passes, a.timeout, a.max_items, a.fanout_passes, a.skip_fanout)
