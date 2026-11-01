# Clean-checkout qualification checks

The `b107c1b`/`ba5b97e` CI runs exposed failures that the original Mac checkout
did not reproduce. These changes retain the design limits and saved native
findings. They do not release any board for fabrication.

- The pure PCB canonicalization helper no longer imports `pcbnew` until its
  Linux-only native entry point runs. An isolated import test with the platform
  set to Linux succeeds without a native SDK. The four previous native-audit
  receipts now reference an exact archived copy of their applied recipe.
- Four small KiCad session-state files were already hashed by preserved ADC and
  NF review seals, but the global ignore rule omitted them from checkout. Their
  exact recorded bytes are included for historical integrity. They do not
  substitute for the project rules, PCB or native reports.
- The thermal regression relocates recognized recorded checkout paths. Its
  previous source bytes are retained in the existing historical-source index;
  no historical result is promoted to current-board acceptance.
- The NP01-P2 checkout successor leaves both sealed NP01/P1 packets unchanged.
  It relocates only recognized checkout prefixes and sealed-verifier file
  lookups in a private namespace. All geometry, identity, hash, type and numerical
  checks remain active, including the existing four-ULP rule for identified sums
  of five unchanged terms. Unknown saved-evidence errors remain failures. A
  separate 26.9 MB checkout reproduces the old path comparison errors and passes
  the successor with all 55 parent and 27 P1 files intact.
- The full-firmware integration fixture now runs a silent startup callback
  before dispatching physical gestures, matching the live-callback prerequisite
  in firmware `canDispatch`. It additionally requires that startup emits no
  unsolicited pad. The existing positive audio-energy requirement is unchanged.
- The Spiral storage regression retains its exact 30,100,112-byte logical SDRAM
  budget through an allocation-accounting adapter. The real `FixedArena` still
  enforces platform-aligned capacity and zero callback allocations. Both the
  ordinary eight-byte arena and an isolated sixteen-byte-alignment variant pass;
  the latter uses 30,100,224 physical bytes. No audio-buffer budget was increased.

Validation: 628 tests pass in the shared current worktree, with three skipped.
All 16 full-firmware tests pass in an isolated source snapshot of `ba5b97e` with
only the integration fixture changed. Both Spiral alignment variants pass
poisoned-history, ownership-transition, finite-output and zero-allocation checks.
The snapshot avoids validating these fixes against concurrent DSP edits.
Fresh GitHub CI results remain the final cross-platform check.

Mac CAD stayed disabled. No bulk audio, supplier request, order or fabrication
release was produced by this CI repair.
