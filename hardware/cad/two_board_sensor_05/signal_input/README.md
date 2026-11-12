# Analog input routing candidate r7

Selected output is `native-r7/signal_main.kicad_pcb`, based on the previously checked I2C r4 board. It closes all **16 internal input-stage opens across ten nets** while retaining every previous authored PCB object and every schematic net partition. Native KiCad reports zero geometry/ERC findings, no input-stage opens, **230 other opens**, and the unchanged missing A_U201 ES9292QPRO footprint. This is a bounded routing checkpoint, not fabrication or analog-performance acceptance.

## Routing and references

The affected nets are `/A_INPUT/ATTN_L/R`, `BUF_IN_L/R`, `BUF_OUT_L/R`, `HP_SRC_L/R`, and `RANGE_L/R`. Existing gain-feedback connections, all component positions/values, board outline and connectors remain unchanged. The actual source places U401 on the front and most input passives on the back; the routing respects those actual pad sides.

The candidate adds 39 trace segments, 12 signal through-vias and 13 ground through-vias. Traces are 0.2 mm wide; new vias are 0.6 mm copper diameter with 0.3 mm drill. Exact endpoints, net names, widths, layers and deterministic UUIDs are in `candidate-r7/routing.json` and the native PCB. Most joins use F.Cu/B.Cu. Two joins use In3.Cu; the right pre-coupling connection uses In5.Cu. No blind or buried vias are assumed.

Front traces use the existing analog In1 ground. New local reference corridors on In4 and In6 serve the inner and back traces. The 16 new zone outlines use priority1, 0.2 mm clearance, 0.25 mm minimum copper thickness, 0.25 mm thermal gap and 0.5 mm thermal bridge width. Native filled area totals are112.821430 mm² on In4 and92.862454 mm² on In6. Corridors are derived from1.2 mm buffers around the relevant routes and0.7 mm buffers around local return connections. These are local additions, not a claim that the full analog ground system is now complete.

All new ground stitches join the already connected analog ground group through existing In1 copper. They do not introduce another analog/digital boundary connection: the existing MCU-control join is unchanged. The new fields create parallel local returns within the analog area, which must be considered in noise/current-distribution review. Seventeen native filled-zone records change: the16 new reference zones and the existing analog In1 plane, whose new signal-via clearances remove9.539578 mm². Full before/after areas and every local contact are recorded in `transitions-r7.json`; every previous authored zone remains exact.

Fifteen signal-transition locations have explicit nearby grounded PTH/via paths. Existing return connections are reused within1.5 mm; additional ground stitches use the closest screened0.1 mm-grid location with a2.5 mm design-distance allowance. The longest selected return distance is2.459675 mm. These are engineering allocations rather than device-manufacturer limits or a signal-integrity proof. The native transition check verifies the same ground group as D_U1001.20, direct filled-copper contact on In1/In4/In6, and continuous local0.2 mm return corridors outside each signal antipad. All15 cases pass. The report contains the exact locations and original nearest-return distances, so no distant return has been silently waived.

## Analog review and limits

TI recommends short input and feedback routing, local bypassing and separation from output/supply traces. This repair preserves all original amplifier feedback/bypass objects and screens the new geometry against those constraints; it does not certify the inherited placement or physical amplifier behavior. See the [OPA165x datasheet, sections8.4.1–8.4.2](https://www.ti.com/lit/ds/symlink/opa1656.pdf).

The first native-clean candidate r6 placed opposite-channel sensitive nodes on In3 within1 mm for approximately4.998 mm, with minimum centerline separation0.428110 mm. Self-review rejected that arrangement. r7 moves only the right pre-coupling route to In5, with actual filled In4 ground between it and the left amplifier input. Native DRC and all reference checks are repeated for r7; the earlier pass is not reused as acceptance of changed geometry.

`analog-review.json` records the complete input-net trace lengths: left24.641752 mm with two signal vias; right9.649706 mm with one. The remaining same-layer input/output/supply/opposite-channel proximity screen finds only a short opposing-input escape proximity near U401:0.919582 mm minimum center distance, with approximately0.139/0.203 mm of the respective traces within1 mm. This is an auditable geometric observation, not a crosstalk limit. The unequal branch lengths, via capacitance, actual dielectric stackup, RF behavior, complete grounding, signal settling, amplifier stability and measured noise/distortion/channel separation still require electrical qualification. No parasitic capacitance or semiconductor simulation is invented from the drawing.

## Evidence and reproduction

- `native-r7/review.json`: native parity, ERC/DRC, exact old objects,230 remaining opens.
- `reference-review-r7.json`: all original connectivity groups retained; only the ten intended input nets merge; new route reference coverage and preservation of previously covered tracks.
- `transitions-r7.json`:15 source-bound local return paths and all changed filled planes.
- `fidelity-r7.json`:134 independent fractured/unfractured native-polygon checks.
- `analog-review.json` and `preview-r7.png`: geometry/proximity review and inspected native copper projections.

Use the pinned isolated Linux KiCad workflow; never launch host CAD. `plan_multilayer.py` creates r5 signal routes, `reference.py` adds r6 returns, and `separate_channels.py` produces r7. `native_r7.py`, `capture_r7.py`, `review_r7.py`, `transitions_r7.py` and `fidelity_r7.py` produce the selected native/reference evidence. Failed front-only and early layer-planning records are retained as history, not competing selections. Final analog and complete-board acceptance remain open even when these bounded routing checks pass.
