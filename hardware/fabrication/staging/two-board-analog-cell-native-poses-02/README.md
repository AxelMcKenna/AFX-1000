# Native analog component poses 02

KiCad 10.0.7 placed twelve declared two-pad components, including three native
board-face flips. These are the poses used by analog routing plans 02 and 03.
[poses.json](poses.json) binds the source board, placement input, native utility
and output board. Plan 03's
[geometry review](../two-board-analog-cell-plan-03/geometry-review.json)
independently compares all 24 pad positions, nets and sides and checks the
provisional mechanical envelope of the twelve moved components.

`native-poses.kicad_pcb` is only a footprint-pose fixture. It retains old copper
without rerouting it and must not be used as a design or manufacturing board.
TBP44 remains selected. No fabrication release.
