"""One isolated CAD operation per invocation; no Mac app and no retry loop."""

import argparse
import hashlib
import json
import math
import subprocess
import uuid
from pathlib import Path

from hardware.cad.a12.enclosure_growth.r1_local.linux_runner.openscad import DOCKER, IMAGE, command
from hardware.cad.a12.thermal.enlarged_base.verify import mesh

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
STOP = REPO / "hardware/validation/board-qualification/NATIVE-CAD-STOP.json"
FAILED = ROOT / "ISOLATED-RUN-FAILED.json"
SCENE = ROOT.parent / "enclosure_growth/nf265_four_cap_repair/workspace/replay.json"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fatal(code, log):
    if code not in [0, 1]:
        return True
    if any(x in log for x in ["Incompatible processor", "Segmentation fault", "Abort trap", "ERROR:", "WARNING:"]):
        return True
    return code == 1 and "Current top level object is empty." not in log


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    args = parser.parse_args()
    assert not FAILED.exists(), "A previous isolated run failed; no retry or next case is allowed"
    policy = json.loads(STOP.read_text())
    assert policy["native_cad_launches_disabled"]
    assert policy["allowed_isolated_image"] == IMAGE
    assert policy["isolated_Linux_restart_authorized_by_user"]
    inputs = {}
    if args.name == "probe":
        entry = ROOT / "control.scad"
        inputs[str(entry)] = sha(entry)
        variables, spec = {}, dict(role="control", expected_volume=1.5)
    elif args.name in ("control-wing-positive","control-wing-receiving"):
        manifest=REPO/"hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/closed-layout-receiving/manifest.json"
        replay=json.loads(manifest.read_text())
        inputs=replay["input_sha256"]
        assert all(sha(Path(p))==h for p,h in inputs.items())
        inputs={**inputs,str(manifest):sha(manifest)}
        entry=Path(replay["entry"])
        positive=args.name=="control-wing-positive"
        variables={"mode":"positive" if positive else "clearance"}
        spec=dict(role="control",expected_volume=replay["expected_positive_volume_mm3"]) if positive else dict(role="empty")
        probe=json.loads((ROOT/"results/probe/result.json").read_text())
        assert probe["clear"] and probe["image"]==IMAGE
    else:
        # Import only portable case specifications; its Mac ENGINE is never
        # accessed or launched by this workflow.
        from hardware.cad.a12.enclosure_growth.nf265_fpc91.verify import specs
        from hardware.cad.a12.enclosure_growth.nf265_fpc91.verify import variables as case_variables
        assert args.name in specs()
        replay = json.loads(SCENE.read_text())
        inputs = replay["rebound_source_sha256"]
        assert all(sha(Path(p)) == h for p, h in inputs.items())
        inputs = {**inputs, str(SCENE): sha(SCENE)}
        entry = Path(replay["entry"])
        variables, spec = case_variables(args.name), specs()[args.name]
        probe = json.loads((ROOT / "results/probe/result.json").read_text())
        assert probe["clear"] and probe["image"] == IMAGE
    out = ROOT / "results" / args.name
    out.mkdir(parents=True, exist_ok=False)
    artifact = out / "output.stl"
    options = ["--hardwarnings", "--backend=Manifold", "--export-format=binstl", "-o", str(artifact)]
    for k, v in variables.items():
        options += ["-D", k + "=" + json.dumps(v)]
    options.append(str(entry))
    container_name = "afx-cad-" + uuid.uuid4().hex[:12]
    cmd = command(options)
    cmd[2:2] = ["--name", container_name, "--memory", "2g", "--cpus", "2"]
    assert cmd[0] == DOCKER and cmd[1] == "run" and IMAGE in cmd
    assert "--network" in cmd and cmd[cmd.index("--network")+1] == "none"
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        # Killing the Docker client alone does not necessarily stop its
        # container. Remove only this exact generated container name.
        subprocess.run([DOCKER, "rm", "-f", container_name], capture_output=True, timeout=10)
        FAILED.write_text(json.dumps(dict(reason="timeout", container=container_name, retries=False)) + "\n")
        raise RuntimeError("Timed out; isolated container stopped; no retry") from None
    log = p.stdout + p.stderr
    (out / "output.log").write_text(log)
    if fatal(p.returncode, log):
        FAILED.write_text(json.dumps(dict(reason="native-runtime-failure", returncode=p.returncode,
                                         case=args.name, retries=False)) + "\n")
        raise RuntimeError("Isolated native operation failed; further operations blocked")
    stat = mesh(artifact) if artifact.exists() else None
    if spec["role"] == "empty":
        clear = p.returncode == 1 and "Current top level object is empty." in log and stat is None
    else:
        clear = p.returncode == 0 and stat is not None and "NoError" in log
        if stat:
            clear &= stat["closed_oriented_boundary"] and not stat["degenerate_triangles_excluded"] and stat["volume_mm3"] > .001
            if "expected_volume" in spec:
                clear &= math.isclose(stat["volume_mm3"], spec["expected_volume"], abs_tol=2e-6)
    assert all(sha(Path(p)) == h for p, h in inputs.items())
    result = dict(case=args.name, image=IMAGE, command=cmd, returncode=p.returncode,
                  input_sha256=inputs, runner_sha256=sha(Path(__file__)),
                  artifact_sha256=sha(artifact) if artifact.exists() else None,
                  log_sha256=sha(out / "output.log"), statistics=stat, clear=bool(clear),
                  network_disabled=True, source_read_only=True, host_Mac_apps_launched=0,
                  automatic_retries=False, physical_qualified=False, fabrication_released=False)
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(case=args.name, clear=bool(clear), statistics=stat, host_Mac_apps_launched=0)))
    if args.name == "probe" and not clear:
        FAILED.write_text(json.dumps(dict(reason="invalid-probe", retries=False)) + "\n")
        raise RuntimeError("Probe geometry invalid; no design check allowed")


if __name__ == "__main__":
    main()
