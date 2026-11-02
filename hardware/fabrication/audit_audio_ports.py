"""AC03 circuit/land checks and source-bound audio-leg connection schedule."""

import argparse
import csv
import io
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_audio_startup import powered_logic, request_corners, timing
from hardware.fabrication.audit_candidate import native_evidence_errors, sha

REPO=Path(__file__).resolve().parents[2]
OLD=REPO/"hardware/fabrication/staging/audio-core-startup-02"
OUT=OLD.parent/"audio-core-ports-03b"
REMOVED={"J103","J104","J204","J205","J303"}
PORTS={
    "J401":{"1":"P12","2":"AGND","3":"N12","4":"V5_REG"},
    "J402":dict(zip(map(str,range(1,11)),("AGND","CODEC/V3V3_IO","CODEC/SCL","CODEC/SDA","CODEC/CODEC_RUN","CODEC/ANALOG_OK","AGND","CODEC/PRE_ANALOG_OK","CODEC/CODEC_PGOOD","CODEC/ANALOG_OK"))),
    "J403":{"1":"AGND","2":"ADC/NBIAS_L","3":"ADC/NBIAS_R"},
    "TP401":{"1":"ADC_DRV_ENABLE"},"TP402":{"1":"CHIP_EN"},
    "TP403":{"1":"ADC/PD_GATED"},"TP404":{"1":"AGND"},
}


def connections():
    rows=[]
    def link(bundle, core, pin, role, header, peer, net):
        rows.append(dict(bundle=bundle,core_header=core,core_pin=str(pin),peer_role=role,
                         peer_header=header,peer_pin=str(peer),net=net))
    for pin,peer,net in ((1,4,"P12"),(2,2,"AGND"),(3,5,"N12"),(4,6,"V5_REG")):
        link("CORE-ANALOG-POWER","J401",pin,"rail_disconnect","J3",peer,net)
    for pin,net in enumerate(("AGND","V3V3_IO","SCL","SDA","CODEC_RUN","ANALOG_OK"),1):
        link("CORE-MCU-CONTROL","J402",pin,"processor_carrier","J6",pin,net)
    for pin,peer,net in ((7,1,"AGND"),(8,2,"PRE_ANALOG_OK")):
        link("CORE-RAIL-HEALTH","J402",pin,"rail_monitor","J4",peer,net)
    link("CORE-BYPASS-HEALTH","J402",10,"sequenced_bypass","J3",3,"ANALOG_OK")
    for pin,net in enumerate(("AGND","NBIAS_L","NBIAS_R"),1):
        link("CORE-BIAS-SENSE","J403",pin,"rail_monitor","J3",pin,net)
    for pin,net in enumerate(("AGND","BCLK","WS","ADC_DATA","DAC_DATA"),1):
        link("CORE-SAI","J203",pin,"processor_carrier","J5",pin,net)
    for core,role,header,nets,bundle in (
        ("J101","input_range","J2",("PRE_OUT_L","AGND","PRE_OUT_R"),"CORE-INPUT"),
        ("J302","output_stage","J1",("RECV_L","AGND","RECV_R"),"CORE-OUTPUT"),
    ):
        for pin,net in enumerate(nets,1):
            link(bundle,core,pin,role,header,pin,net)
    return rows


def circuit():
    native=json.loads((OUT/"native-review.json").read_text())
    construction=json.loads((OUT/"construction.json").read_text())
    for record in (native,construction):
        assert all(sha(REPO/p)==digest for p,digest in record["source_sha256"].items())
    for field in ("raw_export_sha256","captured_library_sha256"):
        assert all(sha(OUT/p)==digest for p,digest in native[field].items())
    erc=json.loads((OUT/"erc.json").read_text())
    assert erc["ignored_checks"]==[] and not any(s["violations"] for s in erc["sheets"])
    old,old_pins=netlist(OLD/"netlist.xml")
    parts,pins=netlist(OUT/"netlist.xml")
    assert set(parts)==set(old)-REMOVED|set(PORTS) and len(parts)==218
    assert sum(len(v) for v in pins.values())==634
    expected=json.loads((OUT/"expected-circuit.json").read_text())
    for ref in parts:
        assert parts[ref].findtext("value")==expected[ref]["value"]
        assert (parts[ref].findtext("footprint") or "")==expected[ref]["footprint"]
        assert set(pins[ref])==set(expected[ref]["pins"])
        for pin,net in expected[ref]["pins"].items():
            assert (pins[ref][pin].startswith("unconnected-") if net is None else pins[ref][pin]==net),(ref,pin)
    for ref in set(old)-REMOVED:
        assert pins[ref]==old_pins[ref],("Undeclared original pin change",ref)
        assert parts[ref].findtext("value")==old[ref].findtext("value")
        assert parts[ref].findtext("footprint")==old[ref].findtext("footprint")
    for ref,contract in PORTS.items():
        assert pins[ref]==contract,(ref,pins[ref],contract)
    headers={ref:terminals for ref,terminals in pins.items() if ref.startswith("J")}
    assert set(headers)=={"J101","J203","J302","J401","J402","J403"}
    assert not any(net in ("CHIP_EN","ADC_DRV_ENABLE","ADC/PD_GATED") for p in headers.values() for net in p.values())
    assert not any(net.startswith(("ADC_L","ADC_R","DAC_L","DAC_R","SENSE_")) for p in headers.values() for net in p.values())
    return parts,pins,native


def lands():
    root=OUT/"libraries"
    records={}
    for ref,subpath,count,pitch in (
        ("J401","Connector_Molex.pretty/Molex_Micro-Fit_3.0_43045-0400_2x02_P3.00mm_Horizontal.kicad_mod",4,3),
        ("J402","Connector_JST.pretty/JST_XH_B10B-XH-A_1x10_P2.50mm_Vertical.kicad_mod",10,2.5),
        ("J403","Connector_JST.pretty/JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical.kicad_mod",3,2.5),
    ):
        path=root/subpath
        pads={str(p[1]):p for p in children(read_sexpr(path.read_text()),"pad") if str(p[1])}
        assert set(pads)=={str(i) for i in range(1,count+1)}
        for i in range(1,count+1):
            p=pads[str(i)]
            xy=list(map(float,first(p,"at")[1:3]))
            wanted=([0,0],[3,0],[0,3],[3,3])[i-1] if ref=="J401" else [(i-1)*pitch,0]
            assert xy==wanted and p[2]=="thru_hole"
            assert float(first(p,"drill")[1])==(1.02 if ref=="J401" else .95)
        records[ref]=dict(source_sha256=sha(path),native_pin_grid_mm={n:list(map(float,first(p,"at")[1:3])) for n,p in pads.items()},
                          finished_hole_nominal_mm=1.02 if ref=="J401" else .95,
                          drawing_orientation_and_mated_receiving_qualified=False)
    return records


def harness(pins,rows=None):
    rows=connections() if rows is None else rows
    scope=json.loads((REPO/"hardware/fabrication/scope.json").read_text())
    selected={r["role"]:r for r in scope["roles"]}
    tables,sources,selection={},{},{}
    for role in {r["peer_role"] for r in rows}:
        row=selected[role]
        project=REPO/row["source"]
        review=REPO/row["native_review"]
        assert not native_evidence_errors(project,json.loads(review.read_text()))
        net=project.parent/"netlist.xml"
        _,tables[role]=netlist(net)
        selection[role]=row["source"]
        sources.update({str(p.relative_to(REPO)):sha(p) for p in (project,review,net)})
    used=set()
    peers=set()
    for row in rows:
        ref,pin,net=row["core_header"],row["core_pin"],row["net"]
        assert ref.startswith("J") and (ref,pin) not in used
        used.add((ref,pin))
        actual=pins[ref][pin].rsplit("/",1)[-1]
        assert actual==net,("Core endpoint mismatch",row,actual)
        peer=(row["peer_role"],row["peer_header"],row["peer_pin"])
        assert peer not in peers,"One contact cannot contain multiple independent wires in this schedule"
        peers.add(peer)
        assert tables[peer[0]][peer[1]][peer[2]]==net,("Peer endpoint mismatch",row)
    expected={(r,p) for r,v in pins.items() if r.startswith("J") for p in v}-{("J402","9")}
    assert used==expected and len(rows)==27
    assert rows==connections(),"Assembly schedule differs from independent intended connection map"
    return dict(source_sha256=sources,peer_source_selection=selection,conductor_count=27,bundle_count=8,
                every_production_header_pin_accounted_for=True,unwired_header_pins=["J402.9 CODEC_PGOOD status/test"],
                source_contact_fanout_inside_audio_leg=False,legacy_enable_wire_present=False,
                wire_part_cut_lengths_crimps_installed_PDN_SI_and_routing_qualified=False)


def check():
    _,pins,native=circuit()
    report=harness(pins)
    proof=powered_logic(pins)
    dc=request_corners()
    budget=timing()
    paths=[Path(__file__),OUT/"native-review.json",OUT/"construction.json",OUT/"netlist.xml",OUT/"erc.json",OUT/"connector-parts.json",
           OLD/"netlist.xml",REPO/"hardware/fabrication/audit_audio_startup.py"]
    report["source_sha256"].update({str(p.relative_to(REPO)):sha(p) for p in paths})
    return dict(source_sha256=report["source_sha256"],electrical_parts=218,exported_physical_terminals=634,
        native_ERC_findings=native["ERC_findings"],all_native_ERC_categories_enabled=True,
        original_211_nonremoved_components_exact=True,removed_duplicate_or_legacy_headers=sorted(REMOVED),
        new_ports_and_testpoints=PORTS,logic=proof,request_DC_screen=dc,settling_budget=budget,
        connector_land_grids=lands(),audio_leg_connection_schedule=report,
        driver_enable_reference_timing_qualified=False,actual_ADC_load_and_partial_power_limits_resolved=False,
        actual_DAC_output_scale_resolved=False,missing_footprint_refs=["U201"],physical_star_copper_checked=False,
        final_audio_PCB_routed=False,enclosure_fit_verified=False,fabrication_released=False)


def schedule_text():
    stream=io.StringIO()
    rows=connections()
    writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    report=check()
    output=OUT/"integration-handoff.json"
    schedule=OUT/"audio-leg-connections.csv"
    if args.check:
        assert json.loads(output.read_text())==report
        assert schedule.read_text().splitlines()==schedule_text().splitlines()
    else:
        with output.open("x") as stream:
            json.dump(report,stream,indent=2)
            stream.write("\n")
        with schedule.open("x",newline="") as stream:
            stream.write(schedule_text())
    print("AC03:218 parts/634 terminals;ERC0;27 conductors checked against six selected peer boards; no external enable lead")
