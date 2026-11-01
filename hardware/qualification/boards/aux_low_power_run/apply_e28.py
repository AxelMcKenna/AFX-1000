"""Source-bound E28 low-power successor; preserve the20-open parent exactly."""

import hashlib
import json
import shutil
from pathlib import Path

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.placement import placed_footprint
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
SOURCE = REPO / "hardware/electronics/rail_disconnect/revision28/generated/closed-logic-cleanup2-work"
WORK = SOURCE.parent / "low-power-run-work"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(f):
    return next(x[2] for x in children(f,"property") if x[1]=="Reference")


def normalized_land(path, name):
    t=read_sexpr(path.read_text())
    t[1]=name
    for text in children(t,"fp_text"):
        if text[1] in ["reference","value"]:
            text[0]=a("property")
            text[1]="Reference" if text[1]=="reference" else "Value"
    return t


def main():
    assert not WORK.exists()
    source=SOURCE/"rail_disconnect.kicad_pcb"
    before=sha(source)
    expected=json.loads((ROOT/"integration-proposal.json").read_text())
    assert before==expected["parent_E28_PCB_sha256"]
    tree=read_sexpr(source.read_text())
    old_footprints={ref(f):sexpr(f) for f in children(tree,"footprint")}
    original_copper={str(first(n,"uuid")[1]):sexpr(n) for kind in ["segment","via","zone"] for n in children(tree,kind)}
    WORK.mkdir()
    (WORK/"generated").mkdir()
    for p in SOURCE.iterdir():
        if p.is_file() and (p.suffix in [".kicad_pcb",".kicad_sch",".kicad_pro",".kicad_sym",".kicad_dru"] or p.name in ["components.json","fp-lib-table","sym-lib-table"]):
            shutil.copyfile(p,WORK/p.name)
        elif p.suffix==".pretty":
            shutil.copytree(p,WORK/p.name)
    parts=json.loads((ROOT/"e28-components-proposed.json").read_text())
    by={p["ref"]:p for p in parts}
    for p in parts:
        if p["ref"]=="U43":
            p["footprint"]="RMX_E28:AX03_DCK0005A"
        if p["ref"]=="C86":
            p["footprint"]="RMX_E28:AX03_C0603"
    notes=[(20,3650,"E28LP: Eight AUPDCU triples + highimpedanceRUN receiver; no original force/timing/reference or latch topology change."),
           (20,3660,"The full271part circuit is a new prototype. All actual-band threshold/current, completehousing, startup and physical gates remain unqualified.")]
    flags=[(name,25.4+i*76.2,25.4) for i,name in enumerate(["P19_SRC","N19_SRC","P12_SRC","N12_SRC","V5_REG_SRC","5V_DIG_SRC","V2V5_AUX","AGND"])]
    generate(WORK,"E17","rail_disconnect",parts,notes,(1700,3700),flags)
    # The source's exact strict design/DRC rules remain authoritative.
    shutil.copyfile(SOURCE/"rail_disconnect.kicad_pro",WORK/"rail_disconnect.kicad_pro")
    nets={str(n[2]).lstrip("/"):int(n[1]) for n in children(tree,"net")}
    assert "RUN_BUFFERED" not in nets
    nets["RUN_BUFFERED"]=max(nets.values())+1
    tree.append([a("net"),a(nets["RUN_BUFFERED"]),"/RUN_BUFFERED"])
    changed=[]
    for f in children(tree,"footprint"):
        name=ref(f)
        if name not in {"U28","R93",*("U"+str(i) for i in range(35,43))}:
            continue
        for p in children(f,"property"):
            if p[1] in ["Value","MPN"]:
                p[2]=by[name]["part"]
            elif p[1]=="Datasheet":
                p[2]=by[name]["source"]
        if name=="U28":
            pad=next(p for p in children(f,"pad") if p[1]=="1")
            first(pad,"net")[1:]=[a(nets["RUN_BUFFERED"]),"/RUN_BUFFERED"]
        changed.append(name)
    assert len(changed)==10
    # Only the old last B-side RUN branch is removed; its preserved raw trunk
    # still joins J5 and R93. New receiver input/output routing is explicit.
    old_uid="eeee037d-599a-597f-a323-0470f21ba53e"
    remove=next(n for n in children(tree,"segment") if first(n,"uuid")[1]==old_uid)
    assert int(first(remove,"net")[1])==nets["POWER_RUN"] and first(remove,"layer")[1]=="B.Cu"
    removed=sexpr(remove)
    tree.remove(remove)
    source_land=ROOT/"RMX_AX03.pretty/TI_DCK0005A.kicad_mod"
    dck=WORK/"RMX_E28.pretty/AX03_DCK0005A.kicad_mod"
    dck.write_text(sexpr(normalized_land(source_land,"AX03_DCK0005A"))+"\n")
    csrc=REPO/"hardware/qualification/boards/fan_health/composite_nf_branch/FPC01.pretty/Capacitor_SMD__C_0603_1608Metric.kicad_mod"
    cap=WORK/"RMX_E28.pretty/AX03_C0603.kicad_mod"
    cap.write_text(sexpr(normalized_land(csrc,"AX03_C0603"))+"\n")
    for name,pose,land in [("U43",(78,49,0,"F"),dck),("C86",(81.1,49.65,0,"F"),cap)]:
        c=by[name]
        fp=placed_footprint(dict(c,value=c["part"],mpn=c["part"],nets={p["number"]:p["net"] or "AX03_NC" for p in c["pins"]}),
            pose,land,{**nets,"AX03_NC":0},namespace="rmx:E28:AX03:")
        if name=="U43":
            p=next(p for p in children(fp,"pad") if p[1]=="1")
            p[:]=[x for x in p if not(isinstance(x,list) and x and x[0]=="net")]
        tree.append(fp)
    actual={ref(f):sexpr(f) for f in children(tree,"footprint")}
    assert len(actual)==275
    assert all(actual[name]==old for name,old in old_footprints.items() if name not in changed)
    current_copper={str(first(n,"uuid")[1]):sexpr(n) for kind in ["segment","via","zone"] for n in children(tree,kind)}
    assert set(original_copper)-set(current_copper)=={old_uid}
    assert all(value==current_copper[uid] for uid,value in original_copper.items() if uid!=old_uid)
    (WORK/"rail_disconnect.kicad_pcb").write_text(sexpr(tree)+"\n")
    assert sha(source)==before
    (WORK/"generated/construction.json").write_text(json.dumps(dict(
        source_PCB_sha256=before,new_PCB_sha256=sha(WORK/"rail_disconnect.kicad_pcb"),
        source_script_sha256=sha(Path(__file__)),exactly_preserved_existing_footprints=263,
        changed_metadata_or_U28_input_net_refs=sorted(changed),added_refs=["U43","C86"],
        all_original273_footprint_poses_preserved=True,removed_only_one_RUN_signal_branch=removed,
        all_other_tracks_vias_and_all_zones_exact=True, original_electrical_parts=269,new_electrical_parts=271,
        mechanical_footprints_unchanged=4, native_ERC_DRC_and_complete_pin_value_parity_required=True,
        current_voltage_PDN_and_physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("E28 lowpower candidate:271parts +4mechanical; original273poses/all force copper exact; one RUN leaf removed, two parts added")


if __name__=="__main__":
    main()
