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

## Fabrication goal: E13 supply-first routing investigation (2026-11-01)

The complete standalone fabrication goal remains active. No manufacturing
release or supplier order has been made. Existing selected sources remain
unchanged while the following separate candidates are evaluated.

- `rail-monitor-supply-first-native-02`: fresh isolated KiCad review of the
  previously pending supply-first candidate. Zero geometry/ERC/parity findings,
  267 opens versus the original placement's 383. The first invocation's
  `rail-monitor-supply-first-native-01` directory is incomplete: it stopped at
  a missing footprint-library environment variable before native checks.
- `rail-monitor-supply-first-routing-01`: bounded network-disabled router
  completed normally; session imported with original footprints, authored
  zones and board setup preserved. Router warnings about fixed same-net
  pad/via proximity are not native acceptance findings.
- `rail-monitor-supply-routed-native-01`: native result was 21 opens, four
  clearance errors and three dangling-via warnings. Every remaining open is
  on `/V3V3_IO`; all other circuit nets are connected.
- `rail-monitor-supply-repaired-native-03`: zero DRC geometry/ERC/parity
  findings, 21 opens. Removed three unused via stubs, moved the
  LOWV_WINDOWS_OK via and its attached endpoints by 0.03 mm, and changed one
  N12_INV via from 0.65/0.30 mm to 0.60/0.30 mm (0.15 mm nominal ring).
  Existing native rule values were retained. Earlier failed repairs remain
  in staging. Recipes are captured beside their construction records.
- `rail-monitor-capped-native-01`: rejected alternative. Nine filled/capped
  via-in-pad additions reduced opens to four but introduced 30 native findings,
  including shorts to existing backside routes. Do not promote this candidate.
- `rail-monitor-power-tree-01`: a bounded In2 power-routing search made no
  connections. Inspection shows most of the 22 isolated 3.3 V groups lack
  through-layer access; the signal routing has occupied their escape space.
  This is evidence for reserving the full 3.3 V distribution before signal
  routing, not a successful distribution design.

Next: start from the original placement/supply-first stage, reserve conventional
3.3 V escapes even where the pad is outside the existing right-side 3.3 V pour,
route that distribution on In2 with fresh 5 V refill/connectivity review, then
reroute signals. Preserve the dedicated In1 ground layer and review the revised
supply copper for resistance, local bypass paths and noise. Do not inherit the
old handoff's assertion that all tracks are on F/B if In2 power tracks are added.

The clean 21-open candidate is a development branch, not a replacement for the
selected 13-open candidate. Exact parts/process acceptance, the converter and
DAC receiver, NF routing and whole-unit integration remain required. Supplier
preference was requested; work can continue with supplier-neutral outputs.

Validation: fresh pinned Linux KiCad 10.0.7 native reports as above; 18 focused
fabrication/package tests pass; `git diff --check` passes. Ruff was unavailable
in the current environment and was not claimed as passed. Mac CAD stayed
disabled. No audio work was changed. Captured Docker execution receipts are
under the clean candidate's `execution-records/` directory.

## E13 complete routing selected (2026-11-01)

The new selected source is `staging/rail-monitor-reserved-closed-native-02`.
Fresh isolated KiCad reports zero DRC findings, zero opens, zero ERC and zero
schematic-parity findings with all rule categories enabled. The original
181 circuit parts, their values/pin nets/footprints, four mounts, placement,
board setup and authored planes remain exact. The prior 13-open candidate
remains preserved and is named as `previous_source` in the inventory.

The supply-first sequence now reserves all 24 missing 3.3 V surface escapes,
then connects them with 0.4 mm In2 power branches before routing signals.
Pre-routing native checks confirm no AGND, V5_REG or V3V3_IO opens. The bounded
router completed with zero unrouted items; native import retains the exact
In2 tracks and original footprint geometry. Its only native clearance error
was repaired by moving one LOWV_WINDOWS_OK via and its attached endpoints
0.03 mm, retaining the 0.2 mm rules. The incomplete `closed-native-01` folder
came from a recipe coordinate-type assertion and contains no valid native
review; `closed-native-02` is the checked result.

Native drill screening covers all 357 vias and finds a minimum 0.1101 mm
hole-edge-to-SMD-copper gap. No via-in-pad assembly process is introduced.
This does not establish acceptable mask webs, stencil or manufacturing
registration. Top/bottom and both inner-layer copper plots were rendered and
visually inspected. Native polygon extraction finds one connected polygon
for each authored AGND, V5_REG and V3V3_IO pour; this is not a DC/AC impedance
qualification. The ground layer contains no signal routes. The new In2 power
routing and changed via population require updated PDN/noise review.

`rail_monitor_reserved_handoff.py` explicitly permits only V3V3_IO power
tracks on In2, and records visual review plus the remaining holds. It does not
inherit the old handoff's all-F/B-track assumption. The new regression checks
validate the actual pre-routing supply closure, original circuit, unchanged
component geometry and authored ground plane. The selected native evidence
and handoff dependencies match their files. Twenty-eight focused tests and
`git diff --check` pass. All 15 functional roles have sources; 11 of 13 PCB
candidates now have zero native findings and opens. NF remains at 176 opens,
E28 retains its 49 warnings, and the codec/DAC receiver still lack layouts.

The complete unit remains unreleased. Remaining E13 work includes exact
precision/passive parts, integrated threshold/noise/error budgets, power
resistance and return paths, the actual 80 x 70 mm installed allocation and
harness, mask/stencil/process acceptance and fabrication/assembly output
inspection. Native checks do not qualify those requirements or authorize
complete-unit power-up. No supplier messages or orders were sent.

## NF six-net routing improvement selected (2026-11-01)

The selected NF source is now `staging/nf-six-net-native-01`, with **170 opens**,
zero native geometry/parity findings and the same two isolated-domain ERC
warnings. All native rule categories remain enabled. The earlier 176-open
source is preserved and recorded as `previous_source`.

The new `net-set-audit.json` independently verifies improvement on exactly six
nets: N19_WD_ENABLE, N12_START, N19_START_DELAY_N, CLAMP_SUPPLY_ENABLE,
N12_ARM_CONDITIONED and N19_BIAS_VALID. No other net's open count changes.
Every component, value, footprint, numbered pin net, authored plane, mounting
feature and non-target copper object remains exact. Project rule values are
unchanged. The schematic's negative-domain ground references are retained;
the two warnings were not suppressed or "repaired" by connecting them to AGND.

Three improvements came from a targeted logic-router trial. The DSN separates
logic and protected nets into classes; the profile excludes the protected
class, and selected logic copper is explicitly unlocked. The saved router
settings confirm that exclusion. The broad imported result has 173 opens and
20 dangling-via warnings; only the three improved nets were adopted. It is not
selected as a whole. The preserved broad trial and all rejected paths remain
available as evidence.

Two additive connections came from the bounded 0.20 mm logic search with new
0.60/0.30 mm vias. A further bounded search using the project's existing
0.16 mm minimum trace width connected N19_BIAS_VALID. Combined native checks
confirm 176 -> 170 opens without regression. There are five new 0.60/0.30 mm
vias (0.15 mm nominal annular ring); existing vias retain their original sizes.
The separate drill screen covers all 17 new/replaced via UUIDs and finds at
least 0.365388 mm from their drilled-hole edges to SMD copper. This is not a
qualification of all legacy via/paste treatments or manufacturing tolerances.
New through-hole clearances, logic path timing/noise and actual plane impedance
still need integrated review.

The no-via short-signal search found no legal additions; its zero-result trial
is retained. The targeted router completed a bounded timeout with a usable
session; no live processes from these trials remain. No native Mac CAD was
launched. Actual native checks use the pinned network-disabled Linux image.

Validation: 21 focused net-boundary mutation, native evidence, single-net and
rail-monitor tests pass; `git diff --check` passes. All selected native reviews
and supplemental handoffs match current source hashes. Regression mutations
reject component motion, protected power-track width changes and relabelling
protected copper as an allowed logic net.

The complete fabrication objective remains active. The next NF work starts
from the captured 170-open geometry and retained failed-pair attempts, with
separate attention to the remaining low-current timing/sense nets and actual
force-current paths. Most remaining connections cannot be closed by simple
surface additions. The ESS land-pattern/reference-interface data remain an
external dependency; a document link or existing supplier contact has been
requested. No supplier messages or orders have been sent, and no unit release
is claimed.

## NF local watchdog timing placement — 170 to 168 opens

The timing-net inventory exposed a placement defect before further routing:
C1 was 57.16 mm from U3 CWD and C2 was 122.05 mm from U9 CWD (projected pad
centres, not routed lengths). The original area packing localised bypass caps
but left these timing capacitors in its general packing pool. TI TPS3431
SNVSB66A (October 2021), section 10.1, page 21, requires the external CWD timing
capacitor to be close to the pin: https://www.ti.com/lit/gpn/tps3431.

A separate candidate moves only C1 and C2 to screened rear sites. Their new
projected pad distances are 2.851 and 4.174 mm. The resulting F/B timing traces
are 3.412 and 8.339 mm, each with one 0.60/0.30 mm via; these planar lengths
exclude the vertical barrel. Each capacitor has a new short rear AGND escape
to In1. Native connectivity puts each return in its owner's ground group.
Only the two vacated front ground stubs and their terminal vias were removed.
No other component pose, existing copper, authored zone, circuit value, pin net,
package or project rule changed. Native DRC/refill regenerates plane fills.

Selected source: `staging/nf-watchdog-routed-native-02/negative_startup_physical.kicad_pro`.
Full independent native checks give zero geometry/parity findings, 168 uncapped
opens and the same two isolated-domain ERC ground warnings, with all checks
enabled. The per-net audit finds no connectivity regression. Four new via
drills have minimum hole-edge-to-SMD-copper clearance 0.175 mm. Native front,
back and ground PDFs and 600-dpi timing-region crops were visually inspected;
In1 AGND remains one filled polygon. New through-via holes still need return
impedance/noise review and mask/stencil/process acceptance.

The board now has 152 front and 113 rear electrical parts. C1/C2 use a proposed
1.9 mm complete rear-height receiving envelope; their courtyards avoid the
conservative carrier X bands. These arithmetic reservations do not qualify the
actual enclosure/body/tail/wire assembly. Scope records renewed receiving and
timing/noise holds. Earlier candidates and failed trials are preserved. The
first routed-native-01 folder contains no completed review because the candidate
file was not yet written; only routed-native-02 is selected.

The source-bound timing inventory also identifies C37/U25 (124.25 mm), C35/U26
(108.68 mm), C8/U21 (103.22 mm), C53/U23 (96.28 mm), and C10/U20 (94.91 mm),
plus other CT/TMR/SS/RAMP placements needing local-cell review. These are explicit
fabrication holds. Routing closure alone is not a sufficient acceptance target.

Validation: 14 focused placement-boundary, net-boundary, native-selection and
reserved-supply tests pass, including mutations that move U3, relabel new timing
copper as force power or remove extra ground copper. The complete unit remains
unreleased; ESS documentation, other boards, integrated electrical/thermal
analysis, current mechanical receiving and inspected production outputs remain
open. No supplier message or order was sent. Fabrication preparation continues.

## NF four local supervisor CT placements — 168 to 166 opens

The previous goal turn made verified progress: two watchdog timing cells were
relocated and routed. This continuation addressed four further remote CT
capacitors. C8/U21, C10/U20, C35/U26 and C37/U25 had projected pad separations
of approximately 103.22, 94.91, 108.68 and 124.25 mm. The new rear placements
reduce those distances to 4.940, 5.809, 7.567 and 5.039 mm respectively. The
placements are source-bound and screened against actual copper, rear courts,
through-hole projections, keepouts, board inset and carrier X reservations.

Selected source: `staging/nf-ct-local-native-01/negative_startup_physical.kicad_pro`.
It contains all four relocated CT capacitors and their correct local reference
returns. C8/C10 timing connections are complete; C35/C37 CT connections remain
open. The references are N19_P03_SRC and N12_P03_SRC, not AGND. TI TPS3890
SLVSD65A, sections 6 and 11, identifies CT and local GND and shows the local
capacitor layout: https://www.ti.com/lit/ds/symlink/tps3890.pdf. The engineering
placement decision uses that topology; no invented numerical TI distance limit
is asserted.

One obstructing N12_COMPLETE segment was replaced by a screened local detour.
Twenty-four vacated reference-branch objects were removed in staged cleanups.
The independent audit compares all authored objects with the 168-open source:
only the four capacitor footprints change; all retained original tracks, vias,
authored zones, project rules, component identities, values and pin nets stay
exact. Six new 0.60/0.30 mm vias have minimum screened drill-edge-to-SMD-copper
clearance 0.190037 mm. All native checks remain enabled. Results: zero geometry
and schematic-parity findings, 166 uncapped missing connections and the same
two isolated-domain ground ERC warnings. No net has more opens, and an explicit
native-group audit verifies that every unmoved pad retains its previous pad
connections. All four capacitor returns join their owning IC's reference group.

Native front/back/ground PDFs and 600-dpi local-region crops were inspected.
In1 AGND remains one filled polygon. There are now 148 front and 117 rear
circuit parts; the four new rear sites use proposed 1.9 mm complete receiving
heights and pass the conservative carrier/upper-seat arithmetic screen. Actual
body/tail/wire fit, assembly tolerances, mask/stencil registration, local noise,
return impedance and fault/thermal integration remain unqualified.

C35/C37 cannot be completed by the existing bounded additive routing screen.
Their CT pin exits face densely placed bypass lands/vias and inner-layer
copper. Separate unselected trials identify the constraints: removing the local
reset routes alone does not free a conventional via site; N12_PERMIT_D blocks
U25's available site, while N12_INTVCC and N12_BIAS_SENSE routes and rear bypass
lands constrain U26. A 0.158 mm U26 bypass-via move passes native geometry but
is not adopted. A larger escape trial connects C37 but strands a reset path,
so it is also not adopted. The selected source preserves the original supply
vias and reset/permit routes. The next useful action is a local placement/routing
revision of the U25/U26 bypass/CT cells, with their complete functional pin
connections checked together. Re-running the unchanged additive search is not
an adequate next step.

All partial trials and their native findings are retained. `capture_rework.py`
permits planning from explicitly retained dangling warnings; it never suppresses
native rules or grants acceptance. The final selected capture has no such
warnings. No native Mac CAD, supplier message or order was used. The complete
fabrication goal remains active, including remaining NF cells, missing ESS
inputs, other boards and the integrated unit.

Validation for this revision: 27 focused fabrication-evidence, CT/watchdog
boundary, per-pad connectivity, net-scope and reserved-supply tests pass.
Mutation cases reject force-track width changes, loss of an unmoved reference
pin connection, and relabelling a local capacitor reference as AGND. Selected
native/supplemental evidence hashes match; `git diff --check` passes.

## NF U25/U26 cell rework and eight-layer feasibility — 164 opens, unselected

The local-cell rework now closes C35/U26 and C37/U25 CT connections in a separate
eight-layer trial. `staging/nf-eight-cell-native-02` has 164 uncapped opens,
zero native geometry or schematic-parity findings and the same two isolated
ground ERC warnings. The authoritative six-layer source remains
`staging/nf-ct-local-native-01`, with 166 opens. This is a demonstrated routing
alternative, not an accepted stackup or fabrication release.

C36/C38, the existing 1206 C0G bypass capacitors, move left by 0.6 mm without
changing parts or pin nets. One existing 0.65/0.30 mm INTVCC via moves by
approximately 0.158 mm. Eleven local CT-cell reset/permit/sense/INTVCC segments
are replaced, six existing trace endpoints are adjusted and seven 0.60/0.30 mm
vias are added. New CT/reset routes use at least 0.16 mm width; sense/INTVCC/
permit routes retain at least 0.20 mm. No project clearance rule was relaxed.
The final sense search reduces only the extra numerical planning margin from
0.010 to 0.001 mm; the saved project still requires 0.20 mm clearance and the
fresh full native DRC passes geometry.

The previous AUX2V6 plane/keepouts move from In4 to In6. In4/In5 become signal
layers, with twelve matching keepouts copied from the existing internal-layer
mechanical reservations. All original authored zones, after that explicit
layer mapping, are exact. Board outline and nominal 1.2 mm thickness remain
exact. No dielectric thickness, material, copper weight, impedance or supplier
stack acceptance is inferred from the nominal thickness or the layer count.

The independent `eight-layer-trial-audit.json` checks exact permitted edits,
unchanged circuit/value/package/pin nets and project rules, original copper
outside the scoped edits, keepout replication and every original pad
connectivity relationship, including both moved bypass capacitors. No net
regresses. All four previously relocated CT capacitors now connect both their
CT pin and their owning local reference. These references remain N12_P03_SRC
and N19_P03_SRC. Seven new and one moved drill have minimum screened
hole-edge-to-SMD-copper gap 0.330613 mm. All existing via holes were also screened
against the moved C36/C38 lands; minimum gap is 0.400 mm. This does not qualify
legacy vias elsewhere or mask/stencil/registration tolerances.

Native front/back/ground/new-In4/new-In5/AUX-In6 PDFs and 600 dpi crops were
inspected; both planes remain one filled polygon. The added internal copper is
localized to these CT and sense cells. CT planar routes measure approximately
12.364 and 11.579 mm with two vias each. The rerouted sense path is 21.715 mm
with two added vias. These lengths, changed bypass escapes and plane antipads
require timing/noise/return and PDN assessment. Contiguous plotted copper is
not evidence of an adequate return impedance. The current 265-part installed
assembly still needs actual body/tail/wire receiving.

Bounded six-layer host searches and a scoped official router run did not close
the entire cell without losing another local connection. Those partial trials
are retained unselected. This does not prove six layers impossible. The
eight-layer alternative gains only two closures at this stage, so broader NF
routing benefit and stack/return tradeoffs must be assessed before changing
the selected development source. Remaining remote CT/TMR/SS/RAMP cells should
be placed locally before further bulk routing; C53/U23 remains a specific
96.28 mm soft-start placement concern.

Validation: 33 focused tests pass, including loss of a new-layer keepout,
incorrect AUX plane mapping, unrelated force-copper changes, bypass-pad
disconnection and local-reference relabelling mutations. Source-bound native
and independent trial receipts are retained. No supplier request or order was
sent. Complete-unit fabrication preparation remains active: missing ESS inputs,
remaining NF routing, E28 warnings, parts/process decisions, integrated power/
fault/thermal/fit analysis and inspected production outputs remain unresolved.

## NF local soft-start/timer cell — six layers, 166 to 163 opens

The previous turn was verified progress: an independently audited eight-layer
CT-routing alternative established a concrete tradeoff. This continuation
improves the selected six-layer board instead. The selected project is now
`staging/nf-softstart-cell-native-02/negative_startup_physical.kicad_pro`.
Native geometry and schematic-parity findings are zero, uncapped opens fall
from 166 to 163, and the same two isolated-reference ERC warnings remain.
All native categories stay enabled and the project rules are unchanged.

C53/U23 soft-start placement reduces projected pad separation from 96.28 to
5.067 mm; C54/U23 timer placement reduces it from 28.55 to 11.965 mm. Both
existing parts retain their values, packages and pin nets. They move to rear
sites at (31.25,31.25) and (15.25,34.75) mm respectively. Both timing paths and
their connections to the controller's local N12_P03_SRC reference are complete.
The extra reference connection also merges two pre-existing reference groups;
native per-net opens change SS 1→0, TMR 1→0 and N12_P03_SRC 7→6.

Three obstructing original segments are replaced: one 0.20 mm N12_VIN supply
segment and two 0.20 mm NF_NO_FAULT status segments. Seventeen vacated local
reference branch objects are pruned. Every retained original track/via and
authored zone stays exact; only C53/C54 footprints change. The original outline,
nominal 1.2 mm thickness and six copper layers stay exact. Independent native
group checks confirm every unmoved pad retains all its previous connections,
including the fault-status circuit. No net regresses. New traces are 0.20 mm;
ten new vias are 0.60/0.30 mm, with minimum screened drill-edge-to-SMD gap
0.200 mm. All legacy and new drills were separately screened against the moved
capacitor lands; minimum gap is 0.225 mm.

The SS timing route has approximately 7.518 mm planar length; the TMR route
has 20.194 mm. The reference branches have approximately 19.012 and 17.067 mm
planar routes in addition to the 0.951 mm controller reference escape. The
front NF_NO_FAULT segment is replaced by a 41.161 mm detour with three new vias,
versus 10.802 mm originally. This restores connectivity but requires renewed
noise/timing assessment; native DRC does not qualify fault-response integrity.
AGND remains one filled polygon, which likewise does not qualify return
impedance or power-plane resistance after added antipads.

The primary LTC4261 Rev D data sheet identifies SS/TMR and, on pages 23–24,
requires a local VEE plane and local component returns distinct from the main
negative-input plane: https://www.analog.com/media/en/technical-documentation/data-sheets/42612fd.pdf.
The new capacitor returns connect to the owning local reference group, not
AGND. Full local-VEE topology/noise qualification remains open. No numerical
manufacturer placement-distance limit is invented. KEMET's C1210C104J5GACTU
specification gives C53 body thickness 1.25±0.15 mm:
https://search.kemet.com/component-documentation/download/specsheet/C1210C104J5GACTU.
The 1.9 mm complete installed-height envelopes remain proposals, including for
C54; actual solder, body/tail/wire and assembly tolerance receiving is pending.
There are now 146 front and 119 rear circuit parts. Native front/back/ground
PDFs and 600 dpi local crops were inspected. Conservative carrier-X and upper
seat arithmetic screens pass for the two new rear courtyards.

The broader four-capacitor placement trial also moved C92/C95, but their pin
escapes remain unresolved. Both were restored exactly to their original poses
and copper in the selected revision. That trial and all intermediate native
findings remain preserved. The placement helper saved its candidate and then
exited with code 139; subsequent independent native loads, complete reviews
and source-bound captures verified the saved CAD. No acceptance relied on that
helper's console success message.

Two planning restrictions were identified: the old via screen rejected ordinary
same-net track/via joints, and a 4 mm routing search window excluded the usable
fault escape. New scoped helpers allow standard same-net track joints while
retaining pad/drill/foreign-copper checks, and expand the bounded window to
10 mm. All final native rules remain unchanged. The numerical planning margin
is 0.001 mm in these trials; that is separate from the unchanged project rules.

Validation: 38 focused tests pass, including unrelated force-width changes,
fault-pad disconnection, local-reference relabelling and existing-via reuse
guards. Native/supplemental hashes are checked before selection. The older
eight-layer branch is explicitly unreconciled with this newer SS/TMR revision;
its raw open count is not a like-for-like comparison. Remaining CT/start-delay/
RAMP placement and routing, ESS inputs, E28 warnings, integrated power/fault/
thermal/fit work and final manufacturing outputs remain open. The full goal
remains active. No supplier message, order or fabrication release was made.

## Reconciled eight-layer CT/SS/TMR alternative — 160 opens, unselected

The preceding turn was verified progress: the selected six-layer SS/TMR cell
reduced opens to 163. This continuation tests whether the CT escape problem
benefits from the newer routing helpers and then reconciles the earlier
eight-layer alternative with that current source. The selected project remains
`nf-softstart-cell-native-02`; the new audited alternative is
`staging/nf-eight-logic-native-01`, with 160 opens, zero native geometry/parity
findings and the same two isolated-reference ERC warnings. No rules were
ignored or relaxed. This is not a manufacturing release or stack acceptance.

The rebased six-layer cell search still could not complete C35/C37 CT paths
and preserve the permit connection. A direct combination of the older
eight-layer CT routes and newer SS/TMR routes produced 38 native findings,
including real shorts and overlapping holes. That combined candidate was
rejected. The source files had no overlapping UUID edits, but their physical
copper conflicted; independent native checks caught the distinction. A fresh
bounded CT search likewise could not use the occupied rear via sites.

Four documented conflicting route sets were removed from the rejected
combination: two local SS/TMR reference branches, the fault-status detour and
the bias-sense detour. These were rerouted against the actual combined geometry.
All timing capacitors, their CT/SS/TMR signal routes and unrelated authored
copper were preserved. A native group comparison then caught the split between
two previously joined U23 reference groups, despite a lower total open count.
An explicit local-reference join restores that connection. The resulting
`nf-eight-combined-native-02` passes full native checks at 161 opens and preserves
every pad connection of the selected six-layer source, including moved bypass
pads and both reference groups. All four local CT cells and both SS/TMR cells
are connected. C36/C38 retain the earlier 0.6 mm rear shifts; the single moved
INTVCC via and its attached endpoint edits remain explicit.

The broader 180-second additive logic search closed only N19_COMPLETE. Native
verification confirms 161→160 opens. Its nine added segments and two vias change
no existing objects. Independent net-count and pad-group comparisons show no
regression. Final new/moved via holes have minimum screened drill-edge-to-SMD
clearance 0.300 mm; the shifted bypass lands were also screened against all
existing vias. Manufacturer mask/stencil/registration and annular-ring
acceptance remain open. Native front/back/ground/new-In4/new-In5/AUX-In6 PDFs
and 600 dpi crops were inspected. Both reference planes remain one filled
polygon. Captured copper-area estimates are recorded for process discussion;
they do not establish the fabricator's residual-copper or balance criteria.

The fault-status reroute now uses a 5.5 mm front escape plus approximately
11.702 mm on an added inner layer, shorter than the selected six-layer
41.161 mm detour. Local reference branches and the bias-sense path still need
return-impedance, coupling and timing/noise analysis. A contiguous plane and
zero native findings do not prove those electrical requirements. The old AUX
plane is mapped to In6; original authored keepouts are preserved and twelve
matching keepouts cover In4/In5. Nominal board thickness and outline are exact.

A specific supplier catalog example is now recorded in
`staging/nf-stack-feasibility-01/catalog-screen.json`: PCBWay entry 15 lists an
eight-layer nominal 1.2 mm construction, with finished thickness 1.24 mm ±10%
and 1 oz copper. Source:
https://www.pcbway.com/multi-layer-laminated-structure.html.
This demonstrates a catalog option only. It is not a quote, supplier selection,
approved material stack or evidence that the board's actual copper balance,
current capacity and installed tolerances are acceptable.

The broader test gives limited routing benefit from two extra layers, so the
160-open candidate remains an alternative. The next action is coordinated pin
escape and placement work, not another unchanged global routing pass. A
source-bound diagnostic on the selected six-layer board finds 219 isolated-pad
open groups. U44 has seven: the finite 4 mm/0.2 mm-grid dogleg screen finds
conventional via exits for five, but none for pins 4/5. The absence of a screened
exit is not proof of impossibility. This identifies a concrete cell to rework
and suggests that coordinated fanouts may help more than additional layers.
The diagnostic is `staging/nf-fanout-demand-01/demand.json`.

Validation: 43 focused tests pass. Mutations reject a lost U23 reference join,
a missing added-layer keepout, unrelated force-copper changes and narrowing of
new reference copper. Source-bound native, geometry, net-set, pad-group, drill
and plot receipts are retained. All rejected and incomplete trials are kept
separate. No supplier message or order was sent. Complete-unit fabrication
preparation remains active, including routing, ESS inputs, parts/process and
integrated power/fault/thermal/fit qualification and final production outputs.

## Six-layer U44 pin escapes — selected at 156 opens

The preceding evaluation turn confirmed status but did not advance the design;
it is classified as no progress. This continuation completes seven additional
logic joins and updates the selected NF source to
`staging/nf-pin-escape-native-04/negative_startup_physical.kicad_pro`.
The independent full native review reports **156 uncapped opens, zero geometry
or schematic-parity findings, and the same two isolated-reference ERC warnings**.
All rules remain enabled. The earlier selected source had 163 opens. No
component, schematic, board outline, layer count, authored zone or keepout moved.
The board remains nominally 1.2 mm and six layers, with 146 front and 119 rear
circuit parts plus two mounting footprints.

The seven joins are U44 pins 1, 4, 5, 8, 9, 11 and 12. N12_COMPLETE,
N12_OUTPUT_UV_GOOD, NOT_NF_FAULT_REQUEST, N19_OUTPUT_QUALIFIED and
N12_OUTPUT_QUALIFIED become fully connected. N19_COMPLETE falls from two opens
to one; E28_NOT_FAULT falls from two to one after joining U44 to R22. Those last
two nets are still unfinished. Native pad-group comparisons preserve every
previous pad connection, including all earlier CT/SS/TMR reference groups.
A lower aggregate open count alone was not used as acceptance.

Explicit pin exits and a conservative 0.1 mm raster search completed the first
four joins, producing verified intermediate boards at 160 and 159 opens.
The raster expands foreign obstacles by an additional half grid diagonal, then
screens every simplified segment against the original captured geometry. This
is a planning method, not a relaxation of the native clearance rules. The
original short global grid searches had spent their bounded searches at pin
exits before reaching useful inner-layer corridors.

U44 pins 4/5 required a local ground-escape rework. Exactly three original AGND
segments and one AGND via were removed. U44.7 now reaches a new conventional
0.60/0.30 mm ground via at (143.0, 7.1) through a 0.2 mm front trace. C83.2 now
reaches the existing R22 ground via at (141.4875, 3.9) through a 0.2 mm rear
trace. The first proposed via position failed the host clearance screen and was
not written. The final relocation passes native checks and preserves all prior
ground-pad relationships. Its effect on local decoupling/return impedance still
needs electrical review. A proposed two-via short join failed the planner's
via-spacing assertion; a single shared via completes the U44/R22 connection
without changing the clearance rule.

The final two signals were limited at U48, not at U44. A finite 4 mm dogleg
probe and its first local-grid fallback found no target exits. A finer local
connected-region diagnostic found legal via sites missed by that radius/grid.
A 0.05 mm local route search, retaining exact copper checks, then completed both
exits. It selected the U48.2 via at (80.9, 34.25) and U48.5 via at (81.55, 27.1).
No U48 component or existing copper was moved. The intermediate zero-route
trial remains separate; it was never selected.

Relative to the previous selected source, the final board adds 90 segments and
12 vias and removes only the three documented ground segments and one ground
via. All other original objects are exact, apart from native zone refill data.
New signal tracks are 0.16 mm; the two new ground tracks are 0.2 mm. New vias are
0.60/0.30 mm with minimum screened drill-edge-to-SMD-copper gap 0.225 mm. The
native front/back/ground/In2/In3 plots and 600 dpi local U44/U48 crops were
inspected. Both reserved planes retain one filled polygon. Neither that fact
nor clean DRC qualifies PDN, mask/stencil/registration or installed operation.

The seven new planar route lengths are approximately 37.761, 2.610, 104.917,
85.618, 39.776, 94.190 and 133.988 mm for U44 pins 1, 4, 5, 8, 9, 11 and 12,
respectively. Several are long. Return paths, coupling, edge behavior and
fault/qualification timing remain explicit holds; this is routing completion
progress, not an electrical-performance claim.

Validation: 52 focused boundary/evidence tests plus two fine-grid corridor tests
pass (54 total). The tests reject unrelated force-width changes, loss of a prior
reference connection, a false claim of a U44 join, routing on a reserved plane,
foreign copper barriers and insufficient clearance. Final source-bound receipts
include `pin-escape-audit.json`, `added-via-drill-review.json`, `layout-review.json`
and `handoff.json`. The selected inventory and readiness report are refreshed.
The historical eight-layer alternative has not adopted these new changes and
is explicitly marked as no longer a like-for-like routing comparison.

The refreshed `remaining-routing-demand.json` identifies 208 isolated-pad groups
(previously 219), including six each at U15 and U38. U44 has no isolated-pad
groups left, although some nets attached to it still have remote opens. This
provides the next concrete routing task. The complete-unit goal remains active:
156 NF opens, the ESS converter layout/documentation, E28 warnings, parts and
process acceptance, integrated electrical/thermal/mechanical/harness work and
inspected manufacturing/first-article outputs are still unfinished. No supplier
message, order or fabrication release was made.

## Multilayer logic joins — selected at 149 opens; paired placement trial next

The preceding turn made verified progress from 163 to 156 opens. This turn
continues from that exact selected source and adopts
`staging/nf-u37-multilayer-native-02/negative_startup_physical.kicad_pro` at
**149 uncapped opens, zero native geometry/parity findings and the same two
isolated-reference ERC warnings**. All checks remain enabled. Every original
component, track, via and authored zone from the 156-open source is retained
exactly. Independent native pad-group comparisons preserve every previous pad
connection, including the earlier local timing and reference cells.

A first single-layer U38 trial found only a long N19_READY join. That host-only
candidate was not adopted. Three other nets had legal endpoint escapes but did
not complete on one signal layer. A new bounded multilayer raster planner uses
F/In2/In3/B signal layers, exact final segment/hole checks and conventional
0.60/0.30 mm vias. Reserved In1 AGND and In4 AUX2V6 remain planes. It screens
hole placement against every captured copper layer, existing drills and via
keepouts, rejects conflicting new vias, and retains the original native rules.
Additional tests exercise a required two-via layer change, an all-layer barrier
and a via keepout that makes that change impossible.

The independently reviewed checkpoints were 154 opens after U38 and 152 after
U41. U37 then added three connections. Its first native review found one new
N19_SAFE via at (30.8, 21.6) connected only on F.Cu. The via was redundant in
the resulting route; the specific removal script verifies it was newly added,
checks the attached layer, and preserves every track. The corrected candidate
was reloaded and fully checked at 149 opens with zero geometry findings. The
warning was removed through a geometry correction, not suppression.

Seven nets improve by one connection each:

- N12_COMPLETE_CLK, N19_CLAMPS_RELEASE_HCS, N19_PERMIT_CLR_N and N19_SAFE become
  fully connected.
- N12_READY, N19_PERMIT and N19_PERMIT_D each retain one remote open.

The final delta is 113 added 0.16 mm segments and 22 added conventional vias;
no object from the prior selected board was removed or changed. The minimum
screened new drill-edge-to-SMD-copper gap is 0.200 mm. Native front/back/ground/
In2/In3 overviews and 600 dpi local U38/U41/U37 crops were inspected. Both
reserved planes still have one filled polygon, which does not establish their
impedance or complete ground connectivity. New planar route lengths range
from about 43.964 to 79.777 mm; the N12_COMPLETE_CLK path is about 78.462 mm.
Return paths, coupling, edge/fault timing, via process, mask and stencil remain
unqualified. No component height, rear placement, stack or mechanical approval
is inferred from this routing progress.

A new placement study changes the next action. U38 and U41 are the same
SN74HCS08PWR part and footprint; their exact local pad shapes match after
excluding net/UUID metadata. Swapping their physical sites reduces the sum of
Euclidean minimum-spanning-tree lengths for affected non-power nets from about
1936.45 to 1513.07 mm, a 423.38 mm reduction. This is an obstacle-free connection
metric, not a predicted routed length, signal-integrity result or manufacturing
qualification. It does not account for reworking existing copper.

The source-bound study is `staging/nf-logic-swap-study-01/study.json`.
`swap-rework-inventory.json` identifies 22 physical-site pin net changes and 25
initial old-net copper cut candidates within the affected pad clearances.
Ground pin 7, GLOBAL_VALID pin 13 and AUX2V6 pin 14 stay on the same nets at both
physical sites. No CAD pose was changed by the study. Vacated-branch pruning,
complete affected-pin routing, local bypass assignment, native/pad-group checks
and return/noise review still have to be performed on a separate swap candidate.
The selected 149-open board is the checkpoint to preserve. The next step is
that controlled paired placement trial, rather than another unchanged long-route
pass that may preserve avoidable routing distance.

Validation: 63 focused routing, geometry, connectivity and source-evidence tests
pass. The generic additive audit excludes power, analog sense/reference and
timing-capacitor nets, rejects original-copper edits and reserved-plane tracks,
and rejects a per-net regression even when total opens improve. Final native,
logic-group, drill, plot and handoff receipts are bound to the selected files.
The inventory has been refreshed. There are 196 isolated-pad groups, down from
208; this count is distinct from the 149 missing connections. The historical
160-open eight-layer branch has not adopted these changes and remains unselected.

Complete-unit fabrication preparation remains active: NF routing and electrical
review, ESS converter inputs/layout, E28 warnings, exact parts and processes,
integrated power/fault/thermal/mechanical/harness verification and the inspected
manufacturing/first-article package remain unfinished. No supplier message,
order or fabrication release was made.

## Latest-design evaluation — selected baseline retained

Read-only verification found all 110 hashes in current-readiness.json still
matching their recorded files. The inventory remains 15 functional roles,
14 development layouts and 12 layouts with zero native DRC/opens/ERC findings.
Those counts do not establish electrical performance or whole-unit readiness.

The newer U38/U41 placement trials remain unselected. The first group-routing
trial has 146 opens but splits eight previously connected pad groups and
regresses three net open counts. The escape-reserved trial was freshly checked
in the pinned isolated Linux KiCad environment as
`staging/nf-logic-swap-reserved-groups-native-01`: 144 opens, eight dangling-via
warnings, zero parity findings and two isolated-reference ERC warnings, with
all native checks enabled. Its source-bound `evaluation-connectivity.json`
confirms six split prior pad groups and regressions on N12_STAGE_ENABLED
(0 to 1 open) and N12_READY (1 to 2). All unaffected net open counts and the
documented geometry-change boundary are preserved. The lower total is not
grounds for replacing the selected 149-open source.

The complete-unit evaluation also retains the missing codec/shared-core PCB,
E28's 49 warnings, process and exact-part holds, unresolved audio interfaces,
power/fault/return analysis, and incomplete manufacturing/bring-up package.
UA01 captures earlier PCB sources and explicitly excludes later NF/FPC/E28
changes; its service-state checks do not qualify the latest assembly. WU01's
passive thermal screen and AP04's adverse forced-air cases remain failures
within their stated model assumptions, not measured temperatures or a current
complete-unit thermal qualification. No design selection or release changed.

## Restored paired placement — selected at 138 opens

The preceding evaluation was progress: it freshly checked the 144-open trial
and exposed six split prior pad groups, which determined the restoration work.
This turn selects `staging/nf-logic-swap-clean-native-01` at **138 uncapped
opens, zero native layout/parity findings and the same two isolated-reference
ERC warnings**. All native checks remain enabled. The independent final audit
preserves every pad connection from the previously selected 149-open board,
finds no per-net open-count regression, and confirms the exact documented
geometry boundary. The cleanup also preserves every pre-cleanup pad connection.

U38/U41 exchange their identical-package physical sites. All other component
poses, pin nets, values, authored zones and board geometry remain unchanged.
The controlled rework removes 164 original segments and 24 original vias and
adds 389 segments and 62 conventional 0.60/0.30 mm vias. Besides the initial
swap-net branch cuts, six explicit N12_WD_ARMED copper objects are reworked to
free the U39.4 stage-enable escape. The relocated U39.5 watchdog connection
rejoins both original inner-layer branches. Ten nonfunctional newly added
objects are removed before the final check; no native warning is suppressed.

The first exact-edge search completed two additional connections. Weighted,
bounded searches then restored GLOBAL_VALID, N12_READY and NF_NO_FAULT. A
reachability check distinguished the fault-net search limit from a disconnected
raster region. U39.4 was physically obstructed by the existing watchdog via
and its branches; expanding the search radius alone did not solve it. The
explicit watchdog rework provided a legal stage-enable escape, allowing the
last lost connection to be restored. Native checkpoints were 142, 140, 139
and 138 opens. All unselected intermediate trials remain available.

Compared with the selected 149-open source, NF_NO_FAULT, N12_ARM_CONDITIONED,
N12_PERMIT, N12_PERMIT_CLR_N, N19_COMPLETE_CLK and N19_COMPLETE_CLR_N each close
one remaining open. N19_READY closes two. GLOBAL_VALID, N19_ARM_CONDITIONED and
N12_SAFE each improve by one but retain an open. This is eleven fewer missing
connections. There are 185 isolated-pad groups, down from 196; these are a
separate measure from the missing-connection count.

The original obstacle-free site-swap study is not treated as a routed-length
prediction. Across the affected nets, actual total track length rises from
1266.70 to 1877.89 mm while additional connections are completed. N12_COMPLETE_CLK,
N19_PERMIT and N19_CLAMPS_RELEASE_HCS become shorter, but the restored N12_READY
route is approximately 154.55 mm and the watchdog escape takes a detour. Return
paths, coupling, clock/fault timing and PDN behavior remain unqualified. No
aggregate routing-length reduction or electrical-performance approval is claimed.

Native front/back/ground/In2/In3 overviews were inspected at 300 dpi, with
U38 and U41/U39 front/back details inspected at 600 dpi. Front/rear circuit-part
counts remain 146/119. Both reserved planes have one filled polygon; that does
not establish their impedance or complete ground connectivity. All 62 new or
replaced via drills have a screened drill-edge-to-SMD-copper gap of at least
0.200 mm. Mask, stencil, registration, via process, body/tail/wire receiving and
whole-unit fit remain open.

Validation: all 129 focused NF tooling tests pass. New tests exercise exact
clearance corridors, layer/via barriers, the explicit watchdog copper exception,
rejection of unlisted removals and unrelated power changes, and preservation of
watchdog pad connections. Final source-bound receipts include logic-swap-audit,
added-via-drill-review, layout-review, focused-tests and handoff JSON files.
The scope, readiness inventory and remaining-routing-demand report are updated.

The full fabrication goal remains active. The selected NF still has 138 opens;
its unfinished CT cells and other timing/logic connections remain concrete
routing work. E28 warnings, the ESS package/interface inputs and converter PCB,
exact parts/process acceptance, coherent installed power/fault/thermal/harness
and mechanical review, inspected manufacturing outputs and first-article
instructions remain unfinished. No order, supplier message or fabrication
release was made.


## DC01 / AP01 — combine digital controls and fix physical layout allocations

Created a 138-part / 709-terminal combined digital schematic from the selected
processor, control-input and LED-driver circuits. Five internal headers are
removed. Fourteen explicit global nets connect the three sheets; all retained
values, footprints and physical pin nets independently replay against the
original exports. E18's external-codec reset profile maps CONTROL_RESET_N to
Seed D0 / CODEC_RUN. The LED translator, series resistors, supply supervisors
and blanking circuits are retained. Native Linux KiCad 10.0.7 ERC is zero with
all categories enabled. Six fault-injection/source-replay tests pass.

Placed the circuit in `staging/digital-core-placement-03`, a notched
114 x 60 x 1.6 mm right-side allocation at [184,44,7]. There are 138 electrical
parts and five proposed mount holes. Native geometry, schematic parity and ERC
are all zero, with no ignored categories. The board remains placed-only at
466 open connections; it has no copper routes, vias or planes. Independent
placement review checks the exact 6630 mm2 profile, all source pin nets and
values, body/edge/mount allocations and opposite-face THT solder reserves.

The first trial's 199 global-net spelling parity warnings and five default
ignored categories remain documented as rejected evidence. Trial 02 corrected
those but overlapped the retained inlet J2 mate reserve. Trial 03 enlarges the
profile relief and moves J3005 and its nearby mount. A bare-PCB clearance was
not used to infer mating clearance. Neither earlier trial is selected.

AP01 (`staging/assembly-layout-01`) fixes the direction for the next layout:
six audio roles in a 150 x 63 mm left-side allocation, combined digital on the
right, current 80 x 70 mm rail monitor above the audio area, and the TC02 touch
module in the existing front bay. Together with P03, inlet, E28, NF and fan
protection these are eight functional PCB allocations; panel/emitter/sensor
boards and Trill are additional. Current native Edge.Cuts are captured rather
than promoting old sealed power/negative-protection assembly sources. The
actual E28 extended-tail polygon clears the two nominal TC02 support posts;
its 156 x 60 bounding rectangle would give a misleading interference result.

The declared digital and monitor component-height intervals clear the retained
pot/button/solder/holder, rear/inlet and release-mechanism box context. They
remain unapproved receiving requirements, not measured or guaranteed part
limits. Full current P03/E28/NF/FPC components, mounting shims, harness and
service paths are not covered by this partial screen. The full native assembly
must be rebuilt with new digital bosses and monitor supports; two monitor
supports require planned audio-board pierce holes and copper keepouts.

The source inventory now includes the combined digital candidate and AP01.
The audio main still needs six-role schematic integration and actual placement;
AC03 only combines ADC/codec/receiver, and its harness still names the older
processor references. Digital routing, exact parts/process, integrated power/
return/fault/thermal and complete mechanical verification, ESS package/interface
inputs and the inspected manufacturing/first-article package remain unfinished.
No Mac CAD was launched. No supplier message, upload, order or release was made.

## E28 — native warning closure and current process map

Selected `staging/e28-branch-cleanup-native-12`: zero native DRC, uncapped opens,
schematic parity and ERC findings, with every rule category enabled. The staged
removal-only sequence deletes 411 tracks and 32 vias from the prior 49-warning
source. Each removal retains one local connected support component after drill
subtraction and layer/zone-island separation; every pass receives native refill
and connectivity checks. Independent final audit verifies exact component poses,
values, pin nets, all retained copper, authored zones, rules and stack. These are
connectivity proofs, not conductance/current-capacity or thermal qualification.
Twenty-nine focused unittest tests pass. All eight native before/after layer
comparisons were inspected at 300 dpi and recorded with source hashes.

The current retained-via map identifies 311 of 1,385 vias whose drills intersect
SMD copper; 310 intersect paste-target lands. All 311 retain native filling/capping
fields set to no. Historical E28 passive and SMT-terminal scripts already require
a candidate filled/capped process, so the manufacturing hold is a map and metadata/
instruction reconciliation issue, not merely the previously listed single small
via. Four more vias fall within the 0.1 mm proximity screen. These are conservative
geometry screening results, not factory acceptance or stencil-aperture checks.
The map includes ordinary passive, IC and terminal lands needing appropriate
individual process treatment. No native manufacturing property was silently changed.

Captured the actual eight-layer 1.62 mm mixed-copper stack: six 80 um copper layers,
two 35 um layers, unaccepted FR4 material values and candidate finish. The sole
0.2 mm drill and all retained drill sizes are unchanged. Supplier process, power/
return/fault/thermal and whole-unit fit remain open. Manufacturing inputs now link
the current drill/land CSV and actual stack capture.

Scope selects the clean E28 development candidate. The AP01 allocation has a new
source-bound receipt with exactly unchanged allocation geometry and receiving
limits; the original AP01 receipt is preserved. This rebind is not a renewed full
native assembly pass. The current source inventory preserves the newer AC04 audio
and DC01 digital work: 329-part/971-terminal six-role audio schematic with no PCB,
466 unrouted digital connections, and 138 NF missing connections. ESS package/
interface inputs, exact parts/process, coherent mechanical/harness/power/thermal
review and inspected manufacturing/first-article outputs remain unfinished.
The full fabrication goal remains active. No supplier message, order or release.

## DC03 / AP03 — digital supply distribution and thermal connections

The user requested continuation after the status review. Selected DC03 is now
`staging/digital-distribution-native-02`, with AGND on In1, 5V_DIG on In2,
outer-layer 3.3 V branches and a 1 mm Seed VIN feed. Native pad-to-source
witnesses verify all 201 pads on five supply/ground nets. Uncapped opens fall
427 -> 255. Geometry, schematic parity and ERC findings remain zero with all
categories enabled; the 39 previous local connections remain connected.

The independent DC03 audit verifies 186 added tracks, 128 added vias and two
added zones against DC02. All original components, tracks, vias, board setup,
outline, mounting, values and pin nets remain exact. The current total is
245 tracks and 136 vias. Each native filled plane is one valid polygon with
holes. The copied Unfracture representation changes the reported area by about
0.000058 mm²; the review records both values and uses an explicit perimeter times
two integer-nanometre grid steps as its contour-area bound. No PCB geometry was
changed to accommodate that representation difference.

The four LED drivers now have 9, 6, 11 and 7 native-connected thermal vias.
Twelve use 1 mm copper branches beyond EP copper; 21 occupy mask-covered EP
copper outside actual solder openings. Those 21 request front/back tenting and
have at least 0.98 mm hole-edge clearance to their package's mask/paste openings.
Every other SMD copper land retains at least 0.15 mm hole-edge clearance.
The remaining 115 vias are wholly outside SMD copper. The location-specific
map makes this distinction explicit; filling/capping and process acceptance
are not inferred. Thermal performance remains unqualified.

The Seed feed has 31.615 mm of 1 mm copper after R1001, plus 1.2 mm before it.
A conditional copper/barrel model with R1001's initial high tolerance gives
0.493–0.508 V drop at the retained 1 A allocation under two stated construction/
temperature scenarios. R1001 alone contributes 0.4747 W. This excludes plane,
return, harness and source losses, resistor TCR and self-heating, so installed
VIN/current capacity is still open. The 0.764 A LED allocation is unchanged.

AP03 rebinds the current PCB and confirms unchanged bodies against the same
conditional receiving limits; no conditional floor/context collisions are
found. Four final copper-layer plots at 300 dpi and the AP03 arrangement were
visually inspected. Fab annotations still need final assembly-drawing cleanup.
The source inventory passes 180 matching hashes with no native/additional
evidence errors; 13 focused digital tests pass. Earlier candidate receipts and
source boards are preserved. No supplier message, upload, order or release.

Remaining work includes 255 digital signal connections; high-speed, quiet
analog and reference returns; installed current/voltage/thermal/fault analysis;
NF's 138 opens; the audio PCB and missing ESS inputs; E28/P03 process holds;
complete assembly/harness receiving; and inspected manufacturing outputs.

AC04's interface audit is also rebound to the newly selected E28 evidence in a
separate handoff receipt. Replay verifies identical audio circuit, powered logic,
DC/settling screens and 42-conductor connection schedule; only E28 evidence paths
and native-export hashes change. Original AC04 and AP01 receipts are retained.

Final inventory validation passes: 15 roles, no missing source files, no native
or additional-evidence errors, and 126 matching inventory source hashes. A further
118 direct cleanup/rebind receipt inputs and all plotted output hashes match.
Thirteen of the fourteen role-level development layouts now have zero native
findings/opens; this does not qualify the combined digital/audio physical boards
or supersede their unfinished routing/layout. Fabrication release remains false.


## AC04 — six-section audio schematic and captured interface receipt

Completed the six-section main-audio integration in
`staging/audio-main-integration-04b`: input range, ADC driver, ESS codec, DAC
receiver, output stage and sequenced bypass. There are 329 electrical parts /
971 physical terminals. Fifteen old headers are removed and two shared power
headers added. Native isolated Linux KiCad 10.0.7 exports all seven pages with
zero ERC findings and no ignored categories. The codec land remains unassigned
and there is no main-audio PCB layout.

The protected P19/N19 rails feed the master output stage; P12/N12 remain with
the send/return amp and other analog stages. Coil/bypass 5V_DIG remains separate
from analog V5_REG. J701's six-pin order matches E28 J3; the AC03 four-way power
harness is incompatible. All retained source values, lands and physical pin
nets replay independently. Exact stereo, gain-coil, ADC force/sense and raw-DAC
joins are checked. Coupled powered Boolean evaluation covers 16,384 startup /
bypass cases, including manual-dry input retention, gain-change invalidation
and stale timer states. Dynamic startup/reset/relay/partial-power behavior and
rapid-rearm CT discharge remain unqualified.

The 42-conductor / 11-bundle audio-leg proposal uses the combined digital
J1005/J1006/J1003/J1007 interfaces. Three duplicate/status contacts are unwired.
Rear/manual contacts remain logical; actual wire/crimp/strain relief, digital
force distribution, installed PDN/SI and the complete-unit harness are open.
The captured Molex J701 signal-hole grid is 3 mm, drill 1.02 mm; JST J702 is
2.5 mm pitch with native 1.0 mm drills. Manufacturer orientation, full mating
receiving and fabrication-process acceptance are not inferred from those lands.

E28 selection changed to its clean native-12 development source during this
work. `peer-selection.json` and `integration-handoff-03.json` freeze AC04's
captured peer evidence. The current source inventory separately checks all used
peer headers against their selected pin/value/land contracts, so unrelated
copper revisions do not silently rewrite the schematic receipt. Prior audio
and E28 rebinding receipts are preserved. The historical AC03 test now replays
its captured peer selections; its wire-fault tests still exercise current peers.

A digital signal router trial was rejected before adoption because it placed
signal tracks on reserved inner layers. The concurrent outer-only routing and
power-cell placement work remains separate and has not replaced the selected
placed-only DC01 source in this milestone. No failed inner-layer result is
presented as a routing pass. A temporary Linux CAD layer probe did not run when
automatic approval review timed out. Mac CAD remained disabled. No supplier
message, upload, order or fabrication release was made.

## DC02 / AP02 — local digital cells and current-pose receiving

Previous goal turn made progress: E28 warnings were closed, the via/process map
was captured, and current source selection was updated. This turn advances the
combined digital physical board rather than treating the separate development
boards' clean native checks as a finished integrated PCB.

The prior DC01 placement put several bypass capacitors 10–46 mm from their owner
pins. The three MCP23017s occupied the space between Seed THT solder rows, leaving
no nearby same-face decoupler sites under the retained courtyard/solder limits.
A bounded joint placement search now moves those three ICs and 39 passives while
retaining all connector/module positions, five mounting holes, outline, circuit
values, lands and pin nets. The ten pot-input filter capacitors move from
9.6–28.4 mm straight-line separation to approximately 2.29 mm local traces.
The actual TI TLC5947 and SN74LVC8T245 source PDFs in the repository support local
bypass/current-reference placement; the 3.5/7 mm search limits are project
allocations, not manufacturer-qualified maxima.

Selected `staging/digital-local-cell-native-01`: 138 electrical parts, 39 native-
verified local pad pairs, 59 segments and eight conventional 0.60/0.30 mm vias.
Uncapped opens fall 466 -> 427. DRC geometry, schematic parity and ERC are all
zero with every native category enabled. Both inner layers remain without signal
tracks. Every via drill clears actual front/back SMD copper; minimum screened
hole-edge separation is 0.175 mm. Mask, registration, plating, stencil, complete
supply/return paths and thermal performance are not qualified by that screen.

An independent inverse-transform audit checks all 42 declared component changes
against the saved native baseline. Only native annotation half-turns are
normalized; electrical/mechanical geometry, values, pin nets and unlisted poses
remain exact. A separate additive audit verifies 59 segments/eight vias and no
other geometry changes. All four hierarchical sheets are captured and hashed.
The initial placed-only file had no persistent pad UUIDs; its existing DRC item
IDs could not support capture. Native checkpoint 05 persists those IDs. Checkpoint
04, which exposed the generic flat-sheet staging limitation, is rejected and
retained. The complete-hierarchy driver verifies the unchanged 138-part circuit.

The earlier digital signal-only router trial 02 violated reserved inner layers
and remains rejected. Trial 03 uses explicit CLI and DSN outer-layer constraints;
its imported copper is confined to the outer faces, but it retains the superseded
remote-cap placement and is not adopted into DC02. These routing artifacts are
not evidence that DC02's remaining signals are complete.

AP02 rechecks actual DC02 component boxes against the existing conditional
controls/rear/release context. The declared 0.3 mm same-face courtyard, 0.5 mm
THT solder reserve, outline and mount clearances pass. No conditional context or
floor collision is found. This is not a complete native assembly/service-path
qualification. Original AP01 and DC01 receipts remain preserved. The new front/
back native copper/Fab plots at 300 dpi and AP02 arrangement were visually
reviewed. Final assembly annotations still need cleanup and output inspection.

Thirteen focused tests pass, including rejection of pad rotation/size/net,
component pose/face and annotation-position changes hidden by text normalization.
The source inventory passes with 141 matching hashes and no native/additional
errors. Selected digital revision is DC02; selected arrangement is AP02.

Remaining digital work includes board-wide power/ground, exposed-pad thermal and
LED return paths, 427 connections and signal/return review. R3002's actual IREF
route is 8.864 mm and needs return/noise review; placement distance is not routed
length. The full unit also retains NF 138 opens, missing audio/codec PCB and ESS
inputs, E28/P03 process holds, exact parts/receiving, complete mechanical/harness/
power/fault/thermal review and inspected manufacturing/first-article outputs.
The full fabrication goal remains active. No supplier message, order or release.


## AC04 — partial physical main-audio placement

Created `staging/audio-main-placement-02`: 328 known electrical footprints plus
six proposed mounts in the AP01 150 x 63 x 1.6 mm allocation at [30,42,6.5].
There are 199 top-side and 129 bottom-side electrical footprints; four are bare
test pads. U201 remains unplaced behind an explicit 16 x 16 mm all-layer data-
hold reserve. No generic codec footprint, exposed-pad pattern or fictitious
codec pad coordinates are introduced. Codec-local passives require renewal
around the eventual manufacturer-approved land.

The planner places complete local networks jointly. All 99 feedback, local
bypass, flying-cap, clock-series and servo groups meet the unchanged declared
3.0/3.5/4.0/5.0/6.0 mm construction bounds at 131 checked endpoints, on the same
face as their owners. The largest local search used 22 candidate placements.
The servo-integrator films remain beside the common-mode control amplifier;
the eight tall output films clear the upper monitor projection. Body, floor,
mount, opposite-face THT solder and declared upper-monitor/tail screens pass.
The minimum declared vertical gaps are 0.84 mm to the upper PCB and 7.74 mm to
its overlapping tail envelopes. These remain conditional on unapproved body,
seat and solder bounds, not a complete current assembly qualification.

The first partial native review found 22 intra-VSSOP clearance errors, 199 field
mismatches, four test-pad BOM attribute mismatches and the missing codec. That
trial remains preserved. The successor changes only instance metadata and
explicit project rules: all 328 placements, lands, nets, outline and keepout
are independently verified exact. Instance Datasheet/MPN/custom fields now
match the schematic; invented value-as-MPN fallbacks are removed. The four bare
test pads match the existing in-BOM attributes and need explicit non-fitted
classification in the final assembly BOM.

The retained ADC development source already uses 0.15 mm clearance. The new
board enforces 0.20 mm general clearance and track width and scopes 0.15 mm only
to pad pairs within the same U101/U102/U105/U106 stock VSSOP footprint. No ignored
severity category is used. The native driver has a separate before/after rule-
input binding. Factory acceptance of the actual copper/mask/registration,
stack and assembly process remains open.

Pinned isolated Linux KiCad 10.0.7 reports zero geometry findings, zero ERC,
one explicit missing-U201 parity finding and 724 uncapped opens, with all rule
categories enabled. The PCB has no routes, vias or planes. Seven focused fault-
injection checks pass: source replay, invented-codec rejection, tall-film upper-
board interference, remote feedback, opposite-face solder collision, incomplete
reserve layers and an empty local-cell receipt. Actual top/bottom land/courtyard
PNGs were visually inspected and linked in the repository README and inventory.

Scope retains the AC04 schematic receipt and separately selects this partial
layout candidate; it does not mark layout, physical partition or fabrication
complete. Main-board routing, ESS package/interface inputs and physical stars,
actual parts, complete connector mates/wire paths, supports/floor regeneration,
PDN/return/noise/stability/thermal and inspected manufacturing/first-article
outputs remain unfinished. No Mac CAD launch, supplier message, upload, order
or fabrication release was made.

## 2026-11-02 — consolidate the current development checkpoint

Replayed the partial AC04 placement handoff and the current 15-role source
inventory successfully; no selected source files are missing. The tooling suite
ran 816 tests successfully with three skips. All 23 CAD integration tests passed.
Focused Ruff checks passed for the four audio-placement construction/audit/render
modules and their placement tests. The broader fabrication/tooling style check
is not clean: it reports formatting, unused imports/locals and wildcard-import
diagnostics in existing and historical scripts. The staged whitespace check also
reports preserved source/artifact whitespace. Sealed historical bytes were not
rewritten to remove those diagnostics.

This checkpoint preserves development candidates, rejected trials and their
source-bound evidence. It does not close PCB routing, the missing ESS package
inputs, installed receiving, electrical/thermal qualification or fabrication
release. The README continues to state the 724 open audio connections and the
unplaced codec. No supplier request, order or native Mac CAD launch was made.


## AC04 — native-checked local main-audio copper

The first local route pass added 234 tracks and closed 129 pad pairs, reducing
724 native opens to 595. Its exact native pad/keepout polygons and complete-rule
review remain preserved. Review of bypass return targets found that C612's
nearest AGND terminal was grounded logic input U608.13, rather than power ground
U608.7. The selected successor removes that trace, filters requested ground
endpoints by the actual native schematic power-input type, and excludes the
OPA1612 grounded input-reference terminals from bypass-ground requests.

The direct same-face branch search did not find acceptable paths for the ten
remaining signal/supply endpoints within the existing construction budgets.
The successor closes eight using sixteen conventional 0.60/0.30 mm via escapes,
while preserving every original component pose, land, pin net, profile, mount
and codec reserve. The eight FDA compensation and sixteen I/V compensation
capacitor terminal routes remain exactly their original direct same-face tracks.
R319.1 to U303.6 and C127.1 to U102.3 still need local rework; thirteen requested
local ground returns remain open. No length or clearance budget was relaxed.
Per-layer copper lengths exclude separately recorded nominal via-barrel length;
these are construction metrics, not analog performance qualification.

Selected `audio-main-local-routing-02` has 257 tracks, sixteen vias and 136
native-confirmed local pairs (129 of 131 declared signal/supply endpoints plus
seven actual power-ground pairs). Isolated Linux KiCad 10.0.7 reports zero native
geometry findings, zero ERC findings, one explicit missing ESS-footprint parity
finding and 588 uncapped open connections. Every DRC/ERC category remains enabled.
The independent replay checks actual tracks/layers/endpoints/widths, native
connectivity witnesses, unchanged receiving geometry and the actual minimum
screened drill-edge-to-SMD-copper gap of 0.170 mm, including same-net lands on
both faces. No via hole intersects an SMD solder land. Stack, mask/tenting,
stencil and assembly acceptance remain open.

Seven new fault-injection tests pass; the full tooling run completes 823 tests
with three skips, and all 23 CAD integration tests pass. The four new routing,
audit and render modules and the new tests pass focused Ruff checks. Actual
top/bottom copper PNGs were visually inspected. The first audit receipt and its
source are preserved before correcting tuple/list JSON replay normalization;
canonical handoff replay now passes. Source inventory selects this partial
routing successor and still withholds fabrication release. The two staged
folders total approximately 7.8 MB. No native Mac CAD application, bulk audio
batch, supplier request or order was launched.

The two local endpoints and thirteen returns, all other board routing, ESS
package/interface data and physical ADC stars, complete parts/mating/harness/
support/case receiving, PDN/noise/stability/thermal qualification, and inspected
manufacturing/first-article outputs remain unfinished.


## 2026-11-02 — DC04 partial signals and four/six-layer comparison

Continued the combined digital routing from DC03's 255 open connections.
Priority audio/SD routes, protected-copper router trials and polygon-screened
routes produced a four-layer checkpoint with 143 opens. Native-reported unused
vias and leaf branches were pruned in successive preserved variants. Selected
`digital-four-clean-native-03` now has zero native geometry, schematic-parity or
ERC findings with all categories enabled. It contains 1,252 tracks and 243 vias;
all DC03 footprints, original tracks/vias, authored planes and root geometry are
exact. All 201 power/ground pads, 39 local connections and 33 thermal connections
remain native-connected. Both refilled planes retain one copper component;
zero-area exported ring slits normalize without changing area materially.

The independent DC04 handoff screens all 107 new via drills against actual SMD
copper on both faces, including same-net lands: minimum gap 0.16998 mm. The 21
older mask-covered heat-spreader vias retain their separate process hold. No
new via hole overlaps an SMD land. Source-bound native witnesses, drill rows,
open-net groups and per-net copper lengths are saved with the checkpoint.

All SD and audio-data nets are connected. SD carrier copper totals nevertheless
range from 47.571 to 84.274 mm, with 0–4 vias and unequal data via counts. This is
an explicit timing/reference/impedance rework item, not a qualified interface.
The totals exclude Seed/module/socket, component, barrel and off-board paths.
The review cites ST AN4938 Rev 7 section 9.4.1. Seventy-six LED-output nets,
thirteen control nets and twenty-seven other nets remain open (116 nets,
143 connection gaps). Reserve local escapes and revisit SD placement before
completing global routing; bounded searches do not prove unroutability.

A separate six-layer trial adds an In3 signal layer and an In4 ground plane.
After another bounded pass and native stub cleanup, `digital-six-clean-native-01`
has 113 opens and zero geometry/parity/ERC findings. Its independent comparison
checks original DC03 copper/poses, the declared layer/zone additions, preserved
power/local/thermal connections and new drill clearances. It still has 72 open
LED-output and thirteen open control nets. The trial is unselected; actual
stack, impedance, process, cost and return-path acceptance remain open.

Scope now selects DC04 and AP04. AP04 rechecks unchanged digital poses against
conditional component/floor/context limits; the full assembly remains unfinished.
The digital handoff, six-layer comparison and AP04 receipt replay exactly. All
thirteen focused digital integration/annotation tests pass, and the complete
15-role source audit passes with no missing sources. Native front/back/ground/
power plots and the AP04 arrangement were visually inspected. Concurrent audio
and runtime-tool work was preserved; selected audio remains local-routing-02.

The saved DC04 README evaluates the unit: audio still has 588 opens and a missing
ESS footprint, NF has 138 opens and two explicit ERC warnings, E28/P03 retain
location-specific drill/process holds, and full PDN/noise/stability/thermal,
mechanical/harness receiving and fabrication/first-article outputs remain open.
No native Mac CAD, supplier request, order, commit or fabrication release occurred.


## AC04 — complete local endpoints and placed-ground reference

The six-section audio candidate now closes all 131 declared local signal/supply
endpoints. D102 shifts 0.5 mm, C118 moves provisionally nearer the codec reserve,
and R324 is reoriented to clear conventional escapes; no amplifier or direct
compensation-capacitor copper moves. Fresh native pads independently match the
planning transform. Native pad UUIDs are generated anew on load, so terminal
identity is checked by reference, number and physical position. The additional
D102.2 V5 clamp contact is independently confirmed. This intermediate has 585
opens and zero native geometry/ERC findings, with the missing codec retained.

A native-filled In1 AGND reference protects twelve sensitive-node openings on
both inner layers and all six proposed mounting-hardware copper exclusions.
The initial legacy-format input omitted the explicit zone net_name; native
capture exposed the unassigned plane before escapes were attempted. Corrected
net assignment and its source snapshots are retained. The first routed trial
closed 197/200 grounds but native checks caught two off-centre track/via joins
at a new C227 ground via. That trial remains unselected with its findings.

The corrected successor removes that via and reuses a centred ground via,
completes C104's return, rotates C310 in its unchanged courtyard and completes
its return, and adds the supervisor ground escape. The latter is 4.75 mm within
the original 5.6 mm local-ground request allowance; all normal ground escapes
retain 3.5 mm, and all analog local length/clearance budgets remain unchanged.
Native checks now confirm all 200 placed AGND terminals connected to J701.2,
all 131 local signal/supply endpoints and all twenty declared local ground
returns. Opens fall from the earlier 588 to 393. The candidate has 448 tracks
and 199 conventional 0.60/0.30 mm vias, including 179 added ground vias.

All native geometry/ERC categories remain enabled: geometry 0, ERC 0, one
explicit missing-U201 footprint parity finding. Independent actual-drill checks
retain a 0.170 mm minimum hole-edge-to-SMD gap across both faces, even on the
same net. Actual reference fill area is 8,182.35 mm². Protected openings are
checked against actual sensitive-node lands and retained copper; boundary
comparison accounts only for one-nanometre coordinate serialization. Receiving
is renewed after the four unrouted-part pose changes. Height, mate, hardware,
stack, mask/tenting/stencil and full analog/PDN/thermal limits remain unapproved.

Top, bottom and inner reference PNGs were visually inspected. Focused audio-main
regression runs 37 tests successfully. Source selection and the README now
reference the complete placed-ground candidate while withholding fabrication
release. Global signals/supplies, actual ESS land/interfaces and ADC stars,
parts/harness/support/case receiving, electrical/fault/noise/stability/thermal
review and inspected manufacturing/first-article outputs remain unfinished.
No native Mac CAD app, bulk-audio batch, supplier request or order was launched.


Final combined-checkpoint verification: 835 tooling tests complete with three
skips; all 23 CAD integration tests pass. All 43 newly added Python sources
parse and have zero syntax/undefined-name diagnostics. Focused audio-module
Ruff checks pass. The current 15-role inventory replays without missing selected
sources. All three new audio PCB views match recorded source/image hashes.
The shared DC04 checkpoint independently retains native-clean partial routing
at 143 opens and its explicit SD timing/process/assembly holds. The read-only
performance observer's existing Scene/Release families are now exposed by its
CLI, and help parsing confirms those choices. The complete unit remains
unreleased; these verification results do not qualify assembled hardware.


## AC04 additive control routing

Selected `audio-main-controls-01` after isolated Linux KiCad 10.0.7 checks:
17 additional control pairs / 27 surface segments reduce uncapped audio opens
393 -> 376. Native geometry/ERC remain zero; the one missing U201 footprint
parity finding remains explicit, with no ignored categories. The 475 tracks
and 199 vias preserve every parent object, including all analog lands, feedback
copper, mounts, sensitive-plane openings and filled In1 reference. Native
connectivity rechecks all 138 explicit prior local pairs and all 200 ground
pads against the new PCB. The remaining local ground pairs are covered by the
complete ground-terminal witness. No vias or component moves were added.

A fresh full native obstacle/island capture, exact copper/endpoint replay,
seven mutation/replay tests, immutable executed-source snapshots and actual
source-bound top/bottom/ground previews accompany the candidate. All three
previews were inspected. Focused audio tests: 44 pass. The 15-role inventory
replays with no missing sources. Timing/coupling/EMI/fault, the 376 remaining
routes, ESS land data and whole-unit/process qualification remain open. No
board release, order, upload, supplier message or Mac CAD launch occurred.


## AC04 inner supply distribution

Selected `audio-main-supplies-02` after isolated Linux KiCad 10.0.7 DRC/ERC,
parity, native refill and complete retained-terminal review. Supply routing
reduces uncapped audio opens 376 -> 306 using 825 new tracks and 68 conventional
0.60/0.30 mm vias. The board now has 1,300 tracks / 267 vias; native geometry/ERC
remain zero, missing U201 parity remains one, and no check is ignored.
Native source connectivity is 110/161 placed supply pads; the other 51 remain
explicitly open. All 138 explicit local pairs, seventeen control pairs and
200 input-ground terminals remain connected. Original analog/control copper,
poses, old drills and authored mounting/sensitive-node/codec exclusions are
unchanged. Native refill changes only stored ground fill, now 8,127.327812 mm².
New drill-edge-to-SMD gap minimum is 0.170 mm on both faces, same-net included.

Distribution uses 0.60 mm on In2, 0.20 mm surface escapes within 3.5 mm and
retained sensitive-node openings. These construction dimensions do not rate
capacity/drop/return impedance or qualify noise/stability/fault/thermal/process.
The first draft was rejected before native acceptance because simplified
raster paths did not preserve all later tree targets. The corrected planner
keeps targets on emitted centreline and excludes near-via branch joins. The
independent replay checks every actual added segment/drill and all selected
supply islands against native source witnesses. All 51 focused audio tests
pass. Codec land/data, the 306 remaining routes and whole-unit manufacturing,
parts/mating/harness/support/installed qualification remain unfinished. No
native Mac CAD, supplier message, upload or order occurred.


## AC04 placed supply/sense completion

Selected `audio-main-supplies-06`: all 161 placed supply/sense terminals now
reach their declared sources. Audio opens fall 306 -> 267. Native Linux
KiCad 10.0.7 geometry/ERC are zero, missing U201 parity remains one, and no
categories are ignored. The board has 1,729 tracks / 271 vias; all 138 explicit
local pairs, seventeen control pairs and 200 input-ground pads remain connected.
The intermediate outer routing adds 28 joins / 248 tracks; final bridges add
eleven joins / 181 tracks / four conventional 0.60/0.30 mm vias. All parent
lands, poses, old copper/drills and authored mount/sensitive/codec exclusions
remain exact. Native refill is retained verbatim; reference area is
8,124.161827 mm². Minimum drill-edge to actual SMD copper remains 0.170 mm.

Fine-pitch exits and via-centre necks retain their 3.5 mm budgets. Reused
powered vias are joined at their centres. The 9.736 mm / 0.20 mm R211 divider
feed has a separate twelve-millimetre low-current construction assessment:
27.7 kΩ / 10 kΩ, nominal 119 µA, with conservative declared rail/current/
copper/temperature assumptions giving under 10 µV trace-only loss. Those
assumptions, noise and installed sensing/fault behaviour remain unqualified.
The long relay feed and its still-unrouted return require current/transient
review. No prior feedback or local bypass length budget was relaxed.

All 59 focused audio tests pass, including eight new mutations/replay tests;
the final receipt was rechecked after cumulative supply-count metadata was
corrected. Rejected generated bridge projects were removed after successful
native checks; executed sources and compact diagnostics remain with the
adopted candidate. Missing codec land/data, 267 remaining routes and complete
installed power/return/noise/stability/thermal/fault, parts/process and assembly
receiving remain open. No Mac CAD, supplier message, upload or order occurred.


## AC04 global control routing checkpoint

Native Linux KiCad 10.0.7 verifies 48 further control joins: 219 total opens, down from 267; 16 targeted control opens remain. Geometry/ERC findings remain zero, with one missing-U201 parity finding and no ignored categories. All 138 local pairs, seventeen earlier control pairs, 200 ground pads and 161 source-connected rail/sense pads remain connected. The new 545 tracks and 85 conventional vias retain all component positions, existing copper and authored keepouts. Exact added-copper replay and complete native pad witnesses pass. The minimum new drill-edge-to-SMD gap is 0.169980855 mm; refilled In1 area is 8056.273842 mm². Timing/coupling/EMI, power/return, codec data and whole-unit/process qualification remain open. Automatic search is giving diminishing returns; the remaining control escapes need placement/routing review. All four current copper-layer plots were inspected. The 92 relevant audio/fabrication checks and 23 CAD integration checks pass (115 total); the new Python sources also pass Ruff. No native Mac CAD application was launched and no order or supplier message was sent.


## AC04 watchdog escape and timing completion

The watchdog U601 and C601/C602 move together into clear space within the unchanged 150 × 63 × 1.6 mm allocation. Receiving and local capacitor spacing are rechecked; amplifier positions, compensation/analog copper, codec reserve and authored exclusions remain exact. Two additional native control joins and the private CWD timing connection reduce opens from 219 to 216; fourteen targeted control opens remain. The corrected candidate has zero geometry/ERC findings, one missing-codec parity finding and no ignored categories. All 138 explicit local pairs, seventeen earlier control pairs, 48 earlier global-control joins, 200 grounds and 161 source-connected rail/sense pads remain native-connected. The actual board has 2291 tracks, 360 conventional vias, 8051.508869 mm² In1 ground and a 0.169980855 mm minimum actual drill-edge-to-SMD gap. Seven abandoned V3V3 leaves are independently checked and pruned. The first native trial exposed a moved ground-via collision and obsolete/dangling copper; those are corrected. Compact diagnostic source snapshots and a rejected-findings summary replace duplicate board exports, and temporary probe data is removed. All four current copper-layer plots were inspected. The 108 relevant audio/fabrication tests and 23 CAD integration tests pass (131 total), and all new live Python sources pass Ruff. ESS land/interface data, remaining routing and full installed/process qualification are still unfinished. No native Mac CAD launch, supplier message or board order was made.


## AC04 settling supervisor and local pull-up completion

U208, C224 and C227 move into freed receiving space, and R204 moves beside the driver. Two new native control joins and CT timing reduce opens from 216 to 213; twelve targeted control opens remain. The corrected board has zero geometry/ERC findings, one explicit missing-codec parity finding and no ignored categories. All 138 local pairs, seventeen earlier control pairs, fifty earlier global-control joins, the earlier watchdog timing pair, all 200 grounds and 161 rail/sense pads remain connected. Actual copper totals 2321 tracks and 371 conventional vias; the minimum actual drill-to-SMD gap is 0.169980855 mm and In1 area is 8043.593905 mm². The isolated 10.072972652 mm, 0.20 mm U208.1 SENSE branch is checked against a 12 mm limit; ordinary VDD/pull-up feeds retain short entries. The fixed TPS389033 sense-current limit is 8 µA at the stated 5 V test condition, distinguished from the adjustable variant’s 100 nA; the 20 µA/0.16 mm finished width/18 µm copper/125 °C illustration gives a maximum trace-only drop near 2.03 µV. These remain unapproved assumptions and exclude via loss, noise and fault qualification. The first native trial found 0.15 mm capacitor-to-via clearance; a 0.07 mm cell shift corrects it while retaining body clearance. Compact rejected-source/findings diagnostics replace duplicate board exports. All four actual copper-layer views were inspected. Missing ESS data, remaining routing and complete installed/process qualification remain open. No native Mac CAD launch, supplier message, upload or board order was made.


Validation passed: fourteen focused supervisor/replay tests, twenty fabrication evidence/geometry tests and twenty-three CAD integration tests (57 checks). The latter two suites were rerun after readiness regeneration completed. Ruff passed for the new Python sources and focused tests. These checks do not qualify installed electrical performance or release manufacturing outputs.
