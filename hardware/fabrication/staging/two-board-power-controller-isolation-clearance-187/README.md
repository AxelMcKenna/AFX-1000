# Controller isolator copper separation

The 1.18 mm keepout between the input and output lands of N_U19 excludes tracks, pads, vias and pours on all eight copper layers. The front-layer N19_CONTROLLER_ON detour adds 1.65 mm and preserves continuous In1 ground coverage along the full trace. The native pad-group comparison preserves all 1,076 remaining opens.

The whole-board isolation survey found 48 layer intersections, down from 51. The loaded layout and regenerated copper have the same filled geometry. Input-to-output voltage withstand and fabrication qualification remain open.

[Keepout](isolation-rule.json) · [Detour](detour.json) · [Filled copper](plane-review.json) · [Isolation survey](isolation-midlines.json) · [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json)
