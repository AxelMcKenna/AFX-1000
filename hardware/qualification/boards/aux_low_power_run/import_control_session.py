"""Import the isolated trial only if every protected copper object survives."""

import argparse
import hashlib
import json
from pathlib import Path

import pcbnew

from hardware.qualification.boards.freerouting_bridge import copper, parts, session_design

WORK=Path(__file__).resolve().parents[4]/"hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/eight-control-reroute"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument("--folder",default="eight-control-reroute")
    args=parser.parse_args()
    assert args.folder.startswith("eight-control-") and all(c.isalnum() or c=="-" for c in args.folder)
    work=WORK.parent/args.folder
    source=work/"rail_disconnect.kicad_pcb"
    session=work/"routed.ses"
    output=work/"imported.kicad_pcb"
    assert not output.exists() and not (work/"import.json").exists()
    original_digest=sha(source)
    command=json.loads((work/"router-command.json").read_text())
    assert command["session_sha256"]==sha(session)
    assert command["source_pcb_sha256"]==original_digest
    assert session_design(session.read_text())=="routing-view"
    manager=pcbnew.GetSettingsManager()
    project_path=work/"rail_disconnect.kicad_pro"
    assert manager.LoadProject(str(project_path))
    project=manager.GetProject(str(project_path))
    assert project is not None and bool(project)
    board=pcbnew.LoadBoard(str(source))
    board.SetProject(project)
    before_parts=parts(board)
    before=copper(board,pcbnew)
    protected_path=WORK/"rail_disconnect.kicad_pcb"
    protected_board=pcbnew.LoadBoard(str(protected_path))
    protected=copper(protected_board,pcbnew)
    assert not protected-before,"Continuation already lost original protected power copper"
    assert pcbnew.ImportSpecctraSES(board,str(session))
    after=copper(board,pcbnew)
    lost=protected-after
    report=dict(source_sha256=original_digest,session_sha256=sha(session),recipe_sha256=sha(Path(__file__)),
        protected_reference_sha256=sha(protected_path),protected_objects=sum(protected.values()),
        before_objects=sum(before.values()),after_objects=sum(after.values()),
        lost_protected_copper_objects=[dict(geometry=list(k),count=n) for k,n in lost.items()],
        parts_and_poses_exact=before_parts==parts(board),source_unchanged=sha(source)==original_digest,
        native_Mac_apps_launched=0,native_ERC_DRC_and_refill_pending=True,physical_qualified=False,fabrication_released=False)
    assert not lost,"Session lost or moved protected power/return copper"
    assert report["parts_and_poses_exact"] and report["source_unchanged"]
    pcbnew.SaveBoard(str(output),board)
    report["candidate_sha256"]=sha(output)
    (work/"import.json").write_text(json.dumps(report,indent=2)+"\n")
    print("Imported trial; all",sum(protected.values()),"protected objects and footprint poses preserved")


if __name__=="__main__":
    run()
