# TBP73 individual placement and DSE cross-check

This checkpoint replaces the coarse reservations with an **unrouted proposal for all 18 added parts** on the frozen TBP73 candidate (`two-board-power-aux-local-distribution-native-03`). Existing copper, footprints, fills and accepted board files are not edited. All proposed courtyards clear the captured board obstacles and each other; this is not evidence of a complete power layout.

## Independent DSE drawing interpretation

`dse-review/ti-page38.svg` is an unannotated vector rendering of the cached TI primary PDF page 38. `annotated-page38.svg` adds a separate review column; `check.py` measures original vector paths without reading the authored footprint dimensions. At the drawing's 40:1 scale, pin 1's blue transverse extent is **0.2500106 mm**, and its surrounding green extent is **0.3499873 mm**. The small deviations from 0.25/0.35 mm are PDF vector coordinate rounding.

The 0.25 mm dimension extension lines end at the **blue exposed-area boundaries**. The lower detail explicitly identifies pads 1–3 as solder-mask-defined: on these pads the blue boundary is the mask opening and the green boundary is copper extending under mask. Therefore the required minimum 0.05 mm overlap on each side is **additional**, not already contained in 0.25 mm. Copper is at least 0.35 mm wide; at 0.5 mm pitch the nominal copper gap is at most 0.15 mm. Pads 4–6 use the opposite relationship: blue is copper, green is mask opening. Color alone does not identify the same material on both banks. The independent stencil example on page 39 repeats the 0.25 mm exposed aperture. `vector-check.json` records the exact source hash, path counts, bounds and arithmetic.

This substantiates the conflict with the current 0.20 mm copper rule. It does not authorize a local exception, establish a fabricator capability or prove mask-registration tolerance. No footprint dimensions have been changed merely to remove the finding.

## Individual component locations

The greedy search uses nonoverlapping six-part buck, nine-part held-supply and three-part main-detector templates. It searches 0.5 mm anchor increments and four rotations on both surfaces, stopping at the nearest available anchor for each template; it does **not** claim a global placement optimum. Each later template excludes earlier chosen courtyards. Passive orientations were subsequently corrected where a 180-degree change removes a pad-order crossing without changing the courtyard.

| Group | Principal B.Cu positions, mm | Remaining physical constraint |
|---|---|---|
| Buck | P_U900 (193.5,147.5), P_C900 (193,143.4), P_L900 (193,151.6), P_C901 (197.4,151.6) | Return escape and feedback/Kelvin routing; thermal pad/vias; 4.1 mm maximum inductor height |
| Held supply | P_C902 (152,171.5), P_C905 (152,165.9), P_U901 (145,168.7), P_R902 (152,176.6), P_U902 (145,172.7) | Bulk caps 3.1 mm maximum height; long 5 V input/sense and held output distribution; resistor pulse heat and LDO thermal spreading |
| Main detector | E_U900 (100,164.5), E_C900 (103,164.5), E_R900 (100,166.7) | DSE rule conflict, main-AUX sense connection, reset loading and narrow-pitch escape |

All resistor/bypass coordinates and exact footprint assignments are in `individual-placement.json`; `individual-placement.png` is a reviewed figure showing the three groups against existing obstacles. The accepted board remains unchanged.

The JSON's `rotation_deg` is the mathematical clockwise rotation **after reflecting local X for B.Cu**. It is not directly the KiCad angle after a left-right flip. Use the separate `kicad_orientation_degrees_after_left_right_flip` field: native KiCad requires an additional 180 degrees for these back-face transformations. `native_poses.py` loads all 18 footprints into an in-memory board, flips them, applies those native angles and exports the actual pads without saving any PCB. Every pad agrees with the independently calculated coordinates within 2.85e−14 mm. The minimum proposed courtyard separation is 0.225 mm. The native report binds the exact proposal hash.

## Paths and loop constraints

`path-screen.json` evaluates 28 declared same-net connections using the native candidate netlist. These are **straight centerline probes**, not tracks. Each uses a 0.3 mm width and 0.20 mm clearance against captured foreign surface copper and proposed foreign pad rectangles, conservatively including rectangular pad corners. It also records mutual centerline conflicts. Same-net existing copper and the explicit endpoint pads are excluded from foreign-copper checks. Filled zones, returns, vias and actual route completion require separate native/reference checks.

Seventeen probes clear captured existing copper; only eleven clear both captured copper and proposed foreign pads. Ten pairs of different-net probes conflict with each other. The input-capacitor/VIN link is 1.675 mm and SW-to-inductor is 1.965 mm; neither makes the loop qualified. The input-loop vertices span 1.15625 mm², but its naive ground centerline crosses the VIN pad/capacitor positive pad. A ground escape around those pads and the actual reference/thermal copper are required. The output return and feedback connections similarly need explicit routes. The DSE fine-pitch region cannot be accepted merely because selected probe widths fail or pass.

The buck-output to reservoir feed is approximately **49.9 mm**, and the buck-output to held-cell 5 V monitor SENSE is **57.8 mm**. These straight probes intersect existing copper. The wired-OR supervisor RESET link is **46.8 mm** before detours; the held-output to the farthest Si8751 VDD is **113.4 mm**. The 10 pF reset-loading condition and 20 mV distribution allocation are therefore not established.

As a sensitivity calculation only, 0.3 mm-wide, 35 µm-thick copper at 125 °C using ρ20 = 1.724e−5 Ω·mm and α = 0.00393/°C gives 2.3194 mΩ/mm. A 113.4 mm outward conductor carrying the conditional 100 mA screening allocation would drop about **26.3 mV before its return or vias**. At least approximately 0.395 mm width is needed for that outward leg alone to stay below 20 mV under those assumptions. Neither foil thickness/temperature nor actual load/current sharing is qualified; this calculation cannot substitute for extracted supply and return resistance.

**Decision:** retain these as component-level geometric candidates, not a layout to promote. A practical implementation needs a routed buck return/feedback cell, wider or plane-based held distribution, a deliberate reset path with measured/extracted capacitance, and either a more favorable held-cell placement or a narrowly scoped existing-placement revision. Do not claim that merely fitting the 18 courtyards resolves the held-rail voltage/timing, fabrication or housing constraints.

## Verification

Primary vector dimensions were rechecked separately from the footprint generator. Native KiCad 10.0.7 validates all 18 poses and exact pin sets; the frozen TBP73 capture/PCB hash pair is checked before placement verification. Six tests pass: existing footprint evidence tests plus rejection of stale pose evidence and a deliberately displaced native pad. The self-review found and fixed the back-face angle-convention mismatch and improved passive pad order; remaining centerline conflicts are intentionally retained as failure evidence. No source, current, thermal, startup, discharge or housing qualification claims from previous checkpoints are upgraded.
