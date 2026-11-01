# Fabrication preparation — 2026-11-01

The first full 12 V prototype remains unreleased. The generated
[inventory](README.md) is the current source selection; older board/gallery
milestones retain their original scope.

## Completed in this work

- Reviewed all 11 available PCB candidates with isolated KiCad 10.0.7,
  explicit native check coverage, refill, schematic parity, ERC and uncapped
  connectivity. Nine candidates report zero findings and opens.
- Reduced NF missing connections from 204 to 177 with 27 logic routes:
  256 new 0.2 mm segments and 43 conventional 0.65/0.3 mm through vias.
  All 267 footprints, original tracks/vias, authored zones, keepouts and
  other board geometry remain exact. No tracks were added to its reserved
  power planes. The final candidate has zero geometry/parity findings and
  retains both isolated-domain ERC warnings. New plane clearances still
  require PDN/noise review; routing does not establish force-current capacity.
- Removed ten geometrically covered E28 track objects. Native warnings fell
  from 52 to 49: 30 track tips and 19 via stubs remain. Opens, hard DRC,
  ERC and parity findings remain zero. Footprints, pads, vias, drills,
  authored zones and retained tracks remain exact.
- Captured portable projects containing only their used footprints and
  symbol libraries. Input-range's split PCB/schematic sources were explicitly
  combined without changing its PCB rules or circuit.
- Independently compared normalized legacy CAD for the inlet, carrier,
  input-range and ADC boards. KiCad's generated identities and numeric-net
  format conversion do not change their authored geometry or attributes.
  The other unchanged candidates passed direct saved-object comparisons.
- Added evidence checks that reject modified PCBs, schematics, projects,
  captured libraries, library tables, native reports and disabled rule checks.
  Geometry tests cover nanometre containment boundaries, non-plated holes,
  inner-layer obstacles, diagonal crossings and exclusion of timing/sense
  nodes from generic logic routing.

The E28 coverage draft's top-level
`no_target_outer_copper_lost_in_conservative_authored_shape_screen` wording
overstates the scope of its polygon approximation. The authoritative per-track
records distinguish conservative polygon coverage from exact integer capsule
containment. The removal audit uses
`actual_track_copper_covered_by_remaining_electrodes`, not that top-level flag.

## Verification

The 23 focused geometry/evidence/audio-storage-pause tests pass, as does Ruff
for the new fabrication tools and tests. All 11 selected native reviews match
their selected checked CAD. The inventory covers all 13 baseline functional
roles plus negative startup and fan protection.

Mac CAD applications were not launched. Bulk audio generation remains paused.
The fabrication staging folder was approximately 153 MB at completion of this
checkpoint, with approximately 540 GB free on the workspace volume. No orders,
vendor messages, commits or pushes were made.

## Remaining design work

NF still needs 177 connections and its final fault/force interfaces. E28 needs
review of 49 warnings and its current/return/process requirements. Four roles
still have no PCB: rail monitor, converter, DAC receiver and sequenced bypass.
The final physical partition must reconcile those functions with the existing
boards. The ESS package drawing remains missing; the exact
[supplier request](manufacturer-inputs.md) is prepared but unsent.

The selected boards also need exact parts/process acceptance, the complete
harness and updated whole-unit receiving, power/fault, noise and thermal
reviews. Fabrication/assembly outputs and their independent inspection,
followed by the first-article bring-up package, remain to be completed.

## Later checkpoint: package corrections and E11 layout

The [package review](package-review.md) identifies generic-land differences
for TPS3431SDRBR and the bypass's SN74LVC1G74DCTR. New candidates correct NF
U3/U9 and fan-protection U4 without changing their circuit values, pin nets,
positions or existing routed copper. Their native counts remain 177 opens/two
ERC warnings and zero findings/opens respectively.

E11 now has a fully routed 110 × 55 mm, four-layer development PCB: 55 circuit
parts, four mounts, 406 segments and 64 conventional through vias. All native
DRC, ERC, parity and connectivity counts are zero with every category enabled.
The original circuit's values and pin nets are exact; only two footprint IDs
change. C1 rotates at the same position to permit a shorter local watchdog
route and the final supply escape. Independent saved-file and top/bottom
visual reviews are recorded in its [handoff](staging/bypass-closed-native-03/handoff.json).

There are now 12 available PCB candidates with source-bound native reviews;
10 have zero native findings and opens. The three roles still without a PCB
are rail monitor, converter and DAC receiver. This supersedes the earlier
four-missing-PCB count. Physical board partition and complete-unit release
remain open. The E11 module's mechanical allocation, exact passive/connector
selection, process, audio/coil returns and measured timing/noise remain
unqualified.

The bounded router used the official pinned Linux ARM64 Java image with no
network or API, 2 GB container memory and two CPUs. Its log's cumulative
allocation counter is not resident memory or disk use; peak heap was about
92 MB. No Mac CAD application was launched. The 30 targeted geometry,
package, evidence, original-circuit and audio-pause tests pass, as does Ruff.

## Later checkpoint: E13 rail-monitor PCB and NF single-net improvement

E13 now has an 80 × 70 × 1.6 mm, four-layer development layout with all 181
original circuit parts and four M2 clearance mounts. Native schematic export
preserves every original value, pin net and footprint ID. Routing reduced 383
initial opens to **13 remaining**. The selected candidate has zero native
geometry, ERC or schematic-parity findings, with all check categories enabled.
It has 1,931 segments and 329 conventional through-vias; signal tracks remain
on F/B copper, with AGND and split supply planes on the inner layers.

The [handoff](staging/rail-monitor-dogbone-native-01/handoff.json) binds the
original circuit, exact placement/plane comparison, native reports, captured
libraries and top/bottom review plots to their saved hashes. All 185 component
and mounting footprints retain their original placed geometry. A separate
native-polygon screen finds at least 0.15 mm between every drilled hole and SMD
copper. This does not accept mask webs, stencil design or assembly processes.
Exact precision/passive MPNs, local-loop/noise/fault review, the proposed board
allocation and installed harness remain open.

Rejected intermediate routes are preserved: widening router necks exposed
three clearance errors near R110, which were repaired using the unchanged
0.2 mm rule. Two byte-identical repeated track occurrences were removed. A
copper-sliver warning was traced to an acute junction at R50 and eliminated
by replacing that junction. No DRC/ERC categories were ignored. A final bounded
finishing attempt found no additional routes; it was not promoted. The next
E13 step is a local routing/placement revision around the remaining supply pads.

NF improves from 177 to **176 opens** by adopting only the
`N19_ARM_CONDITIONED` net from a bounded continuation. The
[single-net audit](staging/nf-arm-only-native-01/single-net-audit.json) confirms
that all other authored objects, component values, pin maps and footprint IDs
are exact, and no other net's open count regresses. Native geometry and parity
findings remain zero; the two isolated-domain ERC warnings remain visible.

The inventory now contains 13 PCB candidates across 15 functional roles;
10 candidates have zero native findings and opens. The converter and DAC
receiver still lack PCB layouts. The ESS package/land drawing, complete-unit
partition, parts/process acceptance, mechanical receiving, harness, power/fault,
noise/thermal review and inspected fabrication/bring-up package remain open.
The unit is not released for fabrication.

All CAD operations used the pinned, bounded, network-disabled Linux tools.
Mac CAD remains disabled and bulk audio generation stays paused.

Verification at this checkpoint: 38 focused circuit, geometry, package,
evidence, drill-boundary and audio-pause tests pass; Ruff and `git diff --check`
pass. Every selected native review and supplemental handoff matches its saved
source hashes. Fabrication staging occupies approximately 278 MB; about
539 GiB remains free on the workspace volume. No supplier messages, orders,
commits or pushes were made in this checkpoint.

## Publication preparation

The owner requested the saved work be committed and pushed to main with a clean
tree. Shapely2.1.2 and SciPy1.18.1 are now explicit locked tooling dependencies,
matching the versions used for geometry/routing and thermal checks. A fresh
locked environment exposed the previously undeclared SciPy requirement in the
E28 barrel-edge regression; it is retained as a required test dependency.
Recorded repository paths can be relocated to another checkout without editing
the original receipt strings or hashes; external inputs retain their original
locations and cannot silently resolve to different repository files.

The new supply-first E13 trial is also preserved in staging. It establishes
116 planned plane connections from the initial placement before signal routing;
native checks remain pending. It does not replace the selected13-open native
candidate or change the fabrication holds.

Pre-push validation in the locked environment passes620 tooling tests
(three skipped),23 CAD integration tests and five A08 inventory tests. Current
selected source/evidence hashes match. The original dogbone recipe bytes are
preserved under `recorded_recipes/`; three generation receipts reference that
snapshot after normalizing the editable helper's final blank line.
