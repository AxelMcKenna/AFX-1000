"""Source-bound private routing round trip; component and critical copper checks."""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "routing/local-pass1"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def poses(board):
    return {
        f.GetReference(): (
            f.GetValue(),
            f.GetPosition().x,
            f.GetPosition().y,
            f.GetOrientationDegrees(),
            f.IsFlipped(),
            {p.GetNumber(): p.GetNetname() for p in f.Pads() if p.GetNumber()},
        )
        for f in board.GetFootprints()
    }


def tracks(board):
    return {
        (
            t.m_Uuid.AsString(),
            t.GetNetname(),
            t.GetLayer(),
            t.GetStart().x,
            t.GetStart().y,
            t.GetEnd().x,
            t.GetEnd().y,
            t.GetWidth(pcbnew.F_Cu) if isinstance(t, pcbnew.PCB_VIA) else t.GetWidth(),
        )
        for t in board.GetTracks()
    }


def export():
    WORK.mkdir(parents=True, exist_ok=True)
    assert not (WORK / "input.dsn").exists(), "Preserve prior inputs"
    project = ROOT / "fan_power_health.kicad_pro"
    manager = pcbnew.GetSettingsManager()
    assert manager.LoadProject(str(project))
    board = pcbnew.LoadBoard(str(SOURCE))
    board.SetProject(manager.GetProject(str(project)))
    for t in board.GetTracks():
        t.SetLocked(True)
    pcbnew.SaveBoard(str(WORK / "input.kicad_pcb"), board)
    assert pcbnew.ExportSpecctraDSN(board, str(WORK / "input.dsn"))
    dsn = WORK / "input.dsn"
    raw = dsn.read_text()
    (WORK / "native-export.dsn").write_text(raw)
    raw = raw.replace("(layer In1.Cu\n      (type signal)", "(layer In1.Cu\n      (type power)")
    raw, n = re.subn(r'    \(wire_keepout "" \(polygon In1.Cu[^\n]+\)\)\n', "", raw)
    assert n == 1
    dsn.write_text(raw)
    for n in ["input", "output"]:
        shutil.copy2(project, WORK / (n + ".kicad_pro"))
    shutil.copy2(ROOT / "fan_power_health.kicad_sch", WORK / "output.kicad_sch")
    (WORK / "fp-lib-table").write_text(
        (ROOT / "fp-lib-table").read_text().replace("${KIPRJMOD}/", "${KIPRJMOD}/../../")
    )
    (WORK / "input-provenance.json").write_text(
        json.dumps(
            dict(
                pcb_sha256=sha(WORK / "input.kicad_pcb"),
                dsn_sha256=sha(WORK / "input.dsn"),
                code_sha256=sha(Path(__file__)),
                critical_local_tracks=len(list(board.GetTracks())),
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


def import_session():
    board = pcbnew.LoadBoard(str(WORK / "input.kicad_pcb"))
    oldposes = poses(board)
    before = tracks(board)
    assert pcbnew.ImportSpecctraSES(board, str(WORK / "output.ses"))
    newposes = poses(board)
    changes = {r: dict(before=oldposes[r], after=newposes[r]) for r in oldposes if oldposes[r] != newposes[r]}
    (WORK / "pose-differences.json").write_text(json.dumps(changes, indent=2) + "\n")
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        old = oldposes[ref]
        new = newposes[ref]
        assert (
            old[0] == new[0]
            and old[3:] == new[3:]
            and abs(old[1] - new[1]) <= 1
            and abs(old[2] - new[2]) <= 1
        ), "Actual component pose/pin/value change"
        fp.SetPosition(pcbnew.VECTOR2I(old[1], old[2]))
    assert poses(board) == oldposes, "Native coordinate restoration failed"

    # SES may rewrite UUIDs; compare physical/net geometry of locked local paths.
    def geom(ts):
        return {t[1:] for t in ts}

    missing = geom(before) - geom(tracks(board))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(WORK / "output.kicad_pcb"), board)
    (WORK / "import-provenance.json").write_text(
        json.dumps(
            dict(
                input_sha256=sha(WORK / "input.kicad_pcb"),
                session_sha256=sha(WORK / "output.ses"),
                output_sha256=sha(WORK / "output.kicad_pcb"),
                components_exact=True,
                missing_literal_geometry=list(missing),
                native_DRC_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Imported; missing literal geometry", len(missing))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["export", "import"])
    p.add_argument("--source", type=Path, default=ROOT / "fan_power_health.kicad_pcb")
    p.add_argument("--work", type=Path, default=WORK)
    a = p.parse_args()
    SOURCE = a.source.resolve()
    assert ROOT in SOURCE.parents
    WORK = a.work.resolve()
    assert WORK.parent == (ROOT / "routing").resolve()
    export() if a.stage == "export" else import_session()
