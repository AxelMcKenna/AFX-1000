"""TBP06: wire the two NF enable interfaces through E_U42's spare channels.

Replace the pin-compatible AUP buffer with LVC for the existing 47k loads.
Current-drive screening does not by itself qualify threshold/noise, partial
power, loaded timing, or the complete AUX pool.
"""
import copy
import json
import shutil
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.integrate_two_board_power_v3 import pin_label, promote
from hardware.fabrication.integrate_two_board_power_v4 import anchor

SOURCE = STAGING / "two-board-power-integration-05"
BASELINE = STAGING / "two-board-power-native-05"
OUT = STAGING / "two-board-power-integration-06"


def build():
    assert not OUT.exists()
    parts, pins = read_netlist(BASELINE / "netlist.xml")
    oldvalue, newvalue = "SN74AUP3G17DCUR", "SN74LVC3G17DCUR"
    assert parts["E_U42"].findtext("value") == oldvalue
    expected = json.loads((SOURCE / "expected-circuit.json").read_text())
    before = copy.deepcopy(expected)
    routes = [
        ("PWR_ALL_RAILS_ALLOW", ("E_U12", "11"), ("E_U42", "3")),
        ("PWR_NF_GLOBAL_MASTER", ("N_J1", "6"), ("E_U42", "5")),
        ("PWR_E28_AUX_VALID_NATIVE", ("E_U31", "3"), ("E_U42", "6")),
        ("PWR_NF_AUX_VALID", ("N_J1", "5"), ("E_U42", "2")),
    ]
    aliases = {expected[r]["pins"][p]: name for name, (r, p), target in routes}
    for part in expected.values():
        part["pins"] = {p: aliases.get(n, n) for p, n in part["pins"].items()}
    for name, source, (r, pin) in routes:
        expected[r]["pins"][pin] = name
    expected["E_U42"]["value"] = newvalue
    shutil.copytree(SOURCE, OUT)
    epath, npath = next(OUT.glob("E_*.kicad_sch")), next(OUT.glob("N_*.kicad_sch"))
    e, n = [read_sexpr(p.read_text()) for p in [epath, npath]]
    for sheet, names in [(e, {"ALL_RAILS_ALLOW": "PWR_ALL_RAILS_ALLOW", "E28_AUX_VALID": "PWR_E28_AUX_VALID_NATIVE"}),
                         (n, {"GLOBAL_MASTER": "PWR_NF_GLOBAL_MASTER", "AUX_VALID": "PWR_NF_AUX_VALID"})]:
        for label in children(sheet, "label"):
            if label[1] in names:
                promote(label, names[label[1]])
    for pin, net in [("3", "PWR_ALL_RAILS_ALLOW"), ("6", "PWR_E28_AUX_VALID_NATIVE")]:
        assert pins[("E_U42", pin)] == "PWR_AGND"
        promote(pin_label(e, "E_U42", pin), net)
    for pin, net in [("5", "PWR_NF_GLOBAL_MASTER"), ("2", "PWR_NF_AUX_VALID")]:
        assert pins[("E_U42", pin)].startswith("unconnected-")
        at = anchor(e, "E_U42", pin)
        markers = [m for m in children(e, "no_connect") if [float(x) for x in first(m, "at")[1:3]] == at]
        assert len(markers) == 1
        e.remove(markers[0])
        end = [at[0] + 5.08, at[1]]
        uid = lambda kind: str(uuid.uuid5(uuid.NAMESPACE_URL, f"AFX:TBP06:E_U42:{pin}:{kind}"))
        e.append(read_sexpr(f'(wire (pts (xy {at[0]} {at[1]}) (xy {end[0]} {end[1]})) (stroke (width 0) (type default)) (uuid {uid("wire")}))'))
        e.append(read_sexpr(f'(global_label "{net}" (shape passive) (at {end[0]} {end[1]} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid {uid("label")}))'))
    symbol = next(s for s in children(e, "symbol") if prop(s, "Reference")[2] == "E_U42")
    libid = first(symbol, "lib_id")[1]
    prop(symbol, "Value")[2] = newvalue
    embedded = next(s for s in children(first(e, "lib_symbols"), "symbol") if s[1] == libid)
    prop(embedded, "Value")[2] = newvalue
    library = OUT / "symbols" / (libid.split(":")[0] + ".kicad_sym")
    libtree = read_sexpr(library.read_text())
    libsym = next(s for s in children(libtree, "symbol") if s[1] == libid.split(":")[1])
    assert prop(libsym, "Value")[2] == oldvalue
    prop(libsym, "Value")[2] = newvalue
    library.write_text(sexpr(libtree) + "\n")
    for path, sheet in [(epath, e), (npath, n)]:
        path.write_text(sexpr(sheet) + "\n")
    pcbpath = OUT / "power_protection.kicad_pcb"
    pcb = read_sexpr(pcbpath.read_text())
    fp = next(f for f in children(pcb, "footprint") if prop(f, "Reference")[2] == "E_U42")
    assert prop(fp, "Value")[2] == oldvalue
    prop(fp, "Value")[2] = newvalue
    pcbpath.write_text(sexpr(pcb) + "\n")
    rootpath = OUT / "power_protection.kicad_sch"
    root = read_sexpr(rootpath.read_text())
    first(first(root, "title_block"), "rev")[1] = "TBP06"
    notes = children(root, "text")
    notes[0][1] = "30 base + 15 NF + 4 enable pin pairs; E_U42 LVC buffer drives MASTER/AUX_VALID. Electrical qualification remains."
    notes[3][1] = "Remaining: loaded thresholds/partial-power/timing, guarded module input, UV capture/minimum OFF and full AUX distribution."
    rootpath.write_text(sexpr(root) + "\n")
    (OUT / "expected-circuit.json").write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n")
    paths = [Path(__file__), REPO / "hardware/fabrication/integrate_two_board_power_v3.py",
             REPO / "hardware/fabrication/integrate_two_board_power_v4.py", BASELINE / "netlist.xml",
             BASELINE / "review.json", BASELINE / "source-sense-audit.json",
             REPO / "hardware/qualification/boards/aux_current_partition/sources/primary/SN74LVC3G17.pdf",
             REPO / "hardware/qualification/boards/startup_negative_circuit/uv_recovery/integration-contract.json",
             *[p for p in SOURCE.rglob("*") if p.is_file()]]
    record = json.loads((SOURCE / "construction.json").read_text())
    record["source_sha256"] = {str(p.relative_to(REPO)): sha(p) for p in paths}
    record["enable_routes"] = [dict(net=net, endpoints=[left, right]) for net, left, right in routes]
    record["declared_component_substitution"] = dict(ref="E_U42", before=oldvalue, after=newvalue,
        pin_and_land_compatible=True, original_ANA_PG2_channel_retained=True)
    record["pin_delta"] = [dict(ref=r, pin=p, before=net, after=expected[r]["pins"][p])
        for r, c in before.items() for p, net in c["pins"].items() if net != expected[r]["pins"][p]]
    record["current_NF_source_contract"] = "NF05R265; supersedes older NF05H261 current/recovery assumptions"
    record["NF_AUX_allocation_receiving_a"] = dict(normal=0.011, fault=0.014)
    record["remaining_unimplemented_interfaces"] = ["Guarded module input/return", "Final signal/power interface"]
    record["enable_full_electrical_qualification"] = False
    record["full_startup_and_fault_recovery_qualified"] = False
    (OUT / "construction.json").write_text(json.dumps(record, indent=2) + "\n")
    print("NF MASTER/AUX_VALID wired through two spare E_U42 channels; one pin-compatible LVC substitution")


if __name__ == "__main__":
    build()
