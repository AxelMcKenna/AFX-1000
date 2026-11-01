"""FPC01 NEW native fan protection/health composition; preserve both parents."""

import copy
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
FH = ROOT.parent / "circuit"
FP = ROOT.parents[1] / "fan_protection"
LIB = Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def components():
    result = []
    provenance = []
    removed = []
    for prefix, parent in [("FH02", FH), ("FP01", FP)]:
        handoff = json.loads((parent / "handoff.json").read_text())
        for rel, digest in handoff["files_sha256"].items():
            assert sha(parent / rel) == digest, (prefix, rel)
        for rel in ["handoff.json", "components.json", "generated/analysis.json", "generated/netlist.xml"]:
            dest = ROOT / "sources" / prefix / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                assert sha(dest) == sha(parent / rel), "Preserve captured parent"
            else:
                shutil.copy2(parent / rel, dest)
        old = json.loads((parent / "components.json").read_text())
        for original in old:
            ref = original["ref"]
            if (prefix == "FH02" and ref == "J1") or (prefix == "FP01" and ref == "J4"):
                removed.append(dict(parent=prefix, ref=ref, part=original["part"], pins=original["pins"],
                                    reason="Redundant interboard6pinheader; all four operating nodes now directPCBnets; twoFAULToutputs were unused inFH02"))
                continue
            p = copy.deepcopy(original)
            if prefix == "FH02" and ref in ("C20","C21"):
                p["part"] = "15pF 50V C0G5% C0603C150J5GACTU"
                p["footprint"] = "Capacitor_SMD:C_0603_1608Metric"
                p["note"] += " Composite: same15pF50V5%C0G valueinreal0603package forshortclockloops; parasiticloadrequiresfreshqualification."
            if prefix == "FP01":
                p["ref"] = ref[0] + str(int(ref[1:]) + 200)
                for pin in p["pins"]:
                    if pin["net"] == "FAN_GND":
                        pin["net"] = "GND"
                    if pin["net"] in ("FAN_L_FAULT_N", "FAN_R_FAULT_N"):
                        pin["net"] = None
                        p["note"] += " Composite: unusedFAULToutputexplicitNC afterremovinginterboardheader; protectioninternalfaultfunctionunchanged."
            p["parent"] = prefix
            p["parent_ref"] = ref
            original_id = p["footprint"]
            library, alias = original_id.split(":")
            source = (parent if library.startswith("RMX_") else LIB) / (library + ".pretty") / (alias + ".kicad_mod")
            target_name = original_id.replace(":", "__")
            target = ROOT / "FPC01.pretty" / (target_name + ".kicad_mod")
            target.parent.mkdir(exist_ok=True)
            if not target.exists():
                shutil.copy2(source, target)
            else:
                assert sha(source) == sha(target), (ref, "captured library changed")
            footprint = "FPC01:" + target_name
            if original_id == "Package_SO:VSSOP-8_2.3x2mm_P0.5mm":
                node = read_sexpr(source.read_text())
                node[1] = "TI_DCU0008A"
                for pad in children(node, "pad"):
                    n = int(pad[1])
                    first(pad, "at")[1:3] = [-1.55 if n <= 4 else 1.55,
                        -.75+.5*(n-1) if n <= 4 else .75-.5*(n-5)]
                    first(pad, "size")[1:3] = [.85,.30]
                    first(pad, "roundrect_rratio")[1] = .05/.30
                    pad.append([a("solder_mask_margin"),.025])
                target = ROOT / "FPC01.pretty/TI_DCU0008A.kicad_mod"
                target.write_text(sexpr(node)+"\n")
                footprint = "FPC01:TI_DCU0008A"
            if original_id == "Package_SO:HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm":
                node=read_sexpr(source.read_text());node[1]="TI_DGN0008C"
                node=[n for n in node if not (isinstance(n,list) and n and n[0]=="pad" and not str(n[1]))]
                for pad in children(node,"pad"):
                    n=int(pad[1])
                    if n<=8:
                        first(pad,"at")[1:3]=[-2.2 if n<=4 else 2.2,-.975+.65*(n-1) if n<=4 else .975-.65*(n-5)]
                        first(pad,"size")[1:3]=[1.4,.45]
                        first(pad,"roundrect_rratio")[1]=.05/.45
                        pad.append([a("solder_mask_margin"),.025])
                    else:
                        first(pad,"size")[1:3]=[2.,3.]
                        first(pad,"layers")[1:]=["F.Cu"]
                node.append([a("pad"),"",a("smd"),a("roundrect"),[a("at"),0,0],[a("size"),1.6,1.92],
                    [a("layers"),"F.Mask","F.Paste"],[a("roundrect_rratio"),.05/1.6]])
                target=ROOT/"FPC01.pretty/TI_DGN0008C.kicad_mod"
                target.write_text(sexpr(node)+"\n");footprint="FPC01:TI_DGN0008C"
            p["footprint"] = footprint
            k = len(result)
            p["x"], p["y"] = round(55.88+137.16*(k%5),2), round(71.12+111.76*(k//5),2)
            provenance.append(dict(ref=p["ref"], parent=prefix, parent_ref=ref,
                parent_part=original["part"],composite_part=p["part"],
                parent_footprint=original["footprint"],original_footprint=original_id, original_library_sha256=sha(source),
                composite_footprint=footprint, composite_library_sha256=sha(target),
                actual_pins_renamed=p["pins"]))
            result.append(p)
    assert len(result) == 84
    report = dict(scope="Native circuit composition; not PCB/noise/physical acceptance",
        parents={"FH02":sha(FH/"handoff.json"),"FP01":sha(FP/"handoff.json")},
        original_part_count=86, composite_part_count=84, removed_headers=removed,
        reference_renaming="FH02unchanged;FP01reference numbers+200",
        net_aliases={"FP01.FAN_GND":"GND"},
        unused_output_net_removal={"FP01.FAN_L_FAULT_N":"U201.4explicitNC","FP01.FAN_R_FAULT_N":"U301.4explicitNC"},
        retained_functional_nodes=["FAN5V_IN","GND","FAN_L_TACH","FAN_R_TACH"],
        functional_current_budget_delta_a=0,
        same_value_clock_cap_package_change=dict(refs=["C20","C21"],part="C0603C150J5GACTU",value="15pF50V5%C0G",parent_package="1206",composite_package="0603",manufacturer_capacitance_qualified=False),
        deleted_connector_and_wire_loss_credit_taken=False,
        manufacturer_land_change=dict(ref="U8", drawing="TI DCU0008A4225266/A09/2014", primary_FH02_pdf="sources/sn74lvc1g74.pdf", primary_page=23,
            pad_size_mm=[.85,.30], row_centres_mm=3.1, pitch_mm=.5, corner_radius_mm=.05, manufacturer_process_accepted=False),
        manufacturer_LDO_land_change=dict(ref="U2",drawing="TI DGN0008C4218838/A11/2017",primary_FH02_pdf="sources/tps7a16.pdf",primary_pages=[35,36],
            pad_size_mm=[1.4,.45],row_centres_mm=4.4,pitch_mm=.65,EP_copper_mm=[2.,3.],EP_mask_and_125um_stencil_mm=[1.6,1.92],manufacturer_process_accepted=False),
        parts=provenance, physical_qualified=False, fabrication_released=False)
    return result, report


def inventory(parts):
    rows=[]
    for p in parts:
        source=ROOT/"FPC01.pretty"/(p["footprint"].split(":")[1]+".kicad_mod")
        tree=read_sexpr(source.read_text())
        points=[]
        for tag in ("fp_line","fp_rect"):
            for n in children(tree,tag):
                if first(n,"layer")[1]=="F.CrtYd":
                    points.extend([[float(x) for x in first(n,t)[1:3]] for t in ("start","end")])
        bbox=[min(x[0] for x in points),min(x[1] for x in points),max(x[0] for x in points),max(x[1] for x in points)]
        pads={str(n[1]) for n in children(tree,"pad") if str(n[1])}
        assert pads=={n["number"] for n in p["pins"]},p["ref"]
        rows.append(dict(ref=p["ref"],part=p["part"],footprint=p["footprint"],courtyard_bbox_mm=bbox,
            library_sha256=sha(source),courtyard_area_mm2=(bbox[2]-bbox[0])*(bbox[3]-bbox[1])))
    return dict(rows=rows,total_enclosing_courtyard_area_mm2=sum(r["courtyard_area_mm2"] for r in rows),
        minimum_placement_edge_margin_mm=2, receiving_board_mm=[66,34,1.6], physical_fit_proven=False)


def main():
    (ROOT/"generated").mkdir(exist_ok=True)
    parts,report=components()
    generate(ROOT,"FPC01","fan_power_health",parts,
        [(20,1970,"FPC01: NEWnativecompositiononly. RAW5operatingforcebranchP03J23/J21; neverTESTJ3."),
         (20,1980,"FP01andFH02parentsunchanged. Two6pinheadersremoved; functionalcurrentdelta0. Allphysical/current/noiseholdsretained."),
         (20,1990,"ReceivingPCB66x34/4layers1.6mm. Actualroute/fit/loop/thermalreceiptsrequiredbeforeanymanufacturingrelease.")],
        (760,2030),[("FAN5V_IN",20.32,20.32),("GND",60.96,20.32)])
    (ROOT/"fp-lib-table").write_text('(fp_lib_table (version 7) (lib (name "FPC01") (type "KiCad") (uri "${KIPRJMOD}/FPC01.pretty") (options "") (descr "Captured and explicitly reviewed manufacturer footprints")))\n')
    (ROOT/"generated/composition.json").write_text(json.dumps(report,indent=2)+"\n")
    (ROOT/"generated/footprint-inventory.json").write_text(json.dumps(inventory(parts),indent=2)+"\n")
    cli="/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    env=dict(os.environ,KICAD_CONFIG_HOME="/private/tmp/rmx-kicad-config",FONTCONFIG_FILE=str(REPO/"build-hardware/kicad-fonts.conf"))
    commands=[]
    for label,args in [("netlist",["sch","export","netlist","--format","kicadxml","--output",str(ROOT/"generated/netlist.xml")]),
                       ("erc",["sch","erc","--format","json","--output",str(ROOT/"generated/erc.json")])]:
        cmd=[cli,*args,str(ROOT/"fan_power_health.kicad_sch")]
        p=subprocess.run(cmd,env=env,capture_output=True,text=True)
        (ROOT/"generated"/(label+".log")).write_text(p.stdout+p.stderr)
        commands.append(dict(command=cmd,returncode=p.returncode))
        assert p.returncode==0,(label,p.stderr)
    actual,pins=netlist(ROOT/"generated/netlist.xml")
    expected={c["ref"]:{p["number"]:p["net"] for p in c["pins"]} for c in parts}
    for ref,pmap in expected.items():
        for n,net in pmap.items():
            assert pins[ref][n]==net if net is not None else pins[ref][n].startswith("unconnected-"),(ref,n)
        assert actual[ref].findtext("value")==next(c["part"] for c in parts if c["ref"]==ref)
    erc=json.loads((ROOT/"generated/erc.json").read_text())
    findings=[v for s in erc["sheets"] for v in s["violations"]]
    (ROOT/"generated/native-schematic.json").write_text(json.dumps(dict(parts=len(parts),native_pin_map_differences=0,findings=findings,commands=commands,physical_qualified=False),indent=2)+"\n")
    print("FPC01",len(parts),"parts; nativepinparity0; ERC",len(findings))


if __name__=="__main__":
    main()
