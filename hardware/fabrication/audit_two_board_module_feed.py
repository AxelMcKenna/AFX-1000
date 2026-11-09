"""Independent native TBP08 module branch, delta and receiving audit."""
import copy
import itertools
import json
import math
from pathlib import Path

from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,read_netlist,sha
from hardware.fabrication.native_two_board_power import partition
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.audit_two_board_enable_recovery import check_uv
from hardware.fabrication.audit_two_board_fault_mask import evaluate
from hardware.fabrication.audit_two_board_source_sense import verify_sense

BEFORE=STAGING/"two-board-power-native-06"
OUT=STAGING/"two-board-power-native-08"


def branch(parts,p):
    assert parts["G_U1"].findtext("value")=="TPS259474LRPWR"
    def same(*nodes):
        nets={p[(r,str(n))] for r,n in nodes}
        assert len(nets)==1,(nodes,nets)
    same(("G_U1",5),("P_U101",17),("P_U101",18),("P_C103",1),("G_C1",1),("G_D1",1),("G_R1",1),("G_R3",1))
    same(("G_U1",6),("N_U17",2),("N_U22",2),("N_C4",1),("N_C31",1),("N_J6",1),("G_C2",1),("G_D2",1))
    same(("G_U1",8),("G_U1",4),("G_NT1",2),("N_U17",1),("N_U22",1),("N_C4",2),("N_C31",2),("N_J6",2),
         ("G_C1",2),("G_C2",2),("G_C3",2),("G_C4",2),("G_R2",2),("G_R4",2),("G_R5",2),("G_D1",2),("G_D2",2))
    same(("G_NT1",1),("P_C103",2),("P_U101",8))
    same(("G_U1",1),("G_R1",2),("G_R2",1))
    same(("G_U1",2),("G_R3",2),("G_R4",1))
    same(("G_U1",7),("G_C3",1))
    same(("G_U1",9),("G_R5",1))
    same(("G_U1",10),("G_C4",1))
    distinct=[p[("G_U1",str(n))] for n in [1,2,3,5,6,7,8,9,10]]+[p[("G_NT1","1")]]
    assert len(set(distinct))==len(distinct)
    assert p[("G_U1","3")].startswith("unconnected-")
    assert p[("G_U1","5")] not in [p[("P_U101","1")],p[("N_J1","6")],p[("E_U29","7")]]
    # No new component other than the declared star reaches quiet/system AGND.
    touched=[n for n,net in p.items() if n[0].startswith("G_") and net==p[("P_C103","2")]]
    assert touched==[("G_NT1","1")],touched
    for r in ["N_U17","N_U22"]:assert parts[r].findtext("value")=="TMR 1-1215"


def rpw_check(f):
    wanted=[]
    for x,nums in [(-.9,[1,2,3,4]),(.9,[10,9,8,7])]:
        for pin,y in zip(nums,[-.7,-.225,.225,.7]):
            corner=pin in [1,4,7,10]
            wanted.append((str(pin),x,y,.6,.3 if corner else .25))
            if corner:wanted.append((str(pin),math.copysign(.725,x),math.copysign(.875,y),.25,.65))
    wanted.extend([("5",-.25,0,.3,2.4),("6",.25,0,.3,2.4)])
    actual=[]
    for pad in children(f,"pad"):
        if not pad[1]:continue
        assert first(pad,"layers")[1:]==["F.Cu","F.Mask"]
        x,y=map(float,first(pad,"at")[1:3]);w,h=map(float,first(pad,"size")[1:3])
        assert abs(float(first(pad,"roundrect_rratio")[1])*min(w,h)-.05)<1e-8
        actual.append((str(pad[1]),x,y,w,h))
    assert sorted(actual)==sorted(wanted)
    paste=[p for p in children(f,"pad") if not p[1]]
    assert len(paste)==16 and all(first(p,"layers")[1:]==["F.Paste"] for p in paste)
    expected_paste=[]
    for sign in [-1,1]:
        for y in [-.7,-.225,.225,.7]:
            corner=abs(y)>.5
            expected_paste.append((sign*.9,y,.6,.275 if corner else .25))
            if corner:expected_paste.append((sign*.7125,math.copysign(.875,y),.225,.65))
        for y in [-.63,.63]:expected_paste.append((sign*.25,y,.28,1.06))
    actual_paste=[tuple(map(float,first(p,"at")[1:3]+first(p,"size")[1:3])) for p in paste]
    assert sorted(expected_paste)==sorted(actual_paste)
    assert float(first(f,"solder_mask_margin")[1])==.05
    return dict(numbered_copper_shapes=14,physical_pins=10,paste_shapes=16,
        copper_and_paste_dimension_match=True, drawing="TI RPW0010A 4225183/A 08/2019",
        mask_paste_and_board_process_accepted=False)


def run():
    parts,p=read_netlist(OUT/"netlist.xml");oldparts,oldp=read_netlist(BEFORE/"netlist.xml")
    added={"G_"+r for r in ["U1","NT1","D1","D2","R1","R2","R3","R4","R5","C1","C2","C3","C4"]}
    assert set(parts)==set(oldparts)|added
    for ref in oldparts:
        for field in ["value","footprint"]:assert parts[ref].findtext(field)==oldparts[ref].findtext(field),(ref,field)
    assert partition({n:v for n,v in p.items() if n[0] in oldparts})==partition(oldp)
    branch(parts,p)
    mutations={}
    for name,node,wrong in [
        ("unprotected_source",("G_U1","5"),("P_U101","1")),
        ("guard_bypass",("N_U17","2"),("G_U1","5")),
        ("primary_return_to_quiet_ground",("N_U17","1"),("N_J1","2")),
        ("star_wrong_side",("G_NT1","1"),("G_NT1","2")),
        ("UV_divider_wrong_return",("G_R2","2"),("G_U1","6")),
        ("clamp_reversed",("G_D2","1"),("G_U1","8")),
        ("module_feed_from_master",("G_U1","5"),("N_J1","6"))]:
        trial=dict(p);trial[node]=p[wrong]
        try:branch(parts,trial)
        except AssertionError:mutations[name]=True
        else:raise AssertionError(name)
    old,new=[read_sexpr((folder/"power_protection.kicad_pcb").read_text()) for folder in [BEFORE,OUT]]
    fps0,fps=[{prop(f,"Reference")[2]:f for f in children(t,"footprint")} for t in [old,new]]
    assert set(fps)==set(fps0)|added
    for r in fps0:assert geometry(fps0[r],r not in oldparts)==geometry(fps[r],r not in oldparts),r
    for tag in ["segment","via","zone"]:assert not children(new,tag)
    checked=0
    for ref,f in fps.items():
        for pad in children(f,"pad"):
            if not pad[1] or ref not in parts:continue
            assert str(first(pad,"net")[2]).lstrip("/")==p[(ref,str(pad[1]))]
            checked+=1
    land=rpw_check(fps["G_U1"])
    assert first(fps["G_NT1"],"net_tie_pad_groups")[1:]==["1,2"]
    # Independent KCL sweep on native component values, not the generator's
    # precomputed answers. Leakage and total budgets are explicit requirements.
    def ohms(ref):
        s=parts[ref].findtext("value").split()[0]
        return float(s.rstrip("k"))*(1000 if s.endswith("k") else 1)
    corners={}
    for key,rt,rb,vrange in [("UV_on","G_R1","G_R2",[1.183,1.223]),("UV_off","G_R1","G_R2",[1.076,1.116]),
                            ("OV_off","G_R3","G_R4",[1.183,1.223]),("OV_on","G_R3","G_R4",[1.076,1.116])]:
        results=[]
        for vt,ts,bs,leak in itertools.product(vrange,[.995,1.005],[.995,1.005],[-1e-7,1e-7]):
            top,bottom=ohms(rt)*ts,ohms(rb)*bs
            vs=vt+top*(vt/bottom+leak)
            assert abs((vs-vt)/top-vt/bottom-leak)<1e-15
            results.append(vs)
        corners[key]=[min(results),max(results)]
    assert corners["UV_on"][1]<11.4 and corners["UV_off"][0]-.1>9
    assert corners["OV_off"][1]<18 and corners["OV_on"][0]>12.6
    assert len(evaluate(p))==32 and len(verify_sense(parts,p))==2
    uv,trace,deep=check_uv(p);assert len(uv)==64
    review=json.loads((OUT/"review.json").read_text())
    assert review["geometry_findings"]==review["schematic_parity_findings"]==0
    erc=json.loads((OUT/"erc.json").read_text())
    findings=[v for s in erc["sheets"] for v in s.get("violations",[])]
    assert len(findings)==2 and all(v["type"]=="ground_pin_not_ground" and v["severity"]=="warning" for v in findings)
    # Important fault corner: thermal trip is not an output-UV guarantee.
    # This is a typical thermal model, not a validated device trajectory.
    current=3334/ohms("G_R5");power=(12-8.7)*current
    fault=dict(input_v=12,output_v=8.7,current_a=current,dissipation_w=power,
        ambient_c=25,example_RthetaJA_c_per_w=41.7,estimated_junction_c=25+power*41.7,
        typical_thermal_trip_c=154,not_a_guaranteed_transient=True,
        conclusion="An input UV comparator cannot detect a sagging output during post-fast-trip current limit. Thermal shutdown is not guaranteed to clear every undervoltage load state. Add output-UV timeout/latch or choose a protector with bounded short fault cutoff.")
    assert fault["estimated_junction_c"]<fault["typical_thermal_trip_c"]
    paths=[Path(__file__),BEFORE/"netlist.xml",BEFORE/"power_protection.kicad_pcb",OUT/"netlist.xml",OUT/"power_protection.kicad_pcb",
        OUT/"review.json",OUT/"erc.json",OUT/"drc.json",STAGING/"two-board-module-feed-01/design.json",
        REPO/"hardware/fabrication/audit_two_board_enable_recovery.py",REPO/"hardware/fabrication/audit_two_board_fault_mask.py",REPO/"hardware/fabrication/audit_two_board_source_sense.py"]
    report=dict(source_sha256={str(f.relative_to(REPO)):sha(f) for f in paths},electrical_parts=len(parts),added_components=sorted(added),
        old_component_values_and_pin_partition_preserved=len(oldparts),unchanged_existing_footprints=len(fps0),
        mapped_pad_instances=checked,new_RPW_land=land,independent_divider_corners_v=corners,mutation_controls_rejected=mutations,
        prior_fault_cases=32,prior_source_sense_channels=2,prior_UV_cases=len(uv),
        module_force_return_only_via_declared_net_tie=True,return_star_routed=False,
        output_undervoltage_fault_counterexample=fault,module_branch_fault_qualified=False,
        complete_power_circuit=False,fabrication_released=False)
    target=OUT/"module-feed-audit.json";assert not target.exists();target.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="source_sha256"},indent=2))


if __name__=="__main__":run()
