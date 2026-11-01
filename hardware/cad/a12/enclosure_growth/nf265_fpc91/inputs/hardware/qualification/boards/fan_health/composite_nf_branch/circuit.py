"""FPC_M2: actual third protected RAW5 leaf; no parent circuit/pose mutations."""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def components():
    parts = copy.deepcopy(json.loads((ROOT / "sources/M1/components.json").read_text()))
    assert len(parts) == 84

    def add(ref, part, alias, pins, note, source):
        k = len(parts)
        parts.append(
            dict(
                ref=ref,
                part=part,
                footprint="FPC01:" + alias,
                pins=[
                    dict(
                        number=str(n),
                        name=name,
                        net=net,
                        kind=kind,
                        side="R" if kind in ["output", "open_collector", "power_out"] else "L",
                    )
                    for n, name, net, kind in pins
                ],
                x=55.88 + 137.16 * (k % 5),
                y=71.12 + 111.76 * (k // 5),
                source=source,
                note=note,
                parent="NEW_FPC_M2",
                parent_ref=None,
            )
        )

    ti = "https://www.ti.com/lit/ds/symlink/tps2553.pdf"
    add(
        "U401",
        "TPS2553DBVR-1",
        "TI_DBV0006A",
        [
            (1, "IN", "FAN5V_IN", "power_in"),
            (2, "GND", "GND", "power_in"),
            (3, "EN", "FAN5V_IN", "input"),
            (4, "FAULT_N", None, "open_collector"),
            (5, "ILIM", "NF_RAW5_ILIM", "output"),
            (6, "OUT", "NF_RAW5", "power_out"),
        ],
        "New always-on protected NF control leaf, independent of E28 MASTER. FAULT explicitNC. Source-cycle rearm/thermal retry/partial-power remain held.",
        ti,
    )
    add(
        "R401",
        "220k 0.1%25ppm TNPW0805220KBEEA - COMPLETE1% RECEIVING",
        "Resistor_SMD__R_0805_2012Metric",
        [(1, "1", "NF_RAW5_ILIM", "passive"), (2, "2", "GND", "passive")],
        "Actual complete220k±1% lies217.8..222.2k inside15..232k primary region. Short Kelvin ILIM/GND loop required.",
        "https://www.vishay.com/docs/28758/tnpw_e3.pdf",
    )
    for ref, net in [("C401", "FAN5V_IN"), ("C402", "FAN5V_IN"), ("C403", "NF_RAW5"), ("C404", "NF_RAW5")]:
        add(
            ref,
            "100nF50V X7R10% C0603C104K5RACTU - EFFECTIVE60nF_MIN_RECEIVING",
            "Capacitor_SMD__C_0603_1608Metric",
            [(1, "1", net, "passive"), (2, "2", "GND", "passive")],
            "Two actual local parallel bypasses perIN/OUT. Perpart effective60nF minimum receiving; initial/T/dcbias/life/process not accepted. Rearbody.95max primary +.10seat=1.05 nominal receiving projection; completeheight1.2 requirement remains.",
            "https://search.kemet.com/component-documentation/download/specsheet/C0603C104K5RACTU",
        )
    add(
        "J401",
        "JST B2B-PH-K-S / PHR-2 / SPH-002T-P0.5S",
        "Connector_JST__JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
        [(1, "NF_RAW5", "NF_RAW5", "passive"), (2, "GND", "GND", "passive")],
        "NEW protected control output toNFJ1.3/quietAGNDJ1.2. CandidateAlpha3049AWG26; actualcrimp/solderstrain/contact/harness/clearance unaccepted. NotJ6moduleprimary and notnegativeforce supply.",
        "https://www.jst.com/wp-content/uploads/2021/01/ePH.pdf",
    )
    assert len(parts) == 91
    return parts
