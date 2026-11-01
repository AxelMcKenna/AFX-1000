"""Native-bound static passive return intervals for the coupled DC model.

These are conditional DC scenarios, not completed full-temperature/current
bounds. Unknown IC, switching and driven-node currents remain explicit; nothing
is silently assigned zero. Positive current enters the AGND electrode.
"""

import hashlib
import itertools
import json

from ...common.netlists import netlist
from . import analysis, bipolar, models
from .spec import REPO, ROOT


def divider_current(voltage, top, bottom, resistor_error, bias):
    values = []
    for v, st, sb, i in itertools.product(voltage, (-1, 1), (-1, 1), (-bias, bias)):
        rt, rb = top * (1 + st * resistor_error), bottom * (1 + sb * resistor_error)
        values.append(v / (rt + rb) - i * rt / (rt + rb))
    return [min(values), max(values)]


def packet(parts, pins):
    src, detail = analysis.source_bounds(parts)
    rails = bipolar.source_corners(parts)
    voltages = {
        "V2V5_AUX": models.auxiliary(parts)["source_interval_v"],
        "VIN_PROTECTED": [9.8, 13.2],
        "DC_IN": [9.8, 13.2],
        "V5_REG_SRC": src["ANA"],
        "5V_DIG_SRC": src["DIG"],
        "P03_PRE6V": detail["preregulator_dc_interval_v"],
    }
    set_error = detail["analog_ldo_set_to_output_error_allowance_v"]
    voltages["P03_ANA_SET"] = [src["ANA"][0] - set_error, src["ANA"][1] + set_error]
    for name, row in rails.items():
        lo, hi = row["source_magnitude_v"]
        voltages[name + "_SRC"] = [-hi, -lo] if name.startswith("N") else [lo, hi]
    rows = []
    expected_direct = dict(
        R111="V2V5_AUX",
        R114="VIN_PROTECTED",
        R24="P19_SRC",
        R38="N19_SRC",
        R29="P12_SRC",
        R43="N12_SRC",
        R245="V5_REG_SRC",
    )
    for ref in expected_direct:
        ground = next(pin for pin, net in pins[ref].items() if net == "AGND")
        other = next(net for net in pins[ref].values() if net != "AGND")
        assert other == expected_direct[ref], (ref, "native load boundary changed")
        r = models.value(parts, ref)
        values = [v / (r * (1 + s * 0.03)) for v, s in itertools.product(voltages[other], (-1, 1))]
        rows.append(
            dict(
                ref=ref,
                pin=ground,
                source_net=other,
                nominal_ohm=r,
                conditional_signed_current_a=[min(values), max(values)],
                resistor_total_error_allocation_fraction=0.03,
                expression=f"V_{other}/{ref}",
            )
        )
    dividers = [
        ("R301", ["R300"], "5V_DIG_SRC", 30e-9),
        ("R303", ["R302"], "V5_REG_SRC", 30e-9),
        ("R305", ["R304"], "P19_SRC", 30e-9),
        ("R307", ["R306"], "P12_SRC", 30e-9),
        ("R309", ["R308"], "VIN_PROTECTED", 30e-9),
        ("R201", ["R200", "R206"], "5V_DIG_SRC", 100e-9),
        ("R221", ["R220"], "P03_PRE6V", 100e-9),
        ("R243", ["R242"], "P03_ANA_SET", 5e-9),
    ]
    for bottom, tops, net, bias in dividers:
        ground = next(pin for pin, n in pins[bottom].items() if n == "AGND")
        rb = models.value(parts, bottom)
        rt = sum(models.value(parts, r) for r in tops)
        node = net
        remaining = set(tops)
        while remaining:
            links = [ref for ref in remaining if node in pins[ref].values()]
            assert len(links) == 1, (bottom, node, "top-divider chain changed")
            ref = links[0]
            node = next(n for n in pins[ref].values() if n != node)
            remaining.remove(ref)
        assert node == pins[bottom]["1"], (bottom, "feedback node changed")
        rows.append(
            dict(
                ref=bottom,
                pin=ground,
                source_net=net,
                top_refs=tops,
                bottom_nominal_ohm=rb,
                top_nominal_ohm=rt,
                input_bias_signed_allocation_a=[-bias, bias],
                conditional_signed_current_a=divider_current(voltages[net], rt, rb, 0.03, bias),
                resistor_total_error_allocation_fraction=0.03,
                expression="V_source/(Rtop+Rbottom) - I_input*Rtop/(Rtop+Rbottom)",
            )
        )
    return dict(
        convention="Positive current enters actual native AGND pad; negative supply bleeds remove current",
        actual_passive_electrodes=rows,
        source_voltage_scenarios_v=voltages,
        source_voltages_are_conditional_analytical_envelopes=True,
        total_resistance_and_bias_allocations_qualified=False,
        omitted_or_symbolic=[
            "Guard UV/OV/PG/FOV and ILIM/MODE active-input currents and signed bias returns",
            "AUX feedback/REF pins and LDO ground current, reference/servo output and startup current",
            "Negative monitor shared-bias return, opamp input/output/drive currents",
            "LTC2910 supply/RESET/monitor current and loaded logic states",
            "Full converter IQ/loss allocation and package ground-pin current sharing",
            "Downstream and E28 currents, independent signed rail currents and switching/noise",
        ],
        no_omitted_current_is_zero=True,
        physical_qualified=False,
        build_ready=False,
    )


def generate():
    parts, pins = netlist(ROOT / "generated/netlist.xml")
    result = packet(parts, pins)
    result["source_sha256"] = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [
            ROOT / "power_p03.kicad_pcb",
            ROOT / "generated/netlist.xml",
            ROOT / "passive_returns.py",
            ROOT / "analysis.py",
            ROOT / "bipolar.py",
            ROOT / "models.py",
        ]
    }
    (ROOT / "generated/dc-passive-returns.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    result = generate()
    print(
        "Native-bound conditional passive returns:",
        len(result["actual_passive_electrodes"]),
        "electrodes; complete-current proof false",
    )
