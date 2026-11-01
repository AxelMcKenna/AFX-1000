"""Move only the reviewed automation files; retain every original byte."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUARANTINE = Path("/private/tmp/afx-cad-quarantine-20261030")


def main():
    plan = json.loads((ROOT / "quarantine-plan.json").read_text())
    assert not (ROOT / "quarantine-completed.json").exists()
    assert 1 <= len(plan["crash_reports"]) <= 51
    assert len(plan["crash_reports"]) == plan["remaining_known_crash_reports"]
    allowed_tools = {
        "/Users/axelmckrnna/Applications/OpenSCAD-2026.10.27.app",
        "/private/tmp/rmx-kicad",
    }
    assert {r["source"] for r in plan["tool_directories"]} == allowed_tools
    for row in plan["crash_reports"]:
        p, target = Path(row["source"]), Path(row["target"])
        assert p.parent == Path.home() / "Library/Logs/DiagnosticReports" and p.suffix == ".ips"
        assert hashlib.sha256(p.read_bytes()).hexdigest() == row["sha256"]
        assert target.parent == QUARANTINE / "crash-reports" and not target.exists()
    for row in plan["tool_directories"]:
        p, target = Path(row["source"]), Path(row["target"])
        assert p.is_dir() and not p.is_symlink() and target.parent == QUARANTINE
        assert not target.exists()
    moves = []
    for row in plan["crash_reports"] + plan["tool_directories"]:
        source, target = Path(row["source"]), Path(row["target"])
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        moves.append(dict(source=str(source), target=str(target)))
    for row in plan["crash_reports"]:
        assert hashlib.sha256(Path(row["target"]).read_bytes()).hexdigest() == row["sha256"]
    (ROOT / "quarantine-completed.json").write_text(json.dumps(dict(
        moves=moves, all_remaining_known_crash_reports_byte_identical=True,
        agent_added_Mac_OpenSCAD_and_KiCad_removed_from_active_paths=True,
        pre_existing_user_apps_changed=False, design_files_changed=False,
        files_deleted=False), indent=2) + "\n")
    print("Moved", len(plan["crash_reports"]), "automation crash reports and two agent-added CAD runtimes into reversible quarantine. No designs changed.")


if __name__ == "__main__":
    main()
