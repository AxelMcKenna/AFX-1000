# ARMED pull-down routing checkpoint — 48 opens

Moving R1005 from back (40,16) mm to back (27.5,29.5) mm connects the previously
isolated ARMED pull-down. The footprint, pin assignments and orientation are
unchanged. Its new signal connection adds 1.574 mm of copper and one conventional
via; its ground connection adds 1.010 mm and one conventional via. Three new
0.20 mm segments and two 0.60/0.30 mm vias preserve all existing copper, including
the former ground junction serving R1003. No circuit values or rules changed.

Native Linux KiCad 10.0.7 reports **48 opens across 47 nets**, down from 49,
with zero geometry, schematic-parity and ERC findings and all categories enabled.
There are 2,616 tracks and 470 vias. Thirty-five LED output nets remain open.
Selected DC04/AP04 remain unchanged. The complete unit is not fabrication-ready.

The exact-delta audit verifies that R1005 only translates, all other footprints
and old copper remain exact, and the native additions match the construction
recipe. Every previously connected pad group survives; ARMED is the sole net
whose disconnected groups merge. All 201 power/ground pads, 39 local connections
and 33 thermal branches remain connected. All four planes retain one physical
copper union, and all 21 heat-spreader vias retain their process hold. Minimum
non-exempt drill-edge-to-SMD gap remains 0.154984 mm.

SD carrier length spread stays 5.999 mm with one via per signal. LED_SCK stays
46.620 mm/two vias. The earlier data-series tradeoff remains unchanged: 16.753 mm
before R3015 and 103.539 mm after it, totaling 120.292 mm versus 88.840 mm before
the relocation. I2C loading/rise time, data-source damping/timing and all complete
interface behavior remain unqualified.

Conditional AP04 context/floor receiving passes for 138 parts and five mounts.
All eight copper plots and a 1200 dpi back-side detail were inspected. All 32
focused tests pass, including rejection of a removed old ground-junction segment,
a changed resistor net and moved old copper. The independent audit replays the
parent checkpoint and screens every new segment and via against actual geometry.

Evidence: [native findings](review.json), [all-net connectivity](stage-connectivity-review.json),
[placement/drill/SD/plane checks](corridor-audit.json),
[exact relocation and connectivity audit](armed-review.json),
[visual review](visual-review.json), [conditional receiving](conditional-assembly-review.json),
and [construction recipe](../digital-armed-repack-01/construction.json).

The initial `digital-armed-native-01` run used the single-sheet reviewer and
stopped at its circuit-export assertion because child sheets were absent. It is
not an accepted result. This `-02` run uses the hierarchy-aware reviewer and
checks all three child sheets. The `digital-armed-inputs-48b` capture uses absolute
source paths for the independent source-hash audit.

Next work is the remaining isolated control pull-downs and LED/control escapes.
The current audio checkpoint has 219 opens and still lacks the approved ESS land;
negative protection has 138 opens and two visible isolated-domain ground warnings.
Accepted stack/process, actual assembly receiving, full electrical/thermal/fault
qualification, inspected manufacturing outputs and a current first-article
package remain open. See the [current unit inventory](../../README.md).
