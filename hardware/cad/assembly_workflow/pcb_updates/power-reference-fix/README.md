# Full power-candidate mechanical handoff

This reproducible audit compares selected TBP73 against the corrected reference-09 isolated candidate. It does not select a board or modify the assembly bridge. Run from the repository root:

```sh
.venv/bin/python -m hardware.cad.assembly_workflow.pcb_updates.power-reference-fix.audit
```

The candidate has 1,120 total footprints versus 1,101 selected: 19 added components, no removed parts, and one moved part, E_C13. E_C13 changes from (97,127.5,180 degrees) to (108.275,129.095,90 degrees). The report lists each added part's actual footprint, pose and MPN so a subsequent receiving-envelope update cannot accidentally cover only the latest C907 addition.

There are also 91 physical-field differences and 37 property differences. Exactly 32 physical records have equal child multisets and differ only in ordering. The remaining 59 are unresolved here; their raw before/after records are retained. No numeric/default normalization, field dropping or automatic equivalence approval is performed. Unknown physical changes continue to fail the shared mechanical freshness gate.

Supplier maximum heights, placement/process tolerances and installed envelopes remain unverified in this audit. Property changes require part/height review even where the footprint is unchanged. The candidate's own electrical verifier is separate and does not qualify housing fit. All added and changed parts must enter a cumulative capture and pass the complete selected assembly screen before power-board selection. No hardware fabrication release follows from this report.

Self-review checked that the audit uses the exact corrected board rather than the older text-defective candidate, binds parser/bridge/source hashes, retains every strict difference and leaves the selected manifest untouched. The result is a qualification queue, not an assertion of geometry equivalence or fit.

## Native serialization comparison

A subsequent pinned Linux KiCad roundtrip resolves the raw serialization ambiguity. Both immutable boards were loaded and saved without refill or editing; the native job exited successfully within its 60-second bound. Retained compressed outputs, script/input hashes and process logs are in `native-roundtrip/`. The shared bridge remains unchanged.

Comparing the two native outputs leaves 19 additions, one pose change, 13 property changes and one physical-field difference: E_C13. Its physical change is exactly the three absolute 180-to-90-degree angles on its two pads and user reference text, with an identical multiset of every other physical child. The other 58 previously unresolved physical records serialize identically. The first host rotation check also required identical child ordering and failed; inspection found only the same exact child-order difference already covered by the audit. The final check compares exact child multisets after those three explicitly constrained angle edits. No native job was retried.

Reproduce the source-bound native-evidence check with `python -m hardware.cad.assembly_workflow.pcb_updates.power-reference-fix.verify_roundtrip`. It validates both compressed outputs against native saved-byte hashes and original input hashes before comparing. This proves the bounded serialization/rotation accounting; it does not approve the capacitor move, added parts, changed part properties or installed heights. The original strict audit remains historical evidence and continues to identify the raw differences.
