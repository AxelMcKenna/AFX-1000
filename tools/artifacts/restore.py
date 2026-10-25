"""Restore archived hardware review artifacts from their recorded Git blobs."""

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "hardware/releases/manifest.json"


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def artifact_path(root, artifact, directory=None):
    relative = PurePosixPath(artifact["name"] if directory else artifact["local_path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Artifact path must stay inside its destination directory")
    if directory is None and not relative.is_relative_to("build/artifacts/releases"):
        raise ValueError("Default artifact destination must be build/artifacts/releases/")
    return (directory if directory is not None else root) / relative


def verify_artifact(path, artifact):
    if path.stat().st_size != artifact["bytes"] or digest(path) != artifact["sha256"]:
        raise ValueError(f"Checksum mismatch; existing file preserved: {path}")


def restore_artifact(root, artifact, directory=None):
    target = artifact_path(root, artifact, directory)
    if target.exists():
        verify_artifact(target, artifact)
        return target
    blob = artifact.get("git_blob")
    if not blob:
        raise ValueError(
            f"Local-only artifact requires its retained copy or published release: {artifact['name']}"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            subprocess.run(
                ["git", "cat-file", "blob", blob], cwd=root, stdout=stream, stderr=subprocess.PIPE, check=True
            )
        verify_artifact(temporary, artifact)
        try:
            # Publish atomically without replacing another writer's file.
            os.link(temporary, target)
        except FileExistsError:
            verify_artifact(target, artifact)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true", help="List names, destinations and recovery sources")
    mode.add_argument("--verify", action="store_true", help="Check existing copies without restoring files")
    parser.add_argument("--name", help="Select one artifact name from the manifest")
    parser.add_argument("--directory", type=Path, help="Use another local release directory")
    args = parser.parse_args()
    artifacts = json.loads(MANIFEST.read_text())["artifacts"]
    if args.name:
        artifacts = [entry for entry in artifacts if entry["name"] == args.name]
        if not artifacts:
            parser.error("Unknown artifact name; use --list")
    failures = 0
    for artifact in artifacts:
        if args.list:
            print(
                artifact["name"], artifact["local_path"], "Git blob" if artifact["git_blob"] else "local only"
            )
            continue
        try:
            path = artifact_path(ROOT, artifact, args.directory)
            if args.verify:
                verify_artifact(path, artifact)
            else:
                restore_artifact(ROOT, artifact, args.directory)
            print("Verified:", path)
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            failures += 1
            print(f"{artifact['name']}: {error}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
