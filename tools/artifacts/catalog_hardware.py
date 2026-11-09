"""Index current hardware selections and retained trials without moving sealed evidence."""

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAB = ROOT / "hardware/fabrication"


def catalog():
    statuses = list((FAB / "staging").glob("two-board-fabrication-status-*/status.json"))
    latest = max(statuses, key=lambda p: int(p.parent.name.rsplit("-", 1)[1]))
    status = json.loads(latest.read_text())
    scope = json.loads((FAB / "scope.json").read_text())
    selected = {str(Path(status[k]).parent) for k in ("signal_project", "power_project")}
    references = {str(Path(r["source"]).parent) for r in scope["roles"]}
    support = {str(latest.parent.relative_to(ROOT))}
    support.update(str(Path(p).parent) for p in status["source_sha256"])
    # Include both tracked evidence and new candidates, excluding disposable ignored files.
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--",
         "hardware/fabrication/staging"], cwd=ROOT,
    ).decode().split("\0")
    groups = defaultdict(list)
    for name in names:
        if name:
            groups["/".join(Path(name).parts[:4])].append(name)
    entries = []
    for directory, files in sorted(groups.items()):
        category = (
            "current-design" if directory in selected else
            "module-reference" if directory in references else
            "current-review-input" if directory in support else
            "retained-history-or-experiment"
        )
        entries.append({
            "path": directory,
            "category": category,
            "files": len(files),
            "bytes": sum((ROOT / name).stat().st_size for name in files),
        })
    return {
        "scope": "Navigation inventory; categories are not fabrication approval or fresh validation.",
        "status": str(latest.relative_to(ROOT)),
        "revision": status["revision"],
        "signal_project": status["signal_project"],
        "power_project": status["power_project"],
        "fabrication_released": status["fabrication_released"],
        "entries": entries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check the saved catalog without writing")
    args = parser.parse_args()
    result = catalog()
    content = json.dumps(result, indent=2) + "\n"
    target = FAB / "workspace-catalog.json"
    if args.check:
        if target.read_text() != content:
            parser.exit(1, "Hardware catalog is stale; regenerate with this module.\n")
    else:
        target.write_text(content)
    print(f"{result['revision']}: {len(result['entries'])} candidate directories indexed")


if __name__ == "__main__":
    main()
