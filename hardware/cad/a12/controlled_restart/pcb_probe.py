"""One headless Linux KiCad probe; no GUI, flips, or native project pointers."""

import hashlib
import json
import subprocess
from pathlib import Path

import pcbnew

REPO = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "results/kicad-probe"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not (OUT / "result.json").exists()
    p = subprocess.run(["kicad-cli", "version"], capture_output=True, text=True, timeout=10)
    assert p.returncode == 0 and p.stdout.strip() == "10.0.7", (p.returncode, p.stdout, p.stderr)
    rows = []
    for name, relative, expected_parts, expected_opens in [
        ("NF", "hardware/qualification/boards/startup_negative_circuit/physical_layout/routing/receiving-continuation-repair-01/output.kicad_pcb", 267, 204),
        ("E28-filled", "hardware/electronics/rail_disconnect/revision28/generated/closed-logic-cleanup2-work/generated/filled-closed-logic-cleanup2.kicad_pcb", 273, 20),
        ("FPC_M2", "hardware/qualification/boards/fan_health/composite_nf_branch/fan_power_health.kicad_pcb", 91, 0),
    ]:
        path = REPO / relative
        before = sha(path)
        b = pcbnew.LoadBoard(str(path))
        assert b is not None and len(list(b.GetFootprints())) == expected_parts, (name, expected_parts)
        b.BuildConnectivity()
        c = b.GetConnectivity()
        c.RecalculateRatsnest()
        actual = c.GetUnconnectedCount(False)
        assert actual == expected_opens, (name, actual, expected_opens)
        assert sha(path) == before
        rows.append(dict(board=name, source=relative, source_sha256=before, parts=expected_parts,
                         uncapped_opens=actual, source_unchanged=True))
    (OUT / "result.json").write_text(json.dumps(dict(version="10.0.7", rows=rows,
        headless_Linux_probe_passed=True, native_Mac_apps_launched=0,
        source_script_sha256=sha(Path(__file__)), physical_qualified=False), indent=2) + "\n")
    print("Linux KiCad10.0.7:", [(r["board"], r["uncapped_opens"]) for r in rows])


if __name__ == "__main__":
    main()
