"""Bounded router interchange for a strict, initially unrouted placement.

The source project and authored planes remain unchanged. Router results require
a separate full native review; importing a session does not qualify a board.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import native_evidence_errors, sha
from hardware.fabrication.bypass_import import identity

if sys.platform == "linux":
    import pcbnew

ROOT = Path(__file__).resolve().parent


def export(source, work, name):
    project = source/(name+".kicad_pro")
    review = source/"review.json"
    report = json.loads(review.read_text())
    assert not native_evidence_errors(project,report)
    counts = report["status"]["counts"]
    assert counts["violations"] == counts["schematic_parity"] == counts["erc"] == 0
    pcb = project.with_suffix(".kicad_pcb")
    tree = read_sexpr(pcb.read_text())
    assert not children(tree,"segment") and not children(tree,"via")
    work.mkdir(exist_ok=False)
    shutil.copyfile(pcb,work/"input.kicad_pcb")
    board = pcbnew.LoadBoard(str(pcb))
    manager = pcbnew.GetSettingsManager()
    assert manager.LoadProject(str(project))
    board.SetProject(manager.GetProject(str(project)))
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    connection.RecalculateRatsnest()
    assert connection.GetUnconnectedCount(False) == report["uncapped_open_connections"]
    assert pcbnew.ExportSpecctraDSN(board,str(work/"native-input.dsn"))
    text = (work/"native-input.dsn").read_text()
    text = text.replace("(clearance 50 (type smd_smd))","(clearance 200 (type smd_smd))")
    changed = []
    for layer in ("In1.Cu","In2.Cu"):
        needle = f"(layer {layer}\n      (type signal)"
        if needle in text:
            assert text.count(needle) == 1
            text = text.replace(needle,f"(layer {layer}\n      (type power)")
            changed.append(layer)
    assert board.GetCopperLayerCount() == 4
    (work/"routing-view.dsn").write_text(text)
    template = ROOT/"staging/bypass-routing-01/config/freerouting.json"
    profile = json.loads(template.read_text())
    assert profile["profile"]["allow_telemetry"] is False
    assert profile["profile"]["allow_contact"] is False
    profile["router"]["layers"] = [dict(routable=i in (0,3),preferred_direction_horizontal=i%2 == 0) for i in range(4)]
    profile["router"]["job_timeout"] = "00:03:00"
    (work/"config").mkdir()
    (work/"config/freerouting.json").write_text(json.dumps(profile,indent=2)+"\n")
    inputs = (pcb,project,review,template,Path(__file__))
    (work/"export.json").write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},
        source=str(pcb),source_PCB_sha256=sha(pcb),routing_DSN_sha256=sha(work/"routing-view.dsn"),
        native_DSN_sha256=sha(work/"native-input.dsn"),expected_footprints=len(identity(board)),
        expected_opens=report["uncapped_open_connections"],explicit_power_layer_adapter=changed,
        no_source_copper_to_replace=True,router_smd_clearance_um=200,
        native_acceptance_pending=True,fabrication_released=False),indent=2)+"\n")
    print("Exported",name,report["uncapped_open_connections"],"opens; F/B signal routing only",flush=True)


def import_routes(work):
    output = work/"merged.kicad_pcb"
    assert not output.exists()
    command = json.loads((work/"router-command.json").read_text())
    assert command["returncode"] == 0 and command["session_exists"]
    session = work/"routed.ses"
    assert sha(session) == command["session_sha256"]
    record = json.loads((work/"export.json").read_text())
    source = work/"input.kicad_pcb"
    assert sha(source) == record["source_PCB_sha256"]
    inputs = (source,session,work/"router-command.json",work/"export.json",Path(__file__))
    hashes = {str(p):sha(p) for p in inputs}
    board = pcbnew.LoadBoard(str(source))
    before = identity(board)
    assert len(before) == record["expected_footprints"]
    assert pcbnew.ImportSpecctraSES(board,str(session))
    after = identity(board)
    assert set(before) == set(after)
    rounding = {}
    for ref in before:
        a,b = before[ref],after[ref]
        assert a[:3] == b[:3] and a[5:] == b[5:],ref
        displacement = max(abs(a[3]-b[3]),abs(a[4]-b[4]))
        assert displacement <= 500,(ref,displacement)
        if displacement:
            rounding[ref] = displacement
    raw = work/"raw-import.kicad_pcb"
    assert pcbnew.SaveBoard(str(raw),board)
    original,routed = [read_sexpr(p.read_text()) for p in (source,raw)]
    assert not children(original,"segment") and not children(original,"via")
    added = [n for n in routed if isinstance(n,list) and n and n[0] in ("segment","via")]
    raised = []
    assert added
    for node in added:
        if node[0] == "segment":
            assert first(node,"layer")[1] in ("F.Cu","B.Cu")
            width = first(node,"width")
            if float(width[1]) < .2:
                assert float(width[1]) in (.12,.15)
                raised.append(dict(uuid=str(first(node,"uuid")[1]),old_width_mm=float(width[1]),new_width_mm=.2))
                width[1] = .2
        else:
            assert float(first(node,"drill")[1]) >= .3
    # Preserve source footprints (including exact poses), zones and board setup.
    output.write_text(sexpr(original+added)+"\n")
    assert all(sha(Path(p)) == digest for p,digest in hashes.items())
    (work/"import.json").write_text(json.dumps(dict(source_sha256=hashes,output_PCB_sha256=sha(output),
        exact_original_footprints_zones_and_setup_retained=True,added_copper_objects=len(added),
        raw_SES_pose_rounding_nm_discarded=rounding,fanout_tracks_raised_to_0p2mm=raised,
        no_project_rule_values_relaxed=True,native_checks_pending=True,fabrication_released=False),indent=2)+"\n")
    print("Merged",len(added),"copper objects; source footprints and planes exact; native checks pending",flush=True)


def run():
    assert sys.platform == "linux","Mac CAD stays disabled"
    parser = argparse.ArgumentParser()
    parser.add_argument("action",choices=("export","import"))
    parser.add_argument("--source")
    parser.add_argument("--workspace",required=True)
    parser.add_argument("--board-name",default="rail_monitor")
    args = parser.parse_args()
    for label in (args.source,args.workspace,args.board_name):
        assert label is None or (label and all(c.isalnum() or c in "-_" for c in label))
    work = ROOT/"staging"/args.workspace
    if args.action == "export":
        assert args.source
        export(ROOT/"staging"/args.source,work,args.board_name)
    else:
        import_routes(work)


if __name__ == "__main__":
    run()
