"""Native TBP06 enable wiring, current screen and settled UV fault capture.

The model operates on actual native physical pins; it excludes analog delay,
partial power and subthreshold corruption. A static trace is not a pulse test.
"""
import copy
import itertools
import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_two_board_fault_mask import evaluate as fault_mask
from hardware.fabrication.audit_two_board_source_sense import verify_sense
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.native_two_board_power import partition

OUT = STAGING / "two-board-power-native-06"
BEFORE = STAGING / "two-board-power-native-05"

# Physical input/output numbers from TI gate pin maps.
GATES = [
    ("E_U23", [1, 2], 3, "OR"),
    ("N_U58", [2], 4, "NOT"), ("N_U48", [13], 12, "NOT"),
    ("N_U51", [12, 13], 11, "AND"), ("N_U47", [1], 2, "NOT"),
    ("N_U35", [9, 10], 8, "AND"), ("N_U45", [1, 2], 3, "OR"),
    ("N_U45", [4, 5], 6, "OR"), ("N_U46", [1, 2], 3, "OR"),
    ("N_U46", [4, 5], 6, "OR"), ("N_U34", [1], 6, "NOT"),
    ("N_U46", [12, 13], 11, "OR"), ("N_U34", [3], 4, "NOT"),
    ("E_U28", [5], 6, "NOT"), ("E_U27", [12, 13], 11, "AND"),
    ("E_U12", [12, 13], 11, "AND"),
    ("E_U42", [3], 5, "BUF"), ("E_U42", [6], 2, "BUF"),
    ("N_U35", [1, 2], 3, "AND"), ("N_U48", [11], 10, "NOT"),
]


def gate_state(p, *, uv_ready, source_safe, arm, aux_valid, run, other_fault=False, q=False):
    def net(r, pin):
        return p[(r, str(pin))]
    state = {}
    for r, pin, value in [
        ("N_U58", 2, uv_ready), ("N_U51", 12, source_safe), ("N_U35", 9, arm),
        ("E_U31", 3, aux_valid), ("E_U23", 1, not run), ("E_U23", 2, not aux_valid),
        ("N_U45", 2, False), ("N_U45", 5, False), ("N_U46", 2, other_fault),
        ("E_U25", 8, False), ("E_U21", 13, q), ("E_U27", 12, run and aux_valid),
        ("E_U12", 12, True),
    ]:
        assert net(r, pin) not in state, ("aliased stimuli", r, pin)
        state[net(r, pin)] = value
    for r, ins, out, op in GATES:
        values = [state[net(r, pin)] for pin in ins]
        output = net(r, out)
        assert output not in state, ("multiple driven outputs", output)
        state[output] = {"AND": all, "OR": any, "NOT": lambda v: not v[0], "BUF": lambda v: v[0]}[op](values)
    set_value, reset = state[net("E_U21", 8)], state[net("E_U21", 11)]
    assert not (set_value and reset)
    return dict(set=set_value, reset=reset, q_before=q,
        q_after=False if reset else True if set_value else q,
        global_valid=state[net("N_U35", 3)],
        arm_clear=state[net("N_U50", 2)],
        aux_fault=state[net("N_U58", 4)])


def check_uv(p):
    # ARM must retain the evidence of a fault until GLOBAL actually drops.
    # A direct UV-driven clear can erase that evidence before E28 captures it.
    assert p[("N_U50", "2")] == p[("N_U50", "8")] == p[("N_U48", "10")]
    rows = []
    for bits in itertools.product([False, True], repeat=6):
        uv_ready, source_safe, arm, aux_valid, run, other_fault = bits
        args = dict(zip(["uv_ready", "source_safe", "arm", "aux_valid", "run", "other_fault"], bits))
        row = gate_state(p, **args)
        expected = ((arm and not (uv_ready and source_safe)) or other_fault) and run and aux_valid
        assert row["set"] == expected
        assert row["reset"] == (not run or not aux_valid)
        assert row["global_valid"] == (run and aux_valid)
        rows.append(dict(inputs=args, outputs=row))
    # After a recognized fault, GLOBAL low clears ARM, removing NF's transient
    # request. E28 must retain Q even once UV readiness returns.
    trace, q, arm = [], False, True
    for phase, uv, run in [("normal_armed", True, True), ("UV_fault", False, True),
                           ("fault_disables_GLOBAL", False, True), ("ARM_cleared", False, True),
                           ("UV_recovers", True, True), ("RUN_off_reset", True, False)]:
        row = gate_state(p, uv_ready=uv, source_safe=True, arm=arm, aux_valid=True, run=run, q=q)
        trace.append(dict(phase=phase, arm_before=arm, **row))
        q = row["q_after"]
        if row["arm_clear"]:
            arm = False
    assert trace[1]["q_after"]
    assert not trace[2]["global_valid"] and trace[2]["arm_clear"]
    assert trace[3]["q_after"] and not trace[3]["set"]
    assert trace[4]["q_after"] and not trace[4]["global_valid"]
    assert not trace[5]["q_after"] and not trace[5]["global_valid"]
    # Explicit counterexample to any claim of retention through AUX_VALID loss.
    deep = gate_state(p, uv_ready=False, source_safe=True, arm=True, aux_valid=False, run=True, q=True)
    assert deep["reset"] and not deep["q_after"]
    return rows, trace, deep


def run():
    parts, pins = read_netlist(OUT / "netlist.xml")
    oldparts, oldpins = read_netlist(BEFORE / "netlist.xml")
    assert parts.keys() == oldparts.keys()
    assert parts["E_U42"].findtext("value") == "SN74LVC3G17DCUR"
    assert oldparts["E_U42"].findtext("value") == "SN74AUP3G17DCUR"
    for r in parts:
        assert parts[r].findtext("footprint") == oldparts[r].findtext("footprint")
        if r != "E_U42":
            assert parts[r].findtext("value") == oldparts[r].findtext("value")
    expected = dict(oldpins)
    for buffer_pin, endpoint in [("3", ("E_U12", "11")), ("5", ("N_J1", "6")),
                                 ("6", ("E_U31", "3")), ("2", ("N_J1", "5"))]:
        expected[("E_U42", buffer_pin)] = oldpins[endpoint]
        assert pins[("E_U42", buffer_pin)] == pins[endpoint]
    assert partition(expected) == partition(pins)
    for pin in ["1", "4", "7", "8"]:
        assert pins[("E_U42", pin)] == oldpins[("E_U42", pin)]
    assert pins[("E_U42", "3")] != pins[("E_U29", "7")]
    for a, b in [(('E_U21', '9'), ('E_U21', '13')), (('E_U21', '10'), ('E_U21', '12')),
                 (('N_U50', '2'), ('N_U50', '8')), (('N_U50', '1'), ('N_U50', '6')),
                 (('N_U50', '3'), ('N_U50', '4')), (('N_U50', '10'), ('N_U50', '12')),
                 (('N_U50', '9'), ('N_U50', '13'))]:
        assert pins[a] == pins[b]
    assert pins[("N_U50", "1")] == pins[("N_U28", "2")]
    assert pins[("N_U28", "4")] == pins[("N_U35", "9")]
    assert pins[("N_U56", "6")] == pins[("N_U58", "2")] == pins[("N_U57", "3")]
    assert pins[("N_U56", "4")] == pins[("N_U57", "1")] == pins[("F_U401", "6")]
    rows, trace, deep = check_uv(pins)
    mutations = {}
    for label, node, source in [
        ("wrong_master_source", ("E_U42", "3"), ("E_U29", "7")),
        ("UV_fault_polarity_reversed", ("N_U51", "13"), ("N_U58", "4")),
        ("UV_directly_clears_ARM", ("N_U50", "2"), ("N_U58", "4")),
        ("fault_does_not_disable_master", ("E_U27", "13"), ("E_U12", "12")),
        ("SET_mask_removed", ("N_U34", "3"), ("N_U34", "6")),
    ]:
        trial = dict(pins)
        trial[node] = pins[source]
        try:
            check_uv(trial)
            mutations[label] = False
        except (KeyError, AssertionError):
            mutations[label] = True
    assert all(mutations.values()), mutations
    assert len(fault_mask(pins)) == 32 and len(verify_sense(parts, pins)) == 2
    # Inventory every receiving terminal before computing the load screen.
    def members(node):
        return {n for n, net in pins.items() if net == pins[node]}
    for out, header, resistor, receiver in [("5", "6", "N_R15", "2"), ("2", "5", "N_R16", "1")]:
        assert members(("E_U42", out)) == {("E_U42", out), ("N_J1", header), (resistor, "1"), ("N_U35", receiver)}
        assert parts[resistor].findtext("value") == "47k 3% TOTAL RECEIVING"
        assert pins[(resistor, "2")] == pins[("E_U42", "4")]
    assert members(("E_U31", "3")) == {("E_U31", "3"), ("E_U24", "13"), ("E_U28", "3"), ("E_U29", "2"), ("E_U42", "6")}
    pull_uA = 2.7 / (47000 * .97) * 1e6
    guarded_output_uA = 1.2 * (pull_uA + 1 + 1)  # HCS leakage requirement and PCB reserve
    source85_uA = 1.2 * (5 + 5 + .5 + 1 + 1)
    source125_uA = 1.2 * (20 + 20 + .5 + 5 + 1)
    assert guarded_output_uA < 100 and source85_uA < 20 and source125_uA > 20
    load = dict(local_AUX_receiving_v=[2.52, 2.7],
        per_output_pull_down_max_uA=pull_uA, per_HCS_input_leakage_receiving_uA=1,
        per_net_PCB_leakage_receiving_uA=1, engineering_guard_factor=1.2,
        per_buffer_output_guarded_uA=guarded_output_uA, LVC_rail_minus_p1_output_test_uA=100,
        original_AUP_output_test_uA=20, original_AUP_cannot_support_47k_light_load_row=True,
        E31_AUX_VALID_guarded_load_through85C_uA=source85_uA,
        E31_AUX_VALID_guarded_load_through125C_uA=source125_uA,
        E31_light_load_row_supported_through85C_given_requirements=True,
        E31_light_load_row_supported_through125C=False,
        old_existing_E31_guarded125C_load_without_new_buffer_uA=1.2*(20+20+.5+1),
        LVC_buffer_max_rail_state_static_package_current_uA=10,
        full_AUX_pool_or_input_transition_current_qualified=False,
        continuous_HCS_and_LVC_Schmitt_threshold_acceptance=False,
        partial_power_and_high_impedance_default_qualified=False)
    pcbpaths = [p / "power_protection.kicad_pcb" for p in [BEFORE, OUT]]
    trees = [read_sexpr(p.read_text()) for p in pcbpaths]
    fps = [{str(prop(f, "Reference")[2]): f for f in children(t, "footprint")} for t in trees]
    assert fps[0].keys() == fps[1].keys() and len(fps[1]) == 1092
    pads = 0
    for ref in fps[0]:
        previous = copy.deepcopy(fps[0][ref])
        if ref == "E_U42":
            prop(previous, "Value")[2] = "SN74LVC3G17DCUR"
        assert geometry(previous) == geometry(fps[1][ref]), ref
        for pad in children(fps[1][ref], "pad"):
            if ref in parts and str(pad[1]):
                assert str(first(pad, "net")[2]).lstrip("/") == pins[(ref, str(pad[1]))]
                pads += 1
    library = OUT / "libraries/TB05_E_RMX_E28.pretty/SN74LVC3G17_DCU0008A.kicad_mod"
    lands = {str(p[1]): p for p in children(read_sexpr(library.read_text()), "pad")}
    assert len(lands) == 8
    for number, pad in lands.items():
        i = int(number)
        want = [-1.55, -.75 + (i-1)*.5] if i <= 4 else [1.55, .75 - (i-5)*.5]
        assert [float(v) for v in first(pad, "at")[1:3]] == want
        assert [float(v) for v in first(pad, "size")[1:3]] == [.85, .3]
        assert abs(float(first(pad, "roundrect_rratio")[1])*.3-.05) < 1e-10
    roots = [[n for n in t if not(isinstance(n, list) and n and n[0] in ["footprint", "net"])] for t in trees]
    assert roots[0] == roots[1]
    review = json.loads((OUT / "review.json").read_text())
    for name, digest in review["source_sha256"].items():
        assert sha(REPO / name) == digest, name
    for name, digest in review["artifact_sha256"].items():
        assert sha(OUT / name) == digest, name
    basepdf = REPO / "hardware/qualification/boards/aux_current_partition/sources/primary"
    paths = [Path(__file__), REPO / "hardware/fabrication/audit_two_board_fault_mask.py",
             REPO / "hardware/fabrication/audit_two_board_source_sense.py",
             REPO / "hardware/fabrication/audit_two_board_power_delta.py", *pcbpaths,
             BEFORE / "netlist.xml", OUT / "netlist.xml", OUT / "review.json", library,
             REPO / "hardware/qualification/boards/startup_negative_circuit/uv_recovery/integration-contract.json",
             *[basepdf / (s + ".pdf") for s in ["SN74LVC3G17", "SN74AUP2G08", "SN74LVC08A", "SN74LVC14A"]]]
    report = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        only_declared_four_enable_pin_connections_and_one_MPN_change=True,
        original_channel1_retained=True, electrical_parts=1077, checked_physical_pads=pads,
        retained_footprint_geometry_count=1092, LVC_DCU_land_matches_4225266_A=True,
        enable_load_screen=load, UV_fault_settled_truth_cases=rows, settled_recovery_trace=trace,
        AUX_VALID_loss_clears_fault_latch_counterexample=deep, mutation_controls=mutations,
        inherited_fault_mask_combinations_rechecked=32, upstream_source_sense_channels_rechecked=2,
        recognized_UV_fault_retained_while_RUN_and_AUX_VALID_stay_high=True,
        no_reclose_proven_during_deep_AUX_corruption=False,
        minimum_recognized_UV_pulse_or_actual_OFF_interval_proven=False,
        complete_enable_electrical_qualification=False, fabrication_released=False)
    with (OUT / "enable-recovery-audit.json").open("x") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print(json.dumps(dict(cases=len(rows), trace=trace, mutations=mutations, load=load, pads=pads)))


if __name__ == "__main__":
    run()
