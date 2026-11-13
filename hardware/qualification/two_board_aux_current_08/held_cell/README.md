# Paused, rejected held-cell plane experiment

This directory preserves an experiment already in flight when the workflow-first pause arrived. It is not a reviewable electrical/PCB checkpoint.

`build_plane.py` proposes a new In6 main-ground rectangle (136,158)–(158,180), copying the original ground zone settings. `native_plane.py` attempts native fill, retention of all original filled zones, and exact original connectivity/identity checks. The pinned Linux KiCad process terminated with exit 139 before writing any refill or candidate board. No fill, reference, connectivity or DRC claim is available. The generated authored input remains local and unchanged; its hash and reproducible source are in `plane-plan.json`.

No retry or further geometry work was performed after the workflow-first pause. The last verified isolated PCB remains `../shared_cutover/native-04` (commit 376a8188); the accepted PCB is unchanged.

Workflow gaps identified before resuming design:

- Package a candidate as source hashes plus declared deltas and reproducible native outputs; repeated complete library/source copies inflate review diffs.
- Centralize stage commands, source hashes, semantic allowlists and pass/fail status so failed native stages cannot look reviewable.
- Move full native courtyard and source-pin/net checks ahead of routing search; keep mutation coverage for TT-versus-GND and RESET-versus-supply errors.
- Add a tested, bounded native zone-fill adapter with crash recording and no automatic retry/promotion. The direct `ZONE_FILLER.Fill` path used here is not yet reliable in this runtime.
- Preserve compact rejected evidence automatically, including native DRC/group deltas and the disposition, without committing every failed full-board snapshot.
