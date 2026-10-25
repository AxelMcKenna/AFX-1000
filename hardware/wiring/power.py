"""Pin-exact source/disconnect harness plan and provisional voltage-loss screen."""

import csv
import hashlib
import io
import json
import math
from pathlib import Path

from ..electronics.common.netlists import netlist
from ..electronics.common.sexpr import children, first, read_sexpr
from ..electronics.output_stage.check_placement import transform

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
ELECTRONICS = REPO / "hardware/electronics"


def plan():
    specs = [
        (
            "main_supply",
            ELECTRONICS / "power_supply/routing/power_supply.kicad_pcb",
            (201, 105, 6.5),
            ELECTRONICS / "power_supply/generated/netlist.xml",
        ),
        (
            "disconnect",
            ELECTRONICS / "rail_disconnect/placement/rail_disconnect.kicad_pcb",
            (8, 108.5, 4.6),
            ELECTRONICS / "rail_disconnect/placement/generated/netlist.xml",
        ),
        (
            "input_power",
            ELECTRONICS / "input_protection/input_protection.kicad_pcb",
            (248, 1.4, 7.9),
            ELECTRONICS / "input_protection/generated/netlist.xml",
        ),
    ]
    cad = REPO / "hardware/cad/a11/generated/components.scad"
    board_line = next(line for line in cad.read_text().splitlines() if line.startswith("boards = "))
    positions = {b[0]: tuple(b[1:4]) for b in json.loads(board_line.removesuffix(";").split(" = ", 1)[1])}
    identifiers = {
        "main_supply": "power_carrier",
        "disconnect": "disconnect_carrier",
        "input_power": "input_power",
    }
    for name, pcb, datum, nl in specs:
        assert positions[identifiers[name]] == datum, ("Wiring datum disagrees with CAD", name)
    boards = {}
    sources = {str(cad.relative_to(REPO)): hashlib.sha256(cad.read_bytes()).hexdigest()}
    for name, pcb, datum, nl in specs:
        _, pins = netlist(nl)
        tree = read_sexpr(pcb.read_text())
        headers = {}
        for f in children(tree, "footprint"):
            ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
            if not ref.startswith("J"):
                continue
            h = {}
            for pad in children(f, "pad"):
                n = str(pad[1])
                net = str(first(pad, "net")[-1]).lstrip("/")
                assert net == pins[ref][n], (name, ref, n, "PCB/netlist mismatch")
                x, y = transform(f, first(pad, "at")[1:3])
                h[n] = dict(net=net, xyz_mm=[x - 100 + datum[0], y - 100 + datum[1], datum[2] + 1.6])
            headers[ref] = h
        boards[name] = headers
        for p in (pcb, nl):
            sources[str(p.relative_to(REPO))] = hashlib.sha256(p.read_bytes()).hexdigest()
    wires = []
    for harness, left, right, pins in (
        ("PWR-ANALOG", ("main_supply", "J2"), ("disconnect", "J1"), range(1, 7)),
        ("PWR-DIGITAL", ("main_supply", "J3"), ("disconnect", "J2"), range(1, 3)),
        ("PWR-AUX-RUN", ("input_power", "J6"), ("disconnect", "J5"), range(1, 4)),
    ):
        for pin in pins:
            a = boards[left[0]][left[1]][str(pin)]
            b = boards[right[0]][right[1]][str(pin)]
            assert a["net"] == b["net"], (harness, pin, "source/load net mismatch", a, b)
            wires.append(
                dict(
                    harness=harness,
                    from_board=left[0],
                    from_header=left[1],
                    from_pin=pin,
                    to_board=right[0],
                    to_header=right[1],
                    to_pin=pin,
                    net=a["net"],
                    from_net=a["net"],
                    to_net=b["net"],
                    straight_line_minimum_mm=math.dist(a["xyz_mm"], b["xyz_mm"]),
                    from_xyz_mm=a["xyz_mm"],
                    to_xyz_mm=b["xyz_mm"],
                    cut_length_mm=None,
                    production_connector=None,
                    wire_gauge=None,
                    assembly_released=False,
                )
            )
    validate(wires)
    for p in (
        Path(__file__),
        ELECTRONICS / "common/netlists.py",
        ELECTRONICS / "common/sexpr.py",
        ELECTRONICS / "output_stage/check_placement.py",
    ):
        sources[str(p.relative_to(REPO))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(
        scope="Source-side power and auxiliary/run harness pin contracts; protected-load fanout and front control wiring remain open",
        wires=wires,
        source_sha256=sources,
        wire_lengths_are_geometric_lower_bounds=True,
        includes_bend_service_loop_or_keepouts=False,
        production_contacts_or_current_rating_qualified=False,
        build_ready=False,
    )


def validate(wires):
    expected = {
        "PWR-ANALOG": (
            "main_supply",
            "J2",
            "disconnect",
            "J1",
            ["P19_SRC", "AGND", "N19_SRC", "P12_SRC", "N12_SRC", "V5_REG_SRC"],
        ),
        "PWR-DIGITAL": ("main_supply", "J3", "disconnect", "J2", ["5V_DIG_SRC", "AGND"]),
        "PWR-AUX-RUN": ("input_power", "J6", "disconnect", "J5", ["V2V5_AUX", "AGND", "POWER_RUN"]),
    }
    assert len(wires) == 11, "Missing or duplicated power wiring"
    seen = set()
    for w in wires:
        key = (w["harness"], w["from_pin"])
        assert key not in seen, "Duplicated power pin"
        seen.add(key)
        a, b, c, d, nets = expected[w["harness"]]
        assert (w["from_board"], w["from_header"], w["to_board"], w["to_header"]) == (a, b, c, d), (
            "Wrong power header endpoints"
        )
        assert 1 <= w["from_pin"] <= len(nets) and w["to_pin"] == w["from_pin"], (
            "Power header pin order changed"
        )
        assert w["net"] == w["from_net"] == w["to_net"] == nets[w["from_pin"] - 1], (
            "Power net mismatch or protected/source substitution"
        )


def screen(p, normal_rows):
    result = []
    # Geometry and assumed conductor area only; no contact resistance is invented.
    for name, harness, pin in (("V5_REG", "PWR-ANALOG", 6), ("5V_DIG", "PWR-DIGITAL", 1)):
        row = next(r for r in normal_rows if r["name"] == name)
        wire = next(w for w in p["wires"] if w["harness"] == harness and w["from_pin"] == pin)
        ground = next(w for w in p["wires"] if w["harness"] == harness and w["net"] == "AGND")
        headroom = row["protected_dc_with_digital_ripple_v"][0] - row["target_at_integrated_board_star_v"][0]
        assert headroom > 0, "Existing source has no remaining low-side voltage budget"
        current = row["maximum_current_screen_a"]
        length = wire["straight_line_minimum_mm"] + ground["straight_line_minimum_mm"]
        # 0.823mm² is an explicit 18AWG trial, not a selected wiring assembly.
        resistance = 1.8e-8 * (length / 1000) / (0.823e-6)
        drop = resistance * current
        result.append(
            dict(
                rail=name,
                current_a=current,
                geometric_loop_minimum_mm=length,
                trial_conductor_area_mm2=0.823,
                assumed_resistivity_ohm_m=1.8e-8,
                wire_only_loss_estimate_v=drop,
                remaining_low_side_budget_v=headroom,
                wire_only_trial_passes=drop <= headroom,
                maximum_total_added_resistance_ohm=headroom / current,
                minimum_conductor_area_mm2_ignoring_contacts=1.8e-8
                * (length / 1000)
                / (headroom / current)
                * 1e6,
                includes_contacts_temperature_routing_or_return_displacement=False,
                production_distribution_qualified=False,
            )
        )
    return result


def main():
    p = plan()
    source = ELECTRONICS / "rail_disconnect/generated/electrical-screens.json"
    p["voltage_loss_screen"] = screen(p, json.loads(source.read_text())["normal_drop"])
    p["source_sha256"][str(source.relative_to(REPO))] = hashlib.sha256(source.read_bytes()).hexdigest()
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    (out / "power-interconnect.json").write_text(json.dumps(p, indent=2) + "\n")
    stream = io.StringIO()
    keys = (
        "harness",
        "from_board",
        "from_header",
        "from_pin",
        "to_board",
        "to_header",
        "to_pin",
        "net",
        "straight_line_minimum_mm",
        "cut_length_mm",
        "production_connector",
        "wire_gauge",
        "assembly_released",
    )
    writer = csv.DictWriter(stream, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(p["wires"])
    (out / "power-interconnect.csv").write_text(stream.getvalue())
    print("Source harness: 11 pin/net pairs verified. Trial wiring is not released; see loss screen.")
    for row in p["voltage_loss_screen"]:
        print(
            row["rail"],
            "wire trial passes:",
            row["wire_only_trial_passes"],
            "drop mV:",
            round(row["wire_only_loss_estimate_v"] * 1000, 3),
            "budget mV:",
            round(row["remaining_low_side_budget_v"] * 1000, 3),
        )


if __name__ == "__main__":
    main()
