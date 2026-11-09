"""TBP07: add guarded module power and a physical return-star net tie.

The added cell placement is provisional. Preserve every previous footprint;
native geometry and complete electrical delta are checked independently.
"""
import copy
import json
import math
import shutil
import uuid
from pathlib import Path

from shapely.geometry import box
from shapely.ops import unary_union

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.placement import strip_and_flip
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.assembly_layout import outline
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.integrate_two_board_power_v3 import promote

SOURCE = STAGING / "two-board-power-integration-06"
BASE = STAGING / "two-board-power-native-06"
DESIGN = STAGING / "two-board-module-feed-01/design.json"
OUT = STAGING / "two-board-power-integration-07"
PROJECT = "power_protection"


def uid(text):
    return str(uuid.uuid5(uuid.NAMESPACE_URL,"AFX:TBP07:"+text))


def footprint(name, body, pads, extra=""):
    return read_sexpr(f'''(footprint "{name}" (version 20250108) (generator pcbnew) (layer "F.Cu")
      (descr "TBP07 manufacturer drawing / declared copper star")
      (property "Reference" "REF**" (at 0 -2 0) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))
      (property "Value" "{name}" (at 0 2 0) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12)) (hide yes)))
      (attr smd) {body} {pads} {extra})''')


def rpw():
    # TI 4225183/A 08/2019, copper and 0.100mm-stencil example, visually reviewed.
    pads=[]
    def pad(n,x,y,w,h,layers):
        pads.append(f'(pad "{n}" smd roundrect (at {x} {y}) (size {w} {h}) (layers {layers}) (roundrect_rratio {round(.05/min(w,h),8)}))')
    for side, nums in [(-1,[1,2,3,4]),(1,[10,9,8,7])]:
        for n,y in zip(nums,[-.7,-.225,.225,.7]):
            corner=n in [1,4,7,10]
            pad(n,side*.9,y,.6,.3 if corner else .25,'"F.Cu" "F.Mask"')
            pad("",side*.9,y,.6,.275 if corner else .25,'"F.Paste"')
            if corner:
                pad(n,side*.725,math.copysign(.875,y),.25,.65,'"F.Cu" "F.Mask"')
                pad("",side*.7125,math.copysign(.875,y),.225,.65,'"F.Paste"')
    for n,x in [(5,-.25),(6,.25)]:
        pad(n,x,0,.3,2.4,'"F.Cu" "F.Mask"')
        for y in [-.63,.63]:
            pad("",x,y,.28,1.06,'"F.Paste"')
    body='''(fp_rect (start -1 -1) (end 1 1) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))
      (fp_rect (start -1.45 -1.45) (end 1.45 1.45) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
      (fp_circle (center -1.55 -.7) (end -1.45 -.7) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))'''
    return footprint("TI_RPW0010A",body," ".join(pads),'(solder_mask_margin .05)')


def star():
    return footprint("Return_Star",'''(fp_rect (start -1.2 -.8) (end 1.2 .8) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
      (fp_rect (start -.5 -.5) (end .5 .5) (stroke (width 0) (type default)) (fill solid) (layer "F.Cu"))
      (fp_rect (start -1 -.6) (end 1 .6) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))''',
      '''(pad "1" smd rect (at -.5 0) (size .8 1) (layers "F.Cu"))
      (pad "2" smd rect (at .5 0) (size .8 1) (layers "F.Cu"))''', '(net_tie_pad_groups "1,2")')


def place(tree, polygon, newfps):
    # Keep the new surface cell together where a reserved box actually fits.
    # No claim that this provisional position meets the final electrical layout.
    obstacles=[]
    for f in children(tree,"footprint"):
        side=str(first(f,"layer")[1])[0]
        if side=="F" or any(p[2] in ["thru_hole","np_thru_hole"] for p in children(f,"pad")):
            obstacles.append(box(*courtyard(f,side+".CrtYd")).buffer(.3))
    occupied=unary_union(obstacles)
    offsets=dict(U1=(0,0), C1=(-3,0), C2=(3.5,0), D1=(-5,-4), D2=(4.5,-4),
                 R1=(-3,3.5),R2=(-3,6),R3=(-.5,3.5),R4=(-.5,6),R5=(2,3.5),
                 C3=(5,3.5),C4=(5,6))
    # Blank placement template is fixed. Use nearest available entire-cell box.
    candidates=[(x*.5,y*.5) for x in range(28,640) for y in range(24,350)]
    candidates.sort(key=lambda xy:(xy[0]-193.5)**2+(xy[1]-114)**2)
    from shapely.affinity import translate
    interior=polygon.buffer(-.5)
    cell=unary_union([translate(box(*courtyard(newfps[r],"F.CrtYd")).buffer(.3),*d) for r,d in offsets.items()])
    location=None
    for x,y in candidates:
        shape=translate(cell,x,y)
        if interior.contains(shape) and not occupied.intersects(shape):
            location=(x,y);break
    assert location is not None,"No complete cell space; revise critical placement"
    for ref,(dx,dy) in offsets.items():
        first(newfps[ref],"at")[1:]=[location[0]+dx,location[1]+dy,0]
    occupied=unary_union([occupied,translate(cell,*location)])
    # Star is independently placed as close as possible to P_C103's ground pad.
    starfp=newfps["NT1"]
    for x,y in candidates:
        shape=translate(box(*courtyard(starfp,"F.CrtYd")).buffer(.3),x,y)
        if interior.contains(shape) and not occupied.intersects(shape):
            first(starfp,"at")[1:]=[x,y,0];break
    else:raise AssertionError("No return-star location")
    return dict(cell_origin_mm=location,star_xy_mm=first(starfp,"at")[1:3],
        star_target="P_C103.2", critical_placement_qualified=False,
        note="No previous part moved. New cell needs electrically optimized placement and star routing before release.")


def build():
    assert not OUT.exists()
    design=json.loads(DESIGN.read_text())
    assert all(sha(REPO/n)==v for n,v in design["source_sha256"].items())
    parts,pins=read_netlist(BASE/"netlist.xml")
    expected=json.loads((SOURCE/"expected-circuit.json").read_text())
    aliases={expected[r]["pins"][p]:name for name,r,p in [
        ("PWR_MODULE_FEED_IN","P_C103","1"), ("PWR_MODULE_12V","N_J6","1"),
        ("PWR_MODULE_INPUT_GND","N_J6","2")]}
    actual_aliases={pins[(r,p)]:name for name,r,p in [
        ("PWR_MODULE_FEED_IN","P_C103","1"),("PWR_MODULE_12V","N_J6","1"),("PWR_MODULE_INPUT_GND","N_J6","2")]}
    shutil.copytree(SOURCE,OUT)
    root=read_sexpr((OUT/(PROJECT+".kicad_sch")).read_text())
    rootid=first(root,"uuid")[1]; sid=uid("module_sheet")
    sheetnames={prop(s,"Sheetfile")[2]:prop(s,"Sheetname")[2] for s in children(root,"sheet")}
    for filename,scope in sheetnames.items():
        path=OUT/filename; s=read_sexpr(path.read_text())
        for lab in children(s,"label")+children(s,"global_label"):
            net=lab[1] if lab[0]=="global_label" else scope+"/"+lab[1]
            if net in actual_aliases:promote(lab,actual_aliases[net])
        if filename.startswith("N_"):
            flag=next(s0 for s0 in children(s,"symbol") if prop(s0,"Reference")[2]=="#N_FLAG1")
            at=first(flag,"at")[1:3]
            label=next(l for l in children(s,"global_label") if first(l,"at")[1:3]==at)
            assert label[1]=="PWR_MODULE_12V"
            s.remove(flag);s.remove(label)
            groundflag=next(s0 for s0 in children(s,"symbol") if prop(s0,"Reference")[2]=="#N_FLAG8")
            prop(groundflag,"Value")[2]="P03 operating return via G_NT1"
        path.write_text(sexpr(s)+"\n")
    for c in expected.values():c["pins"]={p:aliases.get(n,n) for p,n in c["pins"].items()}
    gen=OUT/"module-cell"
    generate(gen,"TBP07", "module_input",design["components"],[
        (25,250,"Independent input from P03 VIN_PROTECTED; never GLOBAL_MASTER powered."),
        (25,260,"G_NT1 is the only primary-return tie, at P_C103 ground. No local NF AGND tie."),
        (25,270,"Provisional electrical/physical design; transient, per-module fault and passive receiving remain open.")],(330,290),[])
    s=read_sexpr((gen/"module_input.kicad_sch").read_text())
    paths=json.loads((SOURCE/"symbol-paths.json").read_text())
    for sym in children(s,"symbol"):
        ref="G_"+prop(sym,"Reference")[2];prop(sym,"Reference")[2]=ref
        first(sym,"instances")[:]=read_sexpr(f'(instances (project "{PROJECT}" (path "/{rootid}/{sid}" (reference "{ref}") (unit 1))))')
        paths[ref]=f'/{rootid}/{sid}/{first(sym,"uuid")[1]}'
    for lab in children(s,"label"):
        if str(lab[1]).startswith("PWR_"):promote(lab,lab[1])
    filename="G_module_input.kicad_sch"
    (OUT/filename).write_text(sexpr(s)+"\n")
    shutil.copyfile(gen/"RMX_TBP07.kicad_sym",OUT/"symbols/RMX_TBP07.kicad_sym")
    symtable=read_sexpr((OUT/"sym-lib-table").read_text())
    symtable.append(read_sexpr('(lib (name "RMX_TBP07") (type "KiCad") (uri "${KIPRJMOD}/symbols/RMX_TBP07.kicad_sym") (options "") (descr "Module input branch"))'))
    (OUT/"sym-lib-table").write_text(sexpr(symtable)+"\n")
    root.append(read_sexpr(f'''(sheet (at 205 190) (size 140 17) (stroke (width 0) (type default)) (fill (color 0 0 0 0)) (uuid {sid})
      (property "Sheetname" "G_module_input" (at 205 188.73 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
      (property "Sheetfile" "{filename}" (at 205 208.27 0) (effects (font (size 1.27 1.27)) (justify left top)))
      (instances (project "{PROJECT}" (path "/{rootid}" (page "8")))))'''))
    first(first(root,"title_block"),"rev")[1]="TBP07"
    children(root,"text")[3][1]="Module branch eFuse and return star added; loaded transient/per-module fault/physical routing review still required."
    (OUT/(PROJECT+".kicad_sch")).write_text(sexpr(root)+"\n")
    tree,poly=outline(SOURCE/(PROJECT+".kicad_pcb"))
    lib=OUT/"libraries/TBP07_Module.pretty";lib.mkdir()
    for f in [rpw(),star()]:(lib/(f[1]+".kicad_mod")).write_text(sexpr(f)+"\n")
    table=read_sexpr((OUT/"fp-lib-table").read_text())
    table.append(read_sexpr('(lib (name "TBP07_Module") (type "KiCad") (uri "${KIPRJMOD}/libraries/TBP07_Module.pretty") (options "") (descr "TI RPW0010A and module return star"))'))
    (OUT/"fp-lib-table").write_text(sexpr(table)+"\n")
    newfps={}
    for c in design["components"]:
        ref="G_"+c["ref"];nick,name=c["footprint"].split(":")
        fp=strip_and_flip(read_sexpr((OUT/"libraries"/(nick+".pretty")/(name+".kicad_mod")).read_text()),False)
        fp[1]=c["footprint"];fp.append([a("at"),0,0,0]);fp.append([a("uuid"),a(uid(ref))])
        prop(fp,"Reference")[2]=ref;first(prop(fp,"Reference"),"layer")[1]="F.Fab"
        prop(fp,"Value")[2]=c["part"]
        newfps[c["ref"]]=fp
        expected[ref]=dict(source_role="G",source_ref=c["ref"],value=c["part"],footprint=c["footprint"],
            pins={p["number"]:(p["net"] if p["net"] and p["net"].startswith("PWR_") else
                "G_module_input/"+p["net"] if p["net"] else "unconnected-G_U1-PG") for p in c["pins"]})
    placement=place(tree,poly,newfps)
    tree.extend(newfps.values())
    (OUT/(PROJECT+".kicad_pcb")).write_text(sexpr(tree)+"\n")
    for name,value in [("expected-circuit.json",expected),("symbol-paths.json",paths),("module-placement.json",placement)]:
        (OUT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
    record=json.loads((SOURCE/"construction.json").read_text())
    record.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),DESIGN,BASE/"netlist.xml",*[p for p in SOURCE.rglob("*") if p.is_file()]]},
        revision="TBP07",electrical_parts=len(expected),source_pin_entries=sum(len(c["pins"]) for c in expected.values()),
        added_components=["G_"+c["ref"] for c in design["components"]],removed_nonphysical_flag="#N_FLAG1",
        module_power_implemented=True,module_force_return_star_implemented=True,return_star_physically_routed=False,
        remaining_unimplemented_interfaces=["Final signal/power interface"],module_branch_qualified=False,
        critical_power_placement_qualified=False,native_validation_pending=True,fabrication_released=False)
    (OUT/"construction.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps(dict(parts=len(expected),added=len(newfps),placement=placement)))


if __name__=="__main__":build()
