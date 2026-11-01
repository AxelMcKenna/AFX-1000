"""P02 wiring requirements and exact interval-safe resistive return analysis.

These are proposed maximum lengths/minimum copper areas and contact limits,
not assertions that the current unspecified harness meets them.
"""

import json
from pathlib import Path

from ...common.circuits import LU

REPO = Path(__file__).resolve().parents[4]
MANIFEST = REPO / "hardware/wiring/generated/system-interconnect.json"
GROUND = "power_supply"


def conductor(length_m, area_mm2, contact_max=0.002):
    # Annealed copper rho20=1.724e-8, alpha=.00393/K; conservative 100 C.
    wire = 1.724e-8 * (1 + 0.00393 * 80) * length_m / (area_mm2 * 1e-6)
    # Two mated interfaces plus two board port/escape copper allocations.
    return wire + 2 * contact_max + 0.001


def harness_resistance(harness, contact_max=0.002):
    if harness in ("PWR-ANALOG", "PWR-DIGITAL"):
        return conductor(0.18, 2.08, contact_max)
    if harness == "DIG-PROCESSOR":
        return conductor(0.15, 2.08, contact_max)
    if harness == "LED-CONTROL":
        return conductor(0.12, 1.31, contact_max)
    if harness.startswith("LOAD-") or harness in ("DIG-BYPASS", "DIG-MONITOR", "P02-CONVERTER-RETURN"):
        return conductor(0.15, 0.823, contact_max)
    return conductor(0.20, 0.326, contact_max)


def node(pin):
    board, header, _ = pin
    if board == "rail_disconnect":
        return "E26_D_GND" if header in ("J2", "J4") else "E26_A_GND"
    return board


def ground_edges(contact_max=0.002):
    wires = json.loads(MANIFEST.read_text())["wires"]
    edges = []
    for wire in wires:
        if wire["net"] != "AGND" or "panel" in (wire["from"][0], wire["to"][0]):
            continue
        resistance = harness_resistance(wire["harness"], contact_max)
        if wire["harness"] == "DC-PROTECTED":
            # NEW co-located input-guard ground star, not the old cable.
            resistance = 0.001
        edges.append((node(wire["from"]), node(wire["to"]), resistance, wire["harness"]))
    edges += [
        ("E26_A_GND", "E26_D_GND", 0.001, "E26-defined-star-bridge"),
        (GROUND, "E26_A_GND", 0.002, "P02-NEW-ANALOG-RETURN-STRAP"),
        (GROUND, "E26_D_GND", 0.002, "P02-NEW-DIGITAL-RETURN-STRAP"),
        (
            "E26_A_GND",
            "converter",
            harness_resistance("P02-CONVERTER-RETURN", contact_max),
            "P02-CONVERTER-RETURN",
        ),
    ]
    return edges


def inverse_ground(edges, fraction):
    nodes = sorted({p for a, b, _, _ in edges for p in (a, b)} - {GROUND})
    idx = {n: i for i, n in enumerate(nodes)}
    matrix = [[0.0] * len(nodes) for _ in nodes]
    for a, b, r, _ in edges:
        assert r > 0
        g = 1 / (r * fraction)
        for n in (a, b):
            if n != GROUND:
                matrix[idx[n]][idx[n]] += g
        if GROUND not in (a, b):
            matrix[idx[a]][idx[b]] -= g
            matrix[idx[b]][idx[a]] -= g
    lu = LU(matrix)
    cols = [lu.solve([float(i == j) for i in range(len(nodes))]) for j in range(len(nodes))]
    return nodes, [[cols[j][i].real for j in range(len(nodes))] for i in range(len(nodes))]


def transfer_bounds(edges):
    """Rigorous enclosure for EVERY independent edge R in [0,Rmax].

    Rayleigh monotonicity bounds each effective resistance between the all-low
    and all-high networks. Polarization Z_ij=(R_i0+R_j0-R_ij)/2 then encloses
    transfer impedance, including cases where mixed edge corners are worse
    than the all-high network. This avoids mistaking all-hot for a transfer
    impedance worst case. The grounded-network maximum principle and reciprocity
    also give 0 <= Z_ij <= min(R_i0,R_j0). Bounds can be conservative; no RSS.
    """
    nodes, hi = inverse_ground(edges, 1)
    # Zero-R limiting network has zero effective resistance everywhere.
    # No minimum contact resistance is imposed or relied upon.
    lo = [[0.0] * len(nodes) for _ in nodes]
    bounds = {}
    for i, a in enumerate(nodes):
        for j, b in enumerate(nodes):
            if i == j:
                lower, upper = lo[i][i], hi[i][i]
            else:
                rij_lo = lo[i][i] + lo[j][j] - 2 * lo[i][j]
                rij_hi = hi[i][i] + hi[j][j] - 2 * hi[i][j]
                lower = max(0, (lo[i][i] + lo[j][j] - rij_hi) / 2)
                upper = min(hi[i][i], hi[j][j], (hi[i][i] + hi[j][j] - rij_lo) / 2)
            bounds[a, b] = (lower, upper)
    return nodes, bounds


# Independent positive/negative analog load cases never assume cancellation.
# Digital reserve is deliberately at the E26 star, not hidden through Seed R1.
LOADS = {
    "seed_local": ("DIG", "processor_carrier", 1.0),
    "led_logic": ("DIG", "led_driver", 0.380),
    **{f"led_group_{i}": ("DIG", "led_driver", 0.096) for i in range(1, 5)},
    "bypass": ("DIG", "sequenced_bypass", 0.080),
    "gain_input": ("DIG", "sequenced_bypass", 0.030),
    "gain_output": ("DIG", "sequenced_bypass", 0.030),
    "monitor_digital": ("DIG", "rail_monitor", 0.080),
    "digital_reserve": ("DIG", "E26_D_GND", 0.416),
    "adc_5v": ("ANA", "adc_driver", 0.100),
    "converter_5v": ("ANA", "converter", 0.140),
    "monitor_5v": ("ANA", "rail_monitor", 0.003),
    "analog_reserve": ("ANA", "E26_A_GND", 0.008),
    **{
        f"{board}_{sign}12": ("OTHER", board, current * sign)
        for board, current in (
            ("dac_receiver", 0.075),
            ("adc_driver", 0.035),
            ("input_range", 0.025),
            ("output_stage", 0.015),
            ("rail_monitor", 0.001),
        )
        for sign in (-1, 1)
    },
    "output_p19": ("OTHER", "output_stage", 0.026),
    "output_n19": ("OTHER", "output_stage", -0.026),
    "converter_3v3": ("OTHER", "converter", 0.035),
    "controls_3v3": ("OTHER", "control_inputs", 0.020),
    "monitor_3v3": ("OTHER", "rail_monitor", 0.020),
    "input_return": ("OTHER", "input_protection", -3.6),
}


def endpoints(contact_max=0.002):
    """Finite positive paths: each edge includes copper, contacts and wire."""

    def h(name):
        return harness_resistance(name, contact_max)

    shared = {
        "DIG": h("PWR-DIGITAL") + 0.003 + 0.006,  # E26 copper + hot FET path
        "ANA": h("PWR-ANALOG") + 0.003 + 0.006,
        "processor": h("DIG-PROCESSOR"),
        "led": h("LED-CONTROL"),
        "bypass": h("DIG-BYPASS"),
    }

    def row(rail, board, pin, loads, branch=0, extra=None):
        paths = {rail: shared[rail], **(extra or {})}
        if branch:
            paths["branch"] = branch
        return dict(rail=rail, board=board, pin=pin, loads=loads, paths=paths)

    rows = {
        "processor_5v": row(
            "DIG",
            "processor_carrier",
            "J1.1",
            ["seed_local", "led_logic", *[f"led_group_{i}" for i in range(1, 5)]],
            extra={"processor": shared["processor"]},
        ),
        "led_5v": row(
            "DIG",
            "led_driver",
            "J1.2",
            ["led_logic", *[f"led_group_{i}" for i in range(1, 5)]],
            extra={"processor": shared["processor"], "led": shared["led"]},
        ),
        "bypass_5v": row(
            "DIG",
            "sequenced_bypass",
            "J1.1",
            ["bypass", "gain_input", "gain_output"],
            extra={"bypass": shared["bypass"]},
        ),
        "monitor_digital": row("DIG", "rail_monitor", "J1.1", ["monitor_digital"], h("DIG-MONITOR")),
        "adc_5v": row("ANA", "adc_driver", "J3.4", ["adc_5v"], h("LOAD-ADC_DRIVER")),
        "converter_5v": row("ANA", "converter", "J4.1", ["converter_5v"], h("LOAD-CONVERTER")),
        "monitor_5v": row("ANA", "rail_monitor", "J2.6", ["monitor_5v"], h("LOAD-RAIL_MONITOR")),
    }
    for i in range(1, 5):
        rows[f"led_anode_{i}"] = row(
            "DIG",
            "led_driver",
            f"J{i + 1}.25/26 -> emitter anode",
            [f"led_group_{i}"],
            conductor(0.15, 0.326, contact_max),
            {"processor": shared["processor"], "led": shared["led"]},
        )
    for suffix, board, pin in (
        ("input", "input_range", "J4.1-2 coil"),
        ("output", "output_stage", "J3.1-2 coil"),
    ):
        rows[f"gain_{suffix}"] = row(
            "DIG",
            "sequenced_bypass",
            pin + " on " + board,
            [f"gain_{suffix}"],
            2 * conductor(0.15, 0.326, contact_max),
            {"bypass": shared["bypass"], "gain_fet": 0.150},
        )
    return rows


def positive_loss(endpoint, load_id, contact_max=0.002):
    rail, _, _ = LOADS[load_id]
    paths = endpoint["paths"]
    r = paths.get(rail, 0)
    processor_load = load_id == "seed_local" or load_id.startswith("led_")
    if processor_load:
        r += paths.get("processor", 0)
    if load_id.startswith("led_"):
        r += paths.get("led", 0)
    if load_id in ("bypass", "gain_input", "gain_output"):
        r += paths.get("bypass", 0)
    if load_id.startswith("gain_"):
        r += paths.get("gain_fet", 0)
    if load_id in endpoint["loads"]:
        r += paths.get("branch", 0)
    return r


def voltage_bounds(sources, contact_max=0.002):
    edges = ground_edges(contact_max)
    nodes, z = transfer_bounds(edges)
    rows = endpoints(contact_max)
    result = {}
    for name, endpoint in rows.items():
        rail, board = endpoint["rail"], endpoint["board"]
        low, high = sources[rail]
        dynamic = 0.003 if rail == "ANA" else 0.020
        # Local ground-plane/load-pad spread remains a nonzero requirement,
        # in addition to the port/escape copper already in every edge.
        spread = 0.0005 if rail == "ANA" else 0.002
        low -= dynamic + spread
        high += dynamic + spread
        losses = []
        for load, (_, return_node, maximum) in LOADS.items():
            _, upper = z[board, return_node]
            positive = positive_loss(endpoint, load, contact_max)
            if maximum >= 0:
                term = maximum * (upper + positive)
                low -= term
                losses.append((load, term))
            else:
                high += -maximum * upper
        target = (4.975, 5.025) if rail == "ANA" else (4.9, 5.1)
        result[name] = dict(
            **endpoint,
            minimum_v=low,
            maximum_v=high,
            target_v=target,
            passes=low >= target[0] and high <= target[1],
            largest_low_losses_v=sorted(losses, key=lambda x: x[1], reverse=True)[:4],
        )
    return dict(
        endpoints=result,
        all_pass=all(p["passes"] for p in result.values()),
        ground_nodes=nodes,
        ground_edges=[dict(a=a, b=b, max_ohm=r, min_ohm=0, harness=h) for a, b, r, h in edges],
        independent_load_allocations={
            k: dict(rail=r, return_node=n, min_a=min(0, i), max_a=max(0, i)) for k, (r, n, i) in LOADS.items()
        },
        resistance_interval_method="Rayleigh monotonicity plus effective-resistance polarization; all independent R in [0,Rmax]; independent current intervals",
        physical_harness_qualified=False,
    )
