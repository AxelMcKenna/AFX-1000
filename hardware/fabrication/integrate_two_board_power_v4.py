"""TBP04: mask the combined fault while E28 RESET is asserted.

Reuses NF's unused fourth OR gate between its two existing inverter stages:
SET = NOT(NOT(COMBINED_FAULT) OR RESET). Settled Boolean behavior is checked
separately; transient priority, minimum reset width and UV recovery remain open.
"""
import copy
import json
import shutil
import uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.integrate_two_board_power_v3 import pin_label, promote

SOURCE = STAGING / "two-board-power-integration-03"
BASELINE = STAGING / "two-board-power-native-03"
OUT = STAGING / "two-board-power-integration-04"


def anchor(tree,ref,pin):
    symbol = next(s for s in children(tree,"symbol") if prop(s,"Reference")[2] == ref)
    lib = next(s for s in children(first(tree,"lib_symbols"),"symbol") if s[1] == first(symbol,"lib_id")[1])
    units = [u for u in children(lib,"symbol") if str(u[1]).endswith(("_"+str(first(symbol,"unit")[1])+"_1","_0_1"))]
    pins = [p for u in units for p in children(u,"pin") if str(first(p,"number")[1]) == pin]
    assert len(pins) == 1
    at,pat = first(symbol,"at"),first(pins[0],"at")
    assert float(at[3]) == 0 and not children(symbol,"mirror")
    return [round(float(at[1])+float(pat[1]),4),round(float(at[2])-float(pat[2]),4)]


def build():
    assert not OUT.exists()
    parts,pins = read_netlist(BASELINE/"netlist.xml")
    assert parts["N_U46"].findtext("value") == "SN74HCS32PWR"
    assert parts["N_U34"].findtext("value") == "SN74AUP2G14DCKR"
    assert pins[("N_U46","12")] == pins[("N_U46","13")] == "PWR_AGND"
    assert pins[("N_U46","11")].startswith("unconnected-")
    assert pins[("N_U34","6")] == pins[("N_U34","3")]
    expected = json.loads((SOURCE/"expected-circuit.json").read_text())
    before = copy.deepcopy(expected)
    inv,masked,reset = "TBP04::INVERTED_COMBINED_FAULT","TBP04::MASKED_INVERTED_FAULT","PWR_E28_RESET"
    oldreset = expected["E_U23"]["pins"]["3"]
    for part in expected.values():
        part["pins"] = {p:reset if n == oldreset else n for p,n in part["pins"].items()}
    for ref,pin,net in [("N_U34","6",inv),("N_U46","12",inv),("N_U34","3",masked),("N_U46","11",masked),("N_U46","13",reset)]:
        expected[ref]["pins"][pin] = net
    shutil.copytree(SOURCE,OUT)
    npath = next(OUT.glob("N_*.kicad_sch"))
    n = read_sexpr(npath.read_text())
    for ref,pin,net in [("N_U34","6","PWR_NF_INVERTED_COMBINED_FAULT"),("N_U46","12","PWR_NF_INVERTED_COMBINED_FAULT"),
                        ("N_U34","3","PWR_NF_MASKED_INVERTED_FAULT"),("N_U46","13",reset)]:
        promote(pin_label(n,ref,pin),net)
    at = anchor(n,"N_U46","11")
    nc = [v for v in children(n,"no_connect") if [float(x) for x in first(v,"at")[1:3]] == at]
    assert len(nc) == 1
    n.remove(nc[0])
    end = [round(at[0]+5.08,4),at[1]]
    uid = lambda name:str(uuid.uuid5(uuid.NAMESPACE_URL,"AFX:TBP04:"+name))
    n.append(read_sexpr(f'(wire (pts (xy {at[0]} {at[1]}) (xy {end[0]} {end[1]})) (stroke (width 0) (type default)) (uuid {uid("mask-wire")}))'))
    n.append(read_sexpr(f'(global_label "PWR_NF_MASKED_INVERTED_FAULT" (shape passive) (at {end[0]} {end[1]} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid {uid("mask-label")}))'))
    npath.write_text(sexpr(n)+"\n")
    epath = next(OUT.glob("E_*.kicad_sch"))
    e = read_sexpr(epath.read_text())
    resetlabels = [l for l in children(e,"label") if l[1] == "E28_RESET"]
    assert len(resetlabels) >= 3
    for lab in resetlabels:
        promote(lab,reset)
    epath.write_text(sexpr(e)+"\n")
    rootpath = OUT/"power_protection.kicad_sch"
    root = read_sexpr(rootpath.read_text())
    first(first(root,"title_block"),"rev")[1] = "TBP04"
    notes = children(root,"text")
    notes[0][1] = "30 base pin pairs plus 15 NF interfaces; existing components retained. Combined-fault SET is reset-masked."
    notes[3][1] = "Remaining: qualified GLOBAL_MASTER/AUX_VALID, guarded module input, UV recovery and minimum reset/OFF timing."
    rootpath.write_text(sexpr(root)+"\n")
    (OUT/"expected-circuit.json").write_text(json.dumps(expected,indent=2,sort_keys=True)+"\n")
    delta = [dict(ref=r,pin=p,before=n,after=expected[r]["pins"][p]) for r,c in before.items() for p,n in c["pins"].items() if n != expected[r]["pins"][p]]
    paths = [Path(__file__),REPO/"hardware/fabrication/integrate_two_board_power_v3.py",BASELINE/"netlist.xml",BASELINE/"review.json",*[p for p in SOURCE.rglob("*") if p.is_file()]]
    record = json.loads((SOURCE/"construction.json").read_text())
    record["source_sha256"] = {str(p.relative_to(REPO)):sha(p) for p in paths}
    record["reset_mask_pin_delta"] = delta
    record["reset_mask_logic"] = "N_U34 first inverter -> N_U46 spare OR with E28_RESET -> N_U34 second inverter -> E_U21.8 SET"
    record["static_reset_priority_requires_independent_native_netlist_check"] = True
    record["transient_reset_priority_and_UV_recovery_qualified"] = False
    (OUT/"construction.json").write_text(json.dumps(record,indent=2)+"\n")
    print("Reset mask inserted using existing N_U46 fourth OR and N_U34 two inverter stages; no parts added")


if __name__ == "__main__":
    build()
