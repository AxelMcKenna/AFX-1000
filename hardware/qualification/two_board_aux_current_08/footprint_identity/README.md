# Schematic / placed-footprint identity

This follows `associations/` and changes only 18 placed schematic symbols' Footprint fields plus the corresponding BOM column. Each now names the exact existing `AUX_ROUTE` assembly variant on the isolated PCB. The PCB file is byte-identical to the association checkpoint, preserving copper, nets, poses, UUIDs, outlines and filled zones. Source and candidate schematic AST comparisons permit only those exact fields; exported netlists preserve every old component and pin/net assignment.

Pinned Linux KiCad verifies all 1,104 electrical UUID associations and footprint IDs, reports **zero schematic parity issues**, and resolves the source-bound footprint libraries without missing-library or footprint geometry mismatch warnings. ERC retains the same inherited warnings. The four TPS3703 DSE 0.15 mm clearance errors against the 0.20 mm rule remain unwaived, and the isolated candidate remains unrouted/unqualified. Selected TBP73 is unchanged.

This is the native association/footprint identity gate, not a claim that an interactive Update PCB from Schematic operation was executed. Such an operation must still preserve the saved-board semantic invariants. No footprint replacement was performed to obtain parity.

The initial native readback used an unsupported overloaded `LIB_ID.Format()` binding after all three CLI checks had completed. `native_initial.py` preserves that script. The corrected accessor is `FOOTPRINT.GetFPIDAsString()`, confirmed in the pinned image. `--resume-readback` reuses those completed outputs only after verifying all recorded input hashes, avoiding unnecessary CAD reruns.

Checks:

```
.venv/bin/python -m hardware.qualification.two_board_aux_current_08.footprint_identity.verify
.venv/bin/python -m unittest hardware.qualification.two_board_aux_current_08.footprint_identity.test_verify
```

Five regression tests reject undeclared value/UUID changes and newly connected/re-netted pins while permitting the exact declared field change. Self-review found that native XML mirrors Footprint both as a top-level element and a named field; the verifier now checks both explicit changes rather than stripping arbitrary component metadata.
