"""Portable source/solid evidence gates for TC01's narrowly declared local fit."""

import hashlib
import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def errors(report=None, native=None):
    r = report if report is not None else json.loads((ROOT / "report.json").read_text())
    n = native if native is not None else json.loads((ROOT / "generated/verification.json").read_text())
    out = []
    if r.get("actual_width_depth_mm") != [53.848, 21.844] or r.get("candidate_datum_mm") != [82, 123.5, 30.6]:
        out.append("wrong C3 geometry")
    mounts = {m["ref"]: m for m in r.get("mounts", [])}
    if set(mounts) != {"H1", "H2"}:
        out.append("missing actual mount")
    else:
        expected = {"H1": [130.0871, 134.422], "H2": [93.0871, 134.4352]}
        for ref, m in mounts.items():
            if (
                m["world_xy_mm"] != expected[ref]
                or m["drill_mm"] != 3.2
                or not m["net"].startswith("unconnected")
            ):
                out.append("mount geometry or ground assumption")
    if r.get("design", {}).get("upper_mating_z_mm") != 42.2:
        out.append("backer datum")
    if [p["net"] for p in r.get("communication_pads", [])] != [
        "/XRES",
        "/EVENT",
        "GND",
        "VCC",
        "/I2C_SDA",
        "/I2C_SCL",
    ]:
        out.append("vendor pin map")
    for key in ["native_fit_qualified", "physical_qualified", "electrical_qualified", "fabrication_released"]:
        if r.get(key) is not False:
            out.append("false claim: " + key)
    for name, h in r.get("source_sha256", {}).items():
        p = ROOT / "sources" / name
        if not p.is_file() or sha(p) != h:
            out.append("source: " + name)
    for name, h in n.get("source_sha256", {}).items():
        p = ROOT / name
        if not p.is_file() or sha(p) != h:
            out.append("native source: " + name)
    for name, h in n.get("artifact_sha256", {}).items():
        p = ROOT / name
        if not p.is_file() or sha(p) != h:
            out.append("native artifact: " + name)
    cases = n.get("cases", {})
    required = {
        "saddle",
        "board",
        "hardware_requirements",
        "saddle_board",
        "saddle_components",
        "saddle_tails",
        "saddle_backer",
        "heads_components",
        "heads_backer",
        "central_aperture",
        "known_board_collision",
        "known_head_collision",
        "backer_contact",
    }
    if set(cases) != required:
        out.append("case coverage")
    for name, row in cases.items():
        if row.get("clear") is not True:
            out.append("failed native " + name)
        mesh = ROOT / "generated" / (name + ".stl")
        log = ROOT / "generated" / (name + ".log")
        if not log.is_file():
            out.append("missing log " + name)
            continue
        text = log.read_text()
        if "WARNING" in text or "ERROR" in text:
            out.append("unclean log " + name)
        if row.get("role") == "empty":
            if (
                mesh.exists()
                or row.get("empty") is not True
                or row.get("returncode") != 1
                or "Current top level object is empty." not in text
            ):
                out.append("empty evidence " + name)
        else:
            if not mesh.is_file():
                out.append("missing required mesh " + name)
                continue
            actual = binary_stl(mesh)
            if actual != row.get("statistics") or row.get("returncode") != 0:
                out.append("mesh metadata " + name)
            v = actual["volume_mm3"]
            if row.get("role") == "control" and not math.isclose(v, 0.008, abs_tol=1e-6):
                out.append("positive control " + name)
            if v <= 0.001:
                out.append("missing volume " + name)
    if n.get("changed_inputs") or n.get("all_local_checks_clear") is not True:
        out.append("native overall rejected")
    return out


if __name__ == "__main__":
    found = errors()
    print(
        json.dumps(dict(errors=found, local_source_geometry_screen_clear=not found, physical_qualified=False))
    )
    raise SystemExit(bool(found))
