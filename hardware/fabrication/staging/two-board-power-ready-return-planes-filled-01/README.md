# Rejected strict refill export

This directory is diagnostic evidence, not an accepted PCB candidate. The strict
refill check rejected a rounding difference in retained In2.Cu supply zone
`0552f897-fa23-5173-9e85-a8133b7a4048`.

The [native comparison](../two-board-ready-return-planes-refill-diagnosis-01/native-comparison.json)
found no other unexpected retained-zone changes. Boundary displacement was
approximately 1.16 nm and symmetric-difference area was 2.54e-7 mm², with
unchanged component and hole counts. The rounded supply copper was not used.

[Retained-fill output](../two-board-power-ready-return-planes-filled-02/local-plane-fill.json)
keeps all 45 original fills exactly and takes only the two declared ground fills
from this native export. Native checks and independent review are in the
[TBP63 working candidate](../two-board-power-ready-return-planes-native-01/).
No fabrication release is implied.
