"""Independent manufacturer pin/topology contract and honest native-draft gate."""

import json
import math
import sys

from hardware.electronics.common.netlists import netlist, number

from .analyze import OUT, sha
from .design import REPO, ROOT


def contract_errors(parts, pins):
    errors = []

    def need(ref, expected):
        if pins.get(ref) != expected:
            errors.append(ref + " manufacturer/topology mismatch")

    for rail, offset, bulk in [("P19", 0, 1500e-6), ("P12", 100, 220e-6)]:

        def ref(s):
            return s[0] + str(int(s[1:]) + offset)

        def net(s):
            return rail + "_" + s

        need(
            ref("U1"),
            {
                "1": net("SENSE"),
                "2": net("BANK_OUT"),
                "3": net("UV"),
                "4": net("OV"),
                "5": "AGND",
                "6": net("TIMER"),
                "7": net("PWR"),
                "8": net("PG_RAW"),
                "9": net("PROTECTED"),
                "10": net("GATE"),
            },
        )
        need(ref("Q1"), {"1": net("GATE"), "2": net("SENSE"), "3": net("PROTECTED")})
        need(ref("Q2"), {"1": net("RAMP_BASE"), "2": net("RAMP_CAP"), "3": "AGND"})
        need(ref("D2"), {"1": net("RAMP_CAP"), "2": net("GATE")})
        need(ref("U2"), {"1": net("LED_A"), "3": net("LED_K"), "4": net("UV_SW_IN"), "6": net("UV")})
        need(ref("Q3"), {"1": net("ENABLE_GATE"), "2": "AGND", "3": net("LED_K")})
        for component, a, b in [
            ("R1", "BANK_OUT", "SENSE"),
            ("R2", "GATE", "RAMP_BASE"),
            ("R5", "BANK_OUT", "UV_SW_IN"),
            ("R6", "UV", "AGND"),
            ("R9", "BANK_OUT", "LED_A"),
            ("R10", "LED_A", "LED_K"),
            ("R11", "ENABLE_3V3", "ENABLE_GATE"),
            ("R12", "ENABLE_GATE", "AGND"),
            ("C4", "PROTECTED", "AGND"),
        ]:
            need(ref(component), {"1": net(a), "2": "AGND" if b == "AGND" else net(b)})
        if not math.isclose(number(parts[ref("C4")].findtext("value")), bulk, rel_tol=1e-12):
            errors.append(rail + " wrong retained bulk")
        if number(parts[ref("C3")].findtext("value")) > 1e-6:
            errors.append(rail + " unexpected upstream reservoir")
        if number(parts[ref("R1")].findtext("value")) != 0.091:
            errors.append(rail + " wrong shunt")
        for component, part in [
            ("U1", "LM5069MM-1/NOPB"),
            ("Q1", "CSD19536KTT"),
            ("Q2", "MMBT5401LT1G"),
            ("Q3", "BSS138BK,215"),
            ("U2", "TLP170GM(TPL,E"),
        ]:
            if parts[ref(component)].findtext("value") != part:
                errors.append(ref(component) + " wrong manufacturer device")
    if any("AUX" in n for row in pins.values() for n in row.values()):
        errors.append("Unbudgeted AUX connection")
    return errors


def main():
    parts, pins = netlist(OUT / "netlist.xml")
    errors = contract_errors(parts, pins)
    erc = json.loads((OUT / "erc.json").read_text())
    violations = [v for s in erc["sheets"] for v in s["violations"]]
    actual_warnings = {}
    for v in violations:
        if v["type"] != "footprint_link_issues" or v["severity"] != "warning":
            errors.append("Unexpected ERC:" + v["type"])
        actual_warnings[v["description"]] = v["items"]
    if len(violations) != 6:
        errors.append("Expected exactly6 unresolved footprint warnings")
    unresolved = {r for r in ["C1", "C2", "U2", "C101", "C102", "U102"]}
    native_warnings = {}
    for v in violations:
        item = v["items"][0]["description"]
        found = [r for r in unresolved if item.startswith("Symbol " + r + " ")]
        if len(found) != 1:
            errors.append("Unexpected unresolved footprint:" + item)
        else:
            native_warnings[found[0]] = v["description"]
    if set(native_warnings) != unresolved:
        errors.append("Unresolved footprint inventory mismatch")
    analysis = json.loads((OUT / "analysis.json").read_text())
    if (
        analysis["five_second_wholeunit_pass"]
        or analysis["whole_unit_implemented"]
        or analysis["physical_tests_performed"] != 0
    ):
        errors.append("Invalid release/physical claim")
    sources = [
        p
        for p in ROOT.iterdir()
        if p.is_file() and p.suffix in {".py", ".json", ".md", ".kicad_sch", ".kicad_sym", ".kicad_pro"}
    ]
    sources += list((ROOT / "sources").glob("*"))
    sources += [
        REPO / "hardware/electronics/common/flat_schematic.py",
        REPO / "hardware/electronics/common/netlists.py",
        REPO / "hardware/electronics/common/symbols.py",
    ]
    evidence = [p for p in OUT.rglob("*") if p.is_file() and p.name != "verification.json"]
    report = dict(
        revision="SC01-native-draft",
        contract_errors=errors,
        actual_component_count=len(parts),
        native_erc_errors=sum(v["severity"] == "error" for v in violations),
        native_erc_warnings=len(violations),
        unresolved_footprint_warnings=native_warnings,
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(set(sources))},
        evidence_sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(evidence)},
        native_draft_contract_accepted=not errors,
        complete_electrical_design=False,
        physical_tests_performed=0,
        startup_qualified=False,
        reverse_current_qualified=False,
        soa_qualified=False,
        pcb_implemented=False,
        fabrication_released=False,
        build_ready=False,
    )
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    if errors:
        print("\n".join(errors), file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
