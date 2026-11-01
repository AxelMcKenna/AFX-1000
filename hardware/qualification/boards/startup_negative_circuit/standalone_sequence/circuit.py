"""NF05S: actual standalone sequential ARM latches and independent START delays.

Exact frozen NF04R parent, no edits to parent/live PCB. Physical states remain
unqualified. All native maps are full physical-pin maps, including relay NC3.
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
    parent = json.loads((ROOT / "sources/parent/components.json").read_text())
    parts = copy.deepcopy(parent)
    by = {c["ref"]: c for c in parts}
    changes = []

    def update(ref, pmap):
        for pin in by[ref]["pins"]:
            if pin["number"] in pmap:
                old = pin["net"]
                pin["net"] = pmap[pin["number"]]
                changes.append(dict(ref=ref, pin=pin["number"], old=old, new=pin["net"]))

    def replace_arm(ref, rail):
        c = by[ref]
        c["part"] = "SN74LVC1G17DCKR"
        c["footprint"] = "Package_TO_SOT_SMD:SOT-353_SC-70-5"
        c["source"] = TI + "sn74lvc1g17.pdf"
        c["pins"] = [
            dict(number=str(n), name=name, net=net, kind=kind, side="R" if kind == "output" else "L")
            for n, name, net, kind in [
                (1, "NC", None, "no_connect"),
                (2, "A", rail + "_ARM_Q", "input"),
                (3, "GND", "AGND", "power_in"),
                (4, "Y", rail + "_ARM_CONDITIONED", "output"),
                (5, "VCC", "AUX2V6", "power_in"),
            ]
        ]
        c["note"] = (
            "Replaces old external ARM conditioner with actual strong Schmitt driver from retained local ARM state. No external ARM driver allowed."
        )

    replace_arm("U28", "N19")
    replace_arm("U30", "N12")
    # The four former host-command pins are now local outputs/monitor contacts.
    for c in parts:
        for p in c["pins"]:
            if p["net"] in ["N19_ARM", "N12_ARM"]:
                p["net"] += "_CONDITIONED"
            if c["ref"] == "J1" and p["number"] in ["18", "19", "24", "25"]:
                p["name"] += "_MONITOR_OUTPUT_ONLY"
    update("U35", {"4": "GLOBAL_VALID", "12": "GLOBAL_VALID"})
    update("U38", {"12": "N12_STAGE_ENABLED"})
    update("U39", {"4": "N12_STAGE_ENABLED"})
    update("U48", {"11": "GLOBAL_VALID", "10": "NOT_GLOBAL_VALID"})
    p = next(p for p in by["U48"]["pins"] if p["number"] == "10")
    p["kind"] = "output"
    p["side"] = "R"
    # Actual physical metal lead3 has no electrical function, but must exist in
    # the native symbol/PCB pad map. Parent omitted it from four relay symbols.
    physical_nc = []
    for c in parts:
        if c["part"].startswith("TLP4590"):
            assert "3" not in {p["number"] for p in c["pins"]}
            c["pins"].append(dict(number="3", name="PHYSICAL_NC", net=None, kind="no_connect", side="L"))
            physical_nc.append(c["ref"])
    assert len(physical_nc) == 4
    feed = []
    for c in parts:
        if c["part"].startswith("392ohm"):
            c["part"] = "402ohm 1% CRCW2010402RFKEF - COMPLETE3% RECEIVING"
            c["source"] = "https://www.vishay.com/docs/20035/dcrcwe3.pdf"
            feed.append(c["ref"])
    assert len(feed) == 4
    actual_DCU_land_changes = []
    for c in parts:
        if c["part"] in ["SN74AUP1G74DCUR", "SN74LVC2T45DCUR"]:
            c["footprint"] = "NF05S_Manufacturer:TI_DCU0008A"
            actual_DCU_land_changes.append(c["ref"])
    assert len(actual_DCU_land_changes) == 6
    watchdog_cap_changes = []
    for ref, value, mpn, height in [
        ("C1", "56nF", "C1206C563J5GACTU", 1.35),
        ("C2", "33nF", "C1206C333J5GACTU", 1.0),
    ]:
        c = by[ref]
        c["part"] = value + "50V C0G5% " + mpn + " - COMPLETE10% RECEIVING"
        c["footprint"] = "Capacitor_SMD:C_1206_3216Metric"
        c["source"] = "https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf"
        watchdog_cap_changes.append(
            dict(
                ref=ref,
                part=mpn,
                old_package="0805-generic-unselected",
                new_package="1206",
                body_max_mm=height,
                physical_accepted=False,
            )
        )

    def add(prefix, part, fp, pins, source, note=""):
        ref = prefix + str(
            max([int(c["ref"][len(prefix) :]) for c in parts if c["ref"].startswith(prefix)] + [0]) + 1
        )
        ps = [
            dict(
                number=str(n),
                name=name,
                net=net,
                kind=kind,
                side="R" if kind in ["output", "open_collector"] else "L",
            )
            for n, name, net, kind in pins
        ]
        c = dict(
            ref=ref,
            part=part,
            footprint=fp,
            pins=ps,
            source=source,
            note=note,
            x=78.74 + (len(parts) % 4) * 215.9,
            y=3454.4 + (len(parts) - 233) // 4 * 78.74,
        )
        parts.append(c)
        return ref

    def ic(part, fp, pmap, power=(), outputs=(), oc=(), nc=(), source=None, note=""):
        return add(
            "U",
            part,
            fp,
            [
                (
                    n,
                    name,
                    net,
                    "no_connect"
                    if n in nc
                    else "power_in"
                    if n in power
                    else "output"
                    if n in outputs
                    else "open_collector"
                    if n in oc
                    else "input",
                )
                for n, (name, net) in pmap.items()
            ],
            source or TI + part.split("PWR")[0].split("DCKR")[0].lower() + ".pdf",
            note,
        )

    def bypass(owner):
        return add(
            "C",
            "100nF50V X7R10% C0603C104K5RACTU - EFFECTIVE/PDN HOLD",
            "Capacitor_SMD:C_0603_1608Metric",
            [(1, "1", "AUX2V6", "passive"), (2, "2", "AGND", "passive")],
            "https://content.kemet.com/datasheets/KEM_C1002_X7R_SMD.pdf",
            "Local same-face bypass for " + owner,
        )

    u = ic(
        "SN74HCS02PWR",
        "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
        {
            1: ("1Y", "N19_ARM_Q"),
            2: ("1A", "NOT_GLOBAL_VALID"),
            3: ("1B", "N19_ARM_QBAR"),
            4: ("2Y", "N19_ARM_QBAR"),
            5: ("2A", "N19_ARM_SET"),
            6: ("2B", "N19_ARM_Q"),
            7: ("GND", "AGND"),
            8: ("3A", "NOT_GLOBAL_VALID"),
            9: ("3B", "N12_ARM_QBAR"),
            10: ("3Y", "N12_ARM_Q"),
            11: ("4A", "N12_ARM_SET"),
            12: ("4B", "N12_ARM_Q"),
            13: ("4Y", "N12_ARM_QBAR"),
            14: ("VCC", "AUX2V6"),
        },
        power=(7, 14),
        outputs=(1, 4, 10, 13),
        source=TI + "sn74hcs02.pdf",
        note="Two real SR ARM states, held until GLOBAL-OFF; SAFE falling does not clear ARM and hide source fault.",
    )
    bypass(u)
    u = ic(
        "SN74HCS08PWR",
        "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
        {
            1: ("1A", "GLOBAL_VALID"),
            2: ("1B", "N19_PERMIT_D"),
            3: ("1Y", "N19_ARM_SET"),
            4: ("2A", "GLOBAL_VALID"),
            5: ("2B", "N19_OUTPUT_QUALIFIED"),
            6: ("2Y", "N12_STAGE_ENABLED"),
            7: ("GND", "AGND"),
            9: ("3A", "N12_STAGE_ENABLED"),
            10: ("3B", "N12_PERMIT_D"),
            8: ("3Y", "N12_ARM_SET"),
            12: ("4A", "AGND"),
            13: ("4B", "AGND"),
            11: ("4Y", None),
            14: ("VCC", "AUX2V6"),
        },
        power=(7, 14),
        outputs=(3, 6, 8),
        nc=(11,),
        source=TI + "sn74hcs08.pdf",
        note="PERMIT_D already contains watchdog-armed/WDO/SAFE/NOFAULT; stage12 cannot arm before true stage19 protected-output completion.",
    )
    bypass(u)
    newtimers = {}
    newdrivers = {}
    for rail in ["N19", "N12"]:
        timer = ic(
            "TPS389001DSET",
            "Package_SON:WSON-6_1.5x1.5mm_P0.5mm",
            {
                1: ("SENSE", rail + "_ARM_CONDITIONED"),
                2: ("GND", "AGND"),
                3: ("MR", "AUX2V6"),
                4: ("RESET_N", rail + "_START_DELAY_N"),
                5: ("CT", rail + "_START_CT"),
                6: ("VDD", "AUX2V6"),
            },
            power=(2, 6),
            oc=(4,),
            source=TI + "tps3890.pdf",
            note="START delay only after retained source-safe/watchdog-ready ARM. CT discharge/reset timings retain explicit receiving requirements.",
        )
        bypass(timer)
        add(
            "C",
            "47nF50V C0G5% C1206C473J5GACTU - COMPLETE6% RECEIVING",
            "Capacitor_SMD:C_1206_3216Metric",
            [(1, "1", rail + "_START_CT", "passive"), (2, "2", "AGND", "passive")],
            "https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf",
        )
        add(
            "R",
            "10k0.1% TNPW080510K0BEEA - COMPLETE3% RECEIVING",
            "Resistor_SMD:R_0805_2012Metric",
            [(1, "1", "AUX2V6", "passive"), (2, "2", rail + "_START_DELAY_N", "passive")],
            "https://www.vishay.com/docs/28758/tnpw_e3.pdf",
        )
        driver = ic(
            "SN74LVC1G17DCKR",
            "Package_TO_SOT_SMD:SOT-353_SC-70-5",
            {
                1: ("NC", None),
                2: ("A", rail + "_START_DELAY_N"),
                3: ("GND", "AGND"),
                4: ("Y", rail + "_START"),
                5: ("VCC", "AUX2V6"),
            },
            power=(3, 5),
            outputs=(4,),
            nc=(1,),
            source=TI + "sn74lvc1g17.pdf",
            note="Strong Schmitt output drives existing47k START pulldown and AUP conditioning cell; no external source on monitor output.",
        )
        bypass(driver)
        newtimers[rail] = timer
        newdrivers[rail] = driver
    assert len(parts) == 249, len(parts)
    return parts, dict(
        parent_part_count=233,
        actual_DCU_land_pattern_changes=actual_DCU_land_changes,
        new_part_count=249,
        new_ICs=[c["ref"] for c in parts if c["ref"].startswith("U") and int(c["ref"][1:]) >= 50],
        new_start_timers=newtimers,
        new_start_drivers=newdrivers,
        exact_existing_pin_changes=changes,
        replaced_ARM_conditioners=["U28", "U30"],
        four_physical_relay_NC3_additions=physical_nc,
        feed_resistor_402_changes=feed,
        watchdog_timing_cap_actual_part_changes=watchdog_cap_changes,
        unused_RESET_REQUEST_parent_pin7_not_misrepresented_as_active_reset=True,
        physical_qualified=False,
    )
