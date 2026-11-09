"""TBP03: explicit NF supply/sense/clamp interfaces and combined-fault insertion.

Remaining master/AUX-valid conditioning and module input remain unresolved.
Native connectivity is required; this is not receiving or dynamic qualification.
"""
import copy
import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha

SOURCE = STAGING / "two-board-power-integration-02"
BASELINE = STAGING / "two-board-power-native-02"
OUT = STAGING / "two-board-power-integration-03"
# The net column states the new common identity, never an inferred name match.
JOINS = [
    ("PWR_V2V5_AUX",("P_U102","1"),("N_J1","1"),"NF local AUX from existing source; finite distribution/pool review remains"),
    ("PWR_PROTECT_REF",("E_J6","3"),("N_J1","8"),"Shared protection reference; six added NF divider branches require loading review"),
    ("PWR_N19_OV_OK",("E_U9","1"),("N_J1","9"),"Existing negative OV comparator status"),
    ("PWR_N12_OV_OK",("E_U9","13"),("N_J1","10"),"Existing negative OV comparator status"),
    ("PWR_N19_OV_SENSE",("E_U9","6"),("N_J1","11"),"Existing filtered negative source sense; NF series input preserved"),
    ("PWR_N12_OV_SENSE",("E_U9","10"),("N_J1","12"),"Existing filtered negative source sense; NF series input preserved"),
    ("PWR_N19",("E_J3","3"),("N_J1","23"),"Actual protected output feeds NF absolute output monitor"),
    ("PWR_N12",("E_J3","5"),("N_J1","29"),"Actual protected output feeds NF absolute output monitor"),
    ("PWR_N19_BANK_GATE",("E_Q3","2"),("N_J3","1"),"Normally-closed clamp reaches actual bank gate via retained NF resistor"),
    ("PWR_N19_BANK_COMMON",("E_Q3","1"),("N_J3","2"),"Clamp returns to actual common-source node, never AGND"),
    ("PWR_N12_BANK_GATE",("E_Q7","2"),("N_J5","1"),"Normally-closed clamp reaches actual bank gate via retained NF resistor"),
    ("PWR_N12_BANK_COMMON",("E_Q7","1"),("N_J5","2"),"Clamp returns to actual common-source node, never AGND"),
    ("PWR_E28_NOT_FAULT",("E_U28","6"),("N_J1","15"),"Buffered inverted native E28 latch state into NF permission"),
    ("PWR_E28_NATIVE_FAULT_REQUEST",("E_U25","8"),("N_J1","13"),"Native request enters NF OR network before the E28 latch"),
    ("PWR_E28_COMBINED_FAULT_REQUEST",("N_J1","14"),("E_U21","8"),"NF OR result returns to isolated E28 latch SET input"),
]


def promote(label, name):
    label[1] = name
    if label[0] == "label":
        label[0] = a("global_label")
        label.insert(2,[a("shape"),a("passive")])


def pin_label(tree, ref, pin):
    """Locate a generated terminal's label by actual embedded physical pin geometry."""
    s = next(s for s in children(tree,"symbol") if prop(s,"Reference")[2] == ref)
    assert float(first(s,"at")[3]) == 0 and not children(s,"mirror")
    lib = next(s0 for s0 in children(first(tree,"lib_symbols"),"symbol") if s0[1] == first(s,"lib_id")[1])
    unit = str(first(s,"unit")[1])
    pins = [p for u in children(lib,"symbol") if str(u[1]).endswith(("_"+unit+"_1","_0_1")) for p in children(u,"pin") if str(first(p,"number")[1]) == pin]
    assert len(pins) == 1,(ref,pin)
    at,pat = first(s,"at"),first(pins[0],"at")
    anchor = (round(float(at[1])+float(pat[1]),4),round(float(at[2])-float(pat[2]),4))
    point = lambda n:tuple(round(float(v),4) for v in n[1:3])
    wires = [w for w in children(tree,"wire") if anchor in {point(p) for p in children(first(w,"pts"),"xy")}]
    assert len(wires) == 1,(ref,pin,len(wires))
    ends = {point(p) for p in children(first(wires[0],"pts"),"xy")}
    labels = [l for l in children(tree,"label")+children(tree,"global_label") if point(first(l,"at")) in ends]
    assert len(labels) == 1,(ref,pin,len(labels))
    return labels[0]


def build():
    assert not OUT.exists()
    base_parts,base_pins = read_netlist(BASELINE/"netlist.xml")
    source_expected = json.loads((SOURCE/"expected-circuit.json").read_text())
    expected = copy.deepcopy(source_expected)
    assert base_pins[("E_U25","8")] == base_pins[("E_U21","8")]
    assert base_parts["E_U21"].findtext("value") == "SN74LVC02APWR"
    assert base_parts["N_U46"].findtext("value") == "SN74HCS32PWR"
    assert base_parts["N_U34"].findtext("value") == "SN74AUP2G14DCKR"
    source_latch_net = expected["E_U21"]["pins"]["8"]
    assert [(r,p) for r,c in expected.items() for p,n in c["pins"].items() if n == source_latch_net] == [("E_U21","8"),("E_U25","8")]
    # This is the one intentional split. The native driver stays on the original
    # net; the latch input receives only the NF OR-result output.
    split_key = "TBP03::E28_LATCH_SET_RECEIVER"
    expected["E_U21"]["pins"]["8"] = split_key
    aliases,ledger = {},[]
    for name,left,right,basis in JOINS:
        keys = [expected[ref]["pins"][pin] for ref,pin in [left,right]]
        assert len(set(keys)) == 2,(name,keys)
        for key in keys:
            assert key not in aliases or aliases[key] == name,(name,key)
            aliases[key] = name
        ledger.append(dict(integrated_net=name,endpoints=[left,right],previous_partition_names=keys,basis=basis,
                           electrical_receiving_qualified=False))
    for part in expected.values():
        part["pins"] = {pin:aliases.get(net,net) for pin,net in part["pins"].items()}
    # Carry forward earlier namespaces and joins; mapping actual labels uses the
    # parent native export's names, independently of the expected source keys.
    native_map = {}
    for ref,component in source_expected.items():
        for pin,old in component["pins"].items():
            if (ref,pin) == ("E_U21","8"):
                continue
            if old in aliases:
                actual = base_pins[(ref,pin)]
                assert actual not in native_map or native_map[actual] == aliases[old]
                native_map[actual] = aliases[old]
    shutil.copytree(SOURCE,OUT)
    sheets = {}
    for file in OUT.glob("[PIEMNF]_*.kicad_sch"):
        role = file.name[0]
        tree = read_sexpr(file.read_text())
        sheets[role] = (file,tree)
    e = sheets["E"][1]
    label = pin_label(e,"E_U21","8")
    assert label[1] == "E28_FAULT_SET"
    promote(label,"PWR_E28_COMBINED_FAULT_REQUEST")
    # Other labels are scoped by the actual root sheet names in the parent export.
    parent_root = read_sexpr((SOURCE/"power_protection.kicad_sch").read_text())
    sheet_names = {str(prop(s,"Sheetfile")[2]):str(prop(s,"Sheetname")[2]) for s in children(parent_root,"sheet")}
    for role,(path,tree) in sheets.items():
        scope = sheet_names[path.name]
        for lab in children(tree,"label")+children(tree,"global_label"):
            key = str(lab[1]) if lab[0] == "global_label" else scope+"/"+str(lab[1])
            if key in native_map:
                promote(lab,native_map[key])
        if role == "N":
            flag = next(s for s in children(tree,"symbol") if prop(s,"Reference")[2] == "#N_FLAG3")
            at = first(flag,"at")[1:3]
            labs = [l for l in children(tree,"global_label") if first(l,"at")[1:3] == at]
            assert len(labs) == 1 and labs[0][1] == "PWR_V2V5_AUX"
            assert not [w for w in children(tree,"wire") if any(p[1:3] == at for p in children(first(w,"pts"),"xy"))]
            tree.remove(flag)
            tree.remove(labs[0])
        path.write_text(sexpr(tree)+"\n")
    assert expected["E_U25"]["pins"]["8"] != expected["E_U21"]["pins"]["8"]
    assert expected["N_U34"]["pins"]["4"] == expected["E_U21"]["pins"]["8"]
    assert expected["N_U46"]["pins"]["4"] == expected["E_U25"]["pins"]["8"]
    (OUT/"expected-circuit.json").write_text(json.dumps(expected,indent=2,sort_keys=True)+"\n")
    (OUT/"NF-interface-joins.json").write_text(json.dumps(ledger,indent=2)+"\n")
    paths = [Path(__file__),REPO/"hardware/fabrication/integrate_two_board_signal.py",BASELINE/"netlist.xml",BASELINE/"review.json",
             REPO/"hardware/qualification/boards/startup_negative_circuit/absolute_aux_gate/integration-contract.json",
             *[p for p in SOURCE.rglob("*") if p.is_file()]]
    record = json.loads((SOURCE/"construction.json").read_text())
    record["source_sha256"] = {str(p.relative_to(REPO)):sha(p) for p in paths}
    record["additional_NF_interface_pin_pairs"] = len(ledger)
    record["fault_latch_input_split"] = dict(ref="E_U21",pin="8",old_source_net=source_latch_net,
        new_net="PWR_E28_COMBINED_FAULT_REQUEST",native_driver="E_U25.8",combined_driver="N_U34.4")
    record["additional_superseded_power_flag"] = dict(ref="#N_FLAG3",retained_driver="P_U102.1")
    record["native_validation_pending"] = True
    record["remaining_unimplemented_interfaces"] = ["GLOBAL_MASTER qualified buffer","AUX_VALID qualified receiver",
        "Guarded module input/return","Fault-latched AUX-UV recovery and actual minimum GLOBAL-OFF interval"]
    record["electrical_receiving_and_dynamic_qualification"] = False
    (OUT/"construction.json").write_text(json.dumps(record,indent=2)+"\n")
    print("15 NF interface pairs composed; latch input split from its native driver; one superseded AUX flag removed")


if __name__ == "__main__":
    build()
