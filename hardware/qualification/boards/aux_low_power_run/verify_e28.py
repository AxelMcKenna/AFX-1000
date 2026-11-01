"""Fresh headless Linux checks on the actual271-part E28 low-power successor."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pcbnew

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.rail_disconnect.revision28.native_profile import summarize

REPO=Path(__file__).resolve().parents[4]
WORK=REPO/"hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--label",default="native")
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--process-profile",choices=["standard","single-ready-020"],default="standard")
    parser.add_argument("--clipped-j12-silk", action="store_true")
    args=parser.parse_args()
    process_profile=args.process_profile
    assert args.label and all(c.isalnum() or c in "-_" for c in args.label)
    out=WORK/"generated"/args.label
    out.mkdir(exist_ok=False)
    candidate = args.candidate.resolve() if args.candidate else WORK / "rail_disconnect.kicad_pcb"
    assert candidate.is_relative_to(WORK.resolve()) and candidate.is_file()
    sources=[WORK/"rail_disconnect.kicad_pcb",WORK/"rail_disconnect.kicad_sch",WORK/"rail_disconnect.kicad_pro",WORK/"components.json"]
    before={str(p):sha(p) for p in sources}
    before[str(candidate)] = sha(candidate)
    for suffix in [".kicad_pcb",".kicad_sch",".kicad_pro"]:
        shutil.copyfile(WORK/("rail_disconnect"+suffix),out/("rail_disconnect"+suffix))
    shutil.copyfile(candidate, out / "rail_disconnect.kicad_pcb")
    process_audit={"profile":process_profile,"changed_rules":{}}
    if process_profile=="single-ready-020":
        audit_board=pcbnew.LoadBoard(str(candidate))
        small=[v for v in audit_board.GetTracks() if v.GetClass()=="PCB_VIA" and v.GetDrillValue()<300000]
        assert len(small)==1,"This profile permits exactly one smaller through-via"
        via=small[0]
        assert via.GetNetname()=="/E28_OUT_READY" and via.GetDrillValue()==200000
        assert all(via.GetWidth(audit_board.GetLayerID(layer))>=500000 for layer in ("F.Cu","B.Cu"))
        project=out/"rail_disconnect.kicad_pro"
        settings=json.loads(project.read_text())
        rules=settings["board"]["design_settings"]["rules"]
        original_rules=dict(rules)
        assert rules["min_through_hole_diameter"]==.3 and rules["min_via_annular_width"]==.15
        rules["min_through_hole_diameter"]=.2
        assert {k:(original_rules[k],rules[k]) for k in rules if rules[k]!=original_rules[k]}=={"min_through_hole_diameter":(.3,.2)}
        project.write_text(json.dumps(settings,indent=2)+"\n")
        process_audit.update(changed_rules={"min_through_hole_diameter":{"before_mm":.3,"after_mm":.2}},
            audited_small_via_uuid=via.m_Uuid.AsString(),small_via_net=via.GetNetname(),
            only_one_via_below_030=True,annular_and_clearance_rules_unchanged=True,
            supplier_process_acceptance=False)
    for name in ["fp-lib-table","sym-lib-table"]:
        (out/name).write_text((WORK/name).read_text().replace("${KIPRJMOD}/","${KIPRJMOD}/../../"))
    library_audit = None
    if args.clipped_j12_silk:
        # A project-local reviewed library keeps mismatch checking enabled and
        # leaves all preserved parent projects and their shared library intact.
        library = "JST_B2B_PH_SM4_TB_MechanicalLands.kicad_mod"
        source_land = WORK / "RMX_E28.pretty" / library
        shutil.copytree(WORK / "RMX_E28.pretty", out / "RMX_E28.pretty")
        land = out / "RMX_E28.pretty" / library
        tree = read_sexpr(land.read_text())
        edits = 0
        for line in children(tree, "fp_line"):
            if first(line, "layer")[1] != "F.SilkS":
                continue
            changed = False
            for tag in ("start", "end"):
                point = first(line, tag)
                if float(point[2]) < -3.65:
                    assert float(point[2]) == -4.36
                    point[2] = a(-3.65)
                    changed = True
            edits += changed
        assert edits == 3
        land.write_text(sexpr(tree) + "\n")
        table = out / "fp-lib-table"
        table.write_text(table.read_text().replace("${KIPRJMOD}/../../RMX_E28.pretty", "${KIPRJMOD}/RMX_E28.pretty"))
        library_audit = dict(original_land_sha256=sha(source_land), checked_land_sha256=sha(land),
                             changed_silkscreen_strokes=3, project_local_copy=True,
                             shared_parent_library_unchanged=True)
    commands=[]
    for label,args in [
        ("netlist",["sch","export","netlist","--format","kicadxml","--output",str(out/"netlist.xml"),str(WORK/"rail_disconnect.kicad_sch")]),
        ("erc",["sch","erc","--format","json","--severity-all","--output",str(out/"erc.json"),str(WORK/"rail_disconnect.kicad_sch")]),
        ("drc",["pcb","drc","--format","json","--all-track-errors","--schematic-parity","--severity-all","--refill-zones","--save-board","--output",str(out/"drc.json"),str(out/"rail_disconnect.kicad_pcb")]),
    ]:
        p=subprocess.run(["kicad-cli",*args],capture_output=True,text=True,timeout=120)
        (out/(label+".log")).write_text(p.stdout+p.stderr)
        commands.append(dict(command=["kicad-cli",*args],returncode=p.returncode))
        assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr)
    actual,pins=netlist(out/"netlist.xml")
    declared=json.loads((WORK/"components.json").read_text())
    assert len(actual)==len(declared)==271
    mismatch=[]
    for c in declared:
        if actual[c["ref"]].findtext("value")!=c["part"]:
            mismatch.append([c["ref"],"value"])
        for pin in c["pins"]:
            n=pins[c["ref"]].get(pin["number"])
            if pin["net"] is not None and n!=pin["net"]:
                mismatch.append([c["ref"],pin["number"],n,pin["net"]])
    b=pcbnew.LoadBoard(str(out/"rail_disconnect.kicad_pcb"))
    assert len(list(b.GetFootprints()))==275
    b.BuildConnectivity()
    conn=b.GetConnectivity()
    conn.RecalculateRatsnest()
    missing=conn.GetUnconnectedCount(False)
    raw=json.loads((out/"drc.json").read_text())
    erc=json.loads((out/"erc.json").read_text())
    status=summarize(raw,erc)
    assert len(raw["unconnected_items"])==min(missing,499)
    assert all(sha(Path(n))==h for n,h in before.items())
    report=dict(source_sha256=before,native_commands=commands,
                actual_native_parts=271,actual_native_footprints=275,
                declared_pin_value_mismatches=mismatch,uncapped_missing_connections=missing,
                status=status,all_sources_unchanged=True,native_Mac_apps_launched=0,
                manufacturing_process_audit=process_audit,checked_project_sha256=sha(out/"rail_disconnect.kicad_pro"),
                connector_library_audit=library_audit,
                raw_DRC_sha256=sha(out/"drc.json"),filled_PCB_sha256=sha(out/"rail_disconnect.kicad_pcb"),
                physical_qualified=False,complete_current_bounds_qualified=False,fabrication_released=False)
    (out/"review.json").write_text(json.dumps(report,indent=2)+"\n")
    assert not mismatch,mismatch
    print("E28 lowpower:",missing,"uncapped opens; counts",status["counts"])


if __name__=="__main__":
    main()
