"""TBP05 independent upstream-sense and startup-dependency audit.

Uses native netlists and manufacturer physical pin functions. Nominal DC
numbers explain the former startup deadlock; they are not corner qualification.
"""
import json
import re
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_two_board_fault_mask import evaluate
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.native_two_board_power import partition

OUT = STAGING / "two-board-power-native-05"
BEFORE = STAGING / "two-board-power-native-04"


def resistance(parts, ref):
    value = parts[ref].findtext("value")
    match = re.match(r"([0-9.]+)\s*(k|M|ohm)?", value)
    assert match, (ref, value)
    return float(match[1]) * {None: 1, "ohm": 1, "k": 1000, "M": 1000000}[match[2]]


def assert_series(pins, refs, start, end):
    net = start
    for ref in refs:
        pair = [pins[(ref, "1")], pins[(ref, "2")]]
        assert net in pair and pair[0] != pair[1], (ref, net, pair)
        net = pair[1] if pair[0] == net else pair[0]
    assert net == end


def zero_path(parts, pins, source, destination):
    """Propagate forced LOW through actual AND gates, without assuming other inputs."""
    paths = {pins[source]: []}
    gates = [(r, ins, out) for r in parts if parts[r].findtext("value") == "SN74HCS08PWR"
             for ins, out in [(('1', '2'), '3'), (('4', '5'), '6'), (('9', '10'), '8'), (('12', '13'), '11')]]
    while True:
        count = len(paths)
        for ref, ins, out in gates:
            for pin in ins:
                before, after = pins[(ref, pin)], pins[(ref, out)]
                if before in paths and after not in paths:
                    paths[after] = paths[before] + [dict(ref=ref, low_input=pin, forced_low_output=out)]
        if len(paths) == count:
            break
    assert pins[destination] in paths
    return paths[pins[destination]]


def verify_sense(parts, pins):
    gnd, refnet = pins[("P_U102", "4")], pins[("E_U7", "6")]
    assert parts["E_U8"].findtext("value") == "OPA2333AID"
    assert parts["N_U14"].findtext("value") == "TLV1822DR"
    rows = []
    for rail, nominal, force, feed, feedback, invpin, minus, plus, series, sensepin, refpin, uvout, divider, ff, protected, drain in [
        ("N19", 19, "N_J2", ["E_R49", "E_R50"], "E_R51", "1", "2", "3", ["E_R52", "N_R36"], "3", "2", "1", ["N_R33", "N_R34", "N_R35"], "N_U1", "N_R23", "N_R71"),
        ("N12", 12, "N_J4", ["E_R53"], "E_R54", "7", "6", "5", ["E_R55", "N_R52"], "5", "6", "7", ["N_R49", "N_R50", "N_R51"], "N_U7", "N_R40", "N_R88"),
    ]:
        source, post = pins[(force, "1")], pins[(force, "2")]
        assert source != post
        assert pins[(feed[0], "1")] == source, (rail, "source sense is not upstream")
        assert_series(pins, feed, source, pins[("E_U8", minus)])
        assert_series(pins, [feedback], pins[("E_U8", minus)], pins[("E_U8", invpin)])
        assert pins[("E_U8", plus)] == gnd
        assert_series(pins, series, pins[("E_U8", invpin)], pins[("N_U14", sensepin)])
        assert_series(pins, divider[:-1], refnet, pins[("N_U14", refpin)])
        assert_series(pins, divider[-1:], pins[("N_U14", refpin)], gnd)
        # Drain monitoring stays post-NF; output UV/OV stays post-E28 bank.
        assert pins[(drain, "1")] == post
        output = pins[("N_J1", "23" if rail == "N19" else "29")]
        assert pins[(protected, "1")] == output
        assert len({source, post, output}) == 3
        gain = resistance(parts, feedback) / sum(resistance(parts, r) for r in feed)
        upper = sum(resistance(parts, r) for r in divider[:-1])
        lower = resistance(parts, divider[-1])
        threshold = 1.25 * lower / (upper + lower)
        nominal_sense = nominal * gain
        assert nominal_sense > threshold > 1
        assert parts[ff].findtext("value") == "SN74AUP1G74DCUR"
        assert pins[(ff, "7")] == pins[(ff, "8")]  # inactive asynchronous PRE
        path = zero_path(parts, pins, ("N_U14", uvout), (ff, "6"))
        rows.append(dict(rail=rail, source=source, post_switch=post, protected_output=output,
            moved_sense_pin=f"{feed[0]}.1", inverter_gain=gain,
            nominal_raw_source_magnitude_v=nominal, nominal_reference_v=1.25,
            nominal_UV_comparison_threshold_v=threshold, nominal_upstream_sense_v=nominal_sense,
            nominal_sense_with_discharged_downstream_v=0,
            source_UV_LOW_to_permit_clear_LOW=path, permit_flipflop=ff,
            old_downstream_sense_holds_permit_cleared=True,
            new_upstream_sense_independent_of_switch_output=True))
    return rows


def run():
    parts, pins = read_netlist(OUT / "netlist.xml")
    oldparts, oldpins = read_netlist(BEFORE / "netlist.xml")
    assert parts.keys() == oldparts.keys()
    assert all(parts[r].findtext(k) == oldparts[r].findtext(k) for r in parts for k in ["value", "footprint"])
    changed = dict(oldpins)
    changed[("E_R49", "1")] = oldpins[("N_J2", "1")]
    changed[("E_R53", "1")] = oldpins[("N_J4", "1")]
    assert partition(changed) == partition(pins)
    rows = verify_sense(parts, pins)
    mutations = {}
    for label, trial in [("both_senses_returned_downstream", dict(oldpins)),
                         ("N19_sense_returned_downstream", dict(pins)),
                         ("N12_sense_returned_downstream", dict(pins)),
                         ("protected_monitor_moved_upstream", dict(pins))]:
        if label.startswith("N19"):
            trial[("E_R49", "1")] = pins[("N_J2", "2")]
        if label.startswith("N12"):
            trial[("E_R53", "1")] = pins[("N_J4", "2")]
        if label.startswith("protected"):
            trial[("N_R23", "1")] = pins[("N_J2", "1")]
        try:
            verify_sense(parts, trial)
            mutations[label] = False
        except AssertionError:
            mutations[label] = True
    assert all(mutations.values())
    fault_rows = evaluate(pins)
    pcbpaths = [p / "power_protection.kicad_pcb" for p in [BEFORE, OUT]]
    trees = [read_sexpr(p.read_text()) for p in pcbpaths]
    fps = [{str(prop(f, "Reference")[2]): f for f in children(t, "footprint")} for t in trees]
    assert fps[0].keys() == fps[1].keys() and len(fps[1]) == 1092
    pads = 0
    for ref in fps[0]:
        assert geometry(fps[0][ref]) == geometry(fps[1][ref]), ref
        for pad in children(fps[1][ref], "pad"):
            if ref in parts and str(pad[1]):
                assert str(first(pad, "net")[2]).lstrip("/") == pins[(ref, str(pad[1]))]
                pads += 1
    roots = [[n for n in t if not (isinstance(n, list) and n and n[0] in ["footprint", "net"])] for t in trees]
    assert roots[0] == roots[1]
    review = json.loads((OUT / "review.json").read_text())
    for name, digest in review["source_sha256"].items():
        assert sha(REPO / name) == digest, name
    for name, digest in review["artifact_sha256"].items():
        assert sha(OUT / name) == digest, name
    paths = [Path(__file__), REPO / "hardware/fabrication/audit_two_board_fault_mask.py",
             REPO / "hardware/fabrication/audit_two_board_power_delta.py", *pcbpaths,
             BEFORE / "netlist.xml", OUT / "netlist.xml", BEFORE / "fault-mask-audit.json", OUT / "review.json"]
    report = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        source_sense_channels=rows, only_two_declared_sense_pin_changes=True,
        native_parts_and_values_retained=1077, retained_complete_footprint_geometries=1092,
        mapped_pad_instances=pads, settled_fault_mask_combinations_rechecked=len(fault_rows),
        source_sense_mutations_rejected=mutations,
        primary_pin_function_sources=["https://www.ti.com/lit/ds/symlink/opa333.pdf",
            "https://www.ti.com/lit/ds/symlink/tlv1822.pdf", "https://www.ti.com/lit/ds/symlink/sn74hcs08.pdf",
            "https://www.ti.com/lit/ds/symlink/sn74aup1g74.pdf"],
        limitations=["Nominal comparison assumes a valid AUX supply, 1.25V reference and settled ideal inverter behavior.",
                     "Source/reference tolerance, input loading, partial-power behavior and timing remain to be qualified.",
                     "Removing this circular dependency does not qualify full startup: MASTER/AUX_VALID, module feed and UV recovery remain incomplete."],
        complete_startup_verified=False, fabrication_released=False)
    with (OUT / "source-sense-audit.json").open("x") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print(json.dumps({k: report[k] for k in ["source_sense_channels", "mapped_pad_instances", "source_sense_mutations_rejected"]}))


if __name__ == "__main__":
    run()
