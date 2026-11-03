# Unselected six-layer audio comparison

This trial is **not ready for fabrication** and does not replace the selected
four-layer checkpoint. The physical six-layer stack, materials, cost and process
have not been accepted.

The native Linux KiCad 10.0.7 review records:

- 201 open connections, down from 203 in `audio-main-controls-08`.
- No remaining opens on DRIVER_SETTLE_READY, TIMER_INPUT_OK or CHIP_EN.
- Zero DRC geometry findings and zero ERC findings, with no ignored checks.
- One schematic parity warning: missing U201 / ES9292QPRO footprint.
- 138 local connections, 17 prior control pairs, 200 ground pads and 161 rail
  pads retained; two private timing pairs and the inherited global witnesses
  also retained.

Three routes repair one existing driver connection and add two new joins. Their
lengths are 10.850 mm, 52.728 mm and 15.421 mm respectively, with three additional
conventional 0.60/0.30 mm vias in total. The driver repair must not be counted as
an additional completed connection relative to the source board.

Evidence: `preparation-record.json`, `distribution-construction.json`,
`native-refill.json`, `placement-native-review.json`,
`terminal-connectivity-review.json`, `additional-terminal-review.json`,
`current-native-pads.json`, `drc.json` and `erc.json`.

Independent preparation/retention audit, physical stack review, the missing codec
land pattern, remaining routing and electrical/mechanical qualification are still
required. These native results establish connectivity and reported rule findings;
they do not establish electrical performance or manufacturing readiness.
