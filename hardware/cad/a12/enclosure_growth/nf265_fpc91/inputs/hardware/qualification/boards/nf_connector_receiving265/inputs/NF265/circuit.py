"""NF05R265: UV participates in retained-ARM fault logic; defined LED MID paths.

Fresh private successor, never a mutation of the sealed NF05H261 checkpoint.
"""

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def components():
    for name, digest in json.loads((ROOT / "sources/manifest.json").read_text()).items():
        assert hashlib.sha256((ROOT / "sources" / name).read_bytes()).hexdigest() == digest, name
    parts = copy.deepcopy(json.loads((ROOT / "sources/parent261/components.json").read_text()))
    by = {c["ref"]: c for c in parts}
    changes = []

    def pin(ref, n, net, name=None, kind=None):
        p = next(p for p in by[ref]["pins"] if p["number"] == str(n))
        old = copy.deepcopy(p)
        p["net"] = net
        if name:
            p["name"] = name
        if kind:
            p["kind"] = kind
            p["side"] = "R" if kind == "output" else "L"
        changes.append(dict(ref=ref, pin=str(n), old=old, new=copy.deepcopy(p)))

    # This does NOT reset ARM from SAFE/UV. The old source-safe producer is
    # retained; its former net is now supplied by an actual spare AND gate.
    pin("U42", 11, "N19_SAFE_SOURCE")
    pin("U51", 12, "N19_SAFE_SOURCE")
    pin("U51", 13, "ABS_AUX_READY")
    pin("U51", 11, "N19_SAFE", kind="output")
    pin("U48", 13, "ABS_AUX_FAULT")
    pin("U48", 12, "ABS_AUX_READY", kind="output")
    # Legacy RESET_REQUEST had no implemented reset effect. It becomes a
    # monitor OUTPUT only; no old host/reset switch may drive this contact.
    pin("J1", 7, "ABS_AUX_FAULT", "ABS_AUX_FAULT_MONITOR_OUTPUT_ONLY")
    pin("R17", 1, "ABS_AUX_FAULT")
    for ref, rail in [("R5", "N19"), ("R12", "N12")]:
        pin(ref, 2, rail + "_CLAMP_LED_MID")
        by[ref]["part"] = "10000ohm 0.1% TNPW080510K0BEEA - COMPLETE3% RECEIVING"
        by[ref]["source"] = "https://www.vishay.com/docs/28758/tnpw_e3.pdf"
        by[ref]["note"] = (
            "Individual first-LED shunt; added second-LED shunt provides a real MID discharge path."
        )
    for ref in ["R4", "R11"]:
        by[ref]["part"] = "499ohm 0.1% TNPW0805499RBEEA - COMPLETE3% RECEIVING"
    by["R97"]["part"] = "680ohm 0.1% TNPW1206680RBEEA - COMPLETE3% RECEIVING"
    by["C99"]["part"] = "100nF25V C0G5% C1206C104J3GACTU - COMPLETE6% UVRECOVERY RECEIVING"
    by["C99"]["note"] = (
        "Longer independent UV recovery; actual CT discharge, pulse recognition and shared-latch reset priority still require qualification."
    )
    for c in parts:
        c["footprint"] = c["footprint"].replace("NF05H_Manufacturer:", "NF05R_Manufacturer:")
        if c["part"] == "SN74LVC1G17DCKR":
            c["footprint"] = "NF05R_Manufacturer:TI_DCK0005A"

    def add(ref, part, fp, pins, source, note):
        assert ref not in by
        c = dict(
            ref=ref,
            part=part,
            footprint=fp,
            source=source,
            note=note,
            x=78.74 + (len(parts) % 4) * 215.9,
            y=4272.28 + (len(parts) - 261) // 4 * 78.74,
            pins=[
                dict(
                    number=str(n),
                    name=name,
                    net=net,
                    kind=kind,
                    side="R" if kind in ["output", "open_collector"] else "L",
                )
                for n, name, net, kind in pins
            ],
        )
        parts.append(c)
        by[ref] = c

    add(
        "U58",
        "SN74LVC1G14DCKR",
        "NF05R_Manufacturer:TI_DCK0005A",
        [
            (1, "NC", None, "no_connect"),
            (2, "A", "CLAMP_SUPPLY_ENABLE", "input"),
            (3, "GND", "AGND", "power_in"),
            (4, "Y", "ABS_AUX_FAULT", "output"),
            (5, "VCC", "AUX2V6", "power_in"),
        ],
        "https://www.ti.com/lit/ds/symlink/sn74lvc1g14.pdf",
        "5.5V-tolerant Schmitt input accepts the RAW5 open-drain supervisor. AUX output enters existing retained-ARM source-fault cone; no SAFE-derived ARM reset.",
    )
    add(
        "C100",
        "100nF50V X7R10% C0603C104K5RACTU - LOCAL_BYPASS_EFFECTIVE_HOLD",
        "Capacitor_SMD:C_0603_1608Metric",
        [(1, "1", "AUX2V6", "passive"), (2, "2", "AGND", "passive")],
        "https://content.kemet.com/datasheets/KEM_C1002_X7R_SMD.pdf",
        "Actual local bypass for U58; pose/effective capacitance/PDN unaccepted.",
    )
    for ref, rail in [("R98", "N19"), ("R99", "N12")]:
        add(
            ref,
            "10000ohm 0.1% TNPW080510K0BEEA - COMPLETE3% RECEIVING",
            "Resistor_SMD:R_0805_2012Metric",
            [(1, "1", rail + "_CLAMP_LED_MID", "passive"), (2, "2", rail + "_CLAMP_LED_K", "passive")],
            "https://www.vishay.com/docs/28758/tnpw_e3.pdf",
            "Individual second-LED shunt. MID is now resistively connected; this is not an inferred hot optical turn-ON bound.",
        )
    assert len(parts) == 265
    return parts, dict(
        parent_parts=261,
        new_parts=265,
        exact_pin_changes=changes,
        N19_SAFE_requires_independent_absolute_AUX_ready=True,
        ARM_NOT_reset_by_SAFE_or_absolute_AUX=True,
        actual_existing_source_fault="U35.9ARM&U35.10NOT_SAFE ->U35.8 N19_F_SOURCE ->existing shared E28 fault latch",
        shared_E28_fault_and_timing_native_integration_implemented=False,
        original_two_floating_LED_MID_nodes_now_resistively_connected=True,
        physical_qualified=False,
    )
