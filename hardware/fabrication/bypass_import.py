"""Import one terminal routing session into a new PCB; original placement stays."""

import json
import sys
from pathlib import Path

from hardware.fabrication.audit_candidate import sha

if sys.platform == "linux":
    import pcbnew

ROOT = Path(__file__).resolve().parent
WORK = ROOT/"staging/bypass-routing-01"


def identity(board):
    return {fp.GetReference():(str(fp.GetFPID().GetLibNickname()),str(fp.GetFPID().GetLibItemName()),
        fp.GetValue(),fp.GetPosition().x,fp.GetPosition().y,fp.GetOrientation().AsDegrees(),
        fp.IsFlipped(),sorted((p.GetNumber(),p.GetNetname()) for p in fp.Pads())) for fp in board.GetFootprints()}


def run():
    assert sys.platform == "linux"
    destination = WORK/"routed.kicad_pcb"
    assert not destination.exists()
    command = json.loads((WORK/"router-command.json").read_text())
    assert command["returncode"] == 0 and command["session_exists"]
    ses,source = WORK/"routed.ses",WORK/"input.kicad_pcb"
    assert sha(ses) == command["session_sha256"]
    hashes = {str(p):sha(p) for p in (source,ses,WORK/"router-command.json",Path(__file__))}
    board = pcbnew.LoadBoard(str(source))
    before = identity(board)
    assert len(before) == 59
    assert pcbnew.ImportSpecctraSES(board,str(ses))
    assert identity(board) == before
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    connection.RecalculateRatsnest()
    missing = connection.GetUnconnectedCount(False)
    assert pcbnew.SaveBoard(str(destination),board)
    assert all(sha(Path(p)) == digest for p,digest in hashes.items())
    (WORK/"import.json").write_text(json.dumps(dict(source_sha256=hashes,output_PCB_sha256=sha(destination),
        original59_component_and_mount_identities_exact=True,uncapped_pre_refill_opens=missing,
        native_DRC_ERC_parity_and_refill_pending=True,fabrication_released=False),indent=2)+"\n")
    print("Imported SES;59 exact poses/pin maps;pre-refill opens",missing)


if __name__ == "__main__":
    run()
