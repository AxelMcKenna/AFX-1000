"""Actual strict isolated-KiCad checks on both thinner-board candidates."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pcbnew

from hardware.electronics.common.netlists import netlist
from hardware.electronics.rail_disconnect.revision28.native_profile import summarize

ROOT=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument("--label",default="native")
    options=parser.parse_args()
    assert options.label and all(c.isalnum() or c=="-" for c in options.label)
    report_path=ROOT/("generated/native-review.json" if options.label=="native" else "generated/"+options.label+"-review.json")
    assert not report_path.exists()
    results=[]
    for ident,name,expected_footprints,expected_opens in (("NF","negative_startup_physical",267,204),("FPC","fan_power_health",91,0)):
        work=ROOT/"generated"/ident
        out=work/options.label
        out.mkdir(exist_ok=False)
        inputs=[work/(name+s) for s in (".kicad_pcb",".kicad_sch",".kicad_pro")]+[work/"components.json"]
        hashes={str(p):sha(p) for p in inputs}
        for path in inputs[:-1]:
            shutil.copyfile(path,out/path.name)
        for table in ("fp-lib-table","sym-lib-table"):
            if (work/table).exists():
                (out/table).write_text((work/table).read_text().replace("${KIPRJMOD}/","${KIPRJMOD}/../"))
        project=out/(name+".kicad_pro")
        settings=json.loads(project.read_text())
        rules=settings.setdefault("erc",{}).setdefault("rule_severities",{})
        promoted=[]
        for rule in ("single_global_label","four_way_junction","simulation_model_issue","footprint_filter"):
            promoted.append(dict(rule=rule,previous=rules.get(rule,"native_default"),new="error"))
            rules[rule]="error"
        project.write_text(json.dumps(settings,indent=2)+"\n")
        commands=[]
        for label,args in (("netlist",["sch","export","netlist","--format","kicadxml","--output",str(out/"netlist.xml"),str(out/(name+".kicad_sch"))]),
            ("erc",["sch","erc","--format","json","--severity-all","--output",str(out/"erc.json"),str(out/(name+".kicad_sch"))]),
            ("drc",["pcb","drc","--format","json","--severity-all","--all-track-errors","--schematic-parity","--refill-zones","--save-board","--output",str(out/"drc.json"),str(out/(name+".kicad_pcb"))])):
            child=subprocess.run(["kicad-cli",*args],capture_output=True,text=True,timeout=120)
            (out/(label+".log")).write_text(child.stdout+child.stderr)
            commands.append(dict(command=["kicad-cli",*args],returncode=child.returncode))
            assert child.returncode==0,(ident,label,child.returncode)
        actual,pins=netlist(out/"netlist.xml")
        declared=json.loads((work/"components.json").read_text())
        mismatch=[]
        for c in declared:
            if c["ref"] not in actual or actual[c["ref"]].findtext("value")!=c["part"]:
                mismatch.append([c["ref"],"value_or_missing"])
            for pin in c["pins"]:
                if pin["net"] is not None and pins.get(c["ref"],{}).get(pin["number"])!=pin["net"]:
                    mismatch.append([c["ref"],pin["number"],pin["net"],pins.get(c["ref"],{}).get(pin["number"])])
        board=pcbnew.LoadBoard(str(out/(name+".kicad_pcb")))
        assert len(list(board.GetFootprints()))==expected_footprints
        thickness=pcbnew.ToMM(board.GetDesignSettings().GetBoardThickness())
        assert abs(thickness-1.2)<1e-9
        board.BuildConnectivity()
        conn=board.GetConnectivity()
        conn.RecalculateRatsnest()
        missing=conn.GetUnconnectedCount(False)
        drc=json.loads((out/"drc.json").read_text())
        erc=json.loads((out/"erc.json").read_text())
        status=summarize(drc,erc)
        result=dict(board=ident,source_sha256=hashes,commands=commands,native_version=pcbnew.GetBuildVersion(),
            actual_footprints=expected_footprints,actual_electrical_parts=len(actual),board_thickness_mm=thickness,
            copper_layers=board.GetCopperLayerCount(),pin_value_mismatches=mismatch,status=status,
            uncapped_open_connections=missing,expected_parent_opens=expected_opens,
            default_ignored_ERC_checks_promoted=promoted,all_sources_unchanged=all(sha(Path(p))==h for p,h in hashes.items()),
            physical_qualified=False,fabrication_released=False)
        results.append(result)
        print(ident,missing,"opens;",status["counts"],"pin mismatches",len(mismatch),flush=True)
    report_path.write_text(json.dumps(dict(recipe_sha256=sha(Path(__file__)),results=results,
        native_Mac_apps_launched=0,full_new_mechanical_receiving_pending=True,
        physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    assert all(r["all_sources_unchanged"] and not r["pin_value_mismatches"] for r in results)
    assert all(r["uncapped_open_connections"]==r["expected_parent_opens"] for r in results)


if __name__=="__main__":
    run()
