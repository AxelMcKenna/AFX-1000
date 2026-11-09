# Refill diagnostic only

This strict refill stopped on the existing In2 supply-zone rounding difference.
It is not an accepted routing candidate. The [native comparison](../two-board-nf-pin-escape-refill-diagnosis-01/native-comparison.json) bounds the only difference to approximately 1.16 nm with unchanged polygon and hole counts.

The [retained-fill candidate](../two-board-power-nf-pin-escape-rework-filled-02/local-plane-fill.json) preserves all 45 original retained zone fills exactly and copies only the two declared ground fills from this native export. Native DRC and the independent connectivity/reference audit are required before acceptance.
