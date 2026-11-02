"""Independently replay AC04's six circuits, joined audio path and startup gates."""

import argparse
import csv
import itertools
import json
import re
from collections import defaultdict
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_audio_core import ADC_STARS, DAC_PINS
from hardware.fabrication.audit_audio_startup import logic as core_logic
from hardware.fabrication.audit_audio_startup import powered_logic, request_corners, timing
from hardware.fabrication.audit_candidate import native_evidence_errors, sha
from hardware.fabrication.audit_digital_layout import check as check_digital

REPO = Path(__file__).resolve().parents[2]
STAGING = REPO/"hardware/fabrication/staging"
OLD = STAGING/"audio-core-ports-03b"
OUT = STAGING/"audio-main-integration-04b"
HANDOFF = OUT/"integration-handoff-03.json"
CORE_REMOVED = {"J101","J302","J401"}
ALIASES = {"ADC/PRE_OUT_L":"PRE_OUT_L","ADC/PRE_OUT_R":"PRE_OUT_R",
           "DAC/RECV_L":"RECV_L","DAC/RECV_R":"RECV_R",
           "CODEC/V3V3_IO":"V3V3_IO","CODEC/ANALOG_OK":"ANALOG_OK"}
SECTIONS = (
    ("INPUT","input-range-native-01",400,{"J1","J2","J3","J4"}),
    ("OUTPUT","output-stage-native-01",500,{"J1","J2","J3","J4"}),
    ("BYPASS","bypass-closed-native-03",600,{"J1","J4","J5","J9"}),
)
SHARED = {"AGND","P19","N19","P12","N12","V5_REG","5V_DIG","V3V3_IO","ANALOG_OK",
          "PROC_IN_L","PROC_IN_R","PRE_OUT_L","PRE_OUT_R","RECV_L","RECV_R","PROC_OUT_L","PROC_OUT_R","GAIN_LOW"}
PORTS = {
    "J701": dict(value="43045-0600",footprint="Connector_Molex:Molex_Micro-Fit_3.0_43045-0600_2x03_P3.00mm_Horizontal",
                 pins=dict(zip(map(str,range(1,7)),("P19","AGND","N19","P12","N12","V5_REG")))),
    "J702": dict(value="B2B-XH-A(LF)(SN)",footprint="Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
                 pins={"1":"5V_DIG","2":"AGND"}),
}


def expected_circuit():
    result = {}
    parts,pins = netlist(OLD/"netlist.xml")
    for ref in parts.keys()-CORE_REMOVED:
        result[ref] = dict(value=parts[ref].findtext("value"),footprint=parts[ref].findtext("footprint") or "",
                           pins={p:None if n.startswith("unconnected-") else ALIASES.get(n,n) for p,n in pins[ref].items()})
    for domain,folder,offset,removed in SECTIONS:
        parts,pins = netlist(STAGING/folder/"netlist.xml")
        for ref in parts.keys()-removed:
            prefix,number = re.fullmatch(r"([A-Z]+)([0-9]+)",ref).groups()
            new = prefix+str(int(number)+offset)
            mapped = {}
            for pin,net in pins[ref].items():
                net = {"5V":"5V_DIG","3V3":"V3V3_IO"}.get(net,net)
                mapped[pin] = None if net.startswith("unconnected-") else net if net in SHARED else domain+"/"+net
            result[new] = dict(value=parts[ref].findtext("value"),footprint=parts[ref].findtext("footprint") or "",pins=mapped)
    result.update(PORTS)
    return result


def verify_export(parts,pins):
    expected = expected_circuit()
    assert set(parts)==set(expected) and len(parts)==329, "Wrong retained component set"
    assert sum(len(v) for v in pins.values())==971, "Wrong physical terminal count"
    by_net = defaultdict(set)
    for ref,spec in expected.items():
        assert parts[ref].findtext("value")==spec["value"], ("Value changed",ref)
        assert (parts[ref].findtext("footprint") or "")==spec["footprint"], ("Land changed",ref)
        assert set(pins[ref])==set(spec["pins"]), ("Terminal set changed",ref)
        for pin,net in spec["pins"].items():
            actual = pins[ref][pin]
            assert (actual.startswith("unconnected-") if net is None else actual==net), ("Pin net changed",ref,pin,net,actual)
            by_net[actual].add((ref,pin))
    for net,spec in ADC_STARS.items():
        assert by_net[net]=={("U201",spec["codec_pin"]),*spec["force"],*spec["sense"]}, ("ADC physical terminal star",net)
    for net,nodes in DAC_PINS.items():
        assert by_net[net]==set(nodes), ("Raw DAC polarity or I/V join",net)
    for net,nodes in {
        "PROC_IN_L":{("K602","3"),("K401","4"),("R401","1")},
        "PROC_IN_R":{("K602","6"),("K401","5"),("R408","1")},
        "PRE_OUT_L":{("U103","3"),("R407","2"),("R107","1")},
        "PRE_OUT_R":{("U103","5"),("R414","2"),("R123","1")},
        "RECV_L":{("R312","2"),("U501","3"),("U502","3"),("R517","1")},
        "RECV_R":{("R324","2"),("U501","5"),("U502","5"),("R518","1")},
        "PROC_OUT_L":{("K601","4"),("K503","3")},
        "PROC_OUT_R":{("K601","5"),("K503","6")},
        "GAIN_LOW":{("Q602","3"),("D602","1"),("K401","8"),("K503","8")},
    }.items():
        assert by_net[net]==nodes, ("Audio/gain interface join changed",net)
    assert pins["U501"]["8"]=="P19" and pins["U501"]["4"]=="N19"
    assert pins["U502"]["8"]=="P12" and pins["U502"]["4"]=="N12"
    for ref in ("K401","K503","K601","K602"):
        assert pins[ref]["1"]=="5V_DIG", ("Coil on wrong 5V rail",ref)
    headers = {r:v for r,v in pins.items() if r.startswith("J")}
    assert set(headers)=={"J203","J402","J403","J602","J603","J606","J607","J608","J701","J702"}
    assert not any(net in {"CHIP_EN","ADC_DRV_ENABLE","ADC/PD_GATED",*ADC_STARS,*DAC_PINS,
                          "PROC_IN_L","PROC_IN_R","PRE_OUT_L","PRE_OUT_R","RECV_L","RECV_R","PROC_OUT_L","PROC_OUT_R","GAIN_LOW"}
                   for terminal in headers.values() for net in terminal.values()), "An internal audio/control boundary still has a header"
    assert [r for r in parts if not parts[r].findtext("footprint")]==["U201"]
    return expected


def bypass_logic(pins,inputs):
    state = {"V3V3_IO":True,**inputs}
    gates = [(ref,ins,out) for ref in ("U602","U606") for ins,out in (((1,2),3),((4,5),6),((9,10),8),((12,13),11))]
    for _ in range(8):
        for ref,ins,out in gates:
            nets = [pins[ref][str(i)] for i in ins]
            if all(n in state for n in nets):
                state[pins[ref][str(out)]]=all(state[n] for n in nets)
        for ins,out in (((1,2),3),((4,5),6)):
            nets = [pins["U608"][str(i)] for i in ins]
            if all(n in state for n in nets):
                state[pins["U608"][str(out)]]=state[nets[0]] != state[nets[1]]
    return state


def coupled_logic(pins):
    startup_inputs = ["CODEC/CODEC_PGOOD","CODEC/PRE_ANALOG_OK","CODEC/CODEC_RUN","CODEC/CLK_VALID",
                      "CODEC/RAMP_DONE","ADC_BIAS_WINDOW_OK","CODEC/TIMER_OK"]
    bypass_inputs = ["BYPASS/LOCAL_OK","BYPASS/GAIN_REQ","BYPASS/GAIN_DELAY","BYPASS/TIMER_INPUT_OK",
                     "BYPASS/PROCESS_OK","BYPASS/MCU_PERMIT","BYPASS/ARMED"]
    cases = 0
    for bits in itertools.product((False,True),repeat=14):
        core = core_logic(pins,dict(zip(startup_inputs,bits[:7])))
        expected_analog = all(bits[:7])
        assert core.get("ANALOG_OK") is expected_analog, "Analog startup qualifier changed"
        local,req,delay,timer,process,permit,armed = bits[7:]
        state = bypass_logic(pins,{**dict(zip(bypass_inputs,bits[7:])),"ANALOG_OK":core["ANALOG_OK"]})
        input_enable = local and expected_analog
        input_ready = input_enable and req==delay and timer
        final = input_ready and process and permit and armed
        for net,value in {"BYPASS/INPUT_ENABLE":input_enable,"BYPASS/INPUT_READY":input_ready,"BYPASS/FINAL_ENABLE":final}.items():
            assert state.get(net) is value, ("Coupled startup/bypass logic mismatch",net,bits,state.get(net),value)
        cases += 1
    # Original startup-only checker retains its original internal spelling.
    normalized = {r:{p:("CODEC/ANALOG_OK" if n=="ANALOG_OK" else "CODEC/V3V3_IO" if n=="V3V3_IO" else n)
                     for p,n in v.items()} for r,v in pins.items()}
    original = powered_logic(normalized)
    return dict(combined_powered_truth_cases=cases,original_startup_truth_replay=original,
        manual_bypass_keeps_input_enabled_when_other_qualifiers_valid=True,
        gain_transition_invalidates_input_ready_and_wet_enable=True,
        dynamic_edges_relay_motion_partial_power_and_rearm_qualified=False)


def connections():
    rows=[]
    def add(bundle,header,pin,role,peer,pin2,net):
        rows.append(dict(bundle=bundle,audio_header=header,audio_pin=str(pin),peer_role=role,
                         peer_header=peer,peer_pin=str(pin2),net=net))
    for pin,net in enumerate(("P19","AGND","N19","P12","N12","V5_REG"),1):
        add("ANALOG-POWER","J701",pin,"rail_disconnect","J3",pin,net)
    for pin,net in enumerate(("5V_DIG","AGND"),1):
        add("COIL-POWER","J702",pin,"rail_disconnect","J4",pin,net)
    for header,peer,nets,bundle in (
        ("J402","J1006",("AGND","V3V3_IO","SCL","SDA","CODEC_RUN","ANALOG_OK"),"MCU-CONTROL"),
        ("J203","J1005",("AGND","BCLK","WS","ADC_DATA","DAC_DATA"),"SAI"),
        ("J602","J1003",("AGND","HEARTBEAT","MCU_PERMIT","GAIN_REQ","ARMED","BYPASS_SENSE"),"MCU-BYPASS"),
        ("J606","J1007",("AGND","INPUT_READY"),"INPUT-READY"),
    ):
        for pin,net in enumerate(nets,1):
            add(bundle,header,pin,"digital_core",peer,pin,net)
    for pin,peer,net in ((7,1,"AGND"),(8,2,"PRE_ANALOG_OK")):
        add("RAIL-HEALTH","J402",pin,"rail_monitor","J4",peer,net)
    for pin,net in enumerate(("AGND","NBIAS_L","NBIAS_R"),1):
        add("BIAS-SENSE","J403",pin,"rail_monitor","J3",pin,net)
    for header,component,nets,bundle in (("J607","line_input",("IN_L","AGND","IN_R"),"REAR-IN"),
                                       ("J608","line_output",("OUT_L","AGND","OUT_R"),"REAR-OUT")):
        for pin,terminal,net in zip((1,2,3),("left","return","right"),nets):
            add(bundle,header,pin,"panel",component,terminal,net)
    for pin,terminal,net in ((1,"loop_supply","V3V3_IO"),(2,"process_loop","PROCESS_OK"),
                             (4,"sense_return","AGND"),(5,"sense","BYPASS_SENSE")):
        add("MANUAL-BYPASS","J603",pin,"panel","manual_bypass",terminal,net)
    return rows


def harness(pins,rows=None):
    rows = connections() if rows is None else rows
    selected = json.loads((OUT/"peer-selection.json").read_text())
    tables,sources = {},{}
    for role in ("rail_disconnect","rail_monitor"):
        row = selected[role]
        project,review = [REPO/row[k] for k in ("source","native_review")]
        assert not native_evidence_errors(project,json.loads(review.read_text()))
        table = project.parent/"netlist.xml"
        _,tables[role] = netlist(table)
        sources.update({str(p.relative_to(REPO)):sha(p) for p in (project,review,table)})
    digital = STAGING/"digital-core-placement-03"
    assert check_digital()==json.loads((digital/"placement-handoff.json").read_text())
    _,tables["digital_core"] = netlist(digital/"native-netlist.xml")
    sources.update({str(p.relative_to(REPO)):sha(p) for p in (digital/"placement-handoff.json",digital/"native-netlist.xml")})
    used,peers = set(),set()
    for row in rows:
        endpoint = row["audio_header"],row["audio_pin"]
        assert endpoint not in used, "Audio contact contains multiple wires"
        used.add(endpoint)
        actual = pins[endpoint[0]][endpoint[1]].rsplit("/",1)[-1]
        assert actual==row["net"], ("Audio leg endpoint mismatch",row)
        peer = row["peer_role"],row["peer_header"],row["peer_pin"]
        assert peer not in peers, "Peer contact contains multiple audio-leg wires"
        peers.add(peer)
        if peer[0]!="panel":
            assert tables[peer[0]][peer[1]][peer[2]].rsplit("/",1)[-1]==row["net"], ("Peer net mismatch",row)
    unwired = {("J402","9"),("J402","10"),("J603","3")}
    assert used == {(r,p) for r,v in pins.items() if r.startswith("J") for p in v}-unwired
    assert rows==connections() and len(rows)==42
    return dict(source_sha256=sources,conductor_count=42,bundle_count=len({r["bundle"] for r in rows}),
        unwired_status_contacts=["J402.9 CODEC_PGOOD","J402.10 ANALOG_OK","J603.3 ANALOG_OK"],
        old_AC03_four_way_power_header_and_enable_harness_compatible=False,
        logical_panel_contacts_only_no_supplier_terminal_numbers=True,
        E28_digital_force_fanout_with_other_loads_qualified=False,
        wire_parts_crimps_lengths_installed_PDN_SI_and_complete_unit_harness_qualified=False)


def current_interfaces():
    """Keep the frozen receipt reproducible; compare present peer interfaces separately."""
    scope=json.loads((REPO/"hardware/fabrication/scope.json").read_text())
    selected={r["role"]:r for r in scope["roles"]}
    captured=json.loads((OUT/"peer-selection.json").read_text())
    current={r:REPO/selected[r]["source"] for r in captured}
    current["digital_core"]=REPO/scope["shared_digital_core"]["source"]
    old={r:REPO/v["source"] for r,v in captured.items()}
    old["digital_core"]=STAGING/"digital-core-placement-03/digital_core.kicad_pro"
    sources={}
    for role,project in current.items():
        old_folder=old[role].parent
        original=old_folder/("native-netlist.xml" if (old_folder/"native-netlist.xml").exists() else "netlist.xml")
        before,before_pins=netlist(original)
        path=project.parent/("native-netlist.xml" if (project.parent/"native-netlist.xml").exists() else "netlist.xml")
        after,after_pins=netlist(path)
        refs={r["peer_header"] for r in connections() if r["peer_role"]==role}
        for ref in refs:
            assert before_pins[ref]==after_pins[ref], ("Changed current peer pins",role,ref)
            for field in ("value","footprint"):
                assert before[ref].findtext(field)==after[ref].findtext(field), ("Changed current peer part/land",role,ref)
        sources.update({str(p.relative_to(REPO)):sha(p) for p in (project,path)})
    return dict(current_source_sha256=sources,all_current_peer_headers_match_frozen_pin_value_and_land_contract=True,
                whole_peer_board_electrical_or_mechanical_qualification_inferred=False)


def lands():
    record={}
    for ref,spec in PORTS.items():
        lib,name=spec["footprint"].split(":")
        path=OUT/"libraries"/(lib+".pretty")/(name+".kicad_mod")
        pads={str(p[1]):p for p in children(read_sexpr(path.read_text()),"pad") if str(p[1])}
        wanted = {str(i+1):[3*(i%3),3*(i//3)] for i in range(6)} if ref=="J701" else {"1":[0,0],"2":[2.5,0]}
        assert set(pads)==set(wanted)
        for pin,xy in wanted.items():
            assert list(map(float,first(pads[pin],"at")[1:3]))==xy and pads[pin][2]=="thru_hole"
            assert float(first(pads[pin],"drill")[1])==(1.02 if ref=="J701" else 1.0)
        record[ref]=dict(source_sha256=sha(path),native_pin_grid_mm=wanted,
                         native_hole_nominal_mm=1.02 if ref=="J701" else 1.0,
                         manufacturer_orientation_mating_and_process_accepted=False)
    return record


def check():
    native,construction=[json.loads((OUT/p).read_text()) for p in ("native-review.json","construction.json")]
    for record in (native,construction):
        assert all(sha(REPO/p)==h for p,h in record["source_sha256"].items()), "Source changed"
    for field in ("raw_export_sha256","captured_library_sha256"):
        assert all(sha(OUT/p)==h for p,h in native[field].items())
    erc=json.loads((OUT/"erc.json").read_text())
    assert len(erc["sheets"])==7 and erc["ignored_checks"]==[] and not any(s["violations"] for s in erc["sheets"])
    assert native["ERC_findings"]==0 and all(c["returncode"]==0 for c in native["complete_native_commands"])
    parts,pins=netlist(OUT/"netlist.xml")
    expected=verify_export(parts,pins)
    saved=json.loads((OUT/"expected-circuit.json").read_text())
    assert expected=={r:{k:v[k] for k in ("value","footprint","pins")} for r,v in saved.items()}
    assert not (OUT/"audio_core.kicad_pcb").exists()
    schedule_path=OUT/"audio-leg-connections.csv"
    with schedule_path.open(newline="") as stream:
        rows=list(csv.DictReader(stream))
    connection=harness(pins,rows)
    paths=[Path(__file__),OUT/"construction.json",OUT/"native-review.json",OUT/"netlist.xml",OUT/"erc.json",schedule_path,OUT/"peer-selection.json",
           REPO/"hardware/fabrication/audit_audio_startup.py",REPO/"hardware/fabrication/audit_audio_core.py"]
    sources={str(p.relative_to(REPO)):sha(p) for p in paths}
    sources.update(connection["source_sha256"])
    return dict(revision="AC04",source_sha256=sources,electrical_parts=329,exported_physical_terminals=971,
        native_ERC_findings=0,all_native_ERC_categories_enabled=True,removed_old_headers=15,new_shared_power_headers=2,
        original_six_section_values_lands_and_pin_nets_independently_replayed=True,
        exact_joined_audio_and_gain_nodes_verified=True,logic=coupled_logic(pins),
        request_DC_screen=request_corners(),settling_budget=timing(),connector_land_grids=lands(),
        audio_leg_connection_schedule=connection,missing_footprint_refs=["U201"],
        physical_star_copper_checked=False,final_audio_PCB_routed=False,enclosure_fit_verified=False,
        actual_ADC_load_partial_power_and_DAC_scale_resolved=False,
        driver_enable_reference_timing_qualified=False,coil_return_thermal_and_noise_qualified=False,fabrication_released=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    parser.add_argument("--write-connections",action="store_true")
    args=parser.parse_args()
    if args.write_connections:
        rows=connections()
        with (OUT/"audio-leg-connections.csv").open("x",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    else:
        result=check()
        path=HANDOFF
        if args.check:
            assert result==json.loads(path.read_text())
        else:
            with path.open("x") as stream:
                json.dump(result,stream,indent=2)
                stream.write("\n")
        print("AC04: six sections / 329 parts / 971 terminals; ERC 0; 16384 coupled powered logic cases; 42 proposed audio-leg wires")
