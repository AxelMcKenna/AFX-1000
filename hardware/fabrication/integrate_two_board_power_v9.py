"""TBP09: timer-operated, latched module-input protection with TPS26601.

Preserve the previous circuits; replace only the provisional G protection cell.
Fault duration and installed behavior require the explicit first-article tests.
"""
import copy
import itertools
import json
import shutil
from pathlib import Path

from shapely.affinity import translate
from shapely.geometry import box
from shapely.ops import unary_union

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.placement import strip_and_flip
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.assembly_layout import outline
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.integrate_two_board_power_v3 import promote
from hardware.fabrication.integrate_two_board_power_v7 import footprint,uid

SOURCE=STAGING/"two-board-power-integration-08"
BASE=STAGING/"two-board-power-native-08"
OUT=STAGING/"two-board-power-integration-09"
PRIMARY=STAGING/"two-board-module-cutoff-review-01/sources/tps2660.pdf"
VIN,VOUT,GND="PWR_MODULE_FEED_IN","PWR_MODULE_12V","PWR_MODULE_INPUT_GND"
RTN="MODULE_RTN"
TI="https://www.ti.com/lit/ds/symlink/tps2660.pdf"


def rhf():
    pads=[]
    def pad(n,x,y,w,h,layers):
        pads.append(f'(pad "{n}" smd roundrect (at {x} {y}) (size {w} {h}) (layers {layers}) (roundrect_rratio {round(.05/min(w,h),9)}))')
    for n in range(1,8):pad(n,-1.9,(n-4)*.5,.6,.24,'"F.Cu" "F.Mask" "F.Paste"')
    for n in range(8,13):pad(n,(n-10)*.5,2.4,.24,.6,'"F.Cu" "F.Mask" "F.Paste"')
    for n in range(13,20):pad(n,1.9,(16-n)*.5,.6,.24,'"F.Cu" "F.Mask" "F.Paste"')
    for n in range(20,25):pad(n,(22-n)*.5,-2.4,.24,.6,'"F.Cu" "F.Mask" "F.Paste"')
    pad(25,0,0,2.65,3.65,'"F.Cu" "F.Mask"')
    for x,y in itertools.product([-.685,.685],[-1.24,0,1.24]):pad("",x,y,1.17,1.04,'"F.Paste"')
    body='''(fp_rect (start -2 -2.5) (end 2 2.5) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))
      (fp_rect (start -2.45 -2.95) (end 2.45 2.95) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
      (fp_line (start -2 -2) (end -1.5 -2.5) (stroke (width .1) (type default)) (layer "F.Fab"))'''
    return footprint("TI_RHF0024A",body," ".join(pads),'(solder_mask_margin .05)')


def components():
    data=json.loads((SOURCE/"module-cell-grid/components.json").read_text())
    for c in data:
        ref=c["ref"]
        if ref=="U1":
            c.update(part="TPS26601RHFR",footprint="TBP09_Module:TI_RHF0024A",source=TI,
                note="MODE open selects timer-operated latch-off. RTN and EP are separate from GND. SHDN internal bias; reset by removing DC input.")
            pinmap={8:("IN",VIN,"power_in"),9:("IN",VIN,"power_in"),10:("UVLO","MODULE_UV","input"),
                12:("OVP","MODULE_OV","input"),13:("MODE",None,"input"),14:("SHDN",None,"input"),
                15:("RTN",RTN,"passive"),17:("GND",GND,"power_in"),18:("IMON",None,"output"),
                19:("ILIM","MODULE_ILM","passive"),20:("DVDT","MODULE_DVDT","passive"),
                22:("FLT",None,"open_collector"),23:("OUT",VOUT,"power_out"),24:("OUT",VOUT,"power_out"),25:("EP",RTN,"passive")}
            c["pins"]=[]
            for n in range(1,26):
                name,net,kind=pinmap.get(n,("NC",None,"no_connect"))
                c["pins"].append(dict(number=str(n),name=name,net=net,kind=kind,side="L" if n<=12 else "R"))
        elif ref in ["R2","R4","R5"]:
            c["pins"][1]["net"]=RTN
            if ref=="R5":c["part"]="22.1k 0.1% 25ppm"
        elif ref in ["C3","C4"]:
            c.update(part="100nF25V C0G C1206C104J3GACTU",footprint="TB05_N_NF06P:PROPOSED_KEMET1206_LevelB",
                note="5% initial, complete 6% receiving; two parallel capacitors total 200nF. Both return to RTN, never force GND.")
            c["pins"][0]["net"]="MODULE_DVDT";c["pins"][1]["net"]=RTN
        elif ref=="NT1":
            c["pins"][0]["name"]="AGND";c["pins"][1]["name"]="MODULE_GND"
    return data


def calculations():
    def divider(bottom,limits):
        v=[t*(1+rt/rb)+i*rt for t,rt,rb,i in itertools.product(limits,[470000*.995,470000*1.005],
            [bottom*.995,bottom*1.005],[-1e-7,1e-7])]
        return [min(v),max(v)]
    uv_on=divider(59000,[1.175,1.225]);uv_off=divider(59000,[1.08,1.125])
    ov_off=divider(43200,[1.17,1.225]);ov_on=divider(43200,[1.085,1.125])
    cap=[200e-9*.94,200e-9*1.06]
    sr=[23.75*4e-6/cap[1],25.5*5.5e-6/cap[0]]
    iol=12/22.1;icb=iol-.03
    # Engineering envelope, not a manufacturer test row at 22.1k:
    # 15% IOL error plus 25mA additional CB offset covers endpoint table
    # discrepancies as a screening assumption. Characterization remains required.
    model_iol=[.85*12/(22.1*1.005),1.15*12/(22.1*.995)]
    model_icb=[model_iol[0]-.055,model_iol[1]-.005]
    cap_current=60e-6*sr[1];combined=.35+cap_current
    assert combined<model_icb[0]
    assert uv_on[1]<11.4 and ov_on[0]>12.6 and ov_off[1]<18
    assert uv_off[0]-.10-.35*.25-.01>9
    return dict(
        input_divider_limits_v=dict(UV_on=uv_on,UV_off=uv_off,OV_off=ov_off,OV_reenable=ov_on),
        nominal_current_limit_a=iol,nominal_circuit_breaker_a=icb,
        modeled_current_limit_a=model_iol,modeled_circuit_breaker_a=model_icb,
        current_envelope_is_engineering_assumption=True,
        total_dvdt_capacitance_f=cap,output_slew_v_per_s=sr,
        ideal_12V_ramp_duration_s=[12/sr[1],12/sr[0]],
        nominal_enable_delay_s=.00025+14.5*200e-6,
        receiving_load_current_a=.35,receiving_output_capacitance_f=60e-6,
        projected_capacitive_inrush_a=cap_current,projected_combined_current_a=combined,
        lower_modeled_CB_margin_a=model_icb[0]-combined,
        normal_max_Ron_ohm=.25,normal_loss_at_receiving_load_w=.35**2*.25,
        normal_switch_drop_at_receiving_load_v=.35*.25,
        input_to_module_board_drop_allowance_v=.1,RTN_reference_offset_allowance_v=.01,
        nominal_fault_timer_s=.004,guaranteed_maximum_fault_timer_s=None,
        reset_policy="Remove external DC input and verify branch VIN below POR falling threshold; RUN cycling alone is not yet qualified.",
        maximum_pulse_at_14_8V_10ms_and_modeled_ILIM_j=.0148*model_iol[1]*10,
        receiving_load_capacitance_passive_and_reference_limits_verified=False,
        prototype_fault_test_abort_s=.010,
        prototype_abort_is_acceptance_requirement_not_datasheet_guarantee=True)


def place(tree,polygon,fps):
    offsets=dict(U1=(0,0),C1=(-4.8,0),C2=(5.3,0),D1=(-5,-5.5),D2=(5,-5.5),
        R1=(-4.5,4.5),R3=(-.7,4.5),R5=(3.1,4.5),C3=(8,4.5),R2=(-4.5,7.5),R4=(-.7,7.5),C4=(4.6,8))
    shapes=[]
    for ref,offset in offsets.items():
        first(fps[ref],"at")[1:]=[0,0,0]
        s=translate(box(*courtyard(fps[ref],"F.CrtYd")).buffer(.15),*offset)
        assert all(not s.intersects(other) for other in shapes),ref
        shapes.append(s)
    cell=unary_union(shapes);obstacles=[]
    for f in children(tree,"footprint"):
        ref=prop(f,"Reference")[2]
        if ref.startswith("G_") and ref!="G_NT1":continue
        side=str(first(f,"layer")[1])[0]
        if side=="F" or any(p[2] in ["thru_hole","np_thru_hole"] for p in children(f,"pad")):
            obstacles.append(box(*courtyard(f,side+".CrtYd")).buffer(.3))
    occupied=unary_union(obstacles);interior=polygon.buffer(-.5)
    candidates=[(x*.5,y*.5) for x in range(28,640) for y in range(24,350)]
    candidates.sort(key=lambda xy:(xy[0]-193.5)**2+(xy[1]-114)**2)
    for x,y in candidates:
        shape=translate(cell,x,y)
        if interior.contains(shape) and not occupied.intersects(shape):break
    else:raise AssertionError("No cell placement; revise surrounding layout")
    for ref,(dx,dy) in offsets.items():first(fps[ref],"at")[1:]=[x+dx,y+dy,0]
    return dict(cell_origin_mm=[x,y],star_xy_mm=first(fps["NT1"],"at")[1:3],
        critical_electrical_placement_qualified=False,thermal_RTN_vias_and_plane_implemented=False)


def build():
    assert not OUT.exists()
    shutil.copytree(SOURCE,OUT)
    data=components();gen=OUT/"module-cell-timed"
    generate(gen,"TBP09","module_input",data,[
        (25.4,248.92,"MODE open: timed latch-off including post-short restart. DC removal resets; RUN cycling unqualified."),
        (25.4,259.08,"RTN / EP and support returns remain distinct from force GND. Thermal vias must connect only to RTN."),
        (25.4,269.24,"C3+C4 = 200nF. Complete R budget 0.5%, C budget 6%. Current and fault timing need first-article verification.")],(330,290),[])
    root=read_sexpr((OUT/"power_protection.kicad_sch").read_text());rootid=first(root,"uuid")[1]
    sheet=next(s for s in children(root,"sheet") if prop(s,"Sheetfile")[2]=="G_module_input.kicad_sch")
    sid=first(sheet,"uuid")[1]
    s=read_sexpr((gen/"module_input.kicad_sch").read_text())
    paths=json.loads((SOURCE/"symbol-paths.json").read_text())
    for sym in children(s,"symbol"):
        ref="G_"+prop(sym,"Reference")[2];prop(sym,"Reference")[2]=ref
        first(sym,"instances")[:]=read_sexpr(f'(instances (project "power_protection" (path "/{rootid}/{sid}" (reference "{ref}") (unit 1))))')
        paths[ref]=f'/{rootid}/{sid}/{first(sym,"uuid")[1]}'
    for lab in children(s,"label"):
        if str(lab[1]).startswith("PWR_"):promote(lab,lab[1])
    (OUT/"G_module_input.kicad_sch").write_text(sexpr(s)+"\n")
    shutil.copyfile(gen/"RMX_TBP09.kicad_sym",OUT/"symbols/RMX_TBP09.kicad_sym")
    table=read_sexpr((OUT/"sym-lib-table").read_text())
    table.append(read_sexpr('(lib (name "RMX_TBP09") (type "KiCad") (uri "${KIPRJMOD}/symbols/RMX_TBP09.kicad_sym") (options "") (descr "Timed module protection"))'))
    (OUT/"sym-lib-table").write_text(sexpr(table)+"\n")
    lib=OUT/"libraries/TBP09_Module.pretty";lib.mkdir()
    (lib/"TI_RHF0024A.kicad_mod").write_text(sexpr(rhf())+"\n")
    table=read_sexpr((OUT/"fp-lib-table").read_text())
    table.append(read_sexpr('(lib (name "TBP09_Module") (type "KiCad") (uri "${KIPRJMOD}/libraries/TBP09_Module.pretty") (options "") (descr "TI RHF0024A 4219064/A"))'))
    (OUT/"fp-lib-table").write_text(sexpr(table)+"\n")
    expected=json.loads((SOURCE/"expected-circuit.json").read_text())
    tree,polygon=outline(SOURCE/"power_protection.kicad_pcb")
    oldfps={prop(f,"Reference")[2]:f for f in children(tree,"footprint")}
    fps={}
    for c in data:
        ref="G_"+c["ref"]
        if c["ref"] in ["U1","C3","C4"]:
            nick,name=c["footprint"].split(":")
            f=strip_and_flip(read_sexpr((OUT/"libraries"/(nick+".pretty")/(name+".kicad_mod")).read_text()),False)
            f[1]=c["footprint"];f.append([a("at"),0,0,0]);f.append([a("uuid"),a(uid("TBP09:"+ref))])
        else:f=copy.deepcopy(oldfps[ref])
        prop(f,"Reference")[2]=ref;first(prop(f,"Reference"),"layer")[1]="F.Fab"
        prop(f,"Value")[2]=c["part"]
        effects=first(prop(f,"Value"),"effects")
        if not children(effects,"hide"):effects.append([a("hide"),a("yes")])
        ds=next(iter([v for v in children(f,"property") if v[1]=="Datasheet"]),None)
        if ds is None:f.append(read_sexpr(f'(property "Datasheet" {json.dumps(c["source"])} (at 0 0 0) (layer "F.Fab") (effects (font (size 1 1)) (hide yes)))'))
        else:ds[2]=c["source"]
        fps[c["ref"]]=f
        expected[ref]=dict(source_role="G",source_ref=c["ref"],value=c["part"],footprint=c["footprint"],
            pins={p["number"]:(p["net"] if p["net"] and p["net"].startswith("PWR_") else "G_module_input/"+p["net"] if p["net"] else "NC_"+ref+"_"+p["number"]) for p in c["pins"]})
    placement=place(tree,polygon,fps)
    for old in list(children(tree,"footprint")):
        if prop(old,"Reference")[2].startswith("G_"):tree.remove(old)
    tree.extend(fps.values())
    (OUT/"power_protection.kicad_pcb").write_text(sexpr(tree)+"\n")
    first(first(root,"title_block"),"rev")[1]="TBP09"
    children(root,"text")[3][1]="TPS26601 module branch: timed latch-off, separate RTN, 200nF ramp; first-article/current/return/routing checks remain."
    (OUT/"power_protection.kicad_sch").write_text(sexpr(root)+"\n")
    for name,value in [("expected-circuit.json",expected),("symbol-paths.json",paths),("module-placement.json",placement),
        ("module-cutoff-design.json",calculations())]:
        (OUT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
    record=json.loads((SOURCE/"construction.json").read_text())
    record.update(revision="TBP09",source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),PRIMARY,
        BASE/"netlist.xml",BASE/"module-feed-audit.json",REPO/"hardware/fabrication/integrate_two_board_power_v7.py",
        REPO/"hardware/electronics/common/flat_schematic.py",*[p for p in SOURCE.rglob("*") if p.is_file()]]},
        electrical_parts=len(expected),source_pin_entries=sum(len(c["pins"]) for c in expected.values()),
        module_protector="TPS26601RHFR",fault_mode="MODE open: timer-operated latch-off",
        R5_ohm=22100,C3_C4_each_f=100e-9,RTN_distinct_from_primary_ground=True,
        nominal_cutoff_timer_s=.004,maximum_cutoff_time_guaranteed=False,
        first_article_validation_pending=True,module_branch_qualified=False,native_validation_pending=True)
    (OUT/"construction.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps(dict(parts=len(expected),pins=record["source_pin_entries"],placement=placement,calculations=calculations()),indent=2))


if __name__=="__main__":build()
