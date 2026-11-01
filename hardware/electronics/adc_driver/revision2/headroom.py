"""Conditional actual-R2 linear corner screen; no guaranteed codec/headroom claim."""

import copy
import itertools
import json
import math
from pathlib import Path

from ...common.netlists import netlist
from ..analyze import Circuit
from ..qualification.audit import REPO, sha
from .design import ROOT, thresholds
from .verify import check_circuit


def screen():
    parts, pins = netlist(ROOT / "generated/netlist.xml")
    check_circuit(parts, pins)
    pins = copy.deepcopy(pins)
    for terminals in pins.values():
        for pin, node in terminals.items():
            if node.startswith("SENSE_"):
                terminals[pin] = node.replace("SENSE_", "ADC_")
    minimum = 99
    maximum = -99
    raw_diff = 0
    for signs in itertools.product((-1, 1), repeat=6):
        overrides = {f"R{i + 1}": (2490 if i < 2 else 1210) * (1 + signs[i] * 0.0015) for i in range(4)}
        overrides.update(R5=3.3 * 1.03, R6=3.3 * 1.03)
        for load in ("per_pin_ground", "differential", "per_pin_reference"):
            ac = Circuit(
                parts,
                pins,
                f=20000,
                load=load,
                load_scale=(1 + signs[4] * 0.15, 1 + signs[5] * 0.15),
                overrides=overrides,
            )
            dc = Circuit(
                parts,
                pins,
                f=0,
                load=load,
                load_scale=(1 + signs[4] * 0.15, 1 + signs[5] * 0.15),
                overrides=overrides,
            )
            ax = ac.solve()
            raw_diff = max(raw_diff, abs(ac.differential(ax)) * 4.06 * math.sqrt(2))
            error = {node: 0 for node in (dc.op, dc.on)}
            for role, amount in [("buffer", 1.2e-3), ("fda", 400e-6), ("reference", 75e-6), ("servo", 75e-6)]:
                x = dc.solve(source=0, offsets={role: amount})
                for node in error:
                    error[node] += abs(dc.v(x, node))
            for node, amount in [("REF_DIV_L", 5e-9), ("CM_SENSE_L", 105e-9)]:
                x = dc.solve(source=0, currents=[(node, "AGND", amount)])
                for name in error:
                    error[name] += abs(dc.v(x, name))
            # Precision reference-divider full allocation causes additional midpoint error.
            for ref, source in itertools.product((3.2, 3.4), (-0.025, 0.025)):
                dx = dc.solve(source=source, reference=ref)
                for node in error:
                    amplitude = abs(ac.v(ax, node)) * 4.06 * math.sqrt(2)
                    allowance = error[node] + ref / 2 * 0.0012
                    minimum = min(minimum, dc.v(dx, node).real - amplitude - allowance)
                    maximum = max(maximum, dc.v(dx, node).real + amplitude + allowance)
    upper = thresholds()["upper_trip_v"][1]
    report = dict(
        source_sha256={
            str(p.relative_to(REPO)): sha(p)
            for p in [Path(__file__), ROOT / "design.py", ROOT / "verify.py", ROOT / "generated/netlist.xml"]
        },
        minimum_driver_after_allocations_v=minimum,
        maximum_driver_after_allocations_v=maximum,
        headroom_at_weakest_upper_trip_v=minimum - upper,
        headroom_allocation_v=0.3,
        conditional_headroom_allocation_satisfied=minimum - upper >= 0.3,
        maximum_ac_differential_peak_v=raw_diff,
        typical_codec_peak_v=2 * math.sqrt(2),
        gain_resistor_full_allocation=0.0015,
        output_resistor_full_allocation=0.03,
        source_rms_allocation_v=4.06,
        reference_allocation_v=[3.2, 3.4],
        servo_board_leakage_allocation_a=100e-9,
        actual_codec_dc_or_switching_model=False,
        manufacturer_model_used_in_this_linear_screen=False,
        physical_headroom_or_thd_verified=False,
        build_ready=False,
        limitations=[
            "Co-location ideal-short force/sense boundary",
            "Borrowed ideal-amplifier MNA stamping only; actual native R2 values and pin maps are checked independently",
            "Ground-load hypothesis is not justified by the real ESS part or vendor common-mode model",
            "Offsets,aging,reference range and leakage are declared allocations requiring validation",
            "No minimum guaranteed codec full scale or manufacturer THD at actual loading",
        ],
    )
    (ROOT / "generated/headroom.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    screen()
