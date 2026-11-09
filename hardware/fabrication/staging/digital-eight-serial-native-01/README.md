# Eight-layer digital checkpoint — 49 opens

The latest separate digital trial has **49 open connections across 48 nets**,
down from [52](../digital-eight-led-clean-native-01/README.md). Native Linux
KiCad 10.0.7 reports zero geometry, schematic-parity and ERC findings with all
categories enabled. Selected DC04/AP04 remain unchanged. The board and complete
unit are not ready for fabrication.

Three additive connections close SCL, DATA_5V_SRC and SERIAL_2. They add 61
segments and five conventional 0.60/0.30 mm vias. Every earlier copper object,
component pose, mount, outline, authored zone and connected pad group survives.
The final board has 2,591 tracks and 466 vias. Thirty-five LED output nets remain
open, together with thirteen other nets; LED_BLANK has three disconnected groups.

| Connection | Added planar copper | New vias | Electrical review still required |
| --- | --- | --- | --- |
| SCL | 60.889 mm | 1 | Full bus capacitance, pull-ups, rise time, speed and harness |
| DATA_5V_SRC | 52.091 mm | 2 | Series-resistor placement, source damping and timing |
| SERIAL_2 | 18.807 mm | 2 | Driver/receiver timing, loading and reference transitions |

SCL now has **202.814 mm total planar copper and five vias**, across its branched
net; this is not a measured end-to-end delay. SDA retains 164.559 mm/fourteen vias.
These are explicit electrical-review items. The data source resistor R3015 is
still remote from the buffer; completing its copper does not establish suitable
series damping. Coordinated resistor/escape rework and an interface budget remain
necessary before this board can be accepted electrically.

The shorter LED_SCK route remains exactly 46.620 mm/two vias. All 201 power/ground
pads, 39 local connections and 33 thermal branches remain connected. SD carrier
spread is 5.999 mm with one via per signal. All four filled planes have one
physical polygon union each. Minimum non-exempt drill-edge-to-SMD-copper gap
remains 0.154984 mm; 21 mask-covered heat-spreader vias keep their process hold.
Conditional AP04 context/floor receiving passes for 138 parts and five mounts.
Actual purchased parts, supports, mates and harnesses remain unverified.

A continuous-geometry search found legal via regions missed by the 0.25 mm
escape grid. A boundary-visibility search found the SERIAL_2 exits that a
0.05 mm local raster missed. Every emitted line is checked against the actual
copper screen and then independently checked by native KiCad. No clearance,
width or hole rule was relaxed. Four new geometry regression tests cover narrow
via regions, disconnected surface regions, visibility detours and real layer
transitions; all 24 focused tests pass.

An exploratory LED_49 connection took a 124.058 mm detour. It was removed from
the retained candidate; its 65 segments and one via remain only in the immutable
trial. A subsequent In3 search on thirteen LED nets produced no joins. These
bounded searches do not prove unroutability. Further progress calls for
coordinated copper/placement changes and better escape access, rather than
repeating the same fixed-geometry search.

Evidence: [native results](review.json), [all-net witnesses](stage-connectivity-review.json),
[placement/drill/SD/plane audit](corridor-audit.json),
[final additive delta](additive-route-review.json),
[complete evidence-chain replay](checkpoint-review.json),
[eight full copper plots plus fine-pitch detail](visual-review.json),
[conditional receiving](conditional-assembly-review.json), and
[search outcomes](routing-search-review.json).

The next design work is the blocked control/LED exits, the remote data-series
resistor and long bus paths, followed by electrical interface acceptance.
For the complete unit, the selected audio board still has 267 opens and the
missing ESS land; negative protection has 138 opens and two explicit isolated
ground warnings. Stack/process, actual assembly receiving, power/noise/fault/
thermal qualification, inspected manufacturing outputs and a current first-
article inspection/bring-up package remain incomplete. The nominal 1.6 mm
setting is not an accepted eight-layer stack. See the [unit inventory](../../README.md).
