#!/usr/bin/env python3
"""Pinned official Linux Manifold runner; host sources are never container-writable."""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[6]
IMAGE = "openscad/openscad@sha256:ad0426f9f16f73211765c0ad2a269af8603bcb5954e35564c126ed1555140dc2"
DOCKER = "/usr/local/bin/docker"


def command(args):
    mounts = [(REPO, True)]
    if "-o" in args:
        target = Path(args[args.index("-o") + 1]).resolve()
        target.relative_to(REPO)
        if target.exists():
            raise ValueError("Fresh evidence only: refuse an existing output file")
        if not target.parent.is_dir():
            raise ValueError("The host must create the explicit output directory")
        mounts.append((target.parent, False))
        # An output directory can also contain captured source or earlier evidence.
        # Rebind every existing file there RO after the writable directory mount.
        mounts.extend((p, True) for p in sorted(target.parent.rglob("*")) if p.is_file())
    cmd = [
        DOCKER,
        "run",
        "--rm",
        "--pull=never",
        "--platform",
        "linux/arm64",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges=true",
        "--pids-limit",
        "256",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=256m,mode=1777",
        "--env",
        "QT_QPA_PLATFORM=offscreen",
        "--env",
        "HOME=/tmp",
        "--env",
        "LC_ALL=C",
        "--workdir",
        str(REPO),
    ]
    for path, readonly in mounts:
        value = f"type=bind,source={path},target={path}" + (",readonly" if readonly else "")
        cmd += ["--mount", value]
    return cmd + [IMAGE, "openscad", *args]


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--print-container-command"]:
        print(json.dumps(command(args[1:])))
    else:
        raise SystemExit(subprocess.run(command(args)).returncode)
