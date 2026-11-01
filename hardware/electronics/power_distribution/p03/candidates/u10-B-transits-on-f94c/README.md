# Isolated U10 contact-copper restoration

This separate candidate restores the four circuits opened by the B-contact transit-removal comparison. It keeps the front-side U10 pose and eight actual EP barrels, while rebuilding quiet SET and SHDN paths outside the contact. Fresh complete native ERC, DRC, schematic parity and open-connection counts are zero; source/artifact hashes are in `generated/current-native.json`. Canonical42 and the closed U102 candidate remain unchanged.

The eight live RAW_N22 EP barrels and original U10 front pose are retained. `generated/u10-restoration.json` preserves exact removed source objects and newly added UUIDs. The original AGND foreign barrel remains a real void. Four dangling original source/SET/SHDN barrels were explicitly removed, and new transfer barrels lie outside the metal contact. A deliberate In1 SET crossover preserves Kelvin sensing after R37; SHDN uses a short F route and an external In2 transfer. A real VIN_PROTECTED C70/L7 island cut by that corridor was stitched using actual matching filled copper. Prior thermal numbers do not qualify this source.

Corrected absolute-pad-angle thermal replay, coupled return/noise/current extraction, physical fit, fabrication and measurement remain required. Heatmap power is supply loss, not the complete standalone thermal budget. No physical, thermal, fabrication or release approval is asserted.
