# E28 cleanup and manufacturing review

The selected [E28 candidate](../e28-branch-cleanup-native-12/rail_disconnect.kicad_pro)
has zero native DRC, uncapped missing connections, schematic-parity and ERC
findings, with all rule categories enabled. **It is not released for fabrication.**

The removal-only cleanup deleted 411 track segments and 32 vias from the prior
49-warning candidate. Sequential local copper proofs account for drills, layer
separation and disconnected zone polygons. Independent source comparison verifies
all 275 footprints, pad nets, values, poses, retained tracks/vias, authored zones,
stack settings and rules are exact. Native refill and uncapped connectivity checks
passed after every accepted pass. The proofs establish connectivity, not unchanged
conductance, thermal paths or return impedance.

All eight native before/after layer plots were inspected at 300 dpi. The comparison
images and their hashes are in [assets.json](assets.json); the scoped findings are
in [visual-review.json](visual-review.json). The cleanup tool's 29 focused tests pass.
The independent [cleanup audit](../e28-branch-cleanup-native-12/cleanup-audit.json)
and [handoff](../e28-branch-cleanup-native-12/handoff.json) bind the selected source.

The retained 1,385 vias include **311 whose drilled holes intersect SMD copper**;
310 intersect lands that declare a paste layer. All 311 have native `filling no`
and `capping no` fields. The [location map](../e28-branch-cleanup-native-12/drill-land-locations.csv)
includes passive, IC and SMT terminal lands. These require appropriate individual
process and stencil review. Another four vias fall within the 0.1 mm proximity
screen without intersecting SMD copper. The screen is not a factory acceptance
criterion or a stencil-aperture analysis.

Historical E28 [passive-via requirements](../../../electronics/rail_disconnect/revision28/generate.py)
and [terminal stitching](../../../electronics/rail_disconnect/revision28/terminal_stitching.py)
already propose filled/capped, flush structures. Those assumptions must be reconciled
with the current native metadata and fabrication/assembly instructions. This review
does not change the metadata or accept a supplier process. Use the current
[construction capture](construction-review.json), not the older six-layer generator:
the selected board declares 1.62 mm total, eight copper layers, six at 80 µm and
In3/In4 at 35 µm. Material values and finish remain unaccepted proposals. The sole
0.2 mm drill is unchanged.

The [AP01 allocation rebind](assembly-allocation-rebind.json) updates only the E28
source path and PCB hash. Its geometry, receiving limits and conditional results
exactly match the preserved original allocation. This is not a fresh complete
assembly clearance pass. The original AP01 receipt remains historical; use
`python -m hardware.fabrication.audit_scope` to validate the current selection.

The [AC04 interface rebind](audio-integration-handoff-rebind.json) likewise
preserves every circuit, logic, DC/settling and 42-conductor schedule result;
only the selected E28 evidence references change. The original audio handoff
is retained. The full inventory audit passes with 126 matching source hashes
and no native or additional-evidence errors.

Before release: resolve the process map, exact parts and assembly instructions;
renew source-to-load power/return, fault and thermal analysis; complete installed
component, mounting, terminal and harness receiving; and inspect final manufacturing
outputs with a bounded first-article inspection and bring-up plan.
