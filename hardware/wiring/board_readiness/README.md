# External-profile board readiness inventory

`generated/board-readiness.json` derives the current 13-board external-converter inventory from the actual component manifests, schematic/PCB files and native records. It includes the separate E10 candidate and the in-progress E25 routing candidate. It excludes the historical E02/E03 relay projects because E11 replaces them in this profile.

```sh
python3 -m hardware.wiring.board_readiness.check
python3 -m hardware.wiring.board_readiness.check --check
python3 -m unittest discover -s tests/tooling -p test_board_readiness.py -v
```

Four board designs still have no PCB: rail monitor, converter, DAC receiver and sequenced bypass. The separate E12 ADC characterization PCB closes native routing but is not fitted into A11. Its force/sense stars end at J2 rather than at the converter pins; final co-location or a revised interface remains necessary. All 60 converter components are counted, including U1's missing footprint. A blank package assignment cannot be hidden by a passing schematic ERC result. Manufacturer package/land/stencil information must be reviewed before creating that board.

Where a native record exists, its actual open/DRC/parity counts and recorded-source freshness are separate fields. `recorded_native_connectivity_closed` summarizes the record's connectivity scope; it does not override stale helper/document fingerprints, qualify component footprints or turn a routed prototype into a fabrication release. Historical records may retain paths or hashes from their source snapshot. Regenerate the owning native checks where the current design needs fresh evidence.

The inventory retains the 24 required unassigned header pins from the 320-pair system wiring review: angle and touch interfaces J9/J10, the SD interface J12 and eight LED-anode supply contacts. All 19 required distribution/fanout assemblies remain unselected. Logical contact names do not establish purchased-part terminal numbers, connector ratings, wire lengths or safe grounding.

A11 names remain reference designations: the new E10 board has no housing integration and cannot replace the output-stage `audio_carrier`. E25 geometry is inherited from its frozen placement, while its new copper still has unresolved connections and unqualified resistance/current sharing. P01 source-regulation analysis is conditional at E25's output star, before outgoing harnesses; it is not an implemented or fully stable power redesign.

This inventory is not a build-ready decision. Every physical, manufacturing and full-unit release flag stays false; it identifies concrete work rather than fabricating completion or measurements.
