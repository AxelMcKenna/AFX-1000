# Conditional panel ground-chain amendment

Open `assembly/panel.kicad_pro` for the 39-page panel drawing with the r12 ground-chain terminal schedule. All 349 components and all native pin nets remain identical to the prior electrical checkpoint. Only switch-sheet notes change: terminal 1 is the signal, 2 is unwired, 3 receives ground, and 4 continues the chain where individually specified. Twenty-five terminal-4 contacts carry an outgoing wire; four chain ends remain unwired. `terminal-schedule.csv` maps every switch reference to its named control and exact neighboring contact.

This is the conditional r12 electrical topology checkpoint. The r13 formed-route study is now evaluating a different two-feed topology; its final adjacency schedule is not selected here. It does not select its sharp-polyline receiving geometry as a finished harness. Manufacturer bend-radius requirements, source-connector exits, restraint, service allowance and complete assembly clearance remain open. A future change to the formed-route feed ownership must generate a corresponding new electrical amendment; do not silently reuse this schedule.

Native verification in `native-strict/` explicitly enables all ERC rules, including four disabled by default in the original panel project. The complete hierarchy has zero ERC errors/warnings, no ignored checks, and an identical component/value/footprint/pin-net map. The verifier rejects an incorrect outgoing contact. Original panel sources and their source-bound evidence remain unchanged.

The independent drawing check allows only annotation changes on the switch sheet and requires all other assembly files to be byte-identical. Three native SVG detail renders were inspected across all 29 switch notes; the introductory note was moved below the page border. The original SVG is retained for zooming/printing. This remains a prototype drawing, not fabrication release.

Reproduction uses `python -m hardware.cad.two_board_controls_04.panel_ground_amendment.build` in a fresh output directory, the pinned Linux KiCad image for `verify --strict-native`, then host `verify`. The verifier checks source hashes before accepting results.
