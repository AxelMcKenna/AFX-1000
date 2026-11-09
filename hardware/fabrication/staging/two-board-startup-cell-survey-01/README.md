# Startup supply, bypass and ground inventory

The [inventory](inventory.json) checks U18–U28 and their local bypass capacitors
against the [current native PCB](../two-board-power-startup-cells-native-03/power_protection.kicad_pro).
**U21/C66, U25/C70 and U28/C73 now have local bypass connections and both ground
returns. None of the surveyed ICs is connected to the auxiliary regulator's
output source.** These cells are not yet powered or functionally verified.

The remaining U22/U23/U24/U26/U27 cells need coordinated placement, routing and
adjacent-ground work. Existing In6 signal traces obstruct U22/U23/U27 reference
coverage; U26 lies outside the current ground outline, and U24 still needs a
clear referenced bypass route. U18/U19/U20 supply, bypass and ground connections
also remain unfinished. Sense and timing component placement needs review.

The [named startup-net survey](../two-board-startup-connectivity-survey-03/README.md)
separately records 58 missing joins across 32 nets. Both inventories bind their
source captures by hash. Geometry diagnostics do not establish electrical,
thermal, noise or startup performance. This is not a fabrication release.
