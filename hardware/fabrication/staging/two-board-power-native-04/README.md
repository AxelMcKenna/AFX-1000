# TBP04: NF interfaces and reset-masked fault input

This historical checkpoint integrates fifteen NF interface pin pairs in addition
to TBP02's thirty. The [newer TBP05 checkpoint](../two-board-power-native-05/README.md)
corrects two negative-source sensing connections; use that version for further work.
**Neither checkpoint is a fabrication release.**

The NF auxiliary supply, reference, negative OV status/sense, protected-output
feedback and bank-clamp endpoints are connected in the schematic. The E28
native fault-request output is split from the latch SET input. NF combines the
requests and drives SET through its existing two inverter stages. The formerly
unused fourth N_U46 OR gate now masks SET while E28 RESET is asserted.
No physical parts, footprints or placements were added or removed.

The [independent fault audit](fault-mask-audit.json) evaluates the exported
native pin graph for all 32 combinations of three fault inputs and two reset
causes, checking all four possible latch equilibria for each. It establishes
settled Boolean reset priority and rejects five faulty variants, including the
previous unmasked TBP03 topology. This is not a propagation-delay, pulse-width,
partial-power or complete startup/fault-recovery proof.

The [native review](review.json) reports 1,077 components, 3,440 mapped physical
pads, 2,677 unrouted connections, zero geometry/parity findings and zero ERC
errors. The two unchanged ISO7721F floating-reference warnings remain recorded,
with no ignored check categories. All 1,092 complete footprint geometries,
outline, mounts and setup are retained. Native exports and source hashes were
checked by the independent audit.

TBP04's E_R49.1 and E_R53.1 still sensed the respective post-NF switch outputs.
This circular startup dependency was discovered during integration review and
is corrected in TBP05. The historical artifact remains unchanged for comparison.
