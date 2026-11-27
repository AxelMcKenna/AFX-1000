# Antagonistic self-review

Scope: new panel electrical hierarchy and local schematics after frozen mechanical commit e3e3b79f. This is a self-review, not an independent audit.

Fixed findings: initial layouts were off KiCad connection grid; native-r1 retains the 19 settings warnings. Grid-aligned native-r2 passes all twelve layouts. Visual review found tall main-header symbols overlapping the next row and left global labels facing inward; spacing and orientation were corrected and assembly-native-r3 reverified. The provisional pot value incorrectly applied a center-detent candidate to every position; it now explicitly says detent TBD, retaining unresolved per-control allocation.

Checks attack five functional defects in the exported native netlist and reject each: reversed button LED polarity, swapped display segment, disconnected RGB branch, missing selector-common ground, and grounded pot wiper. Independent circuit specifications match frozen PCB values/footprints/net groups. Whole-panel instance maps preserve these subgraphs, and function-based checks trace all 96 driver channels rather than merely counting nets. Five physical selector positions are simulated against the source contact table. The full hierarchy passes severity-all ERC without suppressions. Generation is deterministic across 356 output files and bound to 46 source inputs.

Remaining limitations: passive symbol ERC does not evaluate electrical drive, power or timing. Logical global supply/ground connections do not define splice hardware; harness distribution and exact mating connectors remain separately owned. Detent allocation/sourcing, actual shaft rotation, brightness/current sharing, tolerances and physical fit are unresolved receiving/bench gates. No fabrication release is asserted.
