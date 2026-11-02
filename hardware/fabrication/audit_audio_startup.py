"""AC02 exact circuit delta, powered logic and conditional request/timing checks."""

import argparse
import itertools
import json
from collections import defaultdict
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.fabrication.audit_audio_core import ADC_STARS, DAC_PINS
from hardware.fabrication.audit_candidate import sha

REPO = Path(__file__).resolve().parents[2]
OLD = REPO / "hardware/fabrication/staging/audio-core-integration-01"
OUT = OLD.parent / "audio-core-startup-02"
NEW_PARTS = {"U210":"SN74LVC2G17DCKR", "U211":"SN74LVC1G17DCKR", "U212":"SN74LVC1G08DCKR",
             "C230":"100nF 16V X7R", "C231":"100nF 16V X7R", "C232":"100nF 16V X7R"}


def logic(pins, inputs):
    nodes = dict(inputs)
    gates = [("U207", (1,2),3), ("U207",(4,5),6), ("U207",(9,10),8), ("U207",(12,13),11),
             ("U210",(1,),6), ("U210",(3,),4), ("U211",(2,),4),
             ("U212",(1,2),4), ("U209",(1,2),4)]
    for _ in range(12):
        for ref, incoming, outgoing in gates:
            names = [pins[ref][str(p)] for p in incoming]
            if all(n in nodes for n in names):
                nodes[pins[ref][str(outgoing)]] = all(nodes[n] for n in names)
    return nodes


def powered_logic(pins):
    inputs = ["CODEC/CODEC_PGOOD", "CODEC/PRE_ANALOG_OK", "CODEC/CODEC_RUN",
              "CODEC/CLK_VALID", "CODEC/RAMP_DONE", "ADC_BIAS_WINDOW_OK", "CODEC/TIMER_OK"]
    for bits in itertools.product((False,True), repeat=7):
        pg,pre,run,clock,ramp,bias,timer = bits
        actual = logic(pins,dict(zip(inputs,bits)))
        request = pg and pre and run
        enable = request and clock and ramp
        ready = enable and bias
        for net,value in {"CHIP_EN":request, "ADC_DRV_ENABLE":enable,
                          "CODEC/DRIVER_SETTLE_READY":ready, "CODEC/ANALOG_OK":ready and timer}.items():
            assert actual.get(net) is value, (net,bits,actual.get(net),value)
    for fault in inputs[:-1]:
        state = dict.fromkeys(inputs,True)
        state[fault] = False
        assert logic(pins,state)["CODEC/ANALOG_OK"] is False, ("Stale high timer bypasses live qualifier",fault)
    return dict(powered_truth_cases=128,stale_high_timer_fault_cases=6,
                pulse_response_and_power_ramp_simulated=False)


def request_corners():
    maximum_current, minimum_pd = 0.0, float("inf")
    cases = 0
    for signs in itertools.product((-1,1),repeat=6):
        series = [47000*(1+signs[i]*.03) for i in (0,1)]
        pull = [68000*(1+signs[i+2]*.03) for i in (0,1)]
        request,ground = 10000*(1+signs[4]*.03),100000*(1+signs[5]*.03)
        branch = [series[i]+pull[i] for i in (0,1)]
        for n1,n2,ib1,ib2,leak in itertools.product((-.286,-.172),(-.286,-.172),(-100e-9,100e-9),(-100e-9,100e-9),(-300e-9,300e-9)):
            for enable in (2.94,3.55):
                biases, currents = (n1,n2),(ib1,ib2)
                gate = (enable/request + sum(biases[i]/branch[i]-currents[i]*pull[i]/branch[i] for i in (0,1))-leak) / (1/request+1/ground+sum(1/b for b in branch))
                maximum_current = max(maximum_current,(enable-gate)/request)
                for i in (0,1):
                    relative = (gate-biases[i])*pull[i]/branch[i]-currents[i]*series[i]*pull[i]/branch[i]
                    minimum_pd = min(minimum_pd,relative)
                cases += 1
    off = max((.4+.286)*68000*(1+s*.03)/(47000*(1+t*.03)+68000*(1+s*.03))
              +100e-9*(47000*(1+t*.03)*68000*(1+s*.03))/(47000*(1+t*.03)+68000*(1+s*.03))
              for s,t in itertools.product((-1,1),repeat=2))
    assert maximum_current < 100e-6 and minimum_pd > 1.15 and off < .55
    return dict(corner_cases=cases,IO_rail_allocation_v=[3.04,3.55],buffered_high_min_v=2.94,
        maximum_normal_source_current_a=maximum_current,minimum_enabled_PD_above_Vminus_v=minimum_pd,
        maximum_disabled_PD_above_Vminus_v=off,full_resistor_error_allocation=.03,
        FDA_bias_current_each_a=100e-9,reset_off_leakage_bound_a=300e-9,
        fault_clamp_source_upper_bound_a=3.55/9700+200e-9,
        normal_request_network_static_pass=True,abrupt_fault_or_partial_power_qualified=False)


def timing(cmin=1.6e-6):
    delay_min = cmin*1.17/(1.35e-6+100e-9)
    after_driver = delay_min-.028-1e-6
    return dict(CT_effective_required_f=[cmin,2.8e-6],total_CT_injection_limit_a=100e-9,
        minimum_timer_s=delay_min,ADC_supervisor_release_max_s=.028,logic_propagation_allocation_s=1e-6,
        minimum_settling_after_driver_enable_s=after_driver,required_ADC_settling_s=1.2,
        passes=after_driver>=1.2,CT_part_and_complete_discharge_qualified=False,
        condition="Stable qualified supplies/bias, bounded load and initially fully discharged CT; rapid fault/rearm needs separate discharge verification")


def check():
    native = json.loads((OUT/"native-review.json").read_text())
    construction = json.loads((OUT/"construction.json").read_text())
    for record in (native,construction):
        assert all(sha(REPO/p) == digest for p,digest in record["source_sha256"].items())
    for field in ("raw_export_sha256","captured_library_sha256"):
        assert all(sha(OUT/p) == digest for p,digest in native[field].items())
    erc = json.loads((OUT/"erc.json").read_text())
    assert erc["ignored_checks"] == [] and not any(s["violations"] for s in erc["sheets"])
    old, opins = netlist(OLD/"netlist.xml")
    parts,pins = netlist(OUT/"netlist.xml")
    assert set(parts)-set(old) == set(NEW_PARTS) and set(old) <= set(parts) and len(parts) == 216
    expected = json.loads((OUT/"expected-circuit.json").read_text())
    assert sum(len(v) for v in pins.values()) == 635
    for ref in parts:
        assert parts[ref].findtext("value") == expected[ref]["value"]
        assert (parts[ref].findtext("footprint") or "") == expected[ref]["footprint"]
        for pin,net in expected[ref]["pins"].items():
            assert (pins[ref][pin].startswith("unconnected-") if net is None else pins[ref][pin] == net), (ref,pin)
    for ref in old:
        assert parts[ref].findtext("value") == old[ref].findtext("value")
        assert parts[ref].findtext("footprint") == old[ref].findtext("footprint")
        wanted = dict(opins[ref])
        if expected[ref]["source_domain"] == "ADC":
            wanted = {p:{"CHIP_EN":"ADC_DRV_ENABLE","ADC/BIAS_OK":"ADC_BIAS_WINDOW_OK"}.get(n,n) for p,n in wanted.items()}
        changes = {"U207":("6","CODEC/CHIP_REQUEST"),"U208":("3","CODEC/DRIVER_SETTLE_READY"),"U209":("1","CODEC/DRIVER_SETTLE_READY")}
        if ref in changes:
            pin,net = changes[ref]
            wanted[pin] = net
        assert pins[ref] == wanted, ("Undeclared original circuit change",ref)
    assert all(parts[r].findtext("value") == value for r,value in NEW_PARTS.items())
    by_net = defaultdict(set)
    for ref,terminals in pins.items():
        for pin,net in terminals.items():
            by_net[net].add((ref,pin))
    for net,spec in ADC_STARS.items():
        assert by_net[net] == {("U201",spec["codec_pin"]),*spec["force"],*spec["sense"]}
    for net,nodes in DAC_PINS.items():
        assert by_net[net] == set(nodes)
    assert pins["U210"] == {"1":"CODEC/CHIP_REQUEST","2":"AGND","3":"CODEC/SETTLE_ENABLE","4":"ADC_DRV_ENABLE","5":"CODEC/V3V3_IO","6":"CHIP_EN"}
    assert pins["U211"]["2"] == "ADC_BIAS_WINDOW_OK" and pins["U211"]["4"] == "CODEC/ADC_BIAS_IO"
    assert pins["U212"]["1"] == "CODEC/SETTLE_ENABLE" and pins["U212"]["2"] == "CODEC/ADC_BIAS_IO" and pins["U212"]["4"] == "CODEC/DRIVER_SETTLE_READY"
    truth,dc,budget = powered_logic(pins),request_corners(),timing()
    assert budget["passes"] and not timing(1.5e-6)["passes"]
    minimum_R209_load_at_required_2v7 = 2.7/103000
    assert minimum_R209_load_at_required_2v7 > 20e-6
    inputs = [Path(__file__), OUT/"construction.json",OUT/"native-review.json",OUT/"expected-circuit.json",OUT/"netlist.xml",OUT/"erc.json",OUT/"primary-documents.json",OLD/"netlist.xml"]
    return dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},electrical_parts=216,
        exported_physical_terminals=635,native_ERC_findings=0,all_native_ERC_categories_enabled=True,
        original_210_parts_retained_with_exact_values_and_footprints=True,analog_ADC_stars_and_DAC_polarity_unchanged=True,
        added_parts=NEW_PARTS,logic=truth,request_DC_screen=dc,settling_budget=budget,
        original_HCS_direct_load_exceeds_20uA_condition=True,minimum_R209_load_at_2v7_a=minimum_R209_load_at_required_2v7,
        HCS_repaired_output_load_bounds_a={"CHIP_REQUEST":5e-6,"SETTLE_ENABLE":10e-6,"SUPPLY_OK":1e-6,"CODEC_FLAGS":1e-6},
        permitted_codec_CHIP_EN_input_load_a=100e-6-3.55/97000-1e-6,
        permitted_timer_MR_load_a=95e-6,remaining_level_conditions=[
            "Actual codec CHIP_EN input load must fit remaining100uA output allowance",
            "Timer MR current must fit output allowance; Schmitt thresholds across actual IO rail and transient loads require review",
            "R2 bias/V5 supervisor release/load timing and actual CT reset discharge must meet the stated model bounds"],
        driver_enable_reference_timing_qualified=False,actual_ADC_load_and_partial_power_limits_resolved=False,
        actual_DAC_output_scale_resolved=False,missing_footprint_refs=["U201"],physical_star_copper_checked=False,
        final_audio_PCB_routed=False,enclosure_fit_verified=False,fabrication_released=False)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    report=check()
    output=OUT/"integration-handoff.json"
    if args.check:
        assert json.loads(output.read_text()) == report
    else:
        with output.open("x") as stream:
            json.dump(report,stream,indent=2)
            stream.write("\n")
    print("AC02:216 parts/635 terminals;ERC0;128 logic+6 stale-timer cases; conditional PD/settling screens pass")
