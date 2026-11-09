"""Repair TBP07's new-cell spacing, schematic grid and datasheet parity.

The failed native checkpoint is retained. Original 1,077 parts remain untouched.
"""
import copy
import json
import shutil
from pathlib import Path

from shapely.affinity import translate
from shapely.geometry import box
from shapely.ops import unary_union

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.assembly_layout import outline
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.integrate_two_board_power_v3 import promote

SOURCE=STAGING/"two-board-power-integration-07"
OUT=STAGING/"two-board-power-integration-08"
DESIGN=STAGING/"two-board-module-feed-01/design.json"


def run():
    assert not OUT.exists()
    shutil.copytree(SOURCE,OUT)
    d=json.loads(DESIGN.read_text())
    parts=copy.deepcopy(d["components"])
    values={"R1":"470k 0.1% 25ppm", "R2":"59.0k 0.1% 25ppm", "R3":"470k 0.1% 25ppm",
        "R4":"43.2k 0.1% 25ppm", "R5":"6.49k 0.1% 25ppm",
        "C3":"4.7nF 50V C0G 5%", "C4":"2.2nF 50V C0G 5%"}
    for c in parts:
        c["part"]=values.get(c["ref"],c["part"])
        c["x"],c["y"]=[round(round(c[k]/1.27)*1.27,4) for k in ["x","y"]]
    gen=OUT/"module-cell-grid"
    generate(gen,"TBP07","module_input",parts,[
        (25.4,248.92,"Independent P03 feed. G_NT1 alone joins primary return to P_C103.2; no NF AGND tie."),
        (25.4,259.08,"Resistor complete budget 0.5%; timing capacitor complete budget 6%. Exact passive BOM remains open."),
        (25.4,269.24,"Provisional: confirm startup/current/capacitance, fault containment, transients and physical routing.")],(330,290),[])
    old=read_sexpr((SOURCE/"G_module_input.kicad_sch").read_text())
    oldsyms={prop(s,"Reference")[2]:s for s in children(old,"symbol")}
    s=read_sexpr((gen/"module_input.kicad_sch").read_text())
    for sym in children(s,"symbol"):
        ref="G_"+prop(sym,"Reference")[2];prop(sym,"Reference")[2]=ref
        first(sym,"instances")[:]=copy.deepcopy(first(oldsyms[ref],"instances"))
    for lab in children(s,"label"):
        if str(lab[1]).startswith("PWR_"):promote(lab,lab[1])
    (OUT/"G_module_input.kicad_sch").write_text(sexpr(s)+"\n")
    shutil.copyfile(gen/"RMX_TBP07.kicad_sym",OUT/"symbols/RMX_TBP07.kicad_sym")
    expected=json.loads((SOURCE/"expected-circuit.json").read_text())
    tree,polygon=outline(SOURCE/"power_protection.kicad_pcb")
    fps={prop(f,"Reference")[2]:f for f in children(tree,"footprint")}
    for c in parts:
        ref="G_"+c["ref"];fp=fps[ref]
        prop(fp,"Value")[2]=c["part"];expected[ref]["value"]=c["part"]
        ds=next(iter([p for p in children(fp,"property") if p[1]=="Datasheet"]),None)
        if ds is None:
            fp.append(read_sexpr(f'(property "Datasheet" {json.dumps(c["source"])} (at 0 0 0) (layer "F.Fab") (effects (font (size 1 1)) (hide yes)))'))
        else:ds[2]=c["source"]
    offsets=dict(U1=(0,0),C1=(-4,0),C2=(4.5,0),D1=(-5,-5),D2=(5,-5),
        R1=(-4.5,3.5),R3=(-.7,3.5),R5=(3.1,3.5),C3=(7,3.5),R2=(-4.5,6.5),R4=(-.7,6.5),C4=(3.5,6.5))
    shapes=[]
    for r,offset in offsets.items():
        fp=fps["G_"+r];first(fp,"at")[1:]=[0,0,0]
        shape=translate(box(*courtyard(fp,"F.CrtYd")).buffer(.15),*offset)
        assert all(not shape.intersects(other) for other in shapes),r
        shapes.append(shape)
    cell=unary_union(shapes)
    obstacles=[]
    for ref,f in fps.items():
        if ref.startswith("G_") and ref!="G_NT1":continue
        side=str(first(f,"layer")[1])[0]
        if side=="F" or any(p[2] in ["thru_hole","np_thru_hole"] for p in children(f,"pad")):
            obstacles.append(box(*courtyard(f,side+".CrtYd")).buffer(.3))
    occupied=unary_union(obstacles); interior=polygon.buffer(-.5)
    candidates=[(x*.5,y*.5) for x in range(28,640) for y in range(24,350)]
    candidates.sort(key=lambda xy:(xy[0]-193.5)**2+(xy[1]-114)**2)
    for x,y in candidates:
        shape=translate(cell,x,y)
        if interior.contains(shape) and not occupied.intersects(shape):break
    else:raise AssertionError("Cell needs wider placement rework")
    for r,(dx,dy) in offsets.items():first(fps["G_"+r],"at")[1:]=[x+dx,y+dy,0]
    (OUT/"power_protection.kicad_pcb").write_text(sexpr(tree)+"\n")
    root=read_sexpr((OUT/"power_protection.kicad_sch").read_text())
    first(first(root,"title_block"),"rev")[1]="TBP08"
    (OUT/"power_protection.kicad_sch").write_text(sexpr(root)+"\n")
    (OUT/"expected-circuit.json").write_text(json.dumps(expected,indent=2,sort_keys=True)+"\n")
    placement=json.loads((SOURCE/"module-placement.json").read_text());placement["cell_origin_mm"]=[x,y]
    placement["new_cell_internal_courtyard_spacing_screen"]=True
    (OUT/"module-placement.json").write_text(json.dumps(placement,indent=2)+"\n")
    record=json.loads((SOURCE/"construction.json").read_text())
    record.update(revision="TBP08",source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),DESIGN,
        STAGING/"two-board-power-native-07/review.json",*[p for p in SOURCE.rglob("*") if p.is_file()]]},
        repaired_findings=["9 new-cell clearance/courtyard errors","3 Datasheet parity warnings","46 schematic grid warnings"],
        original_components_or_circuit_changed=False, native_validation_pending=True)
    (OUT/"construction.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps(placement))


if __name__=="__main__":run()
