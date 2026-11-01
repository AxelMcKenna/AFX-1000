"""Clean the final AX03-only defects without touching strict source power copper."""

import hashlib
import json
import sys
from pathlib import Path

import pcbnew

from hardware.electronics.common.sexpr import children, first, read_sexpr

WORK = Path(__file__).resolve().parents[4] / "hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter"


def missing(board):
    board.BuildConnectivity()
    c = board.GetConnectivity()
    c.RecalculateRatsnest()
    return c.GetUnconnectedCount(False)


def run():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    source = WORK / "generated/native-local-bypass"
    output = WORK / "generated/closed-transmitter"
    assert not output.exists()
    pcb = source / "power_p03.kicad_pcb"
    digest = hashlib.sha256(pcb.read_bytes()).hexdigest()
    parent = read_sexpr((WORK.parent / "strict-native-centering/power_p03.kicad_pcb").read_text())
    protected = {str(first(n, "uuid")[1]) for kind in ("segment", "via") for n in children(parent, kind)
                 if first(n, "net")[1] != "/POWER_RUN"}
    board = pcbnew.LoadBoard(str(pcb))
    assert missing(board) == 0
    objects = {item.m_Uuid.AsString(): item for item in board.GetTracks()}
    drc = json.loads((source / "drc.json").read_text())
    edits = []
    centering = [v for v in drc["violations"] if v["type"] == "track_not_centered_on_via"]
    assert len(centering) == 1
    for finding in centering:
        track = objects[finding["items"][0]["uuid"]]
        via = objects[finding["items"][1]["uuid"]]
        assert track.m_Uuid.AsString() not in protected and track.GetNetname() == "/AX03_SOURCE_CT"
        start, end, target = track.GetStart(), track.GetEnd(), via.GetPosition()
        assert (end.x-start.x)*(target.y-start.y) == (end.y-start.y)*(target.x-start.x)
        before = [[start.x, start.y], [end.x, end.y]]
        if (start.x-target.x)**2 + (start.y-target.y)**2 < (end.x-target.x)**2 + (end.y-target.y)**2:
            track.SetStart(target)
        else:
            track.SetEnd(target)
        edits.append(dict(uuid=track.m_Uuid.AsString(), before_nm=before,
                          after_nm=[[track.GetStart().x, track.GetStart().y], [track.GetEnd().x, track.GetEnd().y]],
                          reason="collinear extension to actual CT via centre"))
    assert missing(board) == 0
    removed = []
    keep_alive = []

    def remove(item):
        identifier = item.m_Uuid.AsString()
        assert identifier not in protected
        board.Remove(item)
        if missing(board):
            board.Add(item)
            assert missing(board) == 0
            return False
        keep_alive.append(item)
        removed.append(dict(uuid=identifier, net=item.GetNetname(), kind=item.GetClass()))
        return True

    for finding in drc["violations"]:
        if finding["type"] == "via_dangling":
            assert remove(objects[finding["items"][0]["uuid"]])
    converged = False
    for _ in range(64):
        connection = board.GetConnectivity()
        tips = [item for item in board.GetTracks() if item.GetClass() == "PCB_TRACK"
                and item.m_Uuid.AsString() not in protected and connection.TestTrackEndpointDangling(item, False)]
        if not tips:
            converged = True
            break
        changed = sum(remove(item) for item in tips)
        assert changed, "Do not remove a branch that carries an actual pad connection"
    assert converged and missing(board) == 0
    output.mkdir()
    destination = output / pcb.name
    pcbnew.SaveBoard(str(destination), board)
    assert hashlib.sha256(pcb.read_bytes()).hexdigest() == digest
    (output/"cleanup.json").write_text(json.dumps(dict(source_pcb_sha256=digest,
        output_pcb_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(), edits=edits, removed=removed,
        all_strict_source_power_ground_AUX_objects_protected=True,
        every_removal_preserved_zero_uncapped_opens=True, native_validation_pending=True,
        physical_qualified=False, fabrication_released=False), indent=2)+"\n")
    print("Centred CT endpoint; removed", len(removed), "unused objects; zero uncapped opens")


if __name__ == "__main__":
    run()
