# Startup connectivity survey after local-cell routing

The [native connectivity inventory](inventory.json) checks 91 nets containing
E28_, ANA_PG or DIG_PG, plus PWR_ALL_RAILS_ALLOW. It finds **58 missing joins
across 32 nets**, down from 60 before the U21/U22 feedback joins.

The source is the [startup-cell candidate](../two-board-power-startup-cells-native-03/power_protection.kicad_pro),
which has 2,199 total power-board opens. This named-net survey excludes supply
and ground distribution. The separate [cell survey](../two-board-startup-cell-survey-01/README.md)
records those connections for U18–U28.

Native connectivity and nearest-pad distances do not establish routing
clearance, return-path quality, timing, current capacity or startup behavior.
The unit is not ready for fabrication.
