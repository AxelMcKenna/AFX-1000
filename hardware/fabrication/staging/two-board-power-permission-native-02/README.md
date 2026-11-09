# Permission routing candidate 02 — superseded

Not selected and not ready for fabrication. Native KiCad reports 2,237 opens,
one dangling-via geometry warning, zero schematic-parity findings and two
retained isolated-reference ERC warnings. The unused R119 AUX via at
(144.5, 132.0) only contacts an inner-layer stub after the bottom escape moved
to (143.8, 133.9). Candidate 03 removes that proposed via and branch. TBP43
remains the selected checkpoint until a successor passes all required reviews.

See [native findings](drc.json) and the [corrected plan](../two-board-permission-plan-03/README.md).
