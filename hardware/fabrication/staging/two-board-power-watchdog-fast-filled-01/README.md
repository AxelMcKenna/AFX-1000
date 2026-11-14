# Rejected strict refill

This export is diagnostic evidence, not an accepted candidate. The strict
check found the recurring approximately 1.16 nm rounding difference in retained
In2 supply zone `0552f897-fa23-5173-9e85-a8133b7a4048`.
The [comparison](../two-board-watchdog-fast-refill-diagnosis-01/native-comparison.json)
proves it is the only unexpected retained-zone change.
The [retained-fill output](../two-board-power-watchdog-fast-filled-02/local-plane-fill.json)
keeps all 44 original fills exactly and takes only the three declared ground
fills from this native export. See the
[TBP64 candidate](../two-board-power-watchdog-fast-native-01/README.md) for native
checks and independent acceptance evidence. No fabrication release is implied.
