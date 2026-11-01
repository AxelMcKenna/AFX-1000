# Isolated U102 merge on closed P03

This candidate retains the complete closed42 supply circuits and adds nine direct U102 EP vias plus actual six-layer AGND spreading. The final three underside poses and exact native evidence are in `generated/u102-candidate.json` and `generated/current-native.json`. Fresh native ERC, DRC, schematic parity and open-connection counts are all zero. Canonical P03 remains unchanged.

This is an unreleased custom-process candidate. Corrected absolute-pad-angle thermal extraction, local/base temperature bounds, coupled ground and endpoint extraction, physical fit, fabrication and measurements remain required. The heatmap is **supply loss**, not complete standalone-unit heat. The two additional control signal VIPs and quiet inner paths require actual filled/capped construction and native geometry extraction; previous thermal or ground numbers do not qualify them. No physical or release flag is true.
