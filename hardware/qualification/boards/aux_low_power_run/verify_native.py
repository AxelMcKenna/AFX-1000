"""Fail-fast isolated-Linux export/ERC and exact physical pin/value checks."""

import hashlib
import json
import subprocess
from pathlib import Path

from hardware.electronics.common.netlists import netlist

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not (ROOT / "generated/native.json").exists()
    version = subprocess.run(["kicad-cli","version"],capture_output=True,text=True,timeout=10)
    assert version.returncode==0 and version.stdout.strip()=="10.0.7"
    results=[]
    for folder, project in [(ROOT,"power_run_low_power"),(ROOT/"receiver","power_run_receiver")]:
        out=folder/"generated"
        out.mkdir(exist_ok=True)
        source=folder/(project+".kicad_sch")
        before=sha(source)
        commands=[]
        for label, options in [
            ("netlist",["sch","export","netlist","--format","kicadxml","--output",str(out/"netlist.xml")]),
            ("erc",["sch","erc","--severity-all","--format","json","--output",str(out/"erc.json")]),
            ("svg",["sch","export","svg","--output",str(out/"svg")]),
        ]:
            cmd=["kicad-cli",*options,str(source)]
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
            (out/(label+".log")).write_text(p.stdout+p.stderr)
            commands.append(dict(command=cmd,returncode=p.returncode))
            assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr)
        declared=json.loads((folder/"components.json").read_text())
        parts,pins=netlist(out/"netlist.xml")
        mismatch=[]
        for c in declared:
            if parts[c["ref"]].findtext("value")!=c["part"]:
                mismatch.append([c["ref"],"value"])
            for p in c["pins"]:
                actual=pins[c["ref"]].get(p["number"])
                if p["net"] is None:
                    if actual is not None and not actual.startswith("unconnected-"):
                        mismatch.append([c["ref"],p["number"],actual,None])
                elif actual!=p["net"]:
                    mismatch.append([c["ref"],p["number"],actual,p["net"]])
        findings=[v for s in json.loads((out/"erc.json").read_text())["sheets"] for v in s["violations"]]
        row=dict(project=project,parts=len(declared),source_sha256=before,commands=commands,
                 mismatches=mismatch,ERC=findings,source_unchanged=sha(source)==before)
        results.append(row)
        assert not mismatch and not findings and row["source_unchanged"],row
    (ROOT/"generated/native.json").write_text(json.dumps(dict(
        native_version="10.0.7",container_platform="linux/amd64",results=results,
        default_ignored_ERC_categories_promoted_to_error=["single_global_label","four_way_junction","simulation_model_issue","footprint_filter"],
        source_script_sha256=sha(Path(__file__)),native_Mac_apps_launched=0,
        PCB_implemented=False,physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("AX03 source/receiver:",[(r["parts"],len(r["ERC"]),len(r["mismatches"])) for r in results])


if __name__=="__main__":
    main()
