# Refill stopped at exact preservation check

This directory is **not an accepted PCB candidate**. Native refill completed,
but the strict canonical-polygon comparison failed for the In2 module-feed
supply zone. No successful `local-plane-fill.json` was produced here.

The [native diagnosis](../two-board-nf-ground-refill-diagnosis-01/native-comparison.json)
found one affected retained zone. Its unfractured boundary displacement is
approximately 1.16 nm, with unchanged component and hole counts. The later
[retained-fill candidate](../two-board-power-nf-logic-ground-filled-03/local-plane-fill.json)
keeps all 42 original zone fills exactly and copies only the five declared
ground-zone fills from this native export. That candidate requires its own
native checks and independent audit; this failed directory is not a release.
