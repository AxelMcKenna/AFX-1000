"""Native export for a bounded NF logic continuation; protected nets stay fixed."""

import json
import shutil
import sys
from pathlib import Path

from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.routing_nets import is_logic_net

if sys.platform == "linux":
    import pcbnew

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT/"staging/nf-watchdog-land-native-01"
WORK = ROOT/"staging/nf-logic-continuation-01"


def run():
    assert sys.platform == "linux"
    assert not WORK.exists()
    source = SOURCE/"negative_startup_physical.kicad_pcb"
    record = json.loads((SOURCE/"review.json").read_text())
    assert record["uncapped_open_connections"] == 177 and record["status"]["counts"]["violations"] == 0
    assert sha(source) == record["checked_PCB_sha256"]
    digest = sha(source)
    board = pcbnew.LoadBoard(str(source))
    manager = pcbnew.GetSettingsManager()
    project = str(SOURCE/"negative_startup_physical.kicad_pro")
    assert manager.LoadProject(project)
    board.SetProject(manager.GetProject(project))
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    connection.RecalculateRatsnest()
    assert connection.GetUnconnectedCount(False) == 177
    protected,logic = 0,0
    for item in board.GetTracks():
        selected = is_logic_net(item.GetNetname())
        if not selected:
            item.SetLocked(True)
            protected += 1
        else:
            logic += 1
    WORK.mkdir()
    shutil.copyfile(source,WORK/"original.kicad_pcb")
    assert pcbnew.SaveBoard(str(WORK/"input.kicad_pcb"),board)
    assert pcbnew.ExportSpecctraDSN(board,str(WORK/"native-input.dsn"))
    text = (WORK/"native-input.dsn").read_text()
    text = text.replace("(clearance 50 (type smd_smd))","(clearance 200 (type smd_smd))")
    for name in ("In1.Cu","In4.Cu"):
        needle = f"(layer {name}\n      (type signal)"
        if needle in text:
            assert text.count(needle) == 1
            text = text.replace(needle,f"(layer {name}\n      (type power)")
    (WORK/"routing-view.dsn").write_text(text)
    template = ROOT.parents[1]/"hardware/qualification/boards/startup_negative_circuit/physical_layout/routing/receiving-continuation-01/router-input-profile.json"
    profile = json.loads(template.read_text())
    profile["profile"].update(allow_telemetry=False,allow_contact=False)
    profile["router"]["layers"] = [dict(routable=i not in (1,4),preferred_direction_horizontal=i%2 == 0) for i in range(6)]
    profile["router"]["job_timeout"] = "00:03:00"
    profile["router"]["fanout"]["enabled"] = True
    profile["logging"]["file"]["location"] = "/work/router.log"
    config = WORK/"config"
    config.mkdir()
    (config/"freerouting.json").write_text(json.dumps(profile,indent=2)+"\n")
    assert sha(source) == digest
    (WORK/"export.json").write_text(json.dumps(dict(source=str(source),source_PCB_sha256=digest,
        routing_DSN_sha256=sha(WORK/"routing-view.dsn"),native_DSN_sha256=sha(WORK/"native-input.dsn"),
        protected_source_copper_objects=protected,logic_source_copper_objects=logic,
        only_selected_logic_copper_may_be_adopted=True,source_project_unchanged=True,
        native_acceptance_pending=True,fabrication_released=False),indent=2)+"\n")
    print("Exported NF177-open trial;",protected,"protected objects;",logic,"logic objects")


if __name__ == "__main__":
    run()
