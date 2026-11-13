# Detailed touch model and corrected fan-bundle ownership

This candidate replaces only the broad touch box with the source-bound C3 board/component/tail model and the duplicated downstream fan-bundle reservation with its exact prefix. All six physical fan wire paths remain unchanged. Original generic fan connector reservations remain selected; the conditional r24 height cap, entry masks and mating-body substitution are not adopted.

The candidate has69 roles and39 checks. `results.json` retains39 passing checks under the earlier runtime. The direct `--manifest` refresh passed all39 checks under workflow95dc951b; see `workflow-cli-results.json`. The candidate is now selected in `current.json`. Historical results retain their original runtime identity.

The five added checks screen controls without the old touch box, sensor and lid against non-shell cooling, detailed touch against non-shell cooling, and sensor against control details. Coverage-02 preserves the original failures. The detailed touch/full-shell raw witness is exactly on Z20, zero reported volume with nonclosed contact boundaries; it is retained under `raw-touch-seat` as a nonempty seat witness, not an empty-check pass. Lever and lid seating planes remain explicit. This is not proof of complete housing fit.

The separate r26 touch fastener/pocket candidate, touch host and electrode wiring, connector receiving tolerances, full service, thermal/electrical and fabrication qualification remain open. Power-candidate verification logs are included for provenance only and do not select an unfinished power PCB.
