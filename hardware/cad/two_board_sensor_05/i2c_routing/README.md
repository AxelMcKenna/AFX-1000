# I2C routing and control-return candidate r3

Selected output is `native-r3/signal_main.kicad_pcb`. It closes all four baseline I2C opens, with zero new native geometry findings and exact schematic netlist partitions. It also joins the two existing LINK_AGND islands at the documented MCU control return. This substantive ground-topology change is a candidate for integration review, not noise qualification or fabrication release. The board retains 246 other opens and the missing A_U201 ES9292QPRO footprint.

## Changes and physical return topology

All new signal traces are 0.2 mm wide. Coordinates are native PCB millimetres:

| Connection | Layer | Path |
|---|---|---|
| SCL pullup | B.Cu | (177.5,81.4125) → (177.5,87) → (175,87) |
| SDA pullup | B.Cu | (172.5,81.4125) → (175,84.5) |
| SCL bridge | In3.Cu | (175,87) → (189.160625,83.70625) |
| SCL existing-trunk escape | B.Cu | (191.660625,83.70625) → (189.160625,83.70625) |
| SDA bridge | In3.Cu | (175,84.5) → (188.5,68.9) |

One new SCL through-via at (189.160625,83.70625) has 0.6 mm copper diameter and 0.3 mm drill. SDA uses an existing via. Existing A_J402.3/.4 plated holes supply the other B/In3 transitions. Added lengths are 25.126141 mm SCL and 24.603056 mm SDA; these must enter the final capacitance calculation.

Two new LINK_AGND zones on In4.Cu and In6.Cu reference the In3 and B routes. Their identical outlines combine a 1 mm buffer around the new routes (nominal 2 mm corridors) with a landing rectangle X171..179/Y80..94. Each filled zone has area 148.95958473584 mm². Full vertices and contact records are in `return-review-final.json`. New zones use priority 1, 0.2 mm pad clearance, 0.25 mm minimum thickness, 0.25 mm thermal gap, and 0.5 mm thermal bridge width. Existing priority-0 authored zones are unchanged; their fills are recomputed.

Both new zones directly contact only existing grounded pad A_J402.1 at (175,92), a plated 1.7 × 1.95 mm round-rect pad with 0.95 mm drill spanning all copper layers. They connect the digital ground field through same-layer zone overlap. The report records the overlap area, every old ground member, and native connectivity. The original 200-pad analog island and 121-pad digital island become one 321-pad group. No other ground net is joined and no component, isolation element, or existing trace is removed or bypassed by a new net alias.

Physical location is supported by `hardware/fabrication/staging/audio-main-integration-04b/audio-leg-connections.csv`: MCU-CONTROL connects J402.1 to digital_core J1006.1 AGND alongside SCL/SDA on J402.3/.4. J402.7 belongs to RAIL-HEALTH and is deliberately not contacted by the r3 additions. Other scheduled SAI/bypass/input-ready ground connections remain unchanged. Processor-carrier and converter documentation call for joined local grounds and continuous returns. This establishes a plausible control-return location; it does not establish analog noise, codec performance, high-current current distribution, or adequacy of a complete signal-board ground system. The new thermal connection is not designated a power-current path.

## Verification and limits

`native-r3/review.json` records pinned Linux KiCad 10.0.7 verification, exact old authored-object preservation, exact all-netlist partitions, zero native geometry findings and 246 opens. `return-review-final.json` independently compares native groups: only SCL (3→1), SDA (3→1), and AGND (2→1) merge; no original group splits. Five new route cases have complete adjacent-layer ground coverage outside same-net plated transitions. All 4,826 previously covered non-ground track cases lose zero covered area, within the explicitly recorded 0.0015 mm geometric tolerance. This coverage check preserves geometric support; it is not an impedance/current/noise simulation. `fidelity.json` separately checks the native fractured-to-unfractured polygon conversion used by this review.

The candidate adds copper on B.Cu and In3.Cu and new reference zones on In4.Cu/In6.Cu. All pre-existing authored objects remain exact. Full refill can alter fill polygons on existing planes; the coverage review checks every adjacent layer, and native connectivity checks every old group. `preview-r3.png` shows actual native filled reference fields and routes.

The earlier `i2c_bus` audit's 150 pF total and 30 pF harness allocations remain proposed acceptance budgets. Neither added trace length nor filled ground geometry proves capacitance without a specified dielectric stackup. Preserve 400 kHz firmware operation; actual board/device/cable loading, VOL and rise time require closure before release. Missing codec footprint/routing, remaining board routing, final harness and physical noise/timing tests remain open.

## Reproduction and retained history

Use `run_linux.py` with the pinned Linux image; never launch Mac CAD. `capture.py` captures immutable signal03. `plan.py` produces r2, then `refine_reference.py` produces r3. `native.py` verifies r3; `capture_after_r3.py` captures its filled geometry. Host `review_final.py`, `fidelity.py`, and `preview.py` consume those artifacts. Use fresh output directories for new native runs.

r1 is rejected because equal-priority new zones produced native overlap errors. r2 resolves priority but contacts the rail-health return; it is retained only as history. r3 moves the direct ground attachment to the documented control return and narrows the reference corridors. Only r3 is the selected candidate. `review.py` is an earlier, slower equivalent review; `review_final.py` caches reference unions and produces the selected report.
