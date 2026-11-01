"""Independent exported-native role, exact parent delta, and actual fault-cone review."""

import copy
import itertools
import json
import xml.etree.ElementTree as ET

from hardware.electronics.common.netlists import netlist

from .analyze import ROOT, sha


def primary_pin_roles(path):
    tree = ET.parse(path).getroot()
    libs = {(c.get("lib"), c.get("part")): c for c in tree.findall("libparts/libpart")}
    errors = []
    count = 0
    for c in tree.findall("components/comp"):
        if not c.findtext("value", "").startswith("TPS3890"):
            continue
        count += 1
        source = c.find("libsource")
        pins = {
            p.get("num"): (p.get("name"), p.get("type"))
            for p in libs[(source.get("lib"), source.get("part"))].findall("pins/pin")
        }
        expect = {
            "1": ("SENSE", "input"),
            "2": ("GND", "power_in"),
            "3": ("MR", "input"),
            "4": ("VDD", "power_in"),
            "5": ("CT", "input"),
            "6": ("RESET", "open_collector"),
        }
        for n, (name, kind) in expect.items():
            got = pins.get(n, ("", ""))
            if not got[0].startswith(name) or got[1] != kind:
                errors.append((c.get("ref"), n, name, kind, got))
    return count, errors


def validate(p):
    required = {
        "U58": {"2": "CLAMP_SUPPLY_ENABLE", "3": "AGND", "4": "ABS_AUX_FAULT", "5": "AUX2V6"},
        "C100": {"1": "AUX2V6", "2": "AGND"},
        "U56": {
            "1": "ABS_AUX_SENSE",
            "2": "AGND",
            "3": "DIG5_FORCE",
            "4": "DIG5_FORCE",
            "5": "ABS_AUX_CT",
            "6": "CLAMP_SUPPLY_ENABLE",
        },
        "U57": {"1": "DIG5_FORCE", "2": "AGND", "3": "CLAMP_SUPPLY_ENABLE", "6": "CLAMP_LED_SUPPLY"},
        "U42": {"11": "N19_SAFE_SOURCE"},
        "U48": {"11": "GLOBAL_VALID", "10": "NOT_GLOBAL_VALID", "13": "ABS_AUX_FAULT", "12": "ABS_AUX_READY"},
        "U51": {
            "1": "GLOBAL_VALID",
            "2": "N19_PERMIT_D",
            "3": "N19_ARM_SET",
            "4": "GLOBAL_VALID",
            "5": "N19_OUTPUT_QUALIFIED",
            "6": "N12_STAGE_ENABLED",
            "9": "N12_STAGE_ENABLED",
            "10": "N12_PERMIT_D",
            "8": "N12_ARM_SET",
            "12": "N19_SAFE_SOURCE",
            "13": "ABS_AUX_READY",
            "11": "N19_SAFE",
        },
        "U50": {
            "1": "N19_ARM_Q",
            "2": "NOT_GLOBAL_VALID",
            "3": "N19_ARM_QBAR",
            "4": "N19_ARM_QBAR",
            "5": "N19_ARM_SET",
            "6": "N19_ARM_Q",
            "8": "NOT_GLOBAL_VALID",
            "9": "N12_ARM_QBAR",
            "10": "N12_ARM_Q",
            "11": "N12_ARM_SET",
            "12": "N12_ARM_Q",
            "13": "N12_ARM_QBAR",
        },
        "U47": {"1": "N19_SAFE", "2": "N19_NOT_SAFE"},
        "U35": {
            "4": "GLOBAL_VALID",
            "5": "GLOBAL_VALID",
            "6": "N19_WD_ENABLE",
            "9": "N19_ARM_CONDITIONED",
            "10": "N19_NOT_SAFE",
            "8": "N19_F_SOURCE",
        },
        "U45": {
            "1": "N19_F_SOURCE",
            "2": "N19_F_TIMEOUT",
            "3": "N19_F0",
            "4": "N19_F0",
            "5": "N19_F_OUTPUT",
            "6": "N19_FAULT_REQUEST",
        },
        "U46": {
            "1": "N19_FAULT_REQUEST",
            "2": "N12_FAULT_REQUEST",
            "3": "NF_FAULT_REQUEST",
            "4": "E28_NATIVE_FAULT_REQUEST",
            "5": "NF_FAULT_REQUEST",
            "6": "E28_COMBINED_FAULT_REQUEST_HCS",
        },
        "U34": {
            "1": "E28_COMBINED_FAULT_REQUEST_HCS",
            "6": "E28_COMBINED_FAULT_REQUEST_BUFFER_MID",
            "3": "E28_COMBINED_FAULT_REQUEST_BUFFER_MID",
            "4": "E28_COMBINED_FAULT_REQUEST",
        },
        "J1": {"7": "ABS_AUX_FAULT", "14": "E28_COMBINED_FAULT_REQUEST"},
        "R17": {"1": "ABS_AUX_FAULT", "2": "AGND"},
        "R4": {"1": "CLAMP_LED_SUPPLY", "2": "N19_CLAMP_LED_A"},
        "R11": {"1": "CLAMP_LED_SUPPLY", "2": "N12_CLAMP_LED_A"},
        "R5": {"1": "N19_CLAMP_LED_A", "2": "N19_CLAMP_LED_MID"},
        "R98": {"1": "N19_CLAMP_LED_MID", "2": "N19_CLAMP_LED_K"},
        "R12": {"1": "N12_CLAMP_LED_A", "2": "N12_CLAMP_LED_MID"},
        "R99": {"1": "N12_CLAMP_LED_MID", "2": "N12_CLAMP_LED_K"},
        "R97": {"1": "CLAMP_LED_SUPPLY", "2": "AGND"},
        "U4": {"5": "AUX2V6", "4": "N19_CLAMP_LED_K"},
        "U10": {"5": "AUX2V6", "4": "N12_CLAMP_LED_K"},
        "U52": {"4": "AUX2V6", "6": "N19_START_DELAY_N"},
        "U54": {"4": "AUX2V6", "6": "N12_START_DELAY_N"},
        "J6": {"1": "GUARDED_12V_FORCE", "2": "MODULE_INPUT_GND"},
    }
    errors = [
        (r, n, want, p.get(r, {}).get(n))
        for r, ps in required.items()
        for n, want in ps.items()
        if p.get(r, {}).get(n) != want
    ]
    primary = {(r, n) for r, ps in p.items() for n, net in ps.items() if net == "MODULE_INPUT_GND"}
    if primary != {("U17", "1"), ("U22", "1"), ("C4", "2"), ("C31", "2"), ("J6", "2")}:
        errors.append(("MODULE_INPUT_GND_members", sorted(primary)))
    if not p["J1"]["4"].startswith("unconnected-"):
        errors.append(("J1.4_not_NC", p["J1"]["4"]))
    return errors


def evaluate_cone(p, source_safe, uv_ready, arm, other_fault=False):
    """Settled Boolean evaluation using actual exported gate-pin identities.

    NOT an analog timing/partial-power model or an E28 hardware latch test.
    """
    assert not validate(p), validate(p)
    v = dict(
        N19_SAFE_SOURCE=source_safe,
        CLAMP_SUPPLY_ENABLE=uv_ready,
        N19_ARM_CONDITIONED=arm,
        N19_F_TIMEOUT=other_fault,
        N19_F_OUTPUT=False,
        N12_FAULT_REQUEST=False,
        E28_NATIVE_FAULT_REQUEST=False,
    )

    def gate(ref, inputs, out, op):
        v[p[ref][str(out)]] = op(*(v[p[ref][str(n)]] for n in inputs))

    def inv(a):
        return not a

    def and2(a, b):
        return a and b

    def or2(a, b):
        return a or b
    for r, ins, out, op in [
        ("U58", [2], 4, inv),
        ("U48", [13], 12, inv),
        ("U51", [12, 13], 11, and2),
        ("U47", [1], 2, inv),
        ("U35", [9, 10], 8, and2),
        ("U45", [1, 2], 3, or2),
        ("U45", [4, 5], 6, or2),
        ("U46", [1, 2], 3, or2),
        ("U46", [4, 5], 6, or2),
        ("U34", [1], 6, inv),
        ("U34", [3], 4, inv),
    ]:
        gate(r, ins, out, op)
    return {
        n: v[n]
        for n in ["ABS_AUX_FAULT", "ABS_AUX_READY", "N19_SAFE", "N19_F_SOURCE", "E28_COMBINED_FAULT_REQUEST"]
    }


def review():
    actual, pins = netlist(ROOT / "generated/netlist.xml")
    assert len(actual) == 265
    assert not validate(pins), validate(pins)
    count, errors = primary_pin_roles(ROOT / "generated/netlist.xml")
    assert count == 7 and not errors, (count, errors)
    old = json.loads((ROOT / "sources/parent261/components.json").read_text())
    new = json.loads((ROOT / "components.json").read_text())
    by = {c["ref"]: c for c in new}
    changed = {}
    aliases = []
    for c in old:
        normalized = copy.deepcopy(c)
        normalized["footprint"] = normalized["footprint"].replace(
            "NF05H_Manufacturer:", "NF05R_Manufacturer:"
        )
        if normalized["footprint"] != c["footprint"]:
            aliases.append(c["ref"])
        delta = {
            k: dict(old=normalized.get(k), new=by[c["ref"]].get(k))
            for k in normalized.keys() | by[c["ref"]].keys()
            if normalized.get(k) != by[c["ref"]].get(k)
        }
        if delta:
            changed[c["ref"]] = delta
    expect = {
        "C99",
        "J1",
        "R11",
        "R12",
        "R17",
        "R4",
        "R5",
        "R97",
        "U28",
        "U30",
        "U42",
        "U48",
        "U51",
        "U53",
        "U55",
    }
    assert set(changed) == expect, set(changed) ^ expect
    assert set(by) - {c["ref"] for c in old} == {"U58", "C100", "R98", "R99"}
    truth = []
    for s, u, a, f in itertools.product([False, True], repeat=4):
        row = evaluate_cone(pins, s, u, a, f)
        assert row["N19_F_SOURCE"] == (a and not (s and u))
        assert row["E28_COMBINED_FAULT_REQUEST"] == (f or (a and not (s and u)))
        truth.append(dict(source_safe=s, UV_ready=u, ARM_retained=a, other_fault=f, **row))
    return dict(
        revision="NF05R265-native-independent-role-and-exact-delta",
        parts=265,
        physical_TPS3890_count=count,
        physical_role_errors=errors,
        inherited_original_four_TPS3890_maps_unchanged=True,
        parent261_component_count=len(old),
        exact_changed_components=changed,
        manufacturer_library_alias_changes_only=aliases,
        original_other_components_unchanged_count=len(old) - len(changed),
        actual_new_component_refs=["C100", "R98", "R99", "U58"],
        truth_cases=truth,
        exported_native_fault_cone_verified=True,
        actual_E28_native_latch_integration_implemented=False,
        analog_loading_delays_and_partial_power_accepted=False,
        source_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                ROOT / "review.py",
                ROOT / "generated/netlist.xml",
                ROOT / "components.json",
                ROOT / "sources/manifest.json",
            ]
        },
        PCB_implemented=False,
        physical_qualified=False,
        release_approved=False,
    )


if __name__ == "__main__":
    assert not (ROOT / "handoff.json").exists()
    (ROOT / "generated/equivalence.json").write_text(json.dumps(review(), indent=2) + "\n")
    print(
        "265 native components; seven physical supervisor maps; 16 actual-gate fault combinations; exact parent delta"
    )
