# Startup connectivity after the TBP52 routing pass

The [native inventory](inventory.json) checks 91 startup-related nets in the
[working power-board candidate](../two-board-power-startup-controls-native-03/README.md).
Thirty remain open, requiring **53 joins**. The preceding survey had 32 open
nets requiring 58 joins. Five joins were closed by this pass.

These counts cover names containing `E28_`, `ANA_PG` or `DIG_PG`, plus
`PWR_ALL_RAILS_ALLOW`. They exclude the separate supply and ground distribution
work. Nearest-pad distances in the inventory are routing hints, not proof of
clearance, a usable return path, timing or current capability.

The complete power board still has **2,167 opens**. The signal board retains
251 opens. Neither the startup circuit nor the complete unit is fabrication-ready.
