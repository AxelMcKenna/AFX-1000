# Startup connectivity survey at TBP46

[Native pad-group inventory](inventory.json) for the checked
[TBP46 power board](../two-board-power-digital-return-native-03/README.md).
It includes all native nets containing `E28_`, `ANA_PG` or `DIG_PG`, plus
`PWR_ALL_RAILS_ALLOW`: 91 nets, of which 32 require 60 additional joins.
This is a named-net routing survey, not full startup functional verification
or an inventory of every supply/ground connection needed by these circuits.

All three analog PG nets and all four digital PG nets are connected. The
DIG_PG3 Schmitt output still has two groups. MASTER_ENABLE has five groups;
TIMEOUT_CT has six; RESET has five. The short adjacent U21.3–U21.4,
U22.3–U22.4 and U23.3–U23.4 pairs are also disconnected. Sense, reset,
fault and permission paths require further routing. The report retains every
pad in each group and the nearest pad pair between each pair of groups.

Distances are planning hints only. A route still needs copper clearance,
ground-reference continuity, appropriate width, owner isolation and native
connectivity verification; shortest distance alone does not establish a route.
The earlier twelve reference gaps remain separately recorded in the
[reference audit](../two-board-power-digital-return-native-03/digital-return-reference-review.json).

Reproduce into a fresh output directory with:

```sh
.venv/bin/python -m hardware.fabrication.inventory_two_board_startup_routes \
  --capture two-board-power-routing-inputs-2210-digital-return-03 \
  --output two-board-startup-connectivity-survey-02
```
