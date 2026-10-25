# E25 independent copper candidate

The current candidate has **2,538 segments, 178 conventional through vias and 123 real open connections**, down from 365 in the frozen placement. KiCad 10.0.7 reports zero all-severity/all-track DRC and schematic-parity violations. This is incomplete exploratory copper, not a fabrication or assembly release. Source/protected net names and all 164 component pin/value contracts are preserved.

This package changes no placement, board outline, mounting hole, component face or parent circuit. The original E25 placement and A11 mechanical sources remain frozen. Native copper connectivity does not qualify body fit, current, resistance, thermal behavior or switching protection.

## Reproduce the reviewed candidate

```sh
python3 -m hardware.electronics.rail_disconnect.routing.generate --reviewed
python3 -m hardware.electronics.rail_disconnect.routing.check --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.rail_disconnect.routing.audit
python3 -m unittest discover -s tests/tooling -p 'test_disconnect_routing.py' -v
```

`reviewed-copper.json` freezes the actual checked exploratory copper as an editable replay recipe. The generator checks its placement-baseline hash before replay. The independent checker compares the complete noncopper tree, exports the original schematic, checks actual local F.Cu graphs and runs native KiCad. It does not trust the recipe's expected open count. Generation always invalidates prior verification.

The local stage connects all three physical source lands on each of fourteen VSON MOSFETs, all seven back-to-back common-source buses and the digital parallel source/protected drain banks. Source bars use 0.7 mm F.Cu, local common buses use 1.2 mm and the digital drain row bridges use 2.0 mm. Thirty-eight independent graph contracts cover those physical lands and junctions. Their reported lengths conservatively sum complete touched segments; they are not an optimized resistance or current-sharing calculation.

## Recover the smaller local milestone

Every generation also saves `generated/local-source-bars/rail_disconnect.kicad_pcb`. This separate 38-segment, zero-via stage has zero native DRC/parity and 327 opens. Its own evidence can be refreshed independently:

```sh
python3 -m hardware.electronics.rail_disconnect.routing.check --local --kicad-cli /path/to/kicad-cli
```

The earlier zero-DRC 141-open broad checkpoint is retained locally in the ignored `generated/checkpoints/broad-141-opens.zip`, with its original source/evidence manifest. It is historical evidence, not the current candidate.

## Continue routing

`generate --complete` starts a new six-layer conservative grid-routing attempt from the placement; it is an experimental alternative to the reviewed replay. `repair` uses actual native open endpoints and a finer 0.125 mm grid, weighted search and a bounded node budget. Every attempt must be followed by the independent native checker. A failed search is unresolved work, not proof of geometric impossibility.

Routing masks cover all six layers for plated pads and through vias. They prevent via-in-pad on SMDs and same-net drilled-hole collisions. Existing plated header lands provide their own layer transitions without extra coincident drills. No capped/filled via process or fabrication stackup has been qualified.

`generated/escape-audit.json` identifies the remaining nets and pad endpoints without surface access to a legal conventional via in the declared 4 mm local search region. Escape corridors must be reserved before routing global conductors. If rerouting cannot retain those corridors, move bottom resistors or widen channel separation in a **new** placement/housing variant; do not silently move the frozen E25/A11 geometry. The audit explicitly makes no global routing-impossibility claim.

## Power and qualification limits

Exploratory digital trunks use 1.0 mm, other rail/ground routes 0.5 mm and low-current signals 0.25 mm. These values are geometry, not proof of ampacity or the earlier 0.5 mΩ copper allocation. A single 6 mm by 2 mm digital row bridge has about 1.54 mΩ resistance under the provisional 35 µm/rho=1.8e-8 Ωm estimate, before vias, contacts or current splitting. Complete positive/common/return paths require a separate actual-copper loss model and likely wider copper/plane distribution. This candidate does not repair the existing failed 5 V system-loss screens.

Remaining work includes all 123 connections, rail and ground topology/loss, parallel-FET current balance and gate transitions, package/stencil review, stackup, thermal/EMI and real startup/fault/audio/assembly measurements. All electrical/physical qualification and build-ready flags remain false. No board has been ordered, powered or measured by this package.
