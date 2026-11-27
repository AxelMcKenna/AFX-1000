# Paired VIN escape — isolated candidate

This adds the buck input feed from P_U101.1 to P_C900.1: four 0.25 mm F.Cu tracks (5.001141 mm), a 0.6/0.3 mm through via at (198,118.6), and nine 0.3 mm B.Cu tracks (31.206477 mm). The paired ground via at (198.8,118.8) is 0.824621 mm away. The earlier 5.240 mm existing-return alternative is not used and the <1 mm transition gate is retained.

`native-04` is the candidate; native-03 has identical PCB bytes and remains intermediate provenance. `native-01` and `native-02` are rejected diagnostics. All remain separate from accepted TBP73. No fabrication or electrical qualification is claimed.

The five declared AGND zones receive only the new VIN antipad. All 44 other zones, including DC_IN and MODULE_FEED, retain their original fills. Existing original ground contact area must remain intact, every native group outside the declared VIN join must remain identical, and all 55 anonymous pad physical identities remain uniquely matched. The new return must contact actual filled In1 and In6 ground; route reference exceptions are limited to the actual new via antipads. The strict checks are in `verify.py`.

The default native full refill heals a pre-existing antipad near (191.475,126.65) and changes remote In4 copper, so copying its complete zone fill was rejected (`native-01`). Native polygon Boolean subtraction then caused remote nanometre-scale saved vertex changes (`native-02`), also rejected. `local_fill_exact.py` inserts the exact new native-refill hole using repeated, visible bridge vertices, preserving all original vertices and prohibiting crossings of existing polygon edges. The native parser, connectivity, geometry extraction and DRC subsequently assess that authored result. The 0.206 mm local envelope is the 0.2 mm rule plus 0.006 mm allowance for KiCad's polygonal antipad contour; it does not change the board clearance rule. The final check compares exact saved filled-polygon paths. Native Unfracture extraction alone produces a 6.19e-8 mm² discrepancy on the bridge zone; this is separately bounded within 1.1 nm of the saved boundary. Exact saved paths show zero added/nonlocal removed area. No positive-area addition or nonlocal removal is permitted beyond the numerical area tolerance of 1e-9 mm².

Both original native refill contexts are archived. The legacy In6 context omits only the newer overlapping reference bridge while calculating the legacy zone; the final board retains all 49 zones. Initial `native_initial.py` failed a guard that confused `UUID:layer` fill keys with UUIDs; corrected `native.py --resume` reused the recorded completed fills. The initial script and outputs are preserved for review.

Both the r31 touch-cradle contacts (c39e0d3b) and the 13 power-board main-mount F.Cu receiving areas (385ee7af) are checked against original and added copper. Main-mount keepout data is copied unchanged with SHA-256 38854f6356625631ad32ec4578c989c2c3e06a6f8c48754ec768c55f53e04d71.

Run from the repository root:

```sh
.venv/bin/python -m hardware.qualification.two_board_aux_current_08.vin_escape.verify
.venv/bin/python -m unittest hardware.qualification.two_board_aux_current_08.vin_escape.test_verify
.venv/bin/python -m hardware.qualification.two_board_aux_current_08.vin_escape.render
```

The existing four DSE clearance errors remain unwaived. Actual current, transient/return impedance, installed thermal performance, hold-up/RESET loading and driver shutdown timing remain qualification gates. This input feed alone does not establish the conditional 20 mV distribution allocation. Main LDO feed, remote supervisor, RESET and held distribution still need completion.

Observed verification: native opens 1945 → 1944; exact declared group merge only; all original objects/pad identities retained; both mechanical contact audits pass; no reference exception outside the actual via antipads.

The extraction comparison is a measured equivalence check, not a universal KiCad error guarantee: saved-versus-Unfracture boundary Hausdorff distances are 0.707088, 1.000000, 0.707096, 0.707088 and 0.707088 nm. KiCad coordinates use a 1 nm grid. The 1.1 nm comparison limit allows 0.1 nm numerical margin over the observed single-grid-step maximum; it applies only to extraction, never to saved copper, clearance or contact loss. The verifier records each measured distance and rejects a larger discrepancy.
