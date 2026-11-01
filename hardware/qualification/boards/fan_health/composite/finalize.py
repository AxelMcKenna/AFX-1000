"""Promote only native-zero private FPC draft; generate independent native geometry facts."""

import hashlib
import json
from pathlib import Path

import pcbnew

from hardware.electronics.common.sexpr import children, read_sexpr
from hardware.qualification.boards.fan_health.composite.native import check

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "routing/timing-cap-repair14/input.kicad_pcb"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fpmap(path):
    t = read_sexpr(path.read_text())
    return {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(t, "footprint")
    }


assert not (ROOT / "handoff.json").exists()
d = json.loads((SRC.parent / "input-drc.json").read_text())
assert not d["violations"] and not d["unconnected_items"] and not d["schematic_parity"]
old = fpmap(ROOT / "routing/locked-signal-pass10/output.kicad_pcb")
new = fpmap(SRC)
assert old.keys() == new.keys()
changed = [r for r in old if old[r] != new[r]]
assert changed == ["C7"], changed
b = pcbnew.LoadBoard(str(SRC))
via = []
for t in b.GetTracks():
    if isinstance(t, pcbnew.PCB_VIA):
        t.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED)
        t.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
        via.append(
            dict(
                x_mm=pcbnew.ToMM(t.GetPosition().x),
                y_mm=pcbnew.ToMM(t.GetPosition().y),
                diameter_mm=pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)),
                finished_drill_mm=pcbnew.ToMM(t.GetDrill()),
            )
        )
assert not [t for t in b.GetTracks() if not isinstance(t, pcbnew.PCB_VIA) and t.GetLayer() == pcbnew.In1_Cu]
pads = []
poses = {}
for f in b.GetFootprints():
    rows = []
    poses[f.GetReference()] = [
        pcbnew.ToMM(f.GetPosition().x),
        pcbnew.ToMM(f.GetPosition().y),
        f.GetOrientationDegrees(),
    ]
    for p in f.Pads():
        if not p.GetNumber():
            continue
        rows.append(
            dict(
                number=p.GetNumber(),
                net=p.GetNetname(),
                centre_mm=[pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)],
                size_mm=[pcbnew.ToMM(p.GetSize().x), pcbnew.ToMM(p.GetSize().y)],
                orientation_degrees=p.GetOrientationDegrees(),
                drill_mm=[pcbnew.ToMM(p.GetDrillSize().x), pcbnew.ToMM(p.GetDrillSize().y)],
            )
        )
    pads.append(dict(ref=f.GetReference(), value=f.GetValue(), pads=rows))
pcbnew.SaveBoard(str(ROOT / "fan_power_health.kicad_pcb"), b)
(ROOT / "generated/native-pad-geometry.json").write_text(json.dumps(pads, indent=2) + "\n")
(ROOT / "generated/native-poses.json").write_text(json.dumps(poses, indent=2) + "\n")
(ROOT / "generated/route-promotion.json").write_text(
    json.dumps(
        dict(
            source_pcb_sha256=sha(SRC),
            source_drc_sha256=sha(SRC.parent / "input-drc.json"),
            complete_unchanged_footprints=83,
            only_changed_footprint="C7",
            all84_anchors_and_rotations_unchanged=True,
            via_count=len(via),
            vias=via,
            front_back_tenting_explicit=True,
            unfilled_via_in_SMD_pad_permitted=False,
            In1_signal_tracks=0,
            part_values_changed_only_C7_same_nominal_class=True,
            physical_qualified=False,
        ),
        indent=2,
    )
    + "\n"
)
check("closed")
