# TBP48 — startup reference repairs

This checked power/protection revision repairs all eight startup-reference gaps recorded in TBP47. It is a partially routed development board, **not a fabrication release**. The two-board unit still has 2,210 power opens and 251 signal opens, plus the missing approved ESS footprint and unfinished mechanical, electrical and manufacturing requirements.

PG0 and PG1 use revised transitions and pull-up paths. PG1 continues on In6 with adjacent In5 ground. U33's enable transition moves to keep its quiet-field extension clear of the PG0 backbone and FOLLOW3 departure. A main-ground via anchors the previously disconnected In1 lobe. No components or schematic pin assignments move or change.

The change replaces 17 tracks and three vias with 25 tracks and five vias. Seven ground outlines change; 16 existing zones are explicitly refilled and the other 31 are preserved exactly. Current totals are 3,039 tracks, 455 vias, 47 zones, 1,101 footprints (1,086 electrical components), 3,481 mapped pads and 2,948 native connection groups.

## Verification

- [Native checks](review.json): 2,210 opens, zero geometry/parity/ERC errors, two retained isolated-reference warnings.
- [Independent topology review](startup-reference-review.json): every native connection group and other physical object preserved; all seven quiet networks retain their contacts, connected ownership graphs and pin-8-only main-ground stars.
- [Reference coverage](startup-reference-coverage.json): all 1,611 retained complete reference cases, nine new paths, eight targeted startup paths and 22 digital ILM/DVDT own-field paths pass.
- The relocated U33 via physically overlaps a retained FOLLOW3 back trace by 0.115077 mm² and shares its native connection group. Its existing 0.515 mm same-net clearance exclusion is applied to the current geometry; the audit does not treat that required antipad as a missing reference. No clearance radius or coverage tolerance was increased.
- [Supply-plane review](startup-supply-plane-review.json): all eleven supply contact sets, region counts and authored outlines are preserved. Three fills change locally. Current distribution, resistance, timing/noise and thermal limits are not qualified by this comparison.
- [Visual review](plots/visual-review.json): six local copper/ground details, both surface overviews and the six-inner-layer contact sheet were directly inspected, with no additional findings.

The [recorded status](../two-board-fabrication-status-48/status.json) selects this revision. The [startup connectivity survey](../two-board-startup-connectivity-survey-01/README.md) remains applicable because connection groups and pad positions are preserved: 60 startup joins remain across 32 nets.

## Copper views

[Front](plots/front.png) · [Back](plots/back.png) · [Inner layers](plots/inner-contact-sheet.png)

[Local front](plots/startup-local-front.png) · [Local back](plots/startup-local-back.png) · [Local In1](plots/startup-local-inner1.png) · [Local In2](plots/startup-local-inner2.png) · [Local In5](plots/startup-local-inner5.png) · [Local In6](plots/startup-local-inner6.png)

## Remaining release work

Complete startup joins and fault-state verification; protected outputs, source/load loops, analog/module distribution, force/quiet returns and signal routing; approved ESS package/land/stencil inputs; accepted stack/plating and exact BOM/process requirements; full installed housing, fastener, cooling, connector and harness fit; loaded current/timing/noise/thermal qualification; reviewed manufacturing outputs and whole-unit prototype inspection/bring-up requirements. The earlier TBP35 inlet resistance model does not qualify these current fills.

Earlier startup candidates remain diagnostic snapshots. Trial 03's strict audit rejected duplicate footprint-path metadata from the historical validator; [the diagnosis](../two-board-startup-trial03-diagnosis/diagnosis.json) records the cause. This revision uses the current canonical-path validator and passes the unchanged-component syntax check.
