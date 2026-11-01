"""Actual serialized source identity, new-stage topology and mount contracts."""

import json

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr

from .circuit import ROOT


def footprints(t):
    return {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(t, "footprint")
    }


def copper(t):
    return {first(n, "uuid")[1]: n for tag in ["segment", "via"] for n in children(t, tag)}


def topology(pins):
    expect = {
        "U401": {"1": "FAN5V_IN", "2": "GND", "3": "FAN5V_IN", "5": "NF_RAW5_ILIM", "6": "NF_RAW5"},
        "R401": {"1": "NF_RAW5_ILIM", "2": "GND"},
        "J401": {"1": "NF_RAW5", "2": "GND"},
        "C401": {"1": "FAN5V_IN", "2": "GND"},
        "C402": {"1": "FAN5V_IN", "2": "GND"},
        "C403": {"1": "NF_RAW5", "2": "GND"},
        "C404": {"1": "NF_RAW5", "2": "GND"},
    }
    errors = [
        (r, n, want, pins.get(r, {}).get(n))
        for r, ps in expect.items()
        for n, want in ps.items()
        if pins.get(r, {}).get(n) != want
    ]
    if not pins["U401"]["4"].startswith("unconnected-"):
        errors.append(("FAULT_not_NC", pins["U401"]["4"]))
    members = {(r, n) for r, ps in pins.items() for n, net in ps.items() if net == "NF_RAW5"}
    if members != {("U401", "6"), ("J401", "1"), ("C403", "1"), ("C404", "1")}:
        errors.append(("NF_RAW5_members", sorted(members)))
    return errors


def validate(tree):
    parent = read_sexpr((ROOT / "sources/M1/fan_power_health.kicad_pcb").read_text())
    old, new = footprints(parent), footprints(tree)
    assert len(old) == 84 and len(new) == 91
    assert all(new.get(r) == f for r, f in old.items()), "Changed complete parentFP/pose/path/value/pads"
    oldcu, newcu = copper(parent), copper(tree)
    assert all(newcu.get(u) == c for u, c in oldcu.items()), "Changed old fan/clock/ADC/return copper"
    assert children(parent, "gr_line") == children(tree, "gr_line"), "Changed board outline"
    for tag in ["general", "layers", "setup"]:
        assert children(parent, tag) == children(tree, tag), ("Changed stack/rules", tag)
    oldzones = {
        first(z, "uuid")[1]: [n for n in z if not isinstance(n, list) or not n or n[0] != "filled_polygon"]
        for z in children(parent, "zone")
    }
    newzones = {
        first(z, "uuid")[1]: [n for n in z if not isinstance(n, list) or not n or n[0] != "filled_polygon"]
        for z in children(tree, "zone")
    }
    assert oldzones == newzones, "Changed zone/clip contracts (refill alone permitted)"
    clips = [
        z
        for z in children(tree, "zone")
        if children(z, "name") and str(first(z, "name")[1]).startswith("MOUNT_CLIP_")
    ]
    assert len(clips) == 16
    for z in clips:
        keep = first(z, "keepout")
        assert all(first(keep, k)[1] == "not_allowed" for k in ["tracks", "vias", "pads", "copperpour"])
    assert not [t for t in children(tree, "segment") if first(t, "layer")[1] == "In1.Cu"]
    assert all(float(first(t, "width")[1]) >= 0.2 for t in children(tree, "segment"))
    _, pins = netlist(ROOT / "generated/netlist.xml")
    assert not topology(pins), topology(pins)
    return dict(
        parts=91,
        parent84_complete_footprints_exact=True,
        parent_all_copper_exact=True,
        all16_clip_and_allzone_contracts_exact_except_refill=True,
        In1_signal_tracks=0,
        native_stage_topology_differences=0,
        physical_qualified=False,
        fabrication_released=False,
    )


if __name__ == "__main__":
    print(json.dumps(validate(read_sexpr((ROOT / "fan_power_health.kicad_pcb").read_text())), indent=2))
