# Native zone-capture diagnostic

The first AUX ground candidate passed native DRC/ERC/parity but failed the
v4 capture's fixed 0.000001 mm² area-difference limit for its output-return
zone. KiCad Unfracture changed that area by 0.0000012248035 mm².

Independent comparison of raw polygons and unfractured polygons finds maximum
boundary displacement below 0.000000708 mm (0.708 nm) across all eight zones.
The discrepancy is at the native integer-coordinate scale, not a board-rule
violation. Raw fractured polygons can contain zero-width slits; buffer(0)
resolves those while the verifier checks area preservation.

The v5 capture exports both representations. Its independent geometric check
requires boundary displacement at most 0.000002 mm and symmetric copper-area
difference bounded by boundary perimeter times that displacement (minimum
0.000001 mm²). It also checks area against native values and component count.
Tests reject a removed clearance hole and an equal-area translated polygon,
while accepting a sub-nanometre shift. No DRC or fabrication rule changes.

[Native before/after evidence](diagnostic.json) ·
[Verifier](../../verify_native_zone_unfracture.py) ·
[Focused tests](../../../../tests/tooling/test_native_zone_unfracture.py)

The first candidate separately failed full feedback-reference coverage by
0.167595 mm². It is retained as an unselected trial. The revised candidate
recesses U20's ground edge and extends the AUX reference under that branch;
its independent checks are recorded with the selected revision.
