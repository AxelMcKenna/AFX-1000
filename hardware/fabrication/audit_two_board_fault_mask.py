"""Independent native-netlist proof of the TBP04 settled fault/reset function.

Physical gate pin maps are from the manufacturers, not the schematic's labels.
This deliberately does not model analog thresholds or propagation delays.
"""
import copy
import itertools
import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.integrate_two_board_signal import CAD, REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.native_two_board_power import partition

OUT = STAGING / "two-board-power-native-04"
BEFORE = STAGING / "two-board-power-native-03"

# ref, physical input pins, physical output pin, function
GATES = [
    ("E_U23", ("1", "2"), "3", "OR"),
    ("N_U46", ("1", "2"), "3", "OR"),
    ("N_U46", ("4", "5"), "6", "OR"),
    ("N_U34", ("1",), "6", "NOT"),
    ("N_U46", ("12", "13"), "11", "OR"),
    ("N_U34", ("3",), "4", "NOT"),
]
INPUTS = {
    "native_fault": ("E_U25", "8"),
    "negative19_fault": ("N_U46", "1"),
    "negative12_fault": ("N_U46", "2"),
    "not_run": ("E_U23", "1"),
    "not_aux": ("E_U23", "2"),
}


def evaluate(pins):
    rows = []
    for bits in itertools.product([False, True], repeat=len(INPUTS)):
        inputs = dict(zip(INPUTS, bits))
        state = {pins[("N_U46", "7")]: False, pins[("N_U46", "14")]: True}
        for name, node in INPUTS.items():
            assert pins[node] not in state, ("aliased stimulus", node)
            state[pins[node]] = inputs[name]
        pending = list(GATES)
        while pending:
            ready = [g for g in pending if all(pins[(g[0], p)] in state for p in g[1])]
            assert ready, "floating input or combinational cycle"
            for ref, ins, out, op in ready:
                output = pins[(ref, out)]
                assert output not in state, ("multiple driven outputs", output)
                values = [state[pins[(ref, p)]] for p in ins]
                state[output] = any(values) if op == "OR" else not values[0]
                pending.remove((ref, ins, out, op))
        reset = state[pins[("E_U21", "11")]]
        set_input = state[pins[("E_U21", "8")]]
        wanted_reset = inputs["not_run"] or inputs["not_aux"]
        fault = inputs["native_fault"] or inputs["negative19_fault"] or inputs["negative12_fault"]
        assert reset == wanted_reset
        assert set_input == (fault and not wanted_reset), (inputs, "wrong SET", set_input)
        assert not (reset and set_input)
        # Native NOR pin pairs, checked against actual latch feedback below.
        stable = [(q, qb) for q, qb in itertools.product([False, True], repeat=2)
                  if qb == (not (set_input or q)) and q == (not (reset or qb))]
        wanted = [(False, True)] if reset else [(True, False)] if fault else [(False, True), (True, False)]
        assert stable == wanted, (inputs, stable)
        rows.append(dict(inputs=inputs, reset=reset, set=set_input,
                         stable_fault_and_complement=stable))
    return rows


def rejected(pins):
    try:
        evaluate(pins)
    except (AssertionError, KeyError):
        return True
    return False


def run():
    parts, pins = read_netlist(OUT / "netlist.xml")
    oldparts, oldpins = read_netlist(BEFORE / "netlist.xml")
    for ref, value in {"E_U21": "SN74LVC02APWR", "E_U23": "SN74LVC32APWR",
                       "N_U46": "SN74HCS32PWR", "N_U34": "SN74AUP2G14DCKR"}.items():
        assert parts[ref].findtext("value") == value
    assert parts.keys() == oldparts.keys()
    assert all(parts[r].findtext(k) == oldparts[r].findtext(k)
               for r in parts for k in ["value", "footprint"])
    for left, right in [(('E_U21', '9'), ('E_U21', '13')),
                        (('E_U21', '10'), ('E_U21', '12')),
                        (('E_U21', '8'), ('N_U34', '4')),
                        (('E_U21', '11'), ('E_U23', '3')),
                        (('N_U46', '4'), ('E_U25', '8'))]:
        assert pins[left] == pins[right]
    assert pins[("E_U25", "8")] != pins[("E_U21", "8")]
    for ref, vcc, gnd in [("E_U21", "14", "7"), ("E_U23", "14", "7"),
                          ("N_U46", "14", "7"), ("N_U34", "5", "2")]:
        assert pins[(ref, vcc)] == pins[("P_U102", "1")]
        assert pins[(ref, gnd)] == pins[("P_U102", "4")]
    # Exact permitted partition changes, independent of expected-circuit.json.
    changed = dict(oldpins)
    changed[("N_U46", "12")] = oldpins[("N_U34", "6")]
    changed[("N_U46", "13")] = oldpins[("E_U23", "3")]
    changed[("N_U34", "3")] = oldpins[("N_U46", "11")]
    assert partition(changed) == partition(pins)
    rows = evaluate(pins)
    mutants = {}
    for name, node, source in [
        ("reset_mask_grounded", ("N_U46", "13"), ("N_U46", "7")),
        ("mask_bypassed", ("N_U34", "3"), ("N_U34", "6")),
        ("native_driver_shorted_to_SET", ("E_U25", "8"), ("E_U21", "8")),
        ("negative19_fault_omitted", ("N_U46", "1"), ("N_U46", "7")),
    ]:
        trial = dict(pins)
        trial[node] = pins[source]
        mutants[name] = rejected(trial)
    mutants["unmasked_native_TBP03_rejected"] = rejected(oldpins)
    assert all(mutants.values())

    # Keep the prior mechanical placement proof, but check all actual new nets.
    pcbpaths = [CAD / "power_protection.kicad_pcb", OUT / "power_protection.kicad_pcb"]
    trees = [read_sexpr(p.read_text()) for p in pcbpaths]
    fps = [{str(prop(f, "Reference")[2]): f for f in children(t, "footprint")} for t in trees]
    assert fps[0].keys() == fps[1].keys() and len(fps[1]) == 1092
    pads = 0
    for ref in fps[0]:
        assert geometry(fps[0][ref], ref not in parts) == geometry(fps[1][ref], ref not in parts), ref
        for pad in children(fps[1][ref], "pad"):
            if ref in parts and str(pad[1]):
                assert str(first(pad, "net")[2]).lstrip("/") == pins[(ref, str(pad[1]))]
                pads += 1
    roots = [[n for n in t if not (isinstance(n, list) and n and n[0] in ["footprint", "net"])] for t in trees]
    assert roots[0] == roots[1]
    assert not any(children(trees[1], t) for t in ["segment", "via", "zone"])
    erc = json.loads((OUT / "erc.json").read_text())
    warnings = [v for s in erc["sheets"] for v in s.get("violations", [])]
    assert len(warnings) == 2 and all(v["severity"] == "warning" and v["type"] == "ground_pin_not_ground" for v in warnings)
    for ref in ["N_U19", "N_U24"]:
        assert pins[(ref, "4")] != pins[(ref, "5")]
    review = json.loads((OUT / "review.json").read_text())
    for name, digest in review["source_sha256"].items():
        assert sha(REPO / name) == digest, name
    for name, digest in review["artifact_sha256"].items():
        assert sha(OUT / name) == digest, name
    paths = [Path(__file__), REPO / "hardware/fabrication/audit_two_board_power_delta.py",
             *pcbpaths, OUT / "netlist.xml", BEFORE / "netlist.xml", OUT / "review.json",
             OUT / "erc.json", OUT / "drc.json"]
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        native_pin_function="SET = (native OR negative19 OR negative12) AND NOT(not_run OR not_aux)",
        source_pin_maps={"SN74LVC02A": "https://www.ti.com/lit/ds/symlink/sn74lvc02a.pdf",
                         "SN74HCS32": "https://www.ti.com/lit/ds/symlink/sn74hcs32.pdf",
                         "SN74AUP2G14": "https://www.ti.com/lit/ds/symlink/sn74aup2g14.pdf"},
        truth_table=rows, settled_input_combinations_checked=len(rows),
        stable_latch_equilibria_checked_per_combination=4,
        reset_priority_in_settled_boolean_model=True, mutation_controls=mutants,
        only_declared_pin_partition_changes=True, unchanged_components=len(parts),
        unchanged_complete_footprint_geometries=len(fps[1]), checked_pad_instances=pads,
        unchanged_outline_mounts_and_setup=True, erc_errors=0, erc_warnings=2,
        limitations=["Ideal settled Boolean model assumes valid supply and valid logic levels.",
                     "This does not prove propagation-delay priority, minimum reset or GLOBAL-OFF pulse width.",
                     "UV recovery, receiving/loading and complete protection behavior remain unqualified."],
        fabrication_released=False)
    with (OUT / "fault-mask-audit.json").open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({k: result[k] for k in ["settled_input_combinations_checked", "mutation_controls",
        "unchanged_components", "unchanged_complete_footprint_geometries", "checked_pad_instances"]}))


if __name__ == "__main__":
    run()
