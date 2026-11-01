"""Independent physical-role checks against the actual native XML export."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from hardware.electronics.common.netlists import netlist

ROOT = Path(__file__).resolve().parent


def physical_TPS3890(path):
    root = ET.parse(path).getroot()
    lib = {(x.get("lib"), x.get("part")): x for x in root.findall("libparts/libpart")}
    errors = []
    count = 0
    for c in root.findall("components/comp"):
        if not c.findtext("value", "").startswith("TPS3890"):
            continue
        count += 1
        k = c.find("libsource")
        ps = {
            p.get("num"): (p.get("name"), p.get("type"))
            for p in lib[(k.get("lib"), k.get("part"))].findall("pins/pin")
        }
        expected = {
            "1": ("SENSE", "input"),
            "2": ("GND", "power_in"),
            "3": ("MR", "input"),
            "4": ("VDD", "power_in"),
            "5": ("CT", "input"),
            "6": ("RESET", "open_collector"),
        }
        for n, (name, kind) in expected.items():
            actual = ps.get(n, ("", ""))
            if not actual[0].startswith(name) or actual[1] != kind:
                errors.append(dict(ref=c.get("ref"), pin=n, expected=[name, kind], actual=actual))
    return count, errors


def validate(pins):
    required = {
        "U4": {"5": "AUX2V6", "4": "N19_CLAMP_LED_K", "2": "N19_CLAMPS_RELEASE"},
        "U10": {"5": "AUX2V6", "4": "N12_CLAMP_LED_K", "2": "N12_CLAMPS_RELEASE"},
        "C3": {"1": "AUX2V6"},
        "C12": {"1": "AUX2V6"},
        "U13": {
            "1": "N19_OUT_INV",
            "2": "N19_OUT_SUM",
            "4": "AGND",
            "6": "N12_OUT_SUM",
            "7": "N12_OUT_INV",
            "8": "AUX2V6",
        },
        "R23": {"1": "N19_PROTECTED", "2": "N19_OUT_SUM"},
        "R24": {"1": "N19_OUT_INV", "2": "N19_OUT_SUM"},
        "R40": {"1": "N12_PROTECTED", "2": "N12_OUT_SUM"},
        "R41": {"1": "N12_OUT_INV", "2": "N12_OUT_SUM"},
        "R4": {"1": "CLAMP_LED_SUPPLY"},
        "R11": {"1": "CLAMP_LED_SUPPLY"},
        "U56": {
            "1": "ABS_AUX_SENSE",
            "2": "AGND",
            "3": "DIG5_FORCE",
            "4": "DIG5_FORCE",
            "5": "ABS_AUX_CT",
            "6": "CLAMP_SUPPLY_ENABLE",
        },
        "U57": {"1": "DIG5_FORCE", "2": "AGND", "3": "CLAMP_SUPPLY_ENABLE", "6": "CLAMP_LED_SUPPLY"},
        "R92": {"1": "AUX2V6", "2": "ABS_AUX_TOP_TRIM"},
        "R93": {"1": "ABS_AUX_TOP_TRIM", "2": "ABS_AUX_SENSE"},
        "R94": {"1": "ABS_AUX_SENSE", "2": "AGND"},
        "R95": {"1": "DIG5_FORCE", "2": "CLAMP_SUPPLY_ENABLE"},
        "R96": {"1": "CLAMP_SUPPLY_ENABLE", "2": "AGND"},
        "R97": {"1": "CLAMP_LED_SUPPLY", "2": "AGND"},
        "C98": {"1": "CLAMP_LED_SUPPLY", "2": "AGND"},
        "J6": {"1": "GUARDED_12V_FORCE", "2": "MODULE_INPUT_GND"},
        "U17": {"1": "MODULE_INPUT_GND"},
        "U22": {"1": "MODULE_INPUT_GND"},
        "C4": {"2": "MODULE_INPUT_GND"},
        "C31": {"2": "MODULE_INPUT_GND"},
        "U52": {"4": "AUX2V6", "6": "N19_START_DELAY_N"},
        "U54": {"4": "AUX2V6", "6": "N12_START_DELAY_N"},
    }
    errors = []
    for ref, ps in required.items():
        for n, want in ps.items():
            if pins.get(ref, {}).get(n) != want:
                errors.append((ref, n, want, pins.get(ref, {}).get(n)))
    for rail, owner, rref, jpin, sink in [
        ("N19", "U32", "R3", "22", "U4"),
        ("N12", "U33", "R10", "28", "U10"),
    ]:
        actual = {(r, p) for r, ps in pins.items() for p, n in ps.items() if n == rail + "_CLAMPS_RELEASE"}
        expected = {(owner, "4"), (rref, "1"), ("J1", jpin), (sink, "2")}
        if actual != expected:
            errors.append(("CLAMPS_RELEASE_load_members", rail, sorted(actual)))
    # Explicit PCB-ground cut: the only module-return electrodes are the real
    # primary input pins/caps plus the separate receiving connector.
    members = {(r, p) for r, ps in pins.items() for p, n in ps.items() if n == "MODULE_INPUT_GND"}
    if members != {("U17", "1"), ("U22", "1"), ("C4", "2"), ("C31", "2"), ("J6", "2")}:
        errors.append(("MODULE_INPUT_GND_members", sorted(members)))
    return errors


def main():
    actual, pins = netlist(ROOT / "generated/netlist.xml")
    assert len(actual) == 261
    count, errors = physical_TPS3890(ROOT / "generated/netlist.xml")
    assert count == 7 and not errors, (count, errors)
    assert not validate(pins), validate(pins)
    assert pins["J1"]["4"].startswith("unconnected-")
    assert pins["U57"]["4"].startswith("unconnected-") and pins["U57"]["5"].startswith("unconnected-")
    old = json.loads((ROOT / "sources/sequence249/components.json").read_text())
    new = json.loads((ROOT / "components.json").read_text())
    by = {c["ref"]: c for c in new}
    changed = {}
    for c in old:
        ref = c["ref"]
        diff = {
            k: dict(old=c.get(k), new=by[ref].get(k))
            for k in c.keys() | by[ref].keys()
            if c.get(k) != by[ref].get(k)
        }
        if diff:
            changed[ref] = diff
    allowed = {
        "U4",
        "U10",
        "C3",
        "C12",
        "R3",
        "R10",
        "R4",
        "R11",
        "U17",
        "U22",
        "C4",
        "C31",
        "J1",
        "U52",
        "U54",
        "U1",
        "U2",
        "U7",
        "U8",
        "U16",
        "U27",
        "U29",
        "U31",
        "U32",
        "U33",
        "U34",
        "U49",
    }
    assert set(changed) == allowed, set(changed) ^ allowed
    return dict(
        parent249_count=len(old),
        new_count=len(new),
        original_unchanged_component_count=249 - len(changed),
        exact_changed_components=changed,
        physical_TPS3890_count=count,
        native_primary_pin_role_differences=errors,
        old249_swapped_START_timer_rejected=physical_TPS3890(
            ROOT / "sources/sequence249/generated/netlist.xml"
        )[1],
        no_PCB_implemented=True,
        physical_qualified=False,
    )


if __name__ == "__main__":
    assert not (ROOT / "handoff.json").exists(), "Preserve sealed native comparison"
    (ROOT / "generated/equivalence.json").write_text(json.dumps(main(), indent=2) + "\n")
    print("261 native components, seven physical supervisor maps, exact parent delta checked")
