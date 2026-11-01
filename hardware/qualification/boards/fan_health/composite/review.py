"""Independent source/native topology review of the actual closed composite."""

import csv
import hashlib
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def by_ref(tree):
    return {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }


def native_pins(tree):
    return {
        r: {
            str(p[1]): (str(first(p, "net")[1]).lstrip("/") if children(p, "net") else None)
            for p in children(f, "pad")
            if p[1]
        }
        for r, f in by_ref(tree).items()
    }


def normalized(value):
    return None if value is None or value.startswith("unconnected-") else value


def validate_tree(tree):
    actual = native_pins(tree)
    parts = json.loads((ROOT / "components.json").read_text())
    expected = {c["ref"]: {p["number"]: p["net"] for p in c["pins"]} for c in parts}
    assert {r: {p: normalized(n) for p, n in ps.items()} for r, ps in actual.items()} == expected, (
        "Actual PCB/native component pin mismatch"
    )
    assert len(actual) == 84
    # Exact firmware contract uses actual native pad identities, not builder parity alone.
    u1 = actual["U1"]
    firmware = {
        "1": "V3V3",
        "14": "GND",
        "2": "XTAL1",
        "3": "XTAL2",
        "4": "MCU_RESET_N",
        "5": "MCU_TACH_R",
        "6": "MCU_HEALTH",
        "7": "ISP_MOSI",
        "8": "ISP_MISO",
        "9": "ISP_SCK",
        "10": "MCU_TACH_L",
        "11": "HEARTBEAT",
        "12": "TEMP_R_ADC",
        "13": "TEMP_L_ADC",
    }
    assert u1 == firmware, (u1, firmware)
    assert actual["J201"] == {"1": "FAN5V_IN", "2": "GND"}
    assert actual["J4"] == {"1": "P03_POWER_RUN", "2": "E28_POWER_RUN"}
    assert actual["U15"]["4"] == "P03_POWER_RUN" and actual["U15"]["6"] == "E28_POWER_RUN"
    assert (
        actual["U8"]["1"] == "FAULT_CLK"
        and actual["U8"]["6"] == "RAW_CLEAR_FAST"
        and actual["U8"]["3"] == "HW_NOFAULT_5"
    ), actual["U8"]
    assert not [t for t in children(tree, "segment") if first(t, "layer")[1] == "In1.Cu"], (
        "Dedicated return plane cut by signal track"
    )
    zones = children(tree, "zone")
    names = {first(z, "name")[1] for z in zones if children(z, "name")}
    for ref, f in by_ref(tree).items():
        for p in children(f, "pad"):
            if p[1] and p[2] == "smd" and any(str(v).endswith(".Cu") for v in first(p, "layers")[1:]):
                assert f"NO_UNFILLED_VIP_{ref}_{p[1]}" in names, "Missing actual-pad via exclusion"
    assert {
        "XTAL_BODY_COPPER_EXCLUSION_0",
        "XTAL_BODY_COPPER_EXCLUSION_1",
        "XTAL_BODY_COPPER_EXCLUSION_2",
        "XTAL_BODY_NO_VIA",
    } <= names, names

    # Literal, manufacturer-sensitive local routes must survive the routing round trip.
    def segment_key(net, layer, width, start, end):
        return (
            net.lstrip("/"),
            str(layer),
            round(float(width), 6),
            tuple(sorted((tuple(round(float(v), 5) for v in start), tuple(round(float(v), 5) for v in end)))),
        )

    segments = {
        segment_key(
            first(t, "net")[1],
            first(t, "layer")[1],
            first(t, "width")[1],
            first(t, "start")[1:3],
            first(t, "end")[1:3],
        )
        for t in children(tree, "segment")
    }
    via_shapes = {
        (
            str(first(v, "net")[1]).lstrip("/"),
            tuple(round(float(x), 6) for x in first(v, "at")[1:3]),
            round(float(first(v, "size")[1]), 6),
            round(float(first(v, "drill")[1]), 6),
        )
        for v in children(tree, "via")
    }
    for r in json.loads((ROOT / "generated/local-routes.json").read_text())["routes"]:
        if "points_mm" in r:
            for a, b in zip(r["points_mm"], r["points_mm"][1:]):
                if a == b:
                    continue
                assert segment_key(r["net"], r["layer"], r["width_mm"], a, b) in segments, (
                    "Lost literal route",
                    r["role"],
                    a,
                    b,
                )
        else:
            assert (
                r["net"].lstrip("/"),
                tuple(r["via_mm"]),
                r["diameter_mm"],
                r["finished_bore_mm"],
            ) in via_shapes, ("Lost literal via", r)
    return dict(
        parts=84,
        firmware_native_pin_contract_exact=True,
        complete_literal_route_geometry_preserved_with_10nm_coordinate_quantization=True,
        dedicated_In1_signal_tracks=0,
    )


def main():
    tree = read_sexpr((ROOT / "fan_power_health.kicad_pcb").read_text())
    result = validate_tree(tree)
    actual, pins = netlist(ROOT / "generated/netlist.xml")
    pcb = native_pins(tree)
    assert {r: {n: normalized(v.lstrip("/")) for n, v in p.items()} for r, p in pins.items()} == {
        r: {n: normalized(v) for n, v in p.items()} for r, p in pcb.items()
    }
    values = {r: c.findtext("value") for r, c in actual.items()}
    assert values == {c["ref"]: c["part"] for c in json.loads((ROOT / "components.json").read_text())}
    with (ROOT / "bom.csv").open() as file:
        bom = {row["Reference"]: row["Part_or_value"] for row in csv.DictReader(file)}
    assert bom == values
    erc = json.loads((ROOT / "generated/erc.json").read_text())
    assert not [v for s in erc["sheets"] for v in s["violations"]]
    drc = json.loads((ROOT / "generated/closed-drc.json").read_text())
    assert not drc["violations"] and not drc["unconnected_items"] and not drc["schematic_parity"]
    receipt = json.loads((ROOT / "generated/current-native.json").read_text())
    assert receipt["pcb_sha256"] == sha(ROOT / "fan_power_health.kicad_pcb")
    assert receipt["raw_report_sha256"] == sha(ROOT / "generated/closed-drc.json")
    old = by_ref(read_sexpr((ROOT / "routing/locked-signal-pass10/output.kicad_pcb").read_text()))
    new = by_ref(tree)
    assert [r for r in old if old[r] != new[r]] == ["C7"]
    for r in old:
        assert first(old[r], "at") == first(new[r], "at")
    result.update(
        schematic_ERC_errors=0,
        PCB_hard_DRC=0,
        warnings=0,
        opens=0,
        schematic_parity=0,
        unchanged_complete_footprints=83,
        only_changed_footprint="C7",
        all84_poses_preserved=True,
        physical_qualified=False,
        fabrication_released=False,
    )
    paths = [
        "fan_power_health.kicad_pcb",
        "fan_power_health.kicad_sch",
        "components.json",
        "bom.csv",
        "construction.json",
        "generated/netlist.xml",
        "generated/erc.json",
        "generated/closed-drc.json",
        "generated/current-native.json",
        "generated/local-routes.json",
        "review.py",
    ]
    result["sources_sha256"] = {p: sha(ROOT / p) for p in paths}
    (ROOT / "generated/final-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
