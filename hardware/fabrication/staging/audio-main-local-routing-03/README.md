# AC04 — all declared local signal/supply endpoints connected

This intermediate candidate closes **131/131** declared feedback, clock, pump,
servo and supply endpoints. Its 138 explicit local routes include seven ground
pairs. The supply route also joins D102.2 to V5_REG, independently confirmed
in `additional-clamp-connectivity.json`.

Isolated Linux KiCad 10.0.7 reports zero geometry/ERC findings, one explicit
missing-U201 footprint finding and **585** uncapped open connections, with all
categories enabled. The board has 264 tracks and twenty conventional vias.

Three previously unrouted parts move to clear the last two escapes: D102 shifts
0.5 mm, C118 moves to [49.5,31] mm at 180°, and R324 moves to [107,30] mm at 90°.
C118 remains provisional pending the actual ESS land and ADC-star receiving.
Every amplifier pose and the original direct compensation capacitor tracks are
unchanged. All conditional body, floor, upper-board, solder-tail, codec-reserve
and support receiving checks were renewed. A fresh native capture independently
matches all 930 pad geometries to the planning transform; generated pad UUIDs
are not treated as persistent physical-terminal identities.

R319's new feedback route is 6.388705 mm and C127's supply route 4.935502 mm,
within the retained 6.4/5.6 mm per-layer trace budgets. Each uses two conventional
0.60/0.30 mm vias and records an additional nominal 3.2 mm barrel traversal.
These construction metrics do not qualify loop parasitics, stability or PDN.

The later [reference-ground candidate](../audio-main-ground-02/README.md)
completes all placed ground connections. This intermediate source and its
native reports remain preserved. Neither stage releases fabrication; the ESS
footprint, global routing and complete qualification remain unfinished.
