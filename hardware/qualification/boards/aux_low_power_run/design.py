"""Generate actual AX03 source/receiver cells; never launches a CAD app."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

from hardware.electronics.common.flat_schematic import generate

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
AX02 = ROOT.parent / "aux_current_partition_followup"
AX01 = ROOT.parent / "aux_current_partition"
E28 = REPO / "hardware/electronics/rail_disconnect/revision28/generated/closed-logic-cleanup2-work"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def schmitt(ref, supply, signal, output, x, y):
    return dict(ref=ref, part="SN74AUP1G17DCKR", footprint="RMX_AX03:TI_DCK0005A",
        source="https://www.ti.com/lit/ds/symlink/sn74aup1g17.pdf",
        note="Actual DCK5:1NC,2A,3GND,4Y,5VCC; Schmitt input and specifiedIoff. Completeactual-band thresholds/current remain receiving requirements.", x=x, y=y,
        pins=[dict(number=n, name=name, net=net, kind=kind, side="R" if kind=="output" else "L")
              for n, name, net, kind in [("1","NC",None,"no_connect"),("2","A",signal,"input"),
              ("3","GND","AGND","power_in"),("4","Y",output,"output"),("5","VCC",supply,"power_in")]])


def main():
    assert not (ROOT / "components.json").exists()
    captured = {}
    for source, name in [(AX02 / "generated/analysis.json", "AX02-analysis.json"),
                         (AX01 / "generated/analysis.json", "AX01-analysis.json"),
                         (AX02 / "components.json", "AX02-components.json"),
                         (E28 / "components.json", "E28-components.json")]:
        digest = sha(source)
        shutil.copyfile(source, ROOT / "sources" / name)
        assert sha(source)==sha(ROOT / "sources" / name)==digest
        captured[str(source)]=digest
    parts = json.loads((ROOT / "sources/AX02-components.json").read_text())
    parts = [p for p in parts if p["ref"]!="U2"]
    parts.insert(1, schmitt("U2","AUX","RUN_GATE_COMMAND","RUN_BUFFERED_SOURCE",177.8,66.04))
    by={p["ref"]:p for p in parts}
    by["R2"].update(part="10M 1%", note="Explicit RESET pulldown; complete3% receiving. 10M plus100k pullup keeps source Schmitt HIGH margin under actual input leakage.")
    by["R4"].update(part="1k 1% CRCW12061K00FKEA",note="Complete3% receiving; 1k series limits line faults. Voh qualification only at normal<=20uA; pin absolute current separately checked.")
    by["R4"]["pins"][0]["net"]="RUN_BUFFERED_SOURCE"
    by["C1"].update(part="100nF 50V X7R C0603C104K5RACTU",footprint="Capacitor_SMD:C_0603_1608Metric",
        note="Source Schmitt local bypass; replaces10uF load-switch input cap. EffectiveC/PDN/process still require validation.")
    lib=ROOT / "RMX_AX03.pretty"
    lib.mkdir()
    land=REPO / "hardware/qualification/boards/startup_negative_circuit/uv_recovery/NF05R_Manufacturer.pretty/TI_DCK0005A.kicad_mod"
    shutil.copyfile(land,lib/land.name)
    captured[str(land)]=sha(land)
    generate(ROOT,"AX03","power_run_low_power",parts,
        [(20,350,"AX03: Active-HIGH RUN preserved; originalP03PG/R113 unchanged. Source/receiver are Schmitt, not standard CMOS."),
         (20,360,"RequiredE28changes: eight DCU triples AUP; R93=200k complete1%; newAUP receiver isolates original U28.1."),
         (20,370,"All actual-band thresholds/current, sourcecollapse, cutoff, physical and fabrication gates remain unqualified.")],
        (550,400),[("AUX",20.32,20.32),("AGND",60.96,20.32)])
    receiver = [schmitt("U43","V2V5_AUX","POWER_RUN","RUN_BUFFERED",177.8,66.04)]
    receiver += [dict(ref="R93",part="200k 0.1% ERA6AEB204V - COMPLETE1% RECEIVING",footprint="Resistor_SMD:R_0805_2012Metric",
        source="https://industrial.panasonic.com/ww/products/pt/resistors/models/ERA6AEB204V",note="Manufacturer/land reconciliation still required before production; complete1% and board leakage are acceptance requirements.",x=55.88,y=66.04,
        pins=[dict(number="1",name="1",net="POWER_RUN",kind="passive",side="L"),dict(number="2",name="2",net="AGND",kind="passive",side="L")])]
    cap=copy.deepcopy(by["C1"])
    cap.update(ref="C86",x=299.72,y=66.04)
    cap["pins"][0]["net"]="V2V5_AUX"
    receiver.append(cap)
    for ref, pins, x in [("J1",["V2V5_AUX","AGND","POWER_RUN"],55.88),("J2",["RUN_BUFFERED","AGND"],177.8)]:
        receiver.append(dict(ref=ref,part="BENCH HEADER - NOT PRODUCTION",footprint=f"Connector_PinHeader_2.54mm:PinHeader_1x0{len(pins)}_P2.54mm_Vertical",
            source="",note="External test fixture only",x=x,y=157.48,
            pins=[dict(number=str(i),name=str(i),net=n,kind="passive",side="L") for i,n in enumerate(pins,1)]))
    dst=ROOT / "receiver"
    dst.mkdir()
    shutil.copytree(lib,dst/lib.name)
    generate(dst,"AX03","power_run_receiver",receiver,[(20,250,"Active-HIGH rawRUN defaultsLOW through200k; buffer output replaces U28.1 feed. No bypass of the existing RUN inhibit logic.")],
        (450,300),[("V2V5_AUX",20.32,20.32),("AGND",60.96,20.32)])
    e28=json.loads((ROOT / "sources/E28-components.json").read_text())
    delta=[]
    for p in e28:
        if p["part"]=="SN74LVC3G17DCUR":
            delta.append(dict(ref=p["ref"],old_part=p["part"],new_part="SN74AUP3G17DCUR",pins_and_package_unchanged=True))
            p.update(part="SN74AUP3G17DCUR",source="https://www.ti.com/lit/gpn/sn74aup3g17",
                     note="Pin-compatibleDCU substitution; all actual-band input thresholds and nonrail current still require characterization. No routing/physical pass inherited.")
        elif p["ref"]=="R93":
            p.update(part=receiver[1]["part"],note=receiver[1]["note"],source=receiver[1]["source"])
        elif p["ref"]=="U28":
            next(x for x in p["pins"] if x["number"]=="1")["net"]="RUN_BUFFERED"
    assert len(delta)==8
    for p in [receiver[0],receiver[2]]:
        new=copy.deepcopy(p)
        new.update(x=1333.5 if p["ref"]=="U43" else 1410.0,y=2743.2)
        e28.append(new)
    assert len(e28)==271 and len({p["ref"] for p in e28})==271
    (ROOT / "e28-components-proposed.json").write_text(json.dumps(e28,indent=2)+"\n")
    (ROOT / "integration-proposal.json").write_text(json.dumps(dict(
        parent_source_sha256=captured, parent_E28_PCB_sha256=sha(E28/"rail_disconnect.kicad_pcb"),
        source_cell_proposed_P03_refs={"U1":"U201","U2":"U202","R1":"R401","R2":"R402","R4":"R403","C1":"C401","C2":"C402","C3":"C403"},
        existing_P03_J106_3=dict(old="POWER_RUN",new="POWER_RUN_E28_LEAF"),
        source_native_signal_polarity="ActiveHIGH; ground short and open wire requestOFF", original_R113_and_PG_unchanged=True,
        E28_value_only_DCU_changes=delta,E28_R93_old="10k1%",E28_R93_new="200k complete1% receiving",
        E28_U28_1_old="POWER_RUN",E28_U28_1_new="RUN_BUFFERED",E28_added_refs=["U43","C86"],
        no_LDO_voltage_or_pool_increase=True, original_sources_written=False, PCB_adopted=False,
        physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    (ROOT / "generated").mkdir(exist_ok=False)
    print("Generated actual AX03 source and receiver cells;271-part E28 proposal; original sources unchanged")


if __name__=="__main__":
    main()
