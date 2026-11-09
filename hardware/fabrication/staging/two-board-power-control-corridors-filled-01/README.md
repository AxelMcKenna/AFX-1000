# Refill diagnostic only

The strict refill stopped on the existing In2 supply-zone rounding difference.
This directory is not an accepted routing candidate. The
[native comparison](../two-board-control-corridor-refill-diagnosis-01/native-comparison.json)
found only that difference, bounded to approximately 1.16 nm with unchanged
polygon and hole counts.

The [retained-fill candidate](../two-board-power-control-corridors-filled-02/local-plane-fill.json)
preserves all 43 original retained zone fills exactly and copies only the four
declared ground fills from this native export. Native DRC and independent
connectivity/reference review are required before acceptance.
