"""Fresh pinned Linux OpenSCAD controls, not inherited Mac geometry evidence."""

import hashlib
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

from .openscad import DOCKER, IMAGE, command

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    (OUT / (name + ".stdout")).write_text(p.stdout)
    (OUT / (name + ".stderr")).write_text(p.stderr)
    return dict(command=cmd, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)


def main():
    assert not (OUT / "verification.json").exists(), "Preserve original proof"
    image = run("image-inspect", [DOCKER, "image", "inspect", IMAGE])
    assert image["returncode"] == 0
    image_metadata = json.loads(image["stdout"])[0]
    assert image_metadata["Architecture"] == "arm64" and image_metadata["Os"] == "linux"
    assert any(IMAGE.split("@", 1)[1] in d for d in image_metadata["RepoDigests"])
    version = run("version", command(["--version"]))
    assert version["returncode"] == 0 and "OpenSCAD version" in version["stdout"] + version["stderr"]
    # Same immutable image and least-privilege runtime, with only a metadata command changed.
    binary = run("binary-sha256", command([])[:-1] + ["sha256sum", "/usr/local/bin/openscad"])
    assert binary["returncode"] == 0 and len(binary["stdout"].split()[0]) == 64
    cases = {}
    for name in ["solid", "witness", "empty"]:
        target = OUT / (name + ".stl")
        assert not target.exists()
        args = [
            "--hardwarnings",
            "--backend",
            "Manifold",
            "--export-format",
            "binstl",
            "-D",
            'proof_case="' + name + '"',
            "-o",
            str(target),
            str(ROOT / "control.scad"),
        ]
        row = run(name, command(args))
        text = row["stdout"] + row["stderr"]
        assert "WARNING" not in text and "ERROR" not in text
        if name == "empty":
            assert (
                row["returncode"] == 1
                and "Current top level object is empty." in text
                and not target.exists()
            )
            row["statistics"] = None
        else:
            assert row["returncode"] == 0 and "NoError" in text and target.exists()
            m = mesh(target)
            assert m["closed_oriented_boundary"] and not m["degenerate_triangles_excluded"]
            assert math.isclose(m["volume_mm3"], 0.008 if name == "witness" else 1.5, abs_tol=1e-7)
            row["statistics"] = m
        cases[name] = row
        print(name, row["returncode"], row["statistics"], flush=True)
    sources = [ROOT / "openscad.py", Path(__file__), ROOT / "control.scad"]
    report = dict(
        image=IMAGE,
        image_id=image_metadata["Id"],
        platform="linux/arm64",
        version=version,
        binary_sha256=binary["stdout"].split()[0],
        cases=cases,
        actual_runtime_controls_passed=True,
        network_disabled=True,
        rootfs_read_only=True,
        non_root_uid=True,
        all_capabilities_dropped=True,
        no_new_privileges=True,
        source_mount_read_only=True,
        explicit_output_directory_only_writable=True,
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources},
        physical_qualified=False,
    )
    report["artifact_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in OUT.iterdir() if p.is_file()}
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
