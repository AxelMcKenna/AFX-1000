"""Private source-derived coherent partial32 unit, ground129.5 and R02 return."""

import json
import re
import shutil
from pathlib import Path

from hardware.cad.a12.enclosure_growth.integration.stage import actual_bores
from hardware.cad.a12.repaired import outline
from hardware.electronics.common.sexpr import children, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard

from .ground_route import ROOT, REPO, sha, write


def fps(path):
    return {next(p[2] for p in children(f,"property") if p[1]=="Reference"):f
            for f in children(read_sexpr(path.read_text()),"footprint")}


def build():
    derived=ROOT/"derived_model"
    if derived.exists():
        raise RuntimeError("Fresh derived scene required")
    cap=json.loads((ROOT/"capture.json").read_text())
    assert all(sha(ROOT/n)==h for n,h in cap["copied_input_sha256"].items())
    assert all(sha(ROOT/n)==h for n,h in cap["AP03_source_model_sha256"].items())
    physical=json.loads((ROOT/"generated/actual-native-boards.json").read_text())
    nativeboards=[]
    for b in physical["boards"]:
        path=ROOT/"inputs"/b["id"]/("power_p03.kicad_pcb" if b["id"]=="P03" else "rail_disconnect.kicad_pcb")
        tree=read_sexpr(path.read_text())
        nativeboards.append([b["id"],b["datum"],b["nominal_thickness_mm"],b["outline_relative_mm"],actual_bores(tree)])
    sourcejoints=[r for r in physical["boxes"] if r[0].startswith("E28_J4")]
    boxes=[r for r in physical["boxes"] if not r[0].startswith("E28_J4")]
    r1path=ROOT/"inputs/R1/processor_carrier.kicad_pcb"
    baseline=REPO/"hardware/cad/a12/harness/proposals/processor-awg18-ear-fanout-j29-central/processor_carrier.kicad_pcb"
    old,new=fps(baseline),fps(r1path)
    assert set(old)==set(new) and len(new)==88 and all(sexpr(old[k])==sexpr(new[k]) for k in new if k!="R1")
    bb=courtyard(new["R1"],"F.CrtYd")
    r1=["e19_R1",bb[0]-70,bb[1]-58,8.1,bb[2]-bb[0],bb[3]-bb[1],1.0]
    assert all(abs(a-b)<1e-7 for a,b in zip(r1[1:],[107.91,78.07,8.1,4.18,7.86,1]))
    tree=read_sexpr(r1path.read_text())
    receiver_outline=outline(tree)
    receiver_holes=actual_bores(tree)
    wire=json.loads((ROOT/"generated/ground-route.json").read_text())
    wr=json.loads((ROOT/"inputs/PB02/wire-raise-1mm/plan.json").read_text())["only_overrides"]
    prefix=wire["paths_mm"]["native"]
    i=wire["boundary_indices"]["native"]
    ground_middle=prefix[i["source_initial_straight_end"]:i["destination_stub_start"]+1]
    pf={"pf_bend":[wr["pf_bend"][0],prefix[i["source_initial_straight_end"]]],
        "pf_middle":[wr["pf_middle"][0],ground_middle],"pf_stub_start":[wr["pf_stub_start"][0],[188,104,15.1]],
        "pf_start":[[161,120.5,6.62],[161,129.5,6.62]],"pf_source_cut":[[161,120.5,9.72],[161,129.5,9.72]],
        "pf_source_tail":[[161,120.5,3.5],[161,129.5,3.5]],
        "pf_source_outline":next(b[3] for b in nativeboards if b[0]=="E28"),"pf_receiver_outline":receiver_outline}
    shutil.copytree(ROOT/"model",derived)
    old_return=derived/"context/hardware/cad/a12/returns/generated/returns.scad"
    old_return_copy=ROOT/"inputs/old-return.scad"
    shutil.copyfile(old_return,old_return_copy)
    new_return=ROOT/"return_variant/generated/returns.scad"
    return_text=new_return.read_text()
    return_text=re.sub(r'import\("([^\"]+)"\)',lambda m:'import("'+str(new_return.parent/m.group(1))+'")',return_text)
    changes=[]
    for p in derived.rglob("*.scad"):
        oldtext=p.read_text()
        s=oldtext.replace(str(ROOT/"model"),str(derived))
        # Replace the actual old base/floor bore arrays beforeCSG; never add
        # an overlapping second hole1.5mm away from the first.
        s=s.replace('return_supports=[[166, 113], [166, 133.125]];',
                    'return_supports=[[166, 113], [166, 134.625]];')
        replacements={"ui_native_boards":nativeboards,"ui_native_boxes":boxes,
            "ui_native_cylinders":physical["cylinders"],"ui_source_joints":sourcejoints,
            "ui_receiver_outline":receiver_outline,"ui_receiver_holes":receiver_holes,
            "repaired_boards":nativeboards,"repaired_boxes":physical["boxes"],"repaired_cylinders":physical["cylinders"]}
        replacements.update(pf)
        for key,value in replacements.items():
            s=re.sub('^'+key+r'=.*;$',key+'='+json.dumps(value)+';',s,flags=re.M)
        for line in s.splitlines():
            if line.startswith("ui_inherited_envelopes="):
                rows=json.loads(line.split("=",1)[1].rstrip(";"))
                assert sum(r[0]=="e19_R1" for r in rows)==1
                rows=[r1 if r[0]=="e19_R1" else r for r in rows]
                s=s.replace(line,"ui_inherited_envelopes="+json.dumps(rows)+";")
        oldpos=str(derived/"context/hardware/cad/a12/positive_links/generated/positive-links.stl")
        s=s.replace(oldpos,str(ROOT/"inputs/PB02-generated/positive-links.stl"))
        if p==old_return:
            s=return_text
        p.write_text(s)
        if oldtext!=s:
            changes.append(dict(path=str(p.relative_to(ROOT)),old_sha256=__import__("hashlib").sha256(oldtext.encode()).hexdigest(),new_sha256=sha(p)))
    # The new SCAD entry preservesAP03actualmechanicaldefinitions; only imports
    # point to the derived board/return/wire context above.
    source=(ROOT/"generated/checks.scad").read_text().replace(str(ROOT/"model"),str(derived))
    (ROOT/"generated/unified-context.scad").write_text(source)
    write(ROOT/"generated/derivation.json",dict(changes=changes,
        native_components=507,all_other_E19_footprints_unchanged=87,new_R1_actual_courtyard=r1,
        native_board_actual_drilled_holes={b[0]:len(b[4]) for b in nativeboards},
        receiver_actual_drilled_holes=len(receiver_holes),new_source_joints=sourcejoints,
        source_ground_native=[161,129.5,6.62],wire_arrays=pf,
        old_positive_hardware_removed_and_replaced_not_union=True,
        old_ANA_support_bore_replaced_not_duplicated=True,
        old_source_ground_and_return_geometry_retained_as_controls=True,
        source_sha256={str(p):sha(p) for p in [Path(__file__),ROOT/"capture.json",ROOT/"generated/ground-route.json",r1path,baseline,new_return]},
        derived_source_sha256={str(p.relative_to(ROOT)):sha(p) for p in derived.rglob("*") if p.is_file()},
        physical_qualified=False,thermal_qualified=False,full_wiring_qualified=False))
    print(json.dumps(dict(derived=True,changed_sources=len(changes),native_parts=507,R1_otherFP_exact=87)))


if __name__=="__main__":
    build()
