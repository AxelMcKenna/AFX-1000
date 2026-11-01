"""Read-only native DSN export of the geometry-clean bypass placement."""

import json
import shutil
import sys
from pathlib import Path

from hardware.fabrication.audit_candidate import sha

if sys.platform == "linux":
    import pcbnew

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT/"staging/bypass-placement-native-04"
WORK = ROOT/"staging/bypass-routing-01"


def run():
    assert sys.platform == "linux"
    status = json.loads((SOURCE/"review.json").read_text())
    assert status["status"]["counts"] == dict(violations=0,unconnected_items=145,schematic_parity=0,erc=0)
    source = SOURCE/"sequenced_bypass.kicad_pcb"
    digest = sha(source)
    WORK.mkdir(exist_ok=False)
    board = pcbnew.LoadBoard(str(source))
    manager = pcbnew.GetSettingsManager()
    project = str(SOURCE/"sequenced_bypass.kicad_pro")
    assert manager.LoadProject(project)
    board.SetProject(manager.GetProject(project))
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    connection.RecalculateRatsnest()
    assert connection.GetUnconnectedCount(False) == 145
    shutil.copyfile(source,WORK/"input.kicad_pcb")
    assert pcbnew.ExportSpecctraDSN(board,str(WORK/"native-input.dsn"))
    text = (WORK/"native-input.dsn").read_text()
    text = text.replace("(clearance 50 (type smd_smd))","(clearance 200 (type smd_smd))")
    changed = []
    for layer in ("In1.Cu","In2.Cu"):
        needle = f"(layer {layer}\n      (type signal)"
        if needle in text:
            assert text.count(needle) == 1
            text = text.replace(needle,f"(layer {layer}\n      (type power)")
            changed.append(layer)
    (WORK/"routing-view.dsn").write_text(text)
    template = ROOT.parents[1]/"hardware/qualification/boards/startup_negative_circuit/physical_layout/routing/receiving-continuation-01/router-input-profile.json"
    profile = json.loads(template.read_text())
    profile["profile"]["allow_telemetry"] = False
    profile["profile"]["allow_contact"] = False
    profile["router"]["layers"] = [dict(routable=i in (0,3),preferred_direction_horizontal=i%2 == 0) for i in range(4)]
    profile["router"]["job_timeout"] = "00:03:00"
    profile["router"]["fanout"]["enabled"] = True
    profile["logging"]["file"]["location"] = "/work/router.log"
    config = WORK/"config"
    config.mkdir()
    (config/"freerouting.json").write_text(json.dumps(profile,indent=2)+"\n")
    assert sha(source) == digest
    (WORK/"export.json").write_text(json.dumps(dict(source=str(source),source_PCB_sha256=digest,
        native_DSN_sha256=sha(WORK/"native-input.dsn"),routing_DSN_sha256=sha(WORK/"routing-view.dsn"),
        explicit_power_layer_adapter=changed,all_board_rules_and_geometry_unchanged=True,
        router_smd_clearance_um=200,native_acceptance_pending=True,fabrication_released=False),indent=2)+"\n")
    print("Exported145-open E11; router limited toF/B withIn1/In2 reserved power planes")


if __name__ == "__main__":
    run()
