# Auxiliary fault isolator copper separation

The 2.13 mm keepout between the input and output lands of N_U17 excludes tracks, pads, vias and pours on all eight copper layers. The In5.Cu ABS_AUX_FAULT detour adds 1.93 mm and preserves the In6 ground reference. Only the two pre-existing signal-via antipads interrupt that reference at the ends. The native pad-group comparison preserves all 1,078 remaining opens.

The whole-board isolation survey found 62 layer intersections, down from 65. The loaded layout and regenerated copper have the same filled geometry. Input-to-output voltage withstand and fabrication qualification remain open.

[Keepout](isolation-rule.json) · [Detour](detour.json) · [Filled copper](plane-review.json) · [Isolation survey](isolation-midlines.json) · [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json)
