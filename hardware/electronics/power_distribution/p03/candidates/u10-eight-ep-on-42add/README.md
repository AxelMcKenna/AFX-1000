# Isolated eight-EP U10 reconstruction

This separate candidate restores all circuits removed by the stronger front-side U10 thermal trial. Fresh complete native ERC, DRC, schematic parity and open-connection counts are zero; source/artifact hashes are in `generated/current-native.json`. Canonical42 and the closed U102 candidate remain unchanged.

The eight live RAW_N22 EP barrels and original U10 front pose are retained. `generated/u10-restoration.json` preserves exact removed source objects and newly added UUIDs. The deliberate AGND fanout adds a real foreign-barrel void inside the RAW_N22 thermal contact; restored source/SET/filter/output paths also alter filled geometry. Prior thermal numbers do not qualify this source.

Corrected absolute-pad-angle thermal replay, coupled return/noise/current extraction, physical fit, fabrication and measurement remain required. Heatmap power is supply loss, not the complete standalone thermal budget. No physical, thermal, fabrication or release approval is asserted.
