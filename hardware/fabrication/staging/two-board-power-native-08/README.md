# TBP08: module-input branch and return-star candidate

The combined power schematic now includes a dedicated feed for both TMR 1-1215
modules and a separate primary force return through a copper net tie.
**This branch is not accepted for fabrication:** fault review identified a
post-short output-undervoltage condition that requires a different cutoff
strategy. The complete two-board unit remains unfinished.

Open [power_protection.kicad_pro](power_protection.kicad_pro).

| Native check | Result |
| --- | --- |
| Electrical parts / schematic pin entries | 1,090 / 3,413 |
| Footprints, including 15 mechanical | 1,105 |
| Physical pad instances mapped | 3,478 |
| Native geometry / schematic-parity findings | 0 / 0 |
| ERC | 0 errors; 2 retained floating-reference warnings |
| Open connections | **2,707** |
| Original parts / full footprint geometries preserved | 1,077 / 1,092 |

## Circuit captured

P_U101.17/.18 and P_C103.1 supply G_U1, a TPS259474LRPWR eFuse. Its output feeds
N_U17.2, N_U22.2 and the existing module input filters. This supply is available
before NF GLOBAL_MASTER; no final-enable dependency is introduced. The 13 new
parts comprise the eFuse, five resistors, four capacitors, two clamps and one
copper net tie. No physical part from TBP06 is removed or changed. The former
external-input power flag is removed because G_U1 now supplies that net.

G_NT1 joins PWR_MODULE_INPUT_GND to PWR_AGND. Its system-ground end must return
at P_C103.2. It is the only declared primary-return connection; there is no
local NF quiet-ground tie. The star currently sits near the bulk capacitor as
an **unrouted placement placeholder**. The new cell is also provisionally placed,
well away from its final electrically optimized location. Neither placement
establishes current-loop, ground-drop, thermal or housing acceptance.

The [independent audit](module-feed-audit.json) checks every new pin, preserves
the original complete pin partition and all 1,092 prior footprint geometries,
maps all physical pads, and rejects seven incorrect wiring variants. It also
rechecks the earlier 32 fault/reset cases, two source-sense channels and 64
settled UV-fault cases. The RPW footprint matches the reviewed manufacturer's
copper dimensions and stencil example; process acceptance remains open.

TBP07's first native check found nine new-cell spacing errors, three Datasheet
field mismatches and 46 schematic-grid warnings. TBP08 corrects those findings
without suppressing any check. [Native results](review.json) are independently
bound to the actual checked files.

## Electrical screens and unresolved fault

With a declared total resistance budget of 0.5% and the specified threshold and
input-leakage limits, the input branch enables at 10.466–11.111 V, disables on
falling input at 9.515–10.143 V and disables on rising input at 13.879–14.710 V.
These are conditional on the passive budget and local reference. The proposed
12 V ±5% supply window and 0.10 V branch-distribution allowance still need
acceptance against the complete supply and layout.

The nominal current limit is 0.514 A. Scaling the manufacturer's 6.65 kΩ test
row to the chosen 6.49 kΩ produces a 0.433–0.592 A **model screen**, not a new
guaranteed test row. The nominal output ramp is 28.2 ms to 12 V. A 0.35 A total
load and 60 µF total output capacitance fit a conditional charging-current
screen, but the modules' startup/internal capacitance and minimum efficiency
are not bounded by the available table. Exact passive order codes, effective
capacitance, surge behavior and per-module fault containment remain open.

Most importantly, the selected eFuse does not latch immediately on every short.
After fast trip it can restart in current limit. The audit records a hypothetical
12 V input / 8.7 V output case whose typical thermal model does not reach thermal
shutdown. Input undervoltage sensing cannot detect that output sag. This is an
identified protection gap, not evidence that a real unit was tested or failed.
The [cutoff review](../two-board-module-cutoff-review-01/README.md) identifies
TPS26601 in its timer-operated latch-off mode as the next candidate. It has not
yet replaced G_U1; its pin map, return reference, current/slew settings, land
pattern and circuit must be implemented and checked.

## Remaining work

Resolve the module cutoff and receiving limits, then complete loaded AUX,
reference/sense/clamp, high-temperature logic and deep-UV/minimum-OFF reviews.
Optimize critical power placement and route both boards; finish the signal/power
interface and ESS codec land pattern. Complete the manufacturing BOM/stack/
process and fabrication files, full installed-fit/support/cooling checks and
prototype inspection/bring-up plan. Prototype measurements belong in that plan;
they are not represented as measurements of an unbuilt unit.

The [native module-sheet SVG](plots-module/G_module_input.svg) was inspected.
Its long G_NT1 pin names overlap and should be shortened in the next circuit
revision. The hierarchy-cover export in `plots/schematic/` is not the module
sheet; the direct export linked here is the correct visual reference.
