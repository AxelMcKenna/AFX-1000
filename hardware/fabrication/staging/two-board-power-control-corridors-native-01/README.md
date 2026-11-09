# Rejected TBP61 routing trial

Native KiCad reports 2,100 opens, zero geometry/parity findings and two retained
ERC warnings. This trial is **not accepted**: the independent full-width
reference audit found new uncovered areas of approximately 0.002663 mm² on
CLAMP_SUPPLY_ENABLE and 0.001398 mm² on N19_SAFE_SOURCE.

The [diagnosis](../two-board-control-return-diagnosis-01/survey.json) records
both defects. Thirteen other unreferenced track sections predate this trial;
comparison with the baseline found no increase in their uncovered areas above
1e-6 mm². The diagnostic's `unreferenced_existing_tracks` field sums all fifteen
failing tracks, including the two marked `added`; it is not a count of fifteen
pre-existing defects.

Both new defects are addressed by the [revised plan](../two-board-control-corridor-plan-02/plan.json),
which retains all 24 intended joins and all 23 via positions. Acceptance
requires another native refill, DRC, connectivity and reference audit.
