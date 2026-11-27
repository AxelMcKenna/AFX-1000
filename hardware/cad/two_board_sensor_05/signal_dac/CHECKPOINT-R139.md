# Signal checkpoint r139 — bounded NBIAS_L join

From accepted r131, adds one 0.2 mm B.Cu track from (67.525,78.5) to (65.325,77.5), length 2.416609 mm. A single In6.Cu LINK_AGND zone extends the existing reference corridor by the exact 0.6 mm buffered path polygon declared in candidate-r139/routing.json. No via, footprint, old copper, authored zone, mount keepout or rule changes.

Native KiCad reports 163 opens, zero geometry/ERC violations, unchanged missing-ESS schematic parity and exact netlist partitions. The cumulative reference gate checks 136 introduced route cases and all 4,873 retained reference identities; 67 existing returns, 239 raw/unfractured zone cases and 99 drill cases remain checked. Patch audit proves native main-ground membership, exact old-zone anchors and only local saved-fill changes. Its explicit 2 nm capture-boundary tolerance accounts for sub-micrometre-squared polygon representation differences; no remote material fill change is allowed.

All 477 r131 footprints retain their poses. Cumulative mechanical changes remain the r125 R303/R308/D101 moves. The nominal D101/C105 receiving gap remains 0.02 mm and is not manufacturing-tolerance acceptance. Root must integrate/select this checkpoint; this task does not edit current.json.

PD_R is still open. The separate r138 diagnostic shows zero captured NBIAS_R reference loss at a via at (75.8,77.65), contrary to the conservative 0.63 mm planning rejection. That diagnostic removes three routes without replacements and is expressly not a candidate. Exact replacement of the three authorized obstacles remains to be designed and verified. The missing ESS package, 163 opens, analog/noise/stability, physical tolerances and fabrication release remain open.

Reproduce: `.venv/bin/python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r139 --reference --regressions`.
