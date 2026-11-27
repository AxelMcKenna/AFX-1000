# ADC control/feedback checkpoint r98

Resumes after the coordinated workflow update and repairs the rejected r95 PD_R reference gap. The front escape changes from (81.5,78.5875) → (80.5,79.5875) to a two-segment path through (81.0,79.0), away from the V5 via at (81.455,79.575). It changes candidate-only copper. No accepted r89 copper, component pose, keepout, tolerance or reference exclusion is changed.

The resulting checkpoint adds ten native joins relative to r89: six monitor/disable-control joins and four adjacent 1.27 mm local unity-buffer feedback connections. Total opens reduce 177 → 167. BIAS_SHIFT_R and PD_GATED become connected; the FDA pin escapes on PD_L/PD_R remain open, as do the other ADC paths. The added inventory comprises 18 route pieces, eight signal vias, four ground vias and eleven physical In4/In6 reference corridors.

The rejected r95 evidence remains frozen. The bounded detour checks actual native copper and filled In1 support before building a fresh candidate. Fresh Linux KiCad geometry/ERC/parity, independent connectivity, exact old-object/group inventory, full new/retained references, transition identity/returns, drill clearance and raw fill fidelity remain required. No failed reference case is masked.

Portable verification: `python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r98 --reference --regressions`. This verifies local source bytes, recomputes frozen audits and rejects missing/wrong-net transition proofs at the intended assertions. Root integration must confirm current mechanical identity before selecting the PCB.

Current E12-R2 source constraints remain bound. Missing ESS footprint, remaining signal-board routing, threshold accuracy, coupled-loop/noise/stability, partial-power behavior and physical/fabrication qualification remain unresolved. Zero modeled DAC opens is not complete DAC or board approval.
