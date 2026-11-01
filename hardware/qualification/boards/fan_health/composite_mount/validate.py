"""Read-only mechanical/electrical invariants for the clip-compatible PCB."""

import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent


def copper(tree, omit_raw=False):
    return {first(n, "uuid")[1]: n for tag in ["segment", "via"] for n in children(tree, tag)
            if not omit_raw or first(n, "net")[1] != "/FAN5V_IN"}


def validate(tree):
    parent = read_sexpr((ROOT / "sources/parent-fan_power_health.kicad_pcb").read_text())
    assert children(tree, "footprint") == children(parent, "footprint"), "Changed complete footprint geometry/pose/value"
    assert len(children(tree, "footprint")) == 84
    assert copper(tree, True) == copper(parent, True), "Changed unrelated clock/sensor/logic/return copper"
    areas = {first(z, "name")[1]: z for z in children(tree, "zone")
             if children(z, "name") and str(first(z, "name")[1]).startswith("MOUNT_CLIP_")}
    expected = set()
    for center in [17., 54.5]:
        for edge, y0, y1 in [("BOTTOM", 0., 1.65), ("TOP", 36.35, 38.)]:
            for layer in ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]:
                name = "MOUNT_CLIP_" + str(center) + "_" + edge + "_" + layer
                expected.add(name)
                assert name in areas, "Missing all-layer clip keepout"
                z = areas[name]
                assert first(z, "layer")[1] == layer
                keep = first(z, "keepout")
                for tag in ["tracks", "vias", "pads", "copperpour"]:
                    assert first(keep, tag)[1] == "not_allowed", (name, tag)
                pts = first(first(z, "polygon"), "pts")
                actual = [[float(v) for v in xy[1:]] for xy in pts[1:]]
                assert actual == [[center - 3.6, y0], [center + 3.6, y0],
                                  [center + 3.6, y1], [center - 3.6, y1]], name
    assert set(areas) == expected and len(areas) == 16
    assert not [n for n in children(tree, "segment") if first(n, "layer")[1] == "In1.Cu"]
    assert all(float(first(n, "width")[1]) >= .2 for n in children(tree, "segment"))
    for via in children(tree, "via"):
        assert float(first(via, "size")[1]) >= .65 and float(first(via, "drill")[1]) >= .3
    return dict(parts=84, complete_parent_footprints_exact=True,
                unrelated_parent_copper_exact=True, clip_keepout_records=16,
                In1_signal_tracks=0, physical_qualified=False, fabrication_released=False)


if __name__ == "__main__":
    print(json.dumps(validate(read_sexpr((ROOT / "fan_power_health.kicad_pcb").read_text()))))
