# Refill diagnostic only

The strict refill stopped on the retained In2 supply-zone rounding difference.
The [native comparison](../two-board-control-corridor-refill-diagnosis-02/native-comparison.json)
found only that approximately 1.16 nm difference, with unchanged polygon and
hole counts. This directory is not an accepted routing candidate.

The [retained-fill candidate](../two-board-power-control-corridors-filled-04/local-plane-fill.json)
keeps all 43 original retained fills exactly and copies only the four declared
ground fills from this native export. Acceptance belongs to the separately
audited revised native board, not to this diagnostic export.
