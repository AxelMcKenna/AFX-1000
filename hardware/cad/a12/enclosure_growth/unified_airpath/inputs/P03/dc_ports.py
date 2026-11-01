"""Native-bound DC converter return algebra for coupled copper extraction.

Positive current enters AGND copper. This supplies topology/KCL expressions,
not a certified current bound or a complete board/cable electrical solution.
AC switching charge paths remain a separate EM/measurement requirement.
"""

import hashlib
import json

from ...common.netlists import netlist
from .spec import REPO, ROOT


def port_contract(parts, pins):
    for ref, pin in [
        ("U20", "5"),
        ("U20", "9"),
        ("U20", "11"),
        ("U23", "5"),
        ("U23", "9"),
        ("U23", "11"),
        ("U1", "5"),
        ("U1", "11"),
        ("U13", "5"),
        ("U13", "11"),
        ("D2", "1"),
        ("D4", "1"),
        ("U5", "11"),
        ("U6", "8"),
        ("U10", "3"),
        ("U11", "3"),
        ("J101", "2"),
        ("J20", "1"),
        ("J21", "1"),
    ]:
        assert pins[ref][pin] == "AGND", (ref, pin, "actual native return does not match DC model")
    assert pins["D2"]["2"] == "CUK_NODE" and pins["D4"]["2"] == "LO_CUK_NODE"
    return dict(
        convention="Positive signed current enters native AGND copper; external input return J101.2 removes total supply current",
        dc_converter_electrodes=[
            dict(
                ref=ic,
                pins=["9", "11"],
                expression=f"I_{tag}_input - I_{tag}_output - I_{tag}_quiet",
                reason="Buck current balance; do not inject full input current at the input guard",
                split_between_package_pins_bounded=False,
            )
            for ic, tag in [("U20", "digital"), ("U23", "analog_pre")]
        ]
        + [
            dict(
                ref=ic,
                pins=["5"],
                expression=f"I_{tag}_quiet",
                reason="Actual separate AGND reference/control pin; never replace by PGND9/11",
                quiet_control_current_bound_verified=False,
            )
            for ic, tag in [("U20", "digital"), ("U23", "analog_pre")]
        ]
        + [
            dict(
                ref=ic,
                pins=["11"],
                expression=f"I_{tag}_positive_input - I_{tag}_positive_output + I_{tag}_negative_input - I_{tag}_fb2n_bias",
                reason="Positive boost switch average plus negative Cuk switch average; includes chosen IC input loss allocation",
                manufacturer_ground_pin="Exposed pad11 only; pin5 is FB2N, not PGND",
            )
            for ic, tag in [("U1", "high_raw"), ("U13", "low_raw")]
        ]
        + [
            dict(
                ref=ic,
                pins=["5"],
                expression=f"I_{tag}_fb2n_bias",
                reason="Separate quiet FB2N reference electrode per LT3471 RevC page4",
                feedback_bias_at_ground_full_temperature_bound_verified=False,
            )
            for ic, tag in [("U1", "high_raw"), ("U13", "low_raw")]
        ]
        + [
            dict(
                ref=d,
                pins=["1"],
                expression=f"I_{tag}_negative_output",
                reason="Cuk capacitor average charge balance: ground cathode receives output-inductor average current; do not lump at IC EP",
            )
            for d, tag in [("D2", "high_raw"), ("D4", "low_raw")]
        ],
        local_static_current_electrodes=[
            dict(
                ref="U5",
                pin="11",
                signed_current_a=0.006,
                scope="OPA4192 four-channel maximum IQ before signal/servo output current",
            ),
            dict(
                ref="U6",
                pin="8",
                signed_current_a=-0.003,
                scope="OPA2192 two-channel maximum IQ, negative-supply amplifier",
            ),
            dict(
                ref="U10",
                pin="3",
                signed_current_a=-0.0225,
                scope="Conservative LT3090 ground-current allocation, not a guaranteed interpolation at actual load",
            ),
            dict(
                ref="U11",
                pin="3",
                signed_current_a=-0.0225,
                scope="Conservative LT3090 ground-current allocation, not a guaranteed interpolation at actual load",
            ),
        ],
        omitted_or_unclosed_current_terms=[
            "Actual downstream six-rail signed loads and E28 stage-controller returns, independent rather than cancelling positive/negative loads",
            "All native bleed/divider/reference/servo output current electrodes and AUX/analog reference/LDO currents",
            "IC ground-pin current sharing and finite internal connection; a uniform combined electrode is a model assumption",
            "Buck quiet/control current and full-temperature efficiency/current limits",
            "Switching-frequency current distribution, capacitor ESL/ESR and common impedance noise",
        ],
        lt3080_control_drive_added_as_fictitious_ground_current=False,
        whole_network_kcl_and_voltage_transfer_qualified=False,
        physical_tests_performed=0,
        build_ready=False,
    )


def generate():
    parts, pins = netlist(ROOT / "generated/netlist.xml")
    result = port_contract(parts, pins)
    result["source_sha256"] = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [ROOT / "power_p03.kicad_pcb", ROOT / "generated/netlist.xml", ROOT / "dc_ports.py"]
    }
    (ROOT / "generated/dc-current-ports.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    generate()
