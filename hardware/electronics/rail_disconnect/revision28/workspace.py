"""Run owned repair tools on a separate, source-bound E28 working project."""

import argparse
import hashlib
import importlib
import json
import shutil
import sys
from pathlib import Path

CANONICAL = Path(__file__).resolve().parent
PREFIX = "hardware.electronics.rail_disconnect.revision28"


def create(path):
    path = Path(path).resolve()
    assert path.is_relative_to((CANONICAL / "generated").resolve())
    assert not path.exists(), "Working project already exists; never overwrite its evidence"
    path.mkdir(parents=True)
    (path / "generated").mkdir()
    copied = {}
    for source in CANONICAL.iterdir():
        if source.suffix == ".pretty":
            shutil.copytree(source, path / source.name)
        elif source.is_file() and (
            source.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru")
            or source.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(source, path / source.name)
    for source in (CANONICAL / "generated").glob("*.json"):
        # Small, original repair recipes and exact native receipts remain bound
        # to their original source; copied data does not become a new pass.
        if source.name.startswith(("native-", "drc-", "erc-", "removed-", "pruned-", "coupled-")):
            continue
        shutil.copy2(source, path / "generated" / source.name)
    for source in path.rglob("*"):
        if source.is_file():
            copied[str(source.relative_to(path))] = hashlib.sha256(source.read_bytes()).hexdigest()
    (path / "generated/workspace-origin.json").write_text(
        json.dumps(
            dict(
                canonical_pcb_sha256=hashlib.sha256(
                    (CANONICAL / "rail_disconnect.kicad_pcb").read_bytes()
                ).hexdigest(),
                copied_source_hashes=copied,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Created isolated E28 project", path)


def activate(path, module):
    path = Path(path).resolve()
    assert path.is_relative_to((CANONICAL / "generated").resolve())
    target = importlib.import_module(PREFIX + "." + module)
    # Imports are local to this Python process. Frozen parent modules and the
    # canonical source files are never redirected or modified.
    for name, loaded in list(sys.modules.items()):
        if name.startswith(PREFIX + ".") and getattr(loaded, "ROOT", None) == CANONICAL:
            loaded.ROOT = path
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--module")
    parser.add_argument("--function", default="main")
    parser.add_argument("--kwargs", default="{}")
    args = parser.parse_args()
    if args.create:
        create(args.root)
    else:
        target = activate(args.root, args.module)
        source = args.root / "rail_disconnect.kicad_pcb"
        if source.exists():
            content = source.read_bytes()
            snapshot = args.root / "generated" / (
                "source-before-" + hashlib.sha256(content).hexdigest() + ".kicad_pcb"
            )
            if not snapshot.exists():
                snapshot.write_bytes(content)
        getattr(target, args.function)(**json.loads(args.kwargs))
