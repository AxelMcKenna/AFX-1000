# Held-cell reference extension and guarded native-fill workflow

`native-plane-04` adds one filled main-ground zone on In6, from (136,158) to (158,180), priority 2. It retains all 47 original zone objects and complete fill geometry exactly. The new fill is 467.853 mm² and overlaps the existing main-ground fill by 185.079 mm². All 2,714 original native groups, original pads/tracks/vias and 55 formerly anonymous pad identities are unchanged. Opens remain 1964. Final native DRC has exactly the four unwaived DSE errors, with no added violations. This remains an isolated candidate; the accepted PCB is unchanged.

`verify_plane.py` independently verifies full retained zone geometry, actual main-fill overlap, protected quiet copper/plane exclusion, native group/object evidence, numeric polygon coordinates, exact source bindings and unchanged project rules. The extension overlaps no protected quiet return. It provides actual reference copper for the reservoir/LDO cell; it does not establish rail-current, thermal, RESET timing or full distribution qualification.

## Diagnosed failure and corrected interface

The first authored polygon mistakenly encoded coordinates as quoted strings, e.g. `(xy "136" "158")`. The direct Python path did not check `LoadBoard` success before constructing `ZONE_FILLER` and exited 139. No native stack trace was captured. The supported CLI entry point diagnosed the input explicitly with exit 3 and a coordinate parse error. This is evidence of invalid authoring and an unchecked load; it is not evidence that the pinned filler itself is unreliable.

The corrected builder emits numeric atoms and preflights them. `run_plane.py` performs coordinate preflight before native work. It calls the supported `kicad-cli pcb drc --refill-zones --save-board` interface with the actual project filename/context, then keeps only the new native fill while retaining all original filled zones. `process_adapter.py` records commands, source hashes, output/error logs, exit codes/signals, timeouts and input preservation before the caller can promote an output. Nonzero, timeout or signal results fail the pipeline. Previous evidence directories cannot be overwritten.

A second input defect used the original priority 1 for an overlapping new zone. Independent DRC rejected this despite successful fill and group checks. The final input assigns only the new zone priority 2; original zone priorities and all clearance rules remain unchanged.

Original invalid input, corrected-numeric intermediate input, and final priority-2 input are preserved under `authored`, `authored-02`, and `authored-03`. Rejected runtime evidence is preserved compactly; failed full candidate boards stay local. The corrected final refill completed in 113.77 seconds, followed by native DRC and the independent verification.

## Reproducible bounded workflow

Use the pinned Linux image `kicad/kicad@sha256:c8f05703e865a1caa7266851cf4986dd01d5fb1148e4f63382b6a73466ba7e71`, linux/amd64, no network, read-only repository mount and isolated writable output. Run `run_plane.py AUX_ROOT EMPTY_OUTPUT`. Its parent bound is 420 seconds; each CLI child is bounded to 180 seconds. Existing nonempty output directories are rejected.

After successful native checks, run `package_plane.py`, then `verify_plane.py`. Packaging replaces the 224 unchanged library files with a relative symlink to the same worktree's `shared_cutover/native-04/libraries`, after verifying identical hashes; the original copy is preserved locally. The verifier rejects missing, changed, unexpected or escaping link targets. Docker must mount the repository containing both candidate and target.

Twelve regression tests cover subprocess success/failure/signal/timeout, prior-evidence preservation, the original quoted-coordinate defect, non-finite coordinates and library confinement. Local cell routing is the next stage and must use captured final filled geometry, with explicit pin/net assertions and semantic group deltas.

Electrical receiving conditions remain unresolved: ≥200 µF effective reservoir, ≤100 mA drain, ≤20 mV distribution drop and ≤1 µs logic-delay allocation. The modeled 81.00348 µs hold interval and 50.00348 µs driver-turnoff allocation remain conditional. No process waiver or fabrication release is implied.

The next verified local-copper checkpoint is `native-local-02`; see [LOCAL.md](LOCAL.md) for its 18 connections, exact preservation checks and remaining external routes.
