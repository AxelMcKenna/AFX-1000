"""Copy explicitly selected PCB inputs into new, bounded review workspaces."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("roles", nargs="+")
    args = parser.parse_args()
    scope = json.loads((ROOT/"scope.json").read_text())
    by_role = {row["role"]: row for row in scope["roles"]}
    for role in args.roles:
        source = REPO/by_role[role]["source"]
        assert source.suffix == ".kicad_pro" and source.is_file()
        board = source.with_suffix(".kicad_pcb")
        digest = hashlib.sha256(board.read_bytes()).hexdigest()
        output = ROOT/"staging"/("source-"+role)
        output.mkdir(exist_ok=False)
        destination = output/board.name
        shutil.copyfile(board,destination)
        assert hashlib.sha256(destination.read_bytes()).hexdigest() == digest
        (output/"source.json").write_text(json.dumps(dict(source=str(board.relative_to(REPO)),
            source_PCB_sha256=digest, role=role, fabrication_released=False),indent=2)+"\n")
        print(role, "staged exact PCB; original unchanged")


if __name__ == "__main__":
    run()
