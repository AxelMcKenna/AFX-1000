"""Bounded DC01 signal-only routing interchange; retain manual power/analog work.

Power, pot ADC, SAI/SD and current-reference nets use an ignored router class.
Their real source pads remain obstacles. Any incidental fanout on those nets
is discarded on adoption. No source geometry or net assignment is replaced.
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.bypass_import import identity

REPO=Path(__file__).resolve().parents[2]
ROOT=REPO/"hardware/fabrication"
SOURCE=ROOT/"staging/digital-core-placement-03"
WORK=ROOT/"staging/digital-signal-routing-02"
NATIVE=ROOT/"staging/digital-signal-routed-native-02"


def manual(net):
    name=net.lstrip("/")
    if name in {"AGND","5V_DIG","V3V3_IO","PROCESSOR/SEED_VIN","PROCESSOR/V3V3_ANALOG"}:
        return True
    if name.startswith(("PROCESSOR/POT_","PROCESSOR/SDMMC_","LED/IREF_","unconnected-")):
        return True
    return name in {"PROCESSOR/BCLK","PROCESSOR/WS","PROCESSOR/ADC_DATA","PROCESSOR/DAC_DATA","PROCESSOR/DAC_DATA_SRC"}


def export():
    assert sys.platform=="linux", "Mac CAD remains disabled"
    import pcbnew

    proof=json.loads((SOURCE/"placement-native-review.json").read_text())
    assert proof["DRC_geometry_findings"]==proof["schematic_parity_findings"]==proof["ERC_findings"]==0
    assert proof["DRC_ignored_checks"]==proof["ERC_ignored_checks"]==[]
    assert all(sha(REPO/p)==h for p,h in proof["source_sha256"].items())
    pcb=SOURCE/"digital_core.kicad_pcb"
    tree=read_sexpr(pcb.read_text())
    assert not children(tree,"segment") and not children(tree,"via")
    WORK.mkdir(exist_ok=False)
    shutil.copyfile(pcb,WORK/"input.kicad_pcb")
    board=pcbnew.LoadBoard(str(pcb))
    manager=pcbnew.GetSettingsManager()
    assert manager.LoadProject(str(SOURCE/"digital_core.kicad_pro"))
    board.SetProject(manager.GetProject(str(SOURCE/"digital_core.kicad_pro")))
    board.BuildConnectivity()
    board.GetConnectivity().RecalculateRatsnest()
    assert board.GetConnectivity().GetUnconnectedCount(False)==466
    assert pcbnew.ExportSpecctraDSN(board,str(WORK/"native-input.dsn"))
    text=(WORK/"native-input.dsn").read_text()
    text=text.replace("(clearance 50 (type smd_smd))","(clearance 200 (type smd_smd))")
    for layer in ("In1.Cu","In2.Cu"):
        needle=f"(layer {layer}\n      (type signal)"
        if needle in text:
            assert text.count(needle)==1
            text=text.replace(needle,f"(layer {layer}\n      (type power)")
        else:
            assert text.count(f"(layer {layer}\n      (type power)")==1
    match=re.search(r"    \(class kicad_default ([\s\S]*?)(      \(circuit[\s\S]*?\n    \))",text)
    assert match
    names=match.group(1).split()
    excluded={n for n in names if manual(n)}
    included=set(names)-excluded
    assert excluded and included and not any(manual(n) for n in included)
    rules=match.group(2)
    classes="    (class AFX_DIGITAL_SIGNALS "+" ".join(sorted(included))+"\n"+rules+"\n"
    classes+="    (class AFX_MANUAL "+" ".join(sorted(excluded))+"\n"+rules
    text=text[:match.start()]+classes+text[match.end():]
    (WORK/"routing-view.dsn").write_text(text)
    template=ROOT/"staging/bypass-routing-01/config/freerouting.json"
    profile=json.loads(template.read_text())
    assert profile["profile"]["allow_telemetry"] is False and profile["profile"]["allow_contact"] is False
    profile["router"]["layers"]=[dict(routable=i in (0,3),preferred_direction_horizontal=i%2==0) for i in range(4)]
    profile["router"]["job_timeout"]="00:03:00"
    profile["router"]["autorouter"]["ignore_net_classes"]=["AFX_MANUAL"]
    (WORK/"config").mkdir()
    (WORK/"config/freerouting.json").write_text(json.dumps(profile,indent=2)+"\n")
    paths=[Path(__file__),pcb,SOURCE/"digital_core.kicad_pro",SOURCE/"placement-native-review.json",template]
    record=dict(source_sha256={str(p):sha(p) for p in paths},source=str(pcb),source_PCB_sha256=sha(pcb),
        routing_DSN_sha256=sha(WORK/"routing-view.dsn"),native_DSN_sha256=sha(WORK/"native-input.dsn"),
        expected_footprints=len(identity(board)),expected_opens=466,manual_net_names=sorted(excluded),
        routed_net_names=sorted(included),signal_layers=["F.Cu","B.Cu"],reserved_inner_layers=["In1.Cu","In2.Cu"],
        router_smd_clearance_um=200,no_source_copper_to_replace=True,native_acceptance_pending=True,fabrication_released=False)
    (WORK/"export.json").write_text(json.dumps(record,indent=2)+"\n")
    shutil.copyfile(Path(__file__),WORK/"applied-export.py.txt")
    print(f"DC01 signal export: {len(included)} router nets; {len(excluded)} manual nets; 466 initial opens",flush=True)


def import_and_review():
    assert sys.platform=="linux", "Mac CAD remains disabled"
    from hardware.fabrication import digital_core_layout
    from hardware.fabrication.placement_router import import_routes

    import_routes(WORK)
    tree=read_sexpr((WORK/"merged.kicad_pcb").read_text())
    names={str(n[1]):str(n[2]) for n in children(tree,"net")}
    rejected=[]
    for node in list(tree):
        if isinstance(node,list) and node and node[0] in ("segment","via") and manual(names[str(first(node,"net")[1])]):
            rejected.append(node)
            tree.remove(node)
    accepted=WORK/"accepted-signals.kicad_pcb"
    accepted.write_text(sexpr(tree)+"\n")
    (WORK/"manual-fanout-filter.json").write_text(json.dumps(dict(
        merged_source_sha256=sha(WORK/"merged.kicad_pcb"),accepted_sha256=sha(accepted),
        discarded_manual_copper_objects=len(rejected),
        kept_signal_copper_objects=len(children(tree,"segment"))+len(children(tree,"via")),
        original_pads_poses_and_setup_unchanged=True),indent=2)+"\n")
    NATIVE.mkdir(exist_ok=False)
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_pro",".kicad_sch",".kicad_sym") or p.name in ("sym-lib-table","fp-lib-table"):
            shutil.copyfile(p,NATIVE/p.name)
    shutil.copytree(SOURCE/"libraries",NATIVE/"libraries")
    shutil.copyfile(accepted,NATIVE/"digital_core.kicad_pcb")
    paths=[Path(__file__),SOURCE/"construction.json",SOURCE/"placement-handoff.json",WORK/"export.json",WORK/"router-command.json",WORK/"import.json",WORK/"manual-fanout-filter.json"]
    record=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        prior_placement=str(SOURCE.relative_to(REPO)),signal_only_routing=True,
        manual_power_analog_reference_and_SAI_SD_work_remaining=True,fabrication_released=False)
    (NATIVE/"construction.json").write_text(json.dumps(record,indent=2)+"\n")
    shutil.copyfile(Path(__file__),NATIVE/"applied-routing.py.txt")
    digital_core_layout.OUT=NATIVE
    digital_core_layout.review()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("export","import"))
    args=parser.parse_args()
    (export if args.action=="export" else import_and_review)()
