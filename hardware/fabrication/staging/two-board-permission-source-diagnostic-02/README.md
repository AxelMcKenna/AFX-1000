# R107 source refill control with locked AUX net

This diagnostic starts from TBP43 and compares an unchanged source-zone refill
with a refill after adding only the R107 AUX via at (141.55, 131.6). The isolated
via is marked free and explicitly assigned to AUX so the filler cannot inherit
a surrounding zone net. Its AUX net is asserted before and after native filling,
and the saved board is independently checked by the candidate review.

The unchanged baseline reproduces the selected source fill exactly. The locked
AUX via changes 0.878034477 mm². The independent candidate audit
compares the exact polygons with the candidate, checks all source contacts and
requires all other changes to lie in the declared via regions. This is a fill
causality experiment, not a current-capacity or thermal qualification.

[Control results and source bindings](source-control.json). Experiment 01 is
invalid because its isolated non-free via inherited the ground net; it is not
accepted as evidence. No fabrication release is implied.
