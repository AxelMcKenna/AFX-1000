"""Independent negative-domain pin and polarity checks, source-bound native draft gate."""

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
            errors.append(ref + " negative manufacturer/topology mismatch")

    if len(parts) != 60 or set(parts) != set(pins):
        errors.append("Actual component inventory mismatch")
    for rail, offset, bulk, cgs, cdv, rin, rpwr in [
        ("N19", 0, 1500e-6, 22e-6, 1.5e-6, 2000, 68100),
        ("N12", 100, 220e-6, 10e-6, 1e-6, 330, 49900),
    ]:

        def ref(s):
            return s[0] + str(int(s[1:]) + offset)

        def n(s):
            return s if s in {"AGND", "HOST_3V3"} else rail + "_" + s

        need(
            ref("U1"),
            {
                "1": n("VCC"),
                "2": n("UV"),
                "3": n("OV"),
                "4": n("PWR"),
                "5": n("BANK_OUT"),
                "6": n("TIMER"),
                "7": n("SENSE"),
                "8": n("GATE_CTRL"),
                "9": n("PROTECTED"),
                "10": n("PG_RAW"),
            },
        )
        need(ref("Q1"), {"1": n("GATE_FET"), "2": n("PROTECTED"), "3": n("SENSE")})
        need(ref("U2"), {"1": n("LED_A"), "3": n("LED_K"), "4": n("UV_SW_IN"), "6": n("UV")})
        need(ref("Q2"), {"1": n("ENABLE_GATE"), "2": "AGND", "3": n("LED_K")})
        need(ref("J1"), {"1": n("BANK_OUT"), "2": "AGND"})
        need(ref("J2"), {"1": n("PROTECTED"), "2": "AGND"})
        need(ref("J3"), {"1": "HOST_3V3", "2": n("ENABLE_3V3"), "3": "AGND"})
        need(ref("J4"), {"1": n("PG_RAW"), "2": n("BANK_OUT"), "3": "AGND"})
        need(ref("D1"), {"1": "AGND", "2": n("PROTECTED")})
        need(ref("D2"), {"1": "AGND", "2": n("BANK_OUT")})
        for component, a, b in [
            ("R1", "SENSE", "BANK_OUT"),
            ("R2", "GATE_CTRL", "GATE_FET"),
            ("R3", "GATE_CTRL", "MILLER"),
            ("C1", "MILLER", "PROTECTED"),
            ("C2", "GATE_FET", "SENSE"),
            ("C3", "TIMER", "BANK_OUT"),
            ("R4", "PWR", "BANK_OUT"),
            ("R5", "AGND", "VCC"),
            ("C4", "VCC", "BANK_OUT"),
            ("C5", "AGND", "PROTECTED"),
            ("R6", "AGND", "PROTECTED"),
            ("R7", "AGND", "UV_SW_IN"),
            ("R8", "UV", "BANK_OUT"),
            ("R9", "AGND", "OV"),
            ("R10", "OV", "BANK_OUT"),
            ("R11", "HOST_3V3", "LED_A"),
            ("R12", "LED_A", "LED_K"),
            ("R13", "ENABLE_3V3", "ENABLE_GATE"),
            ("R14", "ENABLE_GATE", "AGND"),
            ("R15", "AGND", "PG_RAW"),
        ]:
            need(ref(component), {"1": n(a), "2": n(b)})
        for component, expected in [
            ("R1", 0.091),
            ("C1", cdv),
            ("C2", cgs),
            ("C3", 470e-9),
            ("C5", bulk),
            ("R5", rin),
            ("R4", rpwr),
        ]:
            if ref(component) not in parts or not math.isclose(
                number(parts[ref(component)].findtext("value")), expected, rel_tol=1e-10
            ):
                errors.append(ref(component) + " incorrect selected draft value")
        for component, expected in [
            ("U1", "LM5067MM-1/NOPB"),
            ("Q1", "CSD19536KTT"),
            ("U2", "TLP170GM(TPL,E"),
            ("Q2", "BSS138BK,215"),
        ]:
            if ref(component) not in parts or parts[ref(component)].findtext("value") != expected:
                errors.append(ref(component) + " wrong manufacturer device")
    if any("AUX" in name for row in pins.values() for name in row.values()):
        errors.append("Unbudgeted AUX connection")
    return errors


def analysis_errors(a):
    errors = []
    for k in [
        "five_second_wholeunit_pass",
        "whole_unit_implemented",
        "guaranteed_ramp_network",
        "soa_qualified",
        "fabrication_released",
        "pcb_implemented",
        "canonical_boards_modified",
    ]:
        if a.get(k) is not False:
            errors.append("Invalid claim:" + k)
    if a.get("complete_startup_bound_s") is not None or a.get("physical_tests_performed") != 0:
        errors.append("Invalid whole-startup or physical claim")
    for rail in ["N19", "N12"]:
        row = a["rail_scenarios"][rail]
        if (
            any(
                row["ramp"][k] is not None
                for k in [
                    "guaranteed_complete_startup_s",
                    "guaranteed_output_slew_v_per_s",
                    "guaranteed_fault_turnoff_s",
                ]
            )
            or row["ramp"]["cross_controller_network_validated"]
        ):
            errors.append("Invalid experimental ramp approval")
        if row["vcc"]["guaranteed_operating_supply_interval_v"] is not None:
            errors.append("Unestablished controller supply guarantee")
        if row["additional_v2v5_aux_load_a"] != 0:
            errors.append("AUX budget changed")
        if (
            row["guaranteed_actual_selected_powerlimit_w"] is not None
            or row["external_anti_injection"]["insertion_off_qualified"]
        ):
            errors.append("Unestablished power/off-state guarantee")
    if any(
        a["timer"][k] is not None
        for k in ["guaranteed_insertion_s", "guaranteed_fault_s", "guaranteed_reset_s"]
    ):
        errors.append("Unestablished timer-state guarantee")
    if (
        not a["rail_scenarios"]["N12"]["vcc"]["failure"]
        or a["rail_scenarios"]["N12"]["vcc"]["recommended_2ma_established_by_comparison"]
    ):
        errors.append("Missing -12V recommended-supply failure")
    if a["digital_interface"]["e28_j9_2p5v_direct_compatible"]:
        errors.append("Invalid direct E28 logic connection")
    return errors


def main():
    parts, pins = netlist(OUT / "netlist.xml")
    errors = contract_errors(parts, pins)
    a = json.loads((OUT / "analysis.json").read_text())
    errors += analysis_errors(a)
    erc = json.loads((OUT / "erc.json").read_text())
    violations = [v for s in erc["sheets"] for v in s["violations"]]
    unresolved = {"C1", "C2", "C3", "U2", "C101", "C102", "C103", "U102"}
    found = set()
    for v in violations:
        if v["type"] != "footprint_link_issues" or v["severity"] != "warning":
            errors.append("Unexpected native ERC:" + v["type"])
        item = v["items"][0]["description"]
        refs = [r for r in unresolved if item.startswith("Symbol " + r + " ")]
        if len(refs) != 1:
            errors.append("Unexpected unresolved footprint:" + item)
        else:
            found.add(refs[0])
    if found != unresolved or len(violations) != 8:
        errors.append("Unresolved draft footprint inventory changed")
    parity = json.loads((OUT / "pin-parity.json").read_text())
    if parity["differences"] or parity["count"] != 60:
        errors.append("Native export parity failure")
    for path, expected in a["source_sha256"].items():
        if sha(REPO / path) != expected:
            errors.append("Stale analysis input:" + path)
    sources = [
        p
        for p in ROOT.iterdir()
        if p.is_file() and p.suffix in {".py", ".md", ".json", ".kicad_sch", ".kicad_sym", ".kicad_pro"}
    ]
    sources += list((ROOT / "sources").glob("*"))
    sources += [
        REPO / "hardware/electronics/common" / f for f in ["flat_schematic.py", "netlists.py", "symbols.py"]
    ]
    sources += [ROOT / "fp-lib-table", ROOT / "sym-lib-table"]
    evidence = [p for p in OUT.rglob("*") if p.is_file() and p.name != "verification.json"]
    report = dict(
        revision="SC02-native-draft",
        contract_errors=errors,
        native_component_count=len(parts),
        native_erc_errors=sum(v["severity"] == "error" for v in violations),
        native_erc_warnings=len(violations),
        unresolved_footprints=sorted(found),
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
