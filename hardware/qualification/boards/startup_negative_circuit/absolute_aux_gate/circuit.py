"""NF05H: independent RAW5 UV gating of the physical NC-clamp LED supply.

The logic supply itself is not credited for behavior below its operating range.
This is a new prototype successor; all sealed parents remain immutable.
"""

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TI = "https://www.ti.com/lit/ds/symlink/"


def components():
    for name, digest in json.loads((ROOT / "sources/manifest.json").read_text()).items():
        assert hashlib.sha256((ROOT / "sources" / name).read_bytes()).hexdigest() == digest, name
    parts = copy.deepcopy(json.loads((ROOT / "sources/sequence249/components.json").read_text()))
    by = {c["ref"]: c for c in parts}
    changes = []
    physical_pin_erratum = []
    for c in parts:
        if c["part"].startswith("TPS3890"):
            old = {v["number"]: (v["name"], v["net"]) for v in c["pins"]}
            if old["4"][0] == "VDD":
                assert "RESET" in old["6"][0]
                continue
            assert "RESET" in old["4"][0] and old["6"][0] == "VDD"
            for v in c["pins"]:
                if v["number"] == "4":
                    v["number"] = "6"
                elif v["number"] == "6":
                    v["number"] = "4"
            physical_pin_erratum.append(
                dict(
                    ref=c["ref"],
                    old_pin4=old["4"],
                    old_pin6=old["6"],
                    corrected_pin4=old["6"],
                    corrected_pin6=old["4"],
                )
            )
    assert len(physical_pin_erratum) == 2

    def change(ref, pin, net):
        p = next(p for p in by[ref]["pins"] if p["number"] == str(pin))
        changes.append(dict(ref=ref, pin=str(pin), old=p["net"], new=net))
        p["net"] = net

    # The ONLY clamp LED forward-energy source is the new independently gated
    # rail. The original two series LED strings and 10k shunts remain intact.
    for ref in ["R4", "R11"]:
        assert by[ref]["pins"][0]["net"] == "DIG5_FORCE"
        change(ref, 1, "CLAMP_LED_SUPPLY")
    # Actual RevAB LVC1G06 RAW5 VIH=0.7*VCC cannot be reached by AUX
    # logic. Power both open-drain sinks and their local bypasses from AUX;
    # output tolerates 5.5V independently. Independent RAW5 gate masks partial
    # AUX corruption; no unpowered-Ioff to partial-power transfer is claimed.
    for ref in ["U4", "U10"]:
        change(ref, 5, "AUX2V6")
        by[ref]["note"] = (
            "AUX-powered sink: actual input VIH1.7 over2.3..2.7V; 5.5V-tolerant OD output. Full powered leakage remains receiving."
        )
    for ref in ["C3", "C12"]:
        change(ref, 1, "AUX2V6")
    for ref in ["R3", "R10"]:
        by[ref]["part"] = "205000ohm 0.1% TNPW0805205KBEEA - COMPLETE3% RECEIVING"
        by[ref]["source"] = "https://www.vishay.com/docs/28758/tnpw_e3.pdf"
    for ref in ["R4", "R11"]:
        by[ref]["part"] = "402ohm 0.1% TNPW0805402RBEEA - COMPLETE3% RECEIVING"
        by[ref]["source"] = "https://www.vishay.com/docs/28758/tnpw_e3.pdf"
    # Separate the primary burst return from all NF quiet/control ground. It is
    # returned at the operating source through the new keyed receiving port;
    # it is never copper-joined to AGND on this module.
    for ref, pin in [("U17", 1), ("U22", 1), ("C4", 2), ("C31", 2)]:
        change(ref, pin, "MODULE_INPUT_GND")
    change("J1", 4, None)
    jpin = next(p for p in by["J1"]["pins"] if p["number"] == "4")
    jpin.update(name="FORMER_MODULE_FORCE_PIN_NC", kind="no_connect")
    for c in parts:
        if c["footprint"] == "NF05S_Manufacturer:TI_DCU0008A":
            c["footprint"] = "NF05H_Manufacturer:TI_DCU0008A"
        if c["part"] == "SN74AUP2G14DCKR":
            c["footprint"] = "NF05H_Manufacturer:TI_DCK0006A"

    def add(prefix, part, fp, pins, source, note=""):
        ref = prefix + str(
            max([int(c["ref"][len(prefix) :]) for c in parts if c["ref"].startswith(prefix)] + [0]) + 1
        )
        parts.append(
            dict(
                ref=ref,
                part=part,
                footprint=fp,
                source=source,
                note=note,
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
                x=78.74 + (len(parts) % 4) * 215.9,
                y=3962.4 + (len(parts) - 249) // 4 * 78.74,
            )
        )
        return ref

    u = add(
        "U",
        "TPS389001DSET",
        "Package_SON:WSON-6_1.5x1.5mm_P0.5mm",
        [
            (1, "SENSE", "ABS_AUX_SENSE", "input"),
            (2, "GND", "AGND", "power_in"),
            (3, "MR", "DIG5_FORCE", "input"),
            (6, "RESET_N", "CLAMP_SUPPLY_ENABLE", "open_collector"),
            (5, "CT", "ABS_AUX_CT", "input"),
            (4, "VDD", "DIG5_FORCE", "power_in"),
        ],
        TI + "tps3890.pdf",
        "Independent RAW5-powered absolute AUX UV supervisor; not driven by partly powered AUX logic. OV is a separate hold.",
    )
    sw = add(
        "U",
        "TPS22919DCKR",
        "NF05H_Manufacturer:TI_DCK0006A",
        [
            (1, "IN", "DIG5_FORCE", "power_in"),
            (2, "GND", "AGND", "power_in"),
            (3, "ON", "CLAMP_SUPPLY_ENABLE", "input"),
            (4, "NC", None, "no_connect"),
            (5, "QOD", None, "no_connect"),
            (6, "VOUT", "CLAMP_LED_SUPPLY", "passive"),
        ],
        TI + "tps22919.pdf",
        "QOD intentionally unused: external 240ohm discharge alone is modeled. Typical tOFF/QOD are not maximums. Output reverse current unqualified.",
    )
    resistors = {}
    for name, value, mpn, a, b in [
        ("UV_TOP", 11300, "TNPU080511K3HWEN00", "AUX2V6", "ABS_AUX_TOP_TRIM"),
        ("UV_TRIM", 49.9, "TNPW080549R9BEEA", "ABS_AUX_TOP_TRIM", "ABS_AUX_SENSE"),
        ("UV_BOTTOM", 10000, "TNPU080510K0HWEN00", "ABS_AUX_SENSE", "AGND"),
        ("EN_PULLUP", 10000, "TNPW080510K0BEEA", "DIG5_FORCE", "CLAMP_SUPPLY_ENABLE"),
        ("EN_PULLDOWN", 47000, "TNPW080547K0BEEA", "CLAMP_SUPPLY_ENABLE", "AGND"),
        ("LED_RAIL_BLEED", 240, "TNPW1206240RBEEA", "CLAMP_LED_SUPPLY", "AGND"),
    ]:
        resistors[name] = add(
            "R",
            f"{value:g}ohm "
            + ("0.02% 2ppm " if name in ["UV_TOP", "UV_BOTTOM"] else "0.1% ")
            + f"{mpn} - "
            + (
                "COMPLETE0.7% TRIM RECEIVING"
                if name == "UV_TRIM"
                else "COMPLETE0.35% RECEIVING"
                if name in ["UV_TOP", "UV_BOTTOM"]
                else "COMPLETE3% RECEIVING"
            ),
            (
                "Resistor_SMD:R_1206_3216Metric"
                if name == "LED_RAIL_BLEED"
                else "Resistor_SMD:R_0805_2012Metric"
            ),
            [(1, "1", a, "passive"), (2, "2", b, "passive")],
            (
                "https://www.vishay.com/docs/28779/tnpu_e3.pdf"
                if name in ["UV_TOP", "UV_BOTTOM"]
                else "https://www.vishay.com/docs/28758/tnpw_e3.pdf"
            ),
            name,
        )
    caps = {}
    for name, value, mpn, a, b in [
        ("SUPERVISOR_INPUT", "100nF25V", "C1206C104J3GACTU", "DIG5_FORCE", "AGND"),
        ("GATED_LED_RAIL", "100nF25V", "C1206C104J3GACTU", "CLAMP_LED_SUPPLY", "AGND"),
        ("UV_RECOVERY_DELAY", "47nF50V", "C1206C473J5GACTU", "ABS_AUX_CT", "AGND"),
    ]:
        caps[name] = add(
            "C",
            value + " C0G5% " + mpn + " - COMPLETE6% CT / TOTAL0.22uF LEDRAIL RECEIVING",
            "Capacitor_SMD:C_1206_3216Metric",
            [(1, "1", a, "passive"), (2, "2", b, "passive")],
            "https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf",
            name,
        )
    j = add(
        "J",
        "NEW MODULE INPUT ONLY - keyed JST XH2 receiving candidate; hot/assembly UNACCEPTED",
        "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
        [
            (1, "GUARDED12", "GUARDED_12V_FORCE", "passive"),
            (2, "MODULE_RETURN", "MODULE_INPUT_GND", "passive"),
        ],
        "https://www.jst-mfg.com/product/pdf/eng/eXH.pdf",
        "Separate primary-current return to P03 operating ground; no board tie to AGND; exact wire/mate/process to be selected.",
    )
    assert len(parts) == 261, len(parts)
    return parts, dict(
        parent="NF05S249",
        parent_part_count=249,
        new_part_count=len(parts),
        exact_pin_changes=changes,
        primary_TPS3890_pin4_VDD_pin6_RESET_erratum=physical_pin_erratum,
        UV_supervisor=u,
        LED_supply_switch=sw,
        resistors=resistors,
        caps=caps,
        module_input_connector=j,
        shared_LED_anodes_gated=True,
        QOD_credited=False,
        AUX_OV_hardgate_implemented=False,
        physical_qualified=False,
    )
