# Combined housing fit checks

New integration work uses the [unified assembly workflow](../assembly_workflow/README.md). This directory preserves the earlier explicit cross-fit evidence.

The current modeled assembly combines the two main PCB allocations, display and selector carriers, 25 button indicators, meter/bank LEDs, RGB ring, revised knobs, populated sensor board and spring mechanism, sensor ribbon harness, and r9 fan pods and leads. The final guide uses `tbh07_connected_guide_variant()`; the superseded ring guide contains an unretained center island.

The r9 housing/cooling body envelope is **363.6 × 192.4 × 45.6 mm**, excluding raised controls, feet and external plugs. This is a candidate fit, not a fabrication or complete installed-fit release. The design currently has two main boards plus 34 passive control boards, a sensor PCB and Daisy Seed; literal two-physical-PCB compliance is unresolved.

## Evidence

- `trial07-knobs/review.json`: 15 checks covering the earlier assembled controls, populated sensor and 25 mm shaft knobs.
- `trial08-fan-harness/review.json`: two internal fan route cross-fit checks.
- `trial10-support-contacts/review.json`: new supports and fasteners clear the lid/guide. The old and new full pod share the same zero-volume lid seating contact; this is recorded separately, not called a strictly empty intersection.
- `trial11-ring-terminal/review.json`: seven checks covering the RGB ring and detailed fan terminal routes. Its guide is superseded for printing.
- `trial13-internal-probe/review.json`: split internal fan route clears the complete controls.
- `trial14-complete-split/`: found a 9.48536 mm³ sensor harness/control interference at X249.363..252, Y70..73.2499, Z29.1..31.6, within the scene-depth pot receiving allocation. The relocated clamp fixes this defect in trial15.
- `trial12-complete-controls/`: the first three combined final-control checks are empty. The full internal-plus-external fan CSG operation timed out at 60 seconds and its container was stopped; no result is claimed for that case. See `timeout-diagnosis.json` for the split-check approach.

Each runner binds recursive SCAD dependencies before and after rendering. It uses the authorized pinned isolated Linux OpenSCAD image, bounded runtime and fresh output directories. The macOS CAD runtime remains disabled. Earlier evidence remains immutable.

- `trial15-corrected-harness-mates/review.json`: all five corrected sensor-harness checks pass. Five panel-mate checks pass, but the conditional mate envelopes overlap the ribbon by14.94994 mm³; trial16 corrects this separate defect.

- `trial16-sensor-mates-repaired/review.json`: all six affected corrected-harness checks pass, including the panel mates.

## Remaining fit gates

Finish the combined final-guide and cable checks, then integrate the remaining exact panel harness mates and routes. Some connector plugged envelopes may exceed the original generic allocation. Confirm actual pot bodies, fan lead exit, wire preparation, printed tolerances, lever return and magnetic sensing. Optical, electrical, airflow and thermal tests remain open. Passing nominal geometry alone does not close these gates.
