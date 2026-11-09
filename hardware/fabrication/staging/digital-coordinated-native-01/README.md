# Coordinated digital routing trial

This is a verified intermediate, not the selected DC04 layout or a fabrication
release. It rebuilds the signal routing from DC03 so the SD interface and LED
pin exits can be planned together. The selected four-layer checkpoint remains
`digital-four-clean-native-03` with 143 opens.

The trial moves fourteen resistors, replaces the long SD supply branch and
seven ground connections, connects the three local LED pull-downs, and adds
82 LED output escapes. It preserves all 201 power/ground pad connections,
39 local connections and 33 thermal connections. Native hierarchy, parity and
electrical-rule checks pass. Native DRC reports 236 open connections and 82
explicit dangling-via warnings at the unfinished LED exits, with no geometry
errors. The warnings remain enabled and are not fabrication waivers.

All six SD carrier paths are connected, each with one 0.60/0.30 mm via and
0.20 mm tracks. Compared with selected DC04, carrier planar length spread
falls from 36.703 mm to 5.999 mm:

| Signal | Carrier planar copper, mm | Vias |
| --- | ---: | ---: |
| D0 | 68.225 | 1 |
| D1 | 67.721 | 1 |
| D2 | 66.720 | 1 |
| D3 | 72.719 | 1 |
| CMD | 69.655 | 1 |
| CLK | 70.628 | 1 |

These figures exclude Seed/module wiring, socket, component, barrel and
off-board/card paths. They establish a routing improvement, not an interface
timing, impedance or signal-integrity qualification. The changed SD supply
branch also requires the final load and voltage-drop assessment.

The independent `corridor-audit.json` checks the actual changed component set,
all 138 electrical courtyards, edge/mount clearances and opposite-face THT
solder reserves. It checks all 218 via drills against both faces' SMD copper,
including same-net lands. The minimum non-exempt hole-edge gap is 0.154984 mm.
The 21 unchanged vias in mask-covered LED heat-spreader copper retain their
separate process hold. Complete component-height, mating and installed
assembly acceptance remain open. `conditional-assembly-review.json` also
rechecks all 138 component envelopes and five mounts against the retained AP04
context and floor; no conditional collisions occur.

Source-bound evidence is in `review.json`, `stage-connectivity-review.json`
and `corridor-audit.json`. The actual front, back, ground and power PDFs in
`plots/` were rendered and visually reviewed. Whole-unit source audit passes
for all fifteen roles, and thirteen digital integration/annotation regression
tests pass.

The first protected four-layer global pass is preserved separately in
`digital-coordinated-signals-native-01`: 194 opens, one 0.1779 mm clearance
error against the 0.20 mm rule, 110 dangling vias and one dangling track.
That output is rejected for selection. The resulting
[clean six-layer comparison](../digital-coordinated-six-clean-native-01/README.md)
has 117 opens and zero native geometry/parity/ERC findings. It retains the
corrected SD paths and closes substantially more LED nets; other interfaces
and the actual six-layer stack still require work. Selected DC04 is unchanged.

The subsequent [interface completion checkpoint](../digital-interface-clean-native-02/README.md)
reduces the count to **75 opens**, with zero geometry/parity/ERC findings and
preserved SD/power/local/thermal connections. It adds a screened 0.8 mm J1001
shift and rechecks conditional assembly receiving. Remaining routing and the
actual six-layer stack remain unfinished. The subsequent
[clock-source rework](../digital-clock-series-clean-native-01/README.md) reaches
74 opens while preserving every previously connected net.

Current whole-unit evidence selects audio `audio-main-controls-01`: 376 opens,
all 200 placed ground pads connected, and one missing ESS codec footprint.
NF retains 138 opens and two explicit isolated-domain ground ERC warnings.
E28/P03 process acceptance, complete mating/harness/support/case receiving,
power/noise/stability/thermal qualification, manufacturing outputs and
first-article verification remain unfinished. Nothing here releases the unit
for manufacture or power-up.

The older `hardware/qualification/generated/plan.json` explicitly targets
E14/E25 baseline interfaces and treats P01 as an unimplemented proposal.
It is not a current P03/E28/AC04/DC04 first-article plan. Its existence cannot
close the current unit's qualification-plan requirement.
