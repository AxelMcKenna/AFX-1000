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

## 2026-11-02 — Coordinated digital SD routing and LED escapes

Rebuilt a reversible routing trial from DC03 to reserve LED pin exits before
global signals and place SD/LED series resistors beside the actual Seed pins.
Fourteen resistor poses changed. The SD supply branch and seven ground returns
were rerouted; all 201 power/ground pads, 39 local connections and 33 thermal
connections remain native-connected. The matched SD carrier paths range from
66.720 to 72.719 mm, with 5.999 mm spread and exactly one via per signal. This
reduces DC04's 36.703 mm spread without claiming a complete timing/impedance
budget or including module/socket/component/barrel/off-board paths.

`digital-coordinated-native-01` has 236 opens, 82 explicit unfinished LED-via
warnings, no native geometry errors, and zero parity/ERC findings. Independent
checks cover all changed poses, actual courtyards, THT solder/mount/edge reserves
and all 218 drilled vias. The minimum non-exempt drill-to-SMD-copper gap is
0.154984 mm; 21 unchanged mask-covered heat-spreader vias retain their process
hold. All 138 components and five mounts also clear the retained conditional
AP04 floor/context envelopes. Front/back/ground/power PDFs were rendered and
visually inspected. The independent trial audit replays exactly.

The four-layer global-routing output was rejected for selection: it retains
194 opens and contains a 0.1779 mm clearance against the 0.20 mm rule. Its
diagnostics remain saved. A protected six-layer comparison, followed by thirteen
short polygon-screened joins, reaches 156 opens with only explicit dangling-via
warnings and zero geometry/parity/ERC errors. LED-priority completion continues
from that verified source. The too-short three-second search allowance was
stopped after obstacle setup consumed most route budgets; the succeeding pass
uses twenty seconds per connection within a six-minute overall bound.

The full fifteen-role source inventory passes and thirteen focused digital
integration/annotation tests pass. Concurrent audio work is preserved and now
selects `audio-main-ground-02` with 393 opens and all 200 placed ground pads
connected. The ESS land remains missing. The old executable bench plan explicitly
targets E14/E25 and cannot qualify the current P03/E28/AC04/DC04 unit. Selected
digital DC04/AP04 remains unchanged while the coordinated trials are evaluated.
No native Mac CAD, supplier request, order, commit or fabrication release occurred.


The subsequent LED-priority pass completes 39 joins. Removing 65 unused vias
and 102 unsupported leaf tracks preserves all connectivity. The final
`digital-coordinated-six-clean-native-01` checkpoint has 117 opens across 91
nets and zero native geometry/parity/ERC findings. It contains 1,460 tracks and
298 vias; all 201 power/ground pads, 39 local and 33 thermal connections remain
native-connected. All six SD paths retain the 5.999 mm spread and one via each.
Independent placement, drill and SD checks pass. Ground-fill contour counts
alone initially over-reported fragmentation: the remaining small J1007 lobe
joins through the actual THT pad. Union of native zone/pad/track/via copper
independently proves one physical copper component on each reference/power
layer, without asserting return-impedance qualification. All six layer plots
were rendered and visually inspected. Remaining nets comprise 39 LED outputs,
12 controls and 40 others; finish the other interfaces next. The earlier
six-layer trial still has four fewer overall gaps, but 72 open LED nets and
uncorrected SD matching. Neither trial replaces selected DC04/AP04 yet.

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


## 2026-11-02 — Digital interface completion to 75 opens

The non-LED-priority pass completes 38 joins from the reviewed 117-open
coordinated six-layer trial. Its 79-open native checkpoint preserves all
201 power/ground pads, 39 local and 33 thermal connections, matched SD paths
and one physical copper component per reference/power layer. Both DAC-data
nets now join ADC data, BCLK and WS as fully connected digital audio nets.

A separate J1001 move from (32,14) to (31.2,14) mm changes exactly that
footprint pose and the ends of its two bulk-cap tracks. All other source
geometry remains exact. The 0.30 mm courtyard gap and conditional AP04
receiving pass. Fourteen newly planned LED escapes are valid geometry but do
not complete an output net. Increasing the routing search bound from 120,000
to 500,000 visits completes four other joins: POT_ADC_05 and branches of
BLANK_5V, CLOCK_5V and LATCH_5V. The blanking/clock paths require the connector
move: against its old pad they have 0.109 mm clearance and overlap respectively.
CLOCK_5V_SRC and both latch-related nets still have gaps; the complete LED
interface is not claimed connected.

Removing all 14 unused escape vias and 28 leaf tracks retains 75 opens and
eliminates their warnings. `digital-interface-clean-native-02` has zero native
geometry/parity/ERC findings with every category enabled, 2,122 tracks and
423 vias. Independent checks pass for all fifteen changed component poses,
actual courtyards/THT/edge/mount reserves, all via drills and the three physical
plane components. Minimum non-exempt drill-edge-to-SMD gap is 0.154984 mm;
21 original mask-covered heat-spreader vias retain their process hold.
All six SD paths retain the 5.999 mm spread and one via each. All 201/39/33
power/local/thermal witnesses remain connected. All six native copper PDFs
were rendered and visually inspected; source-bound visual and conditional
assembly receipts accompany the candidate. Nineteen routing/native/audit/visual
receipts replay their exact source hashes. Thirteen focused digital tests pass.

The remaining 66 open nets comprise 39 LED outputs, two controls and 25 other
nets. Exploratory grid connectivity checks around LED_04/29/31 find separated
source/header regions on each individual signal layer; they are diagnostics,
not a proof that every multilayer route is impossible. Coordinated escape and
copper rework is the next task, rather than repeating the same bounded search.
The selected DC04/AP04 sources remain unchanged. Current audio selection is
preserved at `audio-main-controls-01`, 376 opens and the missing ESS footprint.
The old E14/E25 bench plan now explicitly links the current inventory and
states that it cannot qualify P03/E28/AC04/DC04 or the six-layer trials.
Full routing, accepted stack/process, installed receiving, unit electrical and
thermal review, manufacturing outputs and current first-article preparation
remain unfinished. No fabrication release, supplier message, order, commit or
native Mac CAD launch occurred in this work.


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


## 2026-11-03 — Clock-source connection and routing-interchange correction

Revalidated the complete 75-open candidate evidence before work. A selective
rerouting experiment exposed an interchange issue: KiCad exports unlocked
objects as DSN `type route`, while the examined Freerouting parser maps unknown
type tokens to a fixed state. The new v2 exporter emits `type normal` for the
1,960 movable DSN items and retains 416 protected DSN items representing the
429 exact SD/power/local source objects. The pinned router log changes from
only fixed conflicts to explicitly movable traces, confirming the correction.
The earlier experiment is retained with a rejection record; sealed legacy
recipes were not edited.

The corrected global trial is also rejected after native checking: 91 opens,
three clearance errors, 29 dangling-via warnings, no newly closed nets and
13 newly open nets compared with the 75-open parent. A horizontal J1004 status
header does not fit the existing J3005 connector row. A finite resistor-site
screen instead found a feasible R3016 move from B(75,21) to B(69,23).

The first ordering restored the crossing supply before routing the new clock
source and trapped that source. Reversing the order succeeds: complete the
clock-source connection and rejoin its existing distribution, then restore
the 0.30 mm 3.3 V branch. The branch grows from 5.161 to 6.503 mm. Native
verification reaches 74 opens with only the obsolete clock-branch warning.
Capturing that explicit warning and removing six leaf tracks yields
`digital-clock-series-clean-native-01`: 74 opens, zero geometry/parity/ERC,
2,125 tracks and 424 vias. U3005.20 -> R3016.1 now has 4.480 mm planar copper
and one via; no formerly connected net regresses. LED_SCK upstream remains
open, so this does not close the entire clock interface.

Independent exact-delta, placement/drill/SD, physical plane-connectivity and
conditional AP04 receiving checks pass. All 201 power/ground pads, 39 local
and 33 thermal connections remain intact. SD spread remains 5.999 mm with one
via per signal. Minimum non-exempt SMD drill gap remains 0.154984 mm; 21
original mask-covered heat-spreader vias retain their process hold. All six
copper-layer PDFs were rendered and visually inspected. The targeted LED_49
and LED_52 follow-up makes no additional join. Remaining 65 open nets comprise
39 LED outputs, two controls and 24 others. Local routing around the buffer,
header and adjacent return/supply/control copper needs further coordinated work.

Selected DC04/AP04 and the concurrent audio selection remain unchanged. Full
routing, ESS package data, accepted stack/process, installed assembly/harness,
electrical/thermal review, manufacturing outputs and first-article preparation
remain unfinished. No supplier message, order, commit, fabrication release or
native Mac CAD launch occurred in this work.

Final verification for this checkpoint: 13 focused digital tests pass; eight new
Python modules parse; both independent clock/placement audits replay exactly;
all final native/connectivity/receiving/visual source hashes match. The complete
15-role source audit has no missing files, and whitespace checks pass.

## 2026-11-03 — Native-sized via spacing and three additive joins

Inspected the exact Freerouting image revision
`b647a2f824cfbc54bc4dcaee71b03b7cd945eb76`. Its hole-clearance override concerns
hole-to-copper obstacles, while its same-net via pairs still receive copper
clearance through Via.isObstacle/Item.clearanceViolations. The existing log's
184 fixed-item conflicts cannot be resolved merely by changing that override.
Pinned source copies and conclusions are preserved in
`digital-router-clearance-diagnosis-01`; the global rerouting experiment remains
rejected. Native KiCad rules are unchanged.

Added an independent digital planning screen using actual via copper sizes
instead of a blanket 0.86 mm centre exclusion. Three additive connections yield
`digital-native-spacing-native-01`: **71 opens across 63 nets**, zero native
geometry/parity/ERC findings, 2,234 tracks and 441 vias. SDA and LED_SCK become
connected and LATCH_5V drops from three pad groups to two. The exact delta is
109 tracks and seventeen 0.60/0.30 mm vias, with every parent copper object,
component pose, mount, outline and authored zone definition retained. Every
parent pad group remains connected, including partial groups on unfinished nets.

Connectivity does not qualify the new routes electrically. LED_SCK has 94.415 mm
of new copper and nine new vias, 96.178 mm total; this needs rework or explicit
signal-integrity acceptance. The latch branch adds 85.046 mm/four vias and SDA
adds 58.979 mm/four vias. Loading, delay, reference transitions, impedance and
installed interfaces remain unqualified. A subsequent bounded pass on 56 other
nets performs 71 searches and adds no copper; the no-op outcome is preserved.

Final validation found that native capture objects omit via drill dimensions.
Sealed v1 recipes are retained. The new v2 planner reads existing via drills
from the hash-checked paired PCB, with a regression test for that exact capture
contract. All three emitted routes and seventeen vias pass the corrected v2
screen. An independent full-board drill comparison finds a minimum new-hole
edge gap of 0.524621 mm, above the 0.25 mm native requirement. Two new vias have
another via within the old 0.86 mm blanket exclusion. Future work uses
`digital_native_spacing_routes_v2`.

Independent placement/drill/SD and physical plane-union checks pass. All 201
power/ground pads, 39 local and 33 thermal connections remain intact. SD paths
retain 5.999 mm spread and one via each; the minimum non-exempt drill-to-SMD gap
is still 0.154984 mm and 21 original heat-spreader vias retain their process hold.
Conditional AP04 receiving passes for 138 parts/five mounts. All six copper
PDFs were rendered and visually inspected. Nineteen focused tests pass.

The full-unit inventory links the 71-open trial without changing selected
DC04/AP04 or the concurrent audio selection. Remaining routing, ESS package
data, stack/process, actual parts/mating/harness/supports, power/noise/thermal,
manufacturing outputs and current first-article qualification remain unfinished.
No supplier message, order, commit, fabrication release or native Mac CAD launch
occurred.


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

## 2026-11-03 — Router geometry diagnosis and eight-layer digital trial

Reproduced the pinned Freerouting geometry behavior with a read-only inspector.
Changing its hole override alone leaves all 463 reported conflicts unchanged.
Circumscribed 64-sided round-pad polygons together with `snap_angle none`
reduce foreign-net router conflicts from 273 to three; polygon conversion alone
is insufficient because the 45-degree search tree uses bounding octagons.
The remaining same-net conflicts remain visible. No runtime/JAR patch or native
rule suppression was applied. Source/geometry evidence is retained in
`digital-router-geometry-diagnostic-01`.

KiCad session import does not accept the polygon via padstacks. The separate
import adapter restores only original circular via-library definitions, proves
all placements/wires unchanged and checks every session via was imported.
Even with that correction, native six-layer results 03/04 give 74/72 opens and
2/1 native findings. Both are rejected; the clean 71-open parent remains intact.

The separate eight-layer preparation adds In5 signal and In6 AGND, retains
all other plane definitions and removes only the documented long LED_SCK route.
Its 72-open baseline routes sixteen joins to 56. LED_SCK falls from 96.178 mm /
nine vias to 46.620 mm / two vias. Every earlier connected pad group is retained;
SD spread remains 5.999 mm with one via per signal.

Seven coordinated LED pin escapes initially hit broad-search bounds. A diagnostic
of native-captured geometry at 0.10 and 0.05 mm shows four share an In5 free-space
component with their destinations. Confining the search to that layer connects
LED_04/06/08/71. The three unused escapes are removed exactly (six segments and
three vias). Final `digital-eight-led-clean-native-01` has **52 opens / 51 nets**,
zero native geometry/parity/ERC, 2,530 tracks and 461 vias. The final LED step
adds 104 segments and four 0.60/0.30 mm vias while preserving every 56-open
parent copper object, footprint, mount, outline, authored zone and pad group.
The four LED lengths are 75.544/76.961/79.773/49.333 mm, each one via; installed
loading/transients/compliance/coupling are not qualified by connectivity.

The first follow-up layer-only control search rejected an empty-contact group
before producing a candidate. A prefilter confirms all sixteen remaining
non-output control nets lack In5 contacts in at least one group. New escapes
or coordinated placement/copper rework are required before repeating that
specific search. Thirty-five LED output nets remain open. These bounded
search outcomes do not prove unroutability.

The complete 71 -> 56 -> 52 evidence chain replays exactly. All 201 power/ground
pads, 39 local and 33 thermal connections survive. Each of the four plane fills
has one physical polygon union. Minimum non-exempt drill-edge/SMD gap remains
0.154984 mm and 21 retained heat-spreader vias keep their process hold. All eight
final native copper plots were rendered and visually inspected. Conditional
AP04 receiving passes for 138 parts/five mounts; complete installed receiving
is still unverified. The nineteen focused digital regression tests pass.

The whole-unit inventory links the new comparison while preserving selected
DC04/AP04 and concurrent audio-main-supplies-06 (267 opens). The nominal 1.6 mm
eight-layer setting is not an accepted stack: copper/dielectric, cost/process,
mask/tenting/stencil and complete electrical/thermal/harness checks remain open.
Remaining routing, ESS land/interface data, coherent full-unit selection,
current assembly receiving, inspected fabrication outputs and first-article
inspection/bring-up still prevent prototype release. No supplier message,
order, commit, release or Mac CAD launch occurred.

## 2026-11-03 — Continuous escapes and three more digital connections

Continued from the source-verified 52-open eight-layer checkpoint. A bounded
surface-escape/In5 planner closes SCL with sixteen segments and one via. A
continuous polygon search finds a small legal region missed by the 0.25 mm
escape grid and closes DATA_5V_SRC with nineteen segments/two vias. Finally,
a visibility search along buffered copper boundaries finds SERIAL_2 escapes
that the 0.05 mm local grid misses. Its retained route adds 26 segments/two vias.
Every path uses exact copper checks before independent native KiCad review.

Native stages are 51 -> 50 -> **49 opens**, all with zero geometry/parity/ERC
findings and all rule categories enabled. Final `digital-eight-serial-native-01`
has 2,591 tracks/466 vias, 48 open nets and 35 remaining LED output nets. All
52-open parent copper objects, poses, mounts, outline, authored zones and
connected pad groups remain exact. The complete prior chain to 71/56/52 and
each new additive receipt replays exactly. All 201 power/ground pads, 39 local
and 33 thermal connections survive; the shortened two-via clock, 5.999 mm SD
spread, four physical plane unions and 0.154984 mm minimum non-exempt SMD drill
gap remain intact. The 21 original heat-spreader vias retain their process hold.

The first new planner inherited a 0.16 mm width in a new-via distance helper,
although its main copper screen and emitted traces use 0.20 mm. Its sole SCL
route is independently rescreened with both widths set to 0.20 mm and passes;
native rules also pass. Later versions explicitly set both widths and include
the inherited module in the construction hashes. Executed sources are sealed.
The final checkpoint replays every new line/via through the corrected screen.

SCL adds 60.889 mm, now 202.814 mm total branched copper/five vias. SDA retains
164.559 mm/fourteen vias. Loading, pull-ups, rise time and installed harness
need explicit electrical acceptance. DATA_5V_SRC is 52.091 mm/two vias and its
remote R3015 placement needs source-damping/timing review or coordinated rework.
SERIAL_2 is 18.807 mm/two vias. Connectivity is not electrical qualification.

The visibility trial also finds a 124.058 mm LED_49 detour. This is deliberately
not retained: only SERIAL_2 is selected by an exact additive filter, removing
65 trial segments and one via. An alternate In3 pass on thirteen LED nets adds
zero joins. The diagnosed access regions and bounded failures guide local
copper/placement rework; they are not a proof of unroutability.

All eight final copper plots and a 1200 dpi fine-pitch front detail are visually
inspected. Conditional AP04 receiving remains clear for 138 parts/five mounts.
Four new geometry regressions cover sub-grid via regions, disconnected surface
regions, exact-clearance visibility detours and real layer transitions. All 24
focused tests pass. Full-unit documentation now links the 49-open trial while
retaining selected DC04/AP04 and audio-main-supplies-06. The old qualification
plan explicitly excludes both six- and eight-layer digital trials.

Remaining routes, data-series/bus review, ESS land/interface data, accepted
stack/process, actual assembly receiving, inspected manufacturing outputs and
a current first-article package remain open. No supplier message, order, commit,
release, physical measurement or native Mac CAD launch occurred.


## AC04 global control routing checkpoint

Native Linux KiCad 10.0.7 verifies 48 further control joins: 219 total opens, down from 267; 16 targeted control opens remain. Geometry/ERC findings remain zero, with one missing-U201 parity finding and no ignored categories. All 138 local pairs, seventeen earlier control pairs, 200 ground pads and 161 source-connected rail/sense pads remain connected. The new 545 tracks and 85 conventional vias retain all component positions, existing copper and authored keepouts. Exact added-copper replay and complete native pad witnesses pass. The minimum new drill-edge-to-SMD gap is 0.169980855 mm; refilled In1 area is 8056.273842 mm². Timing/coupling/EMI, power/return, codec data and whole-unit/process qualification remain open. Automatic search is giving diminishing returns; the remaining control escapes need placement/routing review. All four current copper-layer plots were inspected. The 92 relevant audio/fabrication checks and 23 CAD integration checks pass (115 total); the new Python sources also pass Ruff. No native Mac CAD application was launched and no order or supplier message was sent.

## 2026-11-03 — R3015 relocation and explicit data-route tradeoff

Retained a separate `digital-data-series-native-01` comparison from the 49-open
serial checkpoint. Native-generated footprint templates support moving R3015
from front (31,11) to back (75,21) mm without inventing a flipped land pattern.
The candidate preserves the original driver escape, removes one old source
segment, reassigns seventeen segments/one via to the resistor output, bridges
the old resistor location and adds 23 segments/two conventional vias. All other
component poses and copper, mounts, outline and authored zones remain exact.
C3010's local bypass is unchanged.

The pre-series trace falls from 52.091 to 16.753 mm with two vias in both cases.
The post-series trace grows from 36.749 mm/no vias to 103.539 mm/two vias. Combined
copper grows from 88.840 to 120.292 mm, an increase of 31.452 mm. This is a
geometric tradeoff, not electrical acceptance. The initial 10 mm search target
found no solution; the retained planner uses an 18 mm optimization target.
Neither target is an electrical rule, and no native clearance/drill rule changed.
Further coordinated placement/routing may be needed to shorten the full path.

Isolated Linux KiCad 10.0.7 passes with 49 opens, zero geometry/parity/ERC
findings and all categories enabled: 2,613 tracks/468 vias. The independent
relocation audit checks the exact native template, source/output net transfer,
unchanged transferred geometry, authored/native equality, complete parent
checkpoint and all prior connected pad groups. All 201 power/ground pads,
39 local and 33 thermal connections remain intact. The 46.620 mm/two-via clock,
5.999 mm SD spread/one via per signal and all four physical plane unions survive.
Minimum non-exempt drill-to-SMD gap remains 0.154984 mm; the 21 heat-spreader
vias retain their process hold. Conditional AP04 receiving passes for 138 parts
and five mounts. All eight copper plots and 1200 dpi front/back details were
visually inspected and recorded with source hashes.

All 28 focused tests pass, including four exact-delta tests that reject changed
transferred geometry, unrelated copper and swapped resistor nets. A new audit
comparison initially failed because JSON drops the S-expression parser's token
subtypes; it now compares receipt token values directly while retaining strict
S-expression comparisons for native geometry. The full audit subsequently passes.
Executed constructor, physical audit and final evidence sources are sealed.

The full-unit inventory links this unselected comparison while preserving
selected DC04/AP04 and the concurrent 219-open audio-main-controls-02 checkpoint.
Thirty-five LED output nets, other digital controls, audio/NF routing, the ESS
land/interface data, stack/process, actual assembly receiving and electrical/
thermal/fault qualification remain open. Inspected manufacturing outputs and a
current first-article package are still required. No supplier message, order,
commit, release, physical measurement or native Mac CAD launch occurred.

## 2026-11-03 — ARMED pull-down connected by placement change

The previous goal turn made verified progress. Continued with the isolated
ARMED pull-down R1005, retaining the 49-open data-series comparison as parent.
A bounded search screened 4,335 translations, finding 599 mechanically legal
and 150 copper/drill-clear placements. R1005 moves on the back from (40,16) to
(27.5,29.5) mm with its orientation, footprint, value and pin assignments exact.
Its short signal lead reaches existing In5 ARMED copper through one conventional
via; its ground lead reaches the AGND planes through a separate conventional
via. Added lengths are 1.574116 mm signal and 1.009796 mm ground. Three segments
and two vias preserve every earlier copper object, including the ground junction
still serving R1003. No clearance, width, hole, courtyard or receiving rule changed.

The first native invocation mistakenly used the single-sheet reviewer; it
stopped at its circuit-export assertion because the child sheets were absent.
That incomplete `digital-armed-native-01` result is not accepted. A new isolated
hierarchy-aware review in `digital-armed-native-02` includes all child sheets and
passes with 48 opens, zero geometry/parity/ERC findings and all categories enabled.
The first capture used relative path keys; `digital-armed-inputs-48b` recaptures
with absolute source paths for the existing independent hash checks.

The retained board has 2,616 tracks/470 vias and 47 open nets, including 35 LED
outputs. Every parent pad-group connection survives; ARMED is the sole merged
net. All 201 power/ground pads, 39 local and 33 thermal connections remain intact.
All four filled planes retain one physical union. SD spread remains 5.999 mm
with one via per signal; clock/data copper remains exact, including the prior
R3015 length tradeoff. Minimum non-exempt drill-edge-to-SMD gap remains 0.154984 mm,
and the 21 mask-covered heat-spreader vias retain their process hold.

All eight copper plots and a 1200 dpi back-side R1005 detail were inspected.
Conditional AP04 receiving passes for 138 parts and five mounts. All 32 focused
tests pass; new tests reject removal of an old ground-junction segment, changed
resistor pin nets and moved old copper. The independent relocation audit checks
native/authored equality, exact translation/additions, all parent pad groups,
actual added copper/via clearance and complete source-bound parent replay.

The full-unit inventory now links the 48-open unselected trial while preserving
selected DC04/AP04 and concurrent audio-main-controls-02 (219 opens). Remaining
control pull-downs and LED escapes are the next placement/routing work. Audio/NF
routing, ESS land/interface data, accepted stack/process, actual assembly
receiving, complete electrical/thermal/fault qualification, inspected fabrication
outputs and a current first-article package remain unfinished. No supplier
message, order, commit, release, physical measurement or native Mac CAD launch
occurred. The full goal remains active.

## 2026-11-03 — Three control pull-down connections; 45 digital opens

The previous turn made verified progress. Continued from the 48-open ARMED
checkpoint with R1003/MCU_PERMIT, R2002/ANALOG_OK and R2003/INPUT_READY. Their
orientations, values, footprints and pin assignments remain exact. Back-side
positions move respectively (43,16) -> (41.5,16), (68,25) -> (101.5,41.5), and
(77,27) -> (101.5,34.5) mm. Six named obsolete ground-spur segments are retired;
all other earlier copper, all other poses, mounts, outline and authored zones
remain exact. Retained old ground vias still join the ground planes.

The new branches add signal/ground lengths of 3.377769/6.912500 mm for MCU_PERMIT,
12.479753/2.628718 mm for ANALOG_OK, and 5.112500/1.755749 mm for INPUT_READY.
Thirteen 0.20 mm segments and two conventional 0.60/0.30 mm signal vias reconnect
all three resistors. INPUT_READY and all replacement ground branches use B.Cu
without new vias. No physical rule changed; the 30 mm total-added-route search
target is an optimization bound, not an electrical acceptance criterion.

The first two bounded planners exhausted their INPUT_READY search without
emitting a board. Subsequent versions added actual surface/via targets, direct
ground paths, expanded the placement domain beyond x=101 mm beside U2003 and
included same-layer visibility search. The v3/v4 processes were positively
identified and intentionally stopped after being superseded; their terminal
codes are 143, not unexplained observation timeouts. The retained v5 candidate
completed all three joins. Surface ground targets explicitly exclude all three
moving resistors so a new branch cannot depend on a soon-to-be-removed pad.
Search outcomes and exact planner hashes are recorded in the final stage.

Isolated hierarchy-aware Linux KiCad 10.0.7 passes with **45 opens across 44 nets**,
zero geometry/parity/ERC findings and all categories enabled. The board has
2,623 tracks/472 vias. Every prior connected pad group survives, including all
201 power/ground pads, 39 local and 33 thermal connections. The exact-delta audit
checks all translations, declared retirement, native/authored equality, emitted
route geometry, actual copper/via spacing and complete parent evidence replay.
All four physical plane unions, the 5.999 mm SD spread/one via per signal, clock,
data-series and ARMED copper remain intact. Minimum non-exempt drill-to-SMD gap
is 0.154984 mm; 21 heat-spreader vias keep their mask/tenting/process hold.

All eight copper layers and two 1200 dpi back-side placement details were
visually inspected. Conditional AP04 receiving passes for 138 parts/five mounts.
All 38 focused tests pass, including six new checks for exact-delta protection
and surface connectivity. Source-bound construction and review evidence is sealed.

The unit inventory links the 45-open unselected comparison while preserving
selected DC04/AP04 and concurrent audio-main-controls-02 (219 opens). Remaining
digital nets include 35 LED outputs plus CONTROL_26, LATCH_5V, LATCH_5V_SRC,
SERIAL_0, SERIAL_1, POT_ADC_09, BYPASS_SENSE, LED_BLANK (three groups) and LED_XLAT.
These local escapes and copper/placement access are next. Audio/NF routing, ESS
land/interface data, accepted stack/process, actual assembly receiving, full
electrical/thermal/fault qualification, inspected manufacturing outputs and a
current first-article package remain incomplete. No supplier message, order,
commit, release, physical measurement or native Mac CAD launch occurred.

## 2026-11-03 — Latch escape repaired by rebuilding one ground return

The previous goal turn made verified progress. Retried nine remaining control/
serial nets on In5 and In3 after the pull-down moves; both fixed-geometry searches
completed with zero joins. A source-bound surface-region diagnostic finds zero
legal conventional-via area for eleven selected blocked endpoints under existing
copper and unchanged planning margins. That is a diagnosis of the retained
geometry, not a claim that the board is generally unroutable.

The diagnostic identifies AGND via `ddf5ce63-a3bc-56b5-bae4-7601e66d24e9` directly
in front of U3002 latch pad 30. Retired that via and its sole R1049 ground spur
`db13c3bf-494c-5004-abf8-d82cf637654f`. R1049 ground now reaches retained AGND copper
on B.Cu through 3.678676 mm, replacing 1.170470 mm, without another ground via.
The cleared (44.0125,13.4) mm site becomes a latch escape. Single-layer In5/In3
searches still fail; a multilayer route using In5/In3/F closes the latch branch.
It adds 22.258112 mm and three conventional 0.60/0.30 mm vias. Eleven new 0.20 mm
segments/three vias replace one segment/one via; all poses and unretired copper
remain exact. No rule changes or hidden native findings were used.

Strict isolated hierarchy-aware Linux KiCad 10.0.7 reports **44 opens across 43
nets**, zero geometry/parity/ERC findings and all categories enabled. The board
has 2,633 tracks/474 vias. Every old pad group survives. All 201 power/ground pads,
39 local connections, 33 thermal branches, four physical plane unions, 5.999 mm
SD spread/one via per signal, clock/data and prior control closures remain intact.
All net records except AGND and latch are exact. Minimum non-exempt drill-to-SMD
gap stays 0.154984 mm and 21 heat-spreader vias retain their process hold.

The full latch net now totals 197.636794 mm of branched copper/thirteen vias,
up from 175.378682 mm/ten vias. These totals do not establish propagation delay,
source damping or timing acceptance. Existing data-series/I2C, real stack and
installed-loading review holds remain explicit.

All eight copper plots and 1200 dpi front latch/back ground-return details were
visually inspected. Conditional AP04 receiving passes for 138 parts/five mounts.
All 42 focused tests pass, including four new exact-delta regressions. The
independent audit checks retired objects, every new native segment/via against
the recipe and exact clearance screen, all prior pad groups, complete physical
checks and the parent evidence chain. The copied obstruction diagnostic, its
results and both zero-join retries are retained with source hashes.

The unit inventory links the 44-open unselected comparison while preserving
selected DC04/AP04 and concurrent 219-open audio-main-controls-02. Remaining
work includes 35 LED outputs and eight other digital nets, especially blocked
serial/control escapes and the isolated LED_BLANK pull-up. Multilayer routing
and coordinated local via/track changes are the next useful actions. Audio/NF
routing, ESS land/interface data, accepted stack/process, actual assembly
receiving, complete electrical/thermal/fault qualification, inspected fabrication
outputs and a current first-article package remain unfinished. No supplier
message, order, commit, release, physical measurement or native Mac CAD launch
occurred. The full goal remains active.

## 2026-11-03 — LED_BLANK pull-up restored without new vias

Continued from the validated 44-open latch checkpoint. A four-signal-layer
planner preserves captured contacts on their real layers and grants broader
access only to actual drilled escapes. Its initial bounded search found no join;
a larger search found a 163.713 mm/seven-via LED_BLANK detour. A less greedy
heuristic found a 108.707 mm/six-via detour. After the pull-up move below, the
same search still found a 108.706 mm/six-via route. All four construction receipts
are source-bound and retained as unadopted search evidence; none of these long
routes is part of the new checkpoint or claimed electrically acceptable.

R3010 moves on B.Cu from (75,25) to (60.5,13.5) mm, retaining value, footprint,
orientation and pin identities. Its signal pad reaches the U3005/R1002 group
through 7.934034 mm of B.Cu. Its supply pad reaches retained V3V3_IO through
11.0875 mm of B.Cu; no false ground-plane supply connection is used. Only the
old V3V3_IO spur fea0fc0e-c268-5cfe-8eb2-4c235472bb03 is retired. The supply
junction and its other branches remain exact. Thirteen 0.20 mm segments replace
one old segment, with no added vias. All unrelated footprints and copper remain.

Strict isolated hierarchy-aware Linux KiCad reports 43 opens across 43 nets,
zero geometry/parity/ERC findings and all categories enabled. There are 2,645
tracks and 474 vias. LED_BLANK now has two groups rather than three; its MCU
connection remains open. All parent connected pad groups and all other net
records are preserved. Independent checks retain all 201 power/ground pads,
39 local connections, 33 thermal branches, four physical plane unions and the
5.999 mm SD spread/one via per signal. Minimum non-exempt drill-to-SMD gap stays
0.154984 mm; 21 heat-spreader vias retain their process hold.

All eight copper plots and a 1200 dpi pull-up detail were visually inspected.
Conditional AP04 receiving passes for 138 parts/five mounts. All 49 focused tests
pass. The independent delta audit replays the complete parent evidence, verifies
the sole retirement and exact translation, checks native additions and actual
spacing, and explicitly proves V3V3_IO and the new signal group are connected.

The unit inventory links the 43-open unselected comparison, preserving selected
DC04/AP04 and the validated 219-open audio-main-controls-02 source. Routing,
approved ESS land/interface data, actual stack/process, installed receiving,
complete electrical/thermal/fault qualification, inspected manufacturing outputs
and a current first-article package remain unfinished. The next useful digital
work is coordinated escape/corridor repair; the 108.7 mm detour is not adopted
merely to lower the open count. No supplier message, order, commit, release,
physical measurement or native Mac CAD launch occurred. The goal remains active.


## AC04 watchdog escape and timing completion

The watchdog U601 and C601/C602 move together into clear space within the unchanged 150 × 63 × 1.6 mm allocation. Receiving and local capacitor spacing are rechecked; amplifier positions, compensation/analog copper, codec reserve and authored exclusions remain exact. Two additional native control joins and the private CWD timing connection reduce opens from 219 to 216; fourteen targeted control opens remain. The corrected candidate has zero geometry/ERC findings, one missing-codec parity finding and no ignored categories. All 138 explicit local pairs, seventeen earlier control pairs, 48 earlier global-control joins, 200 grounds and 161 source-connected rail/sense pads remain native-connected. The actual board has 2291 tracks, 360 conventional vias, 8051.508869 mm² In1 ground and a 0.169980855 mm minimum actual drill-edge-to-SMD gap. Seven abandoned V3V3 leaves are independently checked and pruned. The first native trial exposed a moved ground-via collision and obsolete/dangling copper; those are corrected. Compact diagnostic source snapshots and a rejected-findings summary replace duplicate board exports, and temporary probe data is removed. All four current copper-layer plots were inspected. The 108 relevant audio/fabrication tests and 23 CAD integration tests pass (131 total), and all new live Python sources pass Ruff. ESS land/interface data, remaining routing and full installed/process qualification are still unfinished. No native Mac CAD launch, supplier message or board order was made.

## 2026-11-03 — Short latch-source connection and rebuilt pull-up feed

The preceding goal turn made verified progress to 43 opens. Continued from that
source without changing selected DC04/AP04. Coarse resistor moves and native
front/back orientations found no complete source/output reconnection: retained
geometry either blocked the connection or required 80–90 mm pre-series detours.
A 0.25 mm sweep found no legal front-side placement in its tested window. A
0.05 mm local back-side sweep found 72 pad-clear poses. Five bounded placement
planners and two clock/blank retirement trials terminated without emitting a
candidate; their source hashes and outcomes are retained. These searches do not
prove the board generally unroutable.

The useful source escape is a shared physical via region reachable from both
faces. Separate endpoint-via proposals can miss it, and an extra 0.005 mm region
erosion discarded a small legal region. The accepted common-region search keeps
the existing 0.20 mm copper clearance, drill/SMD/hole rules and planning margins;
it removes only that additional search erosion. A regression exercises a tiny
shared region and rejects disjoint surface regions.

R3017 moves B(75,23) -> B(68,25) mm without value, footprint, pin or orientation
changes. Its pre-series latch connection is 4.784980 mm/one conventional
0.60/0.30 mm via. Its output reconnects through 13.896098 mm of B.Cu. This became
possible by replacing the V3V3_IO branch that blocked the output corridor. A
physical component analysis shows the removed supply branch fed only the
R1002/R3010 pull-up island; a new 7.931229 mm, 0.30 mm-wide route and one via join
that island to retained main-source copper. Native checks prove all 27 V3V3_IO
pads remain connected. The clock and blank buffer escape copper is unchanged.

The first native trial had three track-dangling warnings. Exact, bounded leaf
cleanup removes six obsolete tracks and one unused latch via. The final isolated
hierarchy-aware Linux KiCad 10.0.7 review reports 42 opens across 42 nets, zero
geometry/parity/ERC findings and all categories enabled. Overall 105 new
segments/two vias replace fifteen old segments/one via; the board now has 2,735
tracks and 475 vias. Every unrelated component and unretired copper object is
exact. The clean result is digital-latch-supply-native-02; native-01 is retained
only as the intermediate with explicit warnings.

All parent pad groups, all 201 power/ground pads, 39 local connections, 33 thermal
branches, four physical plane unions and 5.999 mm SD spread/one via per signal
survive. Minimum non-exempt drill-to-SMD gap remains 0.154984 mm; 21 heat-spreader
vias retain their process hold. Every net record except latch source, latch
output and V3V3_IO remains exact. Post-series latch copper changes from 197.637
mm/thirteen vias to 199.915 mm/twelve vias. V3V3_IO changes from 275.448 mm/two
vias to 272.413 mm/three vias. These totals do not establish timing, impedance,
source damping, supply noise or installed performance.

All eight copper plots and three 1200 dpi details were inspected. Conditional
AP04 receiving passes for 138 parts/five mounts. All 56 focused tests pass.
The independent audit replays the full parent evidence and the leaf-pruning
algorithm, verifies the sole footprint translation, every new segment/via and
actual mixed-width clearance, and checks preservation of every old pad group.
Its source-bound receipt passes.

The unit inventory now links the 42-open unselected comparison while retaining
the concurrent validated 216-open audio-main-watchdog-repack-01 and 138-open
negative-protection sources. The audio work advanced during this turn and was
preserved by the final inventory replay. Thirty-five LED output nets and seven other digital nets remain open.
Coordinated local escape repair, actual common via regions and rerouting limited
blocking branches remain useful next actions. Approved ESS land/interface data,
accepted stack/process, installed receiving, complete electrical/thermal/fault
qualification, inspected manufacturing outputs and a current first-article
package remain unfinished. No supplier message, order, commit, fabrication
release, physical measurement or native Mac CAD launch occurred. The goal remains
active.

## 2026-11-03 — exact-region LED_52 checkpoint, 41 digital opens

Completed digital-exact-regions-native-01 from the 42-open latch/supply parent.
LED_52 adds a 15.315642 mm route with nine 0.20 mm segments and one 0.60/0.30 mm
via. The accepted board has 2,744 tracks/476 vias and 41 opens across 41 nets,
with zero native geometry, schematic-parity or ERC findings and every checking
category enabled. Every earlier copper object, component pose, outline, mount
and zone definition is exact. Every other net record is unchanged.

The updated bounded planner retains actual surface contacts even when no new
via escape is available, and removes only the extra 0.005 mm erosion of the
available via region. Existing copper, hole and SMD rules and screening margins
are unchanged. LED_52 uses the area freed by the preceding R3017 move. This does
not establish process tolerance or electrical performance.

The full independent checkpoint replay verifies its parent evidence, the exact
additive delta, actual new-copper clearance, native route geometry and every old
pad group. All 201 power/ground pads, 39 local pairs, 33 thermal branches, four
physical plane unions and 5.999 mm SD spread/one via per signal remain intact.
Minimum non-exempt drill-to-SMD gap stays 0.154984 mm; the 21 mask-covered
heat-spreader vias retain their process hold. Conditional AP04 receiving passes
for 138 parts/five mounts. All eight copper plots and two 1200 dpi details were
inspected. All 58 focused tests pass.

The initial search rejected LED_49/LED_BLANK/POT_ADC_09 routes of approximately
84.229/107.953/165.190 mm. Starting from the smaller portal group produced only
84.229/107.110/164.211 mm detours, also unadopted. The first follow-up invocation
used a wrong hierarchical LED_BLANK name and exited before writing; the corrected
invocation completed. These attempts do not prove that shorter routes are impossible.

A source-bound diagnosis kept all pads, holes and keepouts but ignored existing
tracks/vias to identify control escape obstructions; it emits no routed board.
A subsequent LED_XLAT trial removed only three declared blocking tracks and
tried both restoration orders. Its escape was legal and CONTROL_22 could be
restored through 5.178500 mm, but LED_MOSI could not be restored within the
bounded search. No candidate was emitted and the accepted board is unchanged.

The whole-unit inventory links this 41-open unselected comparison and preserves
the validated audio-main-watchdog-repack-01 at 216 opens, the selected four-layer
DC04 at 143 opens and negative protection at 138 opens/two explicit isolated
ground warnings. Thirty-four LED outputs and seven other digital nets remain
open. Exact approved ESS package/interface data, real stack/process acceptance,
installed receiving, complete routing and electrical/thermal/fault qualification,
inspected manufacturing outputs and a current first-article package remain
unfinished. No fabrication release, supplier message, order, commit, physical
measurement or native Mac CAD launch occurred. The overall goal remains active.

## 2026-11-03 — R1040 pot-input relocation, 40 digital opens

Completed digital-pot-filter-native-01 from the 41-open exact-region parent.
Native KiCad 10.0.7 reports 40 opens across 40 nets, zero geometry/parity/ERC
findings and all checking categories enabled. POT_ADC_09 is now connected.
R1040 moves from F(70,30) mm to B(40.5,35.5) mm at 90 degrees using the captured
native R1040-B-90 template. Its 1k 1% value, land, terminal assignments and
identity are preserved. U1001, C1020, R1050 and every other footprint remain exact.

The accepted construction is digital-pot-filter-repack-04. Twenty-five new
0.20 mm segments and four 0.60/0.30 mm vias replace only the old 3.479606 mm
POT_RAW_09 spur. Every other copper object is retained. The new raw branch is
40.853117 mm/one via; the new ADC branch is 29.221499 mm/three vias. Final totals
are 2,768 tracks/480 vias. Raw copper increases from 41.862898 mm/three vias to
79.236409 mm/four vias; ADC branched copper increases from 24.562514 mm/one via
to 53.784013 mm/four vias. Both nets are now fully connected. These lengths are
routing evidence, not acceptance of settling, coupling/noise, off-board loading,
reference transitions or installed performance.

Nearby front-side translations screened 5,785 poses, found 49 pad-clear poses,
and tried 32 without accepting the roughly 163 mm ADC detours. Native template
searches screened 35,624 front/back/orientation poses and found 300 pad-clear
poses. The ADC-first 25 mm target and a two-pose relaxed follow-up did not restore
both nets. Trial 04 sampled distinct placement regions and routed the raw side
first; the tenth attempt restored both nets with the existing raw route retained.
Trial 05 instead retired all raw-input copper in a temporary search but could
not reconnect both nets; it emitted no candidate. All five searches completed.
The first constructor invocation failed a numeric-token assertion before any
output; parsing the stored coordinates as floats corrected that check.

Native capture, connectivity and all-eight-layer plots are complete. The
independent placement/drill/SD/plane audit includes the R1040 native template
and its actual relocated pad copper. Conditional AP04 receiving passes for 138
electrical parts and five mounts. All 201 power/ground pads, 39 local connections,
33 thermal branches, four physical plane unions and 5.999 mm SD spread/one via
per signal survive. Minimum non-exempt drill-to-SMD gap remains 0.154984 mm;
21 mask-covered heat-spreader vias retain their process hold. Every net record
except POT_RAW_09/POT_ADC_09 remains exact.

All eight copper plots and two 1200 dpi placement details were inspected.
The exact-delta audit replays the complete parent evidence, checks the sole
native footprint transformation and retired spur, verifies every new segment
and via against the recipe and actual geometry, and proves all earlier pad
groups are preserved. Its source-bound receipt passes. All 62 focused tests
pass, including four R1040 regression cases that reject unrelated changes,
undeclared raw-copper retirement and resistor pin-net swaps.

A follow-up bounded search on CONTROL_26, LED_XLAT, LED_BLANK, SERIAL_0,
SERIAL_1 and BYPASS_SENSE completed with zero joins. Their escape bottlenecks
still need coordinated work; searches do not prove that no shorter route exists.
Thirty-four LED outputs and those six control nets remain open. The accepted
40-open comparison remains unselected; selected DC04/AP04 and the validated
216-open audio/138-open negative-protection sources are preserved. The complete
15-role inventory has no missing source files. Approved ESS package/interface
data, final routing, real stack/process acceptance, actual installed receiving,
electrical/thermal/fault qualification, inspected manufacturing outputs and a
current first-article package remain unfinished. No fabrication release, order,
supplier message, commit, physical measurement or native Mac CAD launch occurred.
The overall goal remains active.

## 2026-11-03 — LED_22/control repair, 39 digital opens

Completed digital-led-control-native-01 from the 40-open pot-filter parent.
Native KiCad reports 39 opens across 39 nets, zero geometry/parity/ERC findings
and all checking categories enabled. LED_22 now connects U3001.27 to J3002.2
through 53.882095 mm/one via. Rebuilding the complete CONTROL_02 and CONTROL_12
nets frees this escape while preserving both control connections. CONTROL_02
changes from 17.691978 mm/two vias to 17.621360 mm/one via; CONTROL_12 changes
from 29.911584 mm/four vias to 24.616400 mm/one via.

The construction retires 19 tracks and six vias, adds 24 tracks and three
0.60/0.30 mm vias, and retains every component pose and all unrelated copper.
All new tracks are 0.20 mm wide. Final totals are 2,773 tracks and 477 vias.
The exact-delta audit replays the full parent chain, verifies all new geometry,
proves every earlier pad group survives and all unrelated net records are exact.
Its source-bound receipt passes. All 66 focused tests pass, including four
new delta cases. All eight copper plots and two 1200 dpi details were inspected.
Conditional AP04 receiving passes for 138 parts/five mounts. All 201 power/ground
pads, 39 local connections, 33 thermal branches, four plane unions, 5.999 mm SD
spread/one via per signal and the earlier drill/process evidence survive.

Obstruction diagnoses retained all pads, holes and keepouts while temporarily
omitting declared track/via classes to identify candidates; these were not
accepted boards. The actual-board diagnostic search produced zero joins.
Paired LED_12/13 and LED_55/54 repairs found no mutually compatible local escape
pair and emitted no candidates. The successful CONTROL_02/12 repair restores
all affected nets before emission. A subsequent bounded search on neighbouring
LED_17/18/19/20/21/23 produced zero joins.

A separate pinned, isolated eight-layer Freerouting trial allowed 133 LED/control
nets to move while protecting other copper. Its internal time limit ended the
search after one pass, with a written session and process exit 0; its own
exchange-model incomplete count stayed 58 and the 252 pre-existing exchange
clearance findings stayed unchanged. These are not native KiCad findings.
The result was not imported or adopted. Unrun import/merge helpers were removed.
All launched searches and native checks are terminal; evidence is retained in
routing-search-review.json. The bounded searches do not establish impossibility.

The 39-open comparison remains unselected. Thirty-three LED outputs and six
control nets remain open. Selected DC04/AP04 and the 216-open audio/138-open
negative-protection sources remain unchanged. Approved ESS package/interface
data, complete routing, accepted physical stack/process, installed receiving,
electrical/thermal/fault qualification, inspected manufacturing outputs and a
current first-article package remain unfinished. No fabrication release, order,
supplier message, commit, physical measurement or native Mac CAD launch occurred.
The overall goal remains active.

## 2026-11-03 — All front control inputs connected, 38 digital opens

Completed digital-control26-native-01 from the independently replayed 39-open
LED/control parent. Native KiCad reports 38 opens across 38 nets, zero geometry,
schematic-parity and ERC findings, with all checking categories enabled. All
32 front button/selector input nets are now connected. Thirty-three LED outputs
and five interfaces remain open: SERIAL_0, SERIAL_1, BYPASS_SENSE, LED_BLANK and
LED_XLAT. Selected four-layer DC04 and AP04 remain unchanged.

The accepted development comparison reconstructs CONTROL_22, CONTROL_25 and
CONTROL_26 together. It reserves three conventional via escapes before routing
any net globally, then routes each local lead around the other reserved vias.
Static precomputed escape paths yielded no compatible triples, but recomputing
these paths with reservations finds valid local routes. Complete global routes
still require a longer path. The earlier 75 mm global-route search target was a
planning preference, not an electrical requirement. A separate explicitly named
complete comparison used a 110 mm global-branch ceiling; it did not relax native
copper, clearance, drill, placement or circuit rules. This is retained routing
progress, not electrical-performance acceptance.

CONTROL_22 shortens from 50.937459 to 47.163137 mm with three vias. CONTROL_25
shortens from 39.008122 mm/five vias to 37.414908 mm/three vias. CONTROL_26 replaces
an isolated 0.037760 mm stub with 113.643545 mm/four vias. Its global branch is
103.738545 mm, plus 9.905 mm of local escape. The circuit contract identifies
these as slow digital switch/selector inputs, not analog pot inputs. Input
settling, noise immunity, harness loading, scan behaviour and EMC/ESD remain
unqualified; the longer CONTROL_26 route remains an explicit tradeoff and a
candidate for shortening.

The construction retires 39 tracks/eight vias and adds 98 tracks/ten vias,
ending at 2,832 tracks/479 vias. New tracks are 0.20 mm wide and vias are
0.60/0.30 mm. Every component pose and all unrelated copper remain exact.
The independent exact-delta audit replays all parent checkpoints, proves no
prior pad group regresses, verifies all new geometry and confirms unchanged
records for every other net. All 70 focused tests pass. All eight copper plots
and two 1200 dpi details were rendered and inspected. Conditional AP04 receiving
passes for 138 parts/five mounts. All 201 power/ground pads, 39 local connections,
33 thermal branches, four physical plane unions and 5.999 mm SD spread/one via
per signal survive. Minimum non-exempt drill-edge-to-SMD gap is 0.154984 mm;
21 mask-covered heat-spreader vias retain their process hold.

Three LED_46/47 permit/control repair trials emitted no candidate: local repair
required a 157.694 mm CONTROL_20 detour, full-net replacement required 116.327 mm,
and a shared-via repair found no complete connection. The permit branch itself
could be restored in 4.684 mm. The first full-net invocation failed an incorrect
expected object-count assertion before output; the actual capture has 22
CONTROL_20 copper objects plus three permit-branch objects, and the corrected
constructor is source-bound. A fresh remaining-pad obstruction diagnosis retains
all pads, holes and keepouts while ignoring declared existing copper only for
candidate discovery. It is not a routed board. An LED_39 trial restored its
blocking CONTROL_20 segment in 3.1 mm, but failed global LED connection and
emitted no candidate.

The greedy CONTROL_26 repair, static joint-escape trial, 112-combination reserved
escape trial and 24-region-diverse trial all ended without a candidate within
their shorter-route targets and bounds. The separate complete comparison
succeeded and passed native and independent review. All processes are terminal;
the source-bound search record retains all nine construction receipts and the
remaining obstruction diagnosis. Bounded searches do not prove no shorter route
exists. No native Mac CAD, physical measurement, supplier message, order, commit
or fabrication release occurred.

The whole unit remains unfinished: audio routing at 216 opens, negative
protection at 138 opens/two explicit isolated-ground warnings, remaining digital
routing, approved ESS package/interface data, accepted stack/process, actual
installed receiving, electrical/thermal/fault qualification, inspected
manufacturing outputs and a current first-article package remain open. The
full objective remains active.


## AC04 settling supervisor and local pull-up completion

U208, C224 and C227 move into freed receiving space, and R204 moves beside the driver. Two new native control joins and CT timing reduce opens from 216 to 213; twelve targeted control opens remain. The corrected board has zero geometry/ERC findings, one explicit missing-codec parity finding and no ignored categories. All 138 local pairs, seventeen earlier control pairs, fifty earlier global-control joins, the earlier watchdog timing pair, all 200 grounds and 161 rail/sense pads remain connected. Actual copper totals 2321 tracks and 371 conventional vias; the minimum actual drill-to-SMD gap is 0.169980855 mm and In1 area is 8043.593905 mm². The isolated 10.072972652 mm, 0.20 mm U208.1 SENSE branch is checked against a 12 mm limit; ordinary VDD/pull-up feeds retain short entries. The fixed TPS389033 sense-current limit is 8 µA at the stated 5 V test condition, distinguished from the adjustable variant’s 100 nA; the 20 µA/0.16 mm finished width/18 µm copper/125 °C illustration gives a maximum trace-only drop near 2.03 µV. These remain unapproved assumptions and exclude via loss, noise and fault qualification. The first native trial found 0.15 mm capacitor-to-via clearance; a 0.07 mm cell shift corrects it while retaining body clearance. Compact rejected-source/findings diagnostics replace duplicate board exports. All four actual copper-layer views were inspected. Missing ESS data, remaining routing and complete installed/process qualification remain open. No native Mac CAD launch, supplier message, upload or board order was made.


Validation passed: fourteen focused supervisor/replay tests, twenty fabrication evidence/geometry tests and twenty-three CAD integration tests (57 checks). The latter two suites were rerun after readiness regeneration completed. Ruff passed for the new Python sources and focused tests. These checks do not qualify installed electrical performance or release manufacturing outputs.


## AC04 additive codec-run and timer-ready completion
Two additive codec branches close CODEC_RUN and the remaining TIMER_OK receiver. Native Linux KiCad 10.0.7 reports 211 opens, zero geometry/ERC findings, one explicit missing-U201 parity finding and no ignored categories. All 138 explicit local pairs, seventeen earlier control pairs, fifty-two earlier global joins, both private timing pairs, all 200 grounds and all 161 source-connected rail/sense pads survive. Tracks/vias total 2354/377. The new paths measure 53.862/40.544 mm and use three conventional vias each; all six new vias join at least two routed faces. Every existing pose, copper object and authored zone remains exact apart from native fill. All 930 actual native pad polygons match the parent capture. Ten targeted control opens remain.

The independent additive replay checks complete physical terminal witnesses, route continuity, length/via budgets, protected analog regions and drill-to-SMD screening. Ten focused mutation/replay tests, twenty fabrication evidence/geometry tests and twenty-three CAD integration tests pass (53 checks). Ruff passes for the new scripts and focused tests. All four actual copper-layer plots were inspected. Length/via construction checks do not establish installed loading, return impedance, timing, coupling, EMI or fault qualification. Remaining routing, ESS package/interface inputs, parts/mechanical receiving, electrical/thermal/process acceptance, inspected manufacturing outputs and a bounded first-article plan remain open. No native Mac CAD, supplier contact, upload or board order occurred.


## Off-grid conventional vias complete the latch input: 38 to 37 opens

The separate eight-layer `digital-xlat-bridge-native-01` comparison connects
LED_XLAT while preserving all parent copper, component poses and circuit mapping.
Native checks report 37 opens and zero geometry/parity/ERC findings with every
rule category enabled. The addition is 54 tracks and eight conventional vias,
134.523696 mm of new copper; total input-net copper is 136.357755 mm. The complete
board contains 2,886 tracks and 487 vias. All 32 front switch/selector inputs,
201 power/ground pads, 39 local connections and 33 thermal branches survive.
Independent additive checks preserve every previous pad group and unrelated net.
All four physical plane unions, the 5.999239 mm SD spread/one via per SD signal,
0.154984 mm minimum non-exempt drill-to-SMD gap and 21 EP process holds remain.
Conditional receiving passes for 138 parts and five mounts. Eight complete
copper plots and two 1200 dpi details were inspected.

The new search adds actual legal via points in connected via regions missed by
the regular grid. Each layer lead is independently screened; no routing rule is
relaxed. Four focused tests verify actual off-grid use, blocked-via rejection,
disconnected-face rejection and a same-face path without unnecessary vias. The
extended-radius helper adds three tests for distant real access, disconnected
regions and drill obstacles. All 77 focused regression tests pass.

The first invocation used incorrect SERIAL net prefixes and stopped at the
open-net assertion before emitting a board or receipt. Corrected names match the
capture. The eight-net off-grid trial then found a 134.524 mm latch route, down
from the prior 198.782 mm attempt, but rejected it at its 90 mm planning target.
A separately named complete comparison explicitly allows 140 mm and emits that
route. These search targets are not verified electrical limits. The eight vias,
long detour, timing, capacitive loading, ringing and reference transitions remain
unqualified and require review; shortening remains desirable.

Both joint MOSI/XLAT escape trials found only incompatible shared via pockets,
even with the local search radius enlarged from 8 to 16 mm. The LED_33/34 trial
found 30 compatible local pairs and made 35 bounded routing attempts without a
complete acceptable pair. Both buffer-channel feasibility probes tested four
matched A/B swaps in two route orders; no complete proposal met their limits.
Neither probe emitted a schematic or PCB, and no channel reassignment is adopted.
The new latch connection retains the original U3005 mapping. These bounded
failures do not prove alternate layouts or shorter routes impossible.

The whole unit remains unfinished. The newer audio control checkpoint at 211
opens is preserved (superseding the 213-open settling checkpoint observed at the
start of this review); negative protection remains at 138 opens/two isolated-ground
warnings. Digital still has 33 LED output nets and four interface nets open.
Approved ESS package/interface data, actual stack/process, installed assembly,
electrical/thermal/fault qualification and a current first-article package remain
outstanding. The selected four-layer DC04 baseline remains unchanged and no
fabrication release, supplier message, upload, order or commit occurred.

The full latch checkpoint replay passed. Final validation checked 2,180 transitive
source-hash bindings across 210 evidence receipts, plus 211 unit-scope hashes
covering 15 functional roles with no missing source files. Review links resolve
and `git diff --check` passes. All routing/native/audit processes for this work
are terminal; the full-unit goal remains active.


## AC04 longer controls with fewer plated transitions
Two further additive branches close BYPASS_SENSE and ADC_BIAS_WINDOW_OK. Native Linux KiCad 10.0.7 reports 209 opens, zero geometry/ERC findings, one explicit missing-U201 parity finding and no ignored categories. All 138 explicit local pairs, seventeen earlier control pairs, fifty-four earlier global joins, both private timing pairs, all 200 grounds and all 161 source-connected rail/sense pads survive. Every earlier pose, copper object and authored zone remains exact apart from native fill. All 930 actual native pad polygons match the parent. Tracks/vias total 2401/380; In1 area is 8036.378836 mm². New drill-to-SMD gap is at least 0.170 mm; the retained all-via minimum remains 0.169980855 mm.

The earlier coarse paths required six/five/six new vias for bypass sense, bias window and ANALOG_OK, and no board was emitted. The subsequent bounded search uses a stronger penalty for plated transitions and emits 113.773760837 mm/one-via bypass sense and 76.433368127 mm/two-via bias-window routes. All existing four-new-via, length, width, clearance, reference and protected-region construction checks remain unchanged. The 47 added tracks are 0.20 mm wide; three added vias are 0.60/0.30 mm and each joins at least two routed faces. ANALOG_OK remains unsolved within this search. Compact rejection diagnostics replace superseded owned draft scripts and duplicate proposals. The selected final proposal is independently source-bound and replayed before accepting the actual copper.

Ten focused mutation/replay tests, twenty fabrication evidence/geometry tests and twenty-three CAD integration tests pass (53 checks); Ruff passes for the new source and tests. All four actual copper-layer views were inspected. These longer paths remain unqualified for installed loading, timing, return impedance, coupling/noise/EMI and fault behaviour. Eight targeted control opens and other global routing remain. ESS package/interface inputs, full installed electrical/thermal review, mechanical/parts receiving, process acceptance, inspected manufacturing outputs and a bounded first-article plan remain open. No native Mac CAD launch, supplier contact, upload or board order occurred.


## Three additive LED closures: 37 to 34 opens

The previous goal turn made verified progress by completing LED_XLAT. This turn
revalidated that source-bound checkpoint and swept all 33 remaining LED output
nets with the off-grid-via search. It completed LED_49 at 80.052736 mm/five vias;
ten other found routes exceeded the 100 mm planning target. The LED_49 native
intermediate has zero geometry/parity/ERC findings and 36 opens. Its native
capture, rather than an assumed in-memory board, feeds the next search.

A separate LED-only complete comparison uses a 180 mm search bound and closes
LED_39 at 133.676339 mm/five vias and LED_33 at 150.675614 mm/four vias. Other
attempts exhaust their available paths/bounds after those additions; the trials
do not prove shorter or coordinated routes impossible. Both length ceilings
are explicitly search guards, not electrical acceptance limits. The long paths
retain current/headroom, PWM coupling, harness and EMC qualification holds.

The combined construction verifies both additive deltas and exact native
intermediate geometry. Final `digital-led-sink-native-01` has 34 opens and zero
native geometry/parity/ERC findings with all categories enabled. Its 170 added
0.20 mm tracks and fourteen 0.60/0.30 mm vias bring totals to 3,056 tracks and
501 vias. All parent copper, component poses, pin assignments and zone definitions
remain exact. No channel reassignment or power-feed edit is adopted.

A read-only LED_35 local-access investigation temporarily omitted the declared
1.0 mm R1001 supply spur only for discovery. A follow-up checks every obstacle
polygon at full power-track width, because the legacy surface screen's fixed
0.5 mm tree query is insufficient for a 1.0 mm trace. It rejects the apparent
restoration at (33.505560,22.123882). A second escape point at
(33.444941,22.040900) is legal against the completely original copper and does
not require editing that supply spur. No PCB was emitted by this diagnostic.
The retained R1001 feed remains 1.0 mm wide and 1.2 mm long. This diagnostic does
not establish a completed global LED_35 route.

Independent additive and physical checks preserve all earlier pad groups,
201 power/ground pads, 39 local connections, 33 thermal branches, all 32 front
switch/selector inputs and every unaffected net record. All four physical plane
unions remain connected. SD spread stays 5.999239 mm with one via per signal;
minimum non-exempt drill-to-SMD gap stays 0.154984 mm. The 21 mask-covered
heat-spreader vias retain their process hold. Conditional receiving passes for
138 components and five mounts. All eight complete copper plots and three
1200 dpi details were rendered and inspected.

All 81 focused tests pass, including four new checks rejecting changes to an
existing power feed, reassignment of new LED copper and reduced via drill size.
Thirty LED output nets and four digital interface nets remain open. The newer
audio controls checkpoint at 209 opens is preserved; negative protection remains
at 138 opens with two explicit isolated-ground warnings. Approved ESS data,
actual stack/process, installed assembly, qualification and the current
first-article package remain unfinished. Selected four-layer DC04 is unchanged.
No supplier message, upload, order, commit or fabrication release occurred.

The complete three-LED checkpoint replay passed. Final validation checked 2,236
transitive source-hash bindings across 217 evidence receipts and 213 unit-scope
hashes over 15 functional roles, with no missing source files. Review links
resolve and `git diff --check` passes. The source-bound LED_35 probe rechecks
both discovered points against the latest 34-open native capture: the first
via is illegal, while (33.444941,22.040900) and its direct front lead remain
legal with all original power copper present. Global LED_35 closure is still
unproven. Every process started for this review is terminal. The full-unit goal
remains active.


## AC04 ANALOG_OK closure and bypass space survey
The remaining ANALOG_OK receiver now connects through an additional 122.441215269 mm/two-via branch. Native Linux KiCad 10.0.7 reports 208 opens, zero geometry/ERC findings, one explicit missing-U201 parity finding and no ignored categories. All 138 explicit local pairs, seventeen earlier control pairs, fifty-six earlier global joins, both private timing pairs, all 200 grounds and all 161 source-connected rail/sense pads survive. Every earlier pose, copper object and authored zone remains exact apart from native fill. All 930 actual native pad polygons match the parent. Tracks/vias total 2425/382; In1 area is 8034.714948 mm². The new drill-to-SMD minimum is 0.285067631 mm and the retained all-via minimum remains 0.169980855 mm. Seven targeted control opens remain.

Reversing search orientation finds this route without changing the width, clearance, four-new-via or length construction limits. A follow-on bounded search found no additional paths and emitted no separate board; compact diagnostics replace its superseded owned draft. Ten focused mutation/replay tests, twenty fabrication evidence/geometry tests and twenty-three CAD integration tests pass (53 checks). Ruff passes for the new source and tests. All four actual copper views were inspected. Earlier published revisions' runs 41545381635, 41546380414 and 41548057948 completed successfully on all five jobs; that does not substitute for the new revision's CI.

A separate native capture of the 208-open board freezes 3737 objects/44 native control islands for bypass rework. The source-bound survey finds four preliminary locations for U605/C606 in unused space: supervisor centres (100,4), (105,4), (110,4) and (112,5) mm. All pass the receiving, foreign-copper and relocated-ground-via screens, with an approximately 0.170 mm SMD drill gap. The (95,4) option fails a moved-support-copper clearance check. Intended moved AGND spurs are excluded from the new-hole obstacle test while every solder land and other-net conductor remains screened; unchanged-centre acceptance is not used for the relocated hole. No CAD candidate is emitted or selected by this survey. Replacement source/sense and control connections, full native checks and complete installed receiving remain unfinished; the selected board retains its exact earlier placements and housing allocation.

The longer ANALOG_OK route remains unqualified for installed loading, timing, return impedance, coupling/noise/EMI and fault behaviour. Remaining routing, ESS package/interface inputs, whole-unit electrical/thermal review, parts/mechanical receiving, process acceptance, inspected manufacturing outputs and a bounded first-article plan remain open. No native Mac CAD launch, supplier contact, upload or board order occurred.

## Digital retained-copper diagnosis and continuous-path rework comparison

The latest fully audited eight-layer digital comparison remains at 34 opens;
no follow-up route is adopted. The selected four-layer DC04 is unchanged.
The newer audio-main-controls-06 checkpoint at 208 opens is preserved.

Known LED_35 escape trials at 0.10 and 0.05 mm grid spacing, eight further
fine-clearance LED searches, the LED_39 shortening attempt and the control-track
omission diagnostic do not produce an adoptable repair. Two alternative
LED_35/39/33 sequences from the 36-open intermediate each complete only two
of the three nets. Neither is substituted for the current board. Sixty-four
LED_34/35 joint-escape attempts also fail to restore both nets.

A source-bound polygon-region graph removes dependence on the routing grid.
Both retained-copper LED_35 checks are disconnected: the standard track-margin
case has 355/283/175/304 surface components on F/In3/In5/B, while the 0.001 mm
track-margin diagnostic has 359/293/178/311. Native clearance rules remain
unchanged. These findings apply to the declared buffered planning geometry;
they do not establish infeasibility at every native-minimum geometry or after
relayout. Pairwise via-region intersections account for track-only restrictions,
and constructive polygon differences verify component containment.

A read-only survey retains every pad and zone while separately omitting copper
on LED_33, LED_34, LED_32, DAC_DATA, POT_ADC_05 and MCU_PERMIT. Each single-net
omission creates potential region connectivity, as do three grouped comparisons.
This does not restore omitted connections or prove joint new-via spacing.
DAC_DATA is the smallest surveyed route: three tracks and one conventional via.

Two-track and full-DAC raster detours fail. A new constrained-triangulation
path finder then finds the continuous corridor that the raster misses, with
all output segments independently screened. Its 248.933718 mm LED_35 path is
rejected at the 180 mm planning bound. Combining that local escape with a
multilayer tail reduces the LED path to 165.781025 mm, but the DAC_DATA repair
then fails. Reversing the order restores DAC_DATA through 13.321877 mm but
blocks the tested LED corridor. None of the four DAC repair trials emits a
PCB. The next useful comparison must reserve space for both signals together
or evaluate coordinated local placement changes; all previous connectivity
must survive before any candidate is adopted.

An independent actual-copper check covers all 170 tracks added by the retained
34-open checkpoint. Its minimum foreign-net edge gap is 0.210038974 mm against
the unchanged 0.20 mm rule. All 92 earlier focused tests pass, followed by four
new polygon-path checks covering narrow bent passages, holes, disconnected
regions and rejection by the independent clearance screen: 96 checks total.
The previous pending test output was unavailable after context recovery; an
exact process check found no running instance before the 92-test batch was
rerun with its output captured. All processes started for this follow-up are
terminal. Existing board geometry, power-feed width, component poses and native
rules are unchanged. The follow-up receipt is
staging/digital-led-sink-native-01/routing-search-followup-review.json.

Remaining digital/audio/negative-protection routing, ESS package/interface data,
actual stack/process, installed assembly, electrical/thermal/fault qualification
and the current first-article package remain unfinished. No supplier message,
upload, order, commit or fabrication release occurred. The full-unit goal
remains active.

Final follow-up verification passes 2,453 transitive source-hash bindings
across 222 source-bound receipts and all 213 current unit-scope source hashes
for fifteen functional roles. No sources are missing. Review links, new-module
syntax and `git diff --check` pass. Every owned routing/test session has returned
a terminal result; an optional final process-inventory query was unavailable
because the system process-list service could not be accessed.

## LED_35 closure through coordinated DAC_DATA and POT_ADC_05 repair

The previous goal turn was diagnostic progress: it established a continuous
LED route but no complete DAC restoration. This turn completes the three-net
repair. The new digital-led35-dac-pot-native-01 comparison has 33 opens,
zero native geometry/parity/ERC findings and every native rule category enabled.
The selected four-layer DC04 remains unchanged.

A new planned-copper region adapter includes the full 0.30 mm radius of each
proposed via plus the 0.31 mm track-centre clearance. It replaces an understated
via buffer in a prior unadopted diagnostic; independent segment checks and
native rules were not relaxed. Four new adapter tests cover full-diameter via
obstacles on both surfaces, track-layer separation, mutual via spacing and
independent segment rejection.

Continuous-region diagnosis confirms that the tested LED's In3 branch isolates
DAC_DATA. The first LED lead/via alone leaves DAC_DATA accessible. Native R1014
orientation templates and a 14,040-pose local survey identify 714 mechanical
and 78 copper/drill-clear poses, but none has output access with the tested LED
route retained. The bounded 25-attempt placement comparison emits no candidate.
Restoring DAC_DATA first also leaves LED_35 disconnected in the declared region
model. No component move is adopted.

Ten nearby signal-track omission comparisons identify potential access through
POT_ADC_05, LED_32, LATCH_5V or MCU_PERMIT rework. The successful construction
retires all three DAC_DATA tracks and its via, plus seven contiguous POT_ADC_05
tracks between retained vias. It adds 71 tracks at 0.20 mm and eight
0.60/0.30 mm vias. LED_35 now spans 165.781026 mm/six vias. DAC_DATA changes from
13.961704 to 14.109765 mm and retains one via. The replacement pot branch is
15.987316 mm/one new via; total POT_ADC_05 changes from 60.259712 mm/three vias
to 59.958042 mm/four vias. The board totals 3,117 tracks and 508 vias. Every
component pose, pad assignment, unretired copper object, outline, mount and
authored zone remains exact, including the 1.0 mm processor supply feed.

The complete independent replay passes, including all earlier parent evidence,
exact removal/addition and route reconstruction checks, restored pad groups,
unchanged unrelated net records and new-via clearances. The minimum screened
foreign-net edge gap among the 71 new tracks is 0.210065628 mm against the
unchanged 0.20 mm rule. All 201 power/ground pads, 39 local connections,
33 thermal branches and 32 switch/selector inputs remain connected. Four
actual plane unions remain connected. SD spread is 5.999239 mm with one via per
signal; non-exempt drill-to-SMD clearance remains 0.154984 mm. The 21 mask-covered
heat-spreader vias retain their process hold. Conditional receiving passes for
138 components and five mounts. All eight copper plots and four 1200 dpi details
were inspected.

The focused suite passes 106 tests. Six new delta checks include rejection of
an undisclosed supply-feed edit, pad reassignment, new LED copper reassignment,
a reduced via drill and missing pot-repair evidence. An initial mutation test
encountered an unconnected mounting pad while finding its fixture; that test
selector was corrected before the complete passing run. No PCB rule or
acceptance condition was changed to make the tests pass.

A source-bound survey of the remaining 29 LED output nets includes existing
same-net via crossings and finds zero connected paths in the retained-copper
planning geometry. These are buffered-planner findings, not proof that every
native-minimum geometry or relayout is impossible. They direct subsequent work
toward coordinated escape/copper changes or separately checked planning-margin
comparisons rather than repeated identical additive grid searches. Four other
digital interface nets remain open. The latest audio checkpoint at 208 opens
and negative-protection checkpoint at 138 opens remain preserved.

LED current/headroom, PWM coupling, harness effects and EMC remain unqualified;
DAC timing/source damping and pot settling/noise require electrical review.
Approved ESS package/interface inputs, actual stack/process, installed assembly,
electrical/thermal/fault qualification and the current first-article package
remain unfinished. No supplier message, upload, order, commit or fabrication
release occurred. Every process for this routing checkpoint is terminal, and
the full-unit goal remains active.

Final checkpoint verification passes 2,756 transitive source-hash bindings
across 239 source-bound receipts and all 213 current unit-scope source hashes
for fifteen functional roles. No sources are missing. Updated review links,
module syntax and `git diff --check` pass. The unit readiness report still
explicitly withholds fabrication release.

## LED_BLANK and CODEC_RUN joint comparison: 33 to 32 opens

The eight-layer comparison `digital-blank-codec-native-01` closes LED_BLANK
while fully reconnecting CODEC_RUN. Strict isolated Linux KiCad reports
32 opens, zero geometry/parity/ERC findings and every rule category enabled.
The selected four-layer DC04 is unchanged; this comparison is unselected.

The change retires one 43.038200 mm B.Cu CODEC_RUN segment and adds 65 tracks
at 0.20 mm plus ten 0.60/0.30 mm vias. The replacement CODEC_RUN section is
76.850866 mm with six new vias, adding 33.812666 mm. LED_BLANK gains
94.972629 mm/four vias. Total CODEC_RUN copper changes from
194.142539 mm/six vias to 227.955205 mm/twelve vias; LED_BLANK totals
106.202922 mm/five vias and all four pads now connect. The board contains
3,181 tracks and 518 vias. R1013 and its 2.587500 mm processor-side trace remain
exact, as do every other component pose, pad assignment, unretired copper
object, outline, mount and authored zone.

The independent delta audit replays the full parent chain and verifies no
regressed pad groups or changed unaffected net records. All 201 power/ground
pads, 39 local connections, 33 thermal branches and 32 front controls remain
connected. Four physical plane unions remain connected. SD spread stays
5.999239 mm with one via per signal. Minimum non-exempt drill-to-SMD clearance
stays 0.154984 mm, with 21 mask-covered heat-spreader vias retaining their
process hold. Actual new-track foreign copper clearance is at least 0.210 mm
against the unchanged 0.200 mm rule. Conditional receiving passes for
138 electrical parts and five mounts. Eight copper plots and three 1200 dpi
processor-corridor details were inspected. All 127 focused tests pass.

The preceding searches are retained in the source-bound routing-search review:

- At the 33-open parent, closer planning margins do not establish retained-copper
  access for the 29 LEDs or four remaining interfaces. Native rules are unchanged.
- Native R1013 orientation templates support a 23,688-pose placement scan:
  2,252 mechanical survivors, 170 pad-clear positions and 50 with optimistic
  separate access to both nets. Bounded routing comparisons make 64, 41 and
  93 net-order attempts without emitting a board. No R1013 move is adopted.
- Local omissions identify POT_ADC_02, CODEC_RUN and POT_RAW_09 as potential
  ways to free the R1013 endpoint. Omissions alone do not prove joint routing.
- POT_ADC_02 trials emit no board. A 101.472 mm BLANK route cannot be shortened
  using legal vertex shortcuts; when admitted for comparison, the displaced
  analog branch is not restored by the tested search. No analog-net change
  from these trials is adopted.
- CODEC_RUN reconstruction produces a complete pair. Its heuristic section
  limit expands from 65 to 80 mm solely for explicit native comparison, with
  the 33.812666 mm increase and six added transitions retained as electrical
  qualification items. No electrical acceptance is inferred from either bound.
- At 32 opens, a new survey still finds no region path for SERIAL_0, SERIAL_1
  or BYPASS_SENSE with either planning margin. The 29-LED region survey belongs
  to the 33-open parent and is not represented as a new 32-open survey.

The remaining digital opens are 29 LED outputs and three interfaces.
Timing, coupling, loading, return transitions and EMC remain unqualified.
Audio/NF routing, approved ESS package/interface inputs, actual stack/process,
installed assembly, electrical/thermal/fault qualification and the current
first-article package remain unfinished. No supplier message, upload, order,
commit or fabrication release occurred. The full-unit goal remains active.

Final verification checks 3,174 transitive source bindings across 261 source-bound
receipts, including the parent diagnostic history, and all 213 unit-scope
hashes for fifteen roles. No sources are missing. Review links, module syntax
and `git diff --check` pass. Every started routing, native and audit process
for this checkpoint is terminal.

## BYPASS_SENSE, signal restoration and thermal branch: 32 to 31 opens

The latest eight-layer comparison is `digital-bypass-ground-signal-native-02`.
It closes BYPASS_SENSE while restoring two CODEC_RUN and two LATCH_5V tracks
and relocating one external U3004 thermal via. Native Linux KiCad reports
31 opens and zero geometry/parity/ERC findings, with every category enabled.
The selected four-layer DC04 remains unchanged and the comparison unselected.

BYPASS_SENSE gains 76.102115 mm/four vias, reaching 98.693358 mm/five vias.
The CODEC_RUN replacement is 20.665919 mm with no new via; total copper becomes
241.606315 mm/twelve vias. The LATCH_5V replacement is 32.474658 mm/three vias;
total copper becomes 223.524163 mm/fifteen vias. Four signal tracks are retired,
59 tracks at 0.20 mm and seven 0.60/0.30 mm vias are added. The board contains
3,236 tracks and 525 vias.

The external ground via keeps UUID `1709749b-df70-5b29-a600-bf25408c657f` and
moves from (100,27) to (99.5,25.7) mm with its 0.60 mm copper/0.30 mm drill
unchanged. Ground track `c69d87f9-b134-552b-97be-347c7c20a818` retains 1.00 mm
width and now joins from (98,28) mm inside the unchanged exposed pad. Its
length increases from 1.000000 to 2.745906 mm. Thermal performance remains
unqualified. All component poses, pad assignments, undeclared copper, outline,
mounts and authored zones remain exact.

Independent replay of the full parent chain verifies every previous pad group
and every unaffected net record. All 201 power/ground pads, 39 local
connections, 33 thermal branches and 32 front controls remain connected.
All four physical plane unions remain connected. SD spread stays 5.999239 mm
with one via per signal. Minimum non-exempt drill-to-SMD clearance remains
0.154984 mm, and the 21 mask-covered heat-spreader vias retain their process
hold. The minimum actual foreign-net copper gap across new tracks and the
changed ground branch is 0.201342 mm against the unchanged 0.200000 mm rule.
Conditional receiving passes for 138 electrical components and five mounts.
Eight full copper views and four 1200 dpi details were inspected. All 145
focused tests pass, including nine new thermal/signal delta tests and
nine native-group target/unused-via/sampled-contact regressions.

The first native trial is explicitly rejected, not adopted: it retained
32 opens and two dangling-via warnings. A global search had selected its own
isolated source stub; a CODEC_RUN same-face junction also carried an unused
via. Native connection groups now exclude all same-group copper from targets.
Unused signal vias are removed only when no second connected copper layer or
ambiguous neighbouring barrel requires them. Regression tests cover both
failures and preserve real layer transitions.

The corrected bounded search made 18 net-order attempts without emitting a
board. With complete local repairs fixed, endpoint and sampled track-interior
region tests remained disconnected at the original planning margin. The
source-side escape reaches the large routing region; the remaining obstruction
was access to the header group. A 16-net local header omission survey identifies
ANALOG_OK as a potential alternative, but that omission is not adopted.
The tighter 0.001 mm planning margin instead exposes a complete 66.578448 mm
continuation to J1004.3, with unchanged native clearance rules. A source-bound
replay combines it with the local repairs and omits the unused vias; the full
native and independent audits then pass at 31 opens.

A fresh survey at the 31-open board samples both complete native groups,
including track interiors and existing conductive crossings. None of the
remaining 29 LED outputs or two serial-chain nets has retained-copper regional
access under the declared tighter planning geometry. This is bounded evidence
for further coordinated rework, not proof that all legal layouts are infeasible.

Signal timing/loading/coupling/return transitions/EMC, thermal performance,
physical stack/process and installed assembly remain unqualified. Audio/NF
routing, approved ESS package/interface inputs, electrical/thermal/fault
qualification and the current first-article package remain unfinished. No
supplier message, upload, order, commit or fabrication release occurred.
The full-unit goal remains active.

Final verification checks 3,508 transitive source bindings across 282
source-bound receipts and all 213 unit-scope hashes for fifteen roles.
Review links, module syntax and `git diff --check` pass. Every started
routing, native and audit process for this checkpoint is terminal.

## SERIAL_1: coordinated escape and restoration investigation

The previous turn's 32-to-31-open checkpoint remains authoritative. This turn
adds eighteen source-bound search receipts and a versioned zero-length-via-leg
routing fix. No new board was emitted or adopted. The source-side cut is
MCU_PERMIT copper; the receiving-side cut includes CLOCK_5V and LED_48. Two
CONTROL_30 front tracks conditionally open global serial access. A 0.05 mm
local via grid finds 102 compatible receiving-end triples and independently
replays eighteen distinct arrangements, correcting the sparse sample's zero
result. The original legal CLOCK/LED48 via positions were absent from that
sparse sample.

Subsequent searches identify LED_37 via 4c8ecf3b-d93e-5c05-82da-95ddc9eeb8d1
and LED_50 In3 track f1ea2e26-acf3-46e4-a518-bdb380e99c7e as additional
restoration obstructions. Trials explicitly require restoration of both nets.
Routing MCU_PERMIT/CLOCK/LED48 together blocks SERIAL_1 in tested geometry;
routing SERIAL_1 earlier blocks LED48. Full retained-component targets include
sampled track interiors. Failures are bounded, not global infeasibility proofs.
Serial-only proposals around 338 mm remain unqualified and unadopted.

The continuous-route helper now skips zero-length legs at reused vias before
calling the polygon router. Six tests cover strict source/destination via
behavior and the four prior route cases; seven new compatibility tests cover
track and through-via spacing. The focused 35-test suite passes. No native CAD
run is claimed this turn because no complete PCB candidate was constructed.

The detailed review records the invalid supply-pad-area probe and the exact
protected supply names used by the final cut-set reduction. The verified
31-open board and all 213 unit-source hashes remain unchanged. Final source
verification checks 3,823 bindings across 342 JSON records.
All started searches are terminal. Full-unit routing, approved ESS inputs,
physical stack/process, installed assembly and qualification remain unfinished.
No supplier message, order, commit or release occurred; the goal remains active.

Review: [SERIAL_1 investigation](staging/digital-serial1-repair-review-01/README.md).

## SERIAL_1: restoration conflicts and native resistor-placement search

Fifteen new terminal search/restoration receipts and two native Linux rotation
template receipts preserve this investigation. No complete PCB candidate was
emitted or adopted. The digital comparison remains at 31 opens; selected
four-layer DC04 remains at 143, audio at 208 and NF at 138.

Three DATA_5V_SRC back-layer tracks conditionally block the reserved serial
route. Removing them permits a 338.507 mm serial proposal but disconnects DATA.
Reconnecting DATA first blocks serial again; no directly reachable local DATA
via passes the 0.1 mm escape grid. LED37's separate access conflict follows the
proposed MCU_PERMIT routes. Complete retained-component probes confirm both.

Native resistor rotations on both faces support placement checks. None of
175 original or 102 northern back-side R3015 legal poses reaches the DATA
source. Its front-side grid supplies no pad-clear pose. A 9.206 mm MCU trunk
proposal retains the original LED37 via, but none of 364 back-side R1003 legal
poses reaches MCU_PERMIT, and its front grid has no mechanical placement.
These are bounded results, not global infeasibility proofs. The next repair
must reconsider paired local escapes rather than fix the same reserved routes.

The focused suite passes 46 tests, including eight new placement tests.
Recursive verification checks 6,714 source bindings across 717
JSON records; all 213 unit-source bindings remain unchanged. Two older NF test
bindings are stale; the current versions pass 10 tests in a new supplemental
log. The original 129-test receipt is preserved and is not claimed as rerun. Native template
work boards are not PCB candidates, and no native PCB acceptance is claimed.
All searches are terminal; routing, ESS inputs, physical stack/process, installed
receiving and first-article qualification remain unfinished. No release, order,
message or commit occurred. The full-unit goal remains active.

Review: [restoration and resistor placement](staging/digital-serial1-restoration-review-01/README.md).

## SERIAL_1: native source-preparation checkpoint

A coordinated LED37 via relocation and MCU_PERMIT rework now passes native
checks on an actual PCB: zero geometry/parity/ERC findings and 31 opens, all
checks enabled. The independent audit proves every native pad group preserved;
only the two declared nets change. Six tracks and two vias are replaced by
eighteen tracks and three vias. Component poses, authored zones and all other
copper remain exact. The future SERIAL_1 source escape passes a fresh native-
capture screen, but is not installed as dangling copper.

The preparation retains 201 power/ground pads, 39 local, 33 thermal and 32
front-control connections. Four plane unions remain connected. The closest
new-track/foreign-copper gap is 0.201383 mm; the nonexempt drill/SMD minimum
remains 0.154984 mm and SD spread 5.999239 mm. The 21 EP-via process holds
remain. All eight layers and four source details were visually inspected.
Thirty-eight tests pass, including seven packing and six mutation-boundary
tests. MCU_PERMIT grows from 53.190 to 77.919 mm and two to three vias; this
trade-off remains electrically unqualified. LED37 shortens slightly.

Recursive verification checks 6,907 bindings across 731 JSON
records. The two disclosed historical NF test mismatches are unchanged; all
213 current unit-source bindings match. The first new capture used relative
source paths; the second, unchanged native-board capture uses absolute paths
for the physical auditor. Both captures are preserved.

This is a development preparation checkpoint, with no reduction in opens and
no change to selected four-layer DC04. Receiving-end joint routing remains
under investigation. Audio/NF routing, approved ESS inputs, stack/process,
installed assembly and first-article qualification remain incomplete. No
order, release, commit or external message occurred. The full goal stays active.

Checkpoint: [native source preparation](staging/digital-serial1-source-preparation-native-01/README.md).

## SERIAL_1: receiving-area topology and alternate departures

Eight terminal searches/diagnostics follow the native source-preparation checkpoint.
Fresh 0.025 mm receiving escapes yield 292 spatial local packs; 32 were replayed
independently. Two-pack topology replay isolates mutual SERIAL_1/LED48
obstruction. Alternate layer departures and 17 farther-left CLOCK packs did
not yield a complete restoration. No new PCB was emitted or adopted.

All 42 focused tests pass. Recursive verification checks 7,112 bindings
across 741 JSON records, with only the same two historical NF test
mismatches. All 213 current unit-source bindings match. Comparison/selected
digital opens stay 31/143. The full unit remains unfinished; no release, order,
commit or external message occurred.

Details: [receiving-area review](staging/digital-serial1-receiving-review-01/README.md).

## SERIAL_1 closed: native-clean 30-open comparison

SERIAL_1 now closes in native KiCad: 31 to 30 opens, zero layout/parity/ERC
findings with all checks enabled. Starting CLOCK on its existing back-layer
via and LED48 on In3 avoids the extra CLOCK via that blocked the receiving
corridor. R3015 translates 0.25 mm right; all five restoration obligations and
both DATA branches are connected. Native feedback led to removal of one
redundant source via and an unused CONTROL30 branch. Footprint serialization
was corrected from native keyword tokens, without changing parsed geometry.

Independent auditing confirms every prior pad connection preserved, only
SERIAL_1 newly closed, and all unrelated net records exact. The delta removes
29 tracks/five vias and adds 94 tracks/eleven vias; the board has 3,313 tracks
and 532 vias. All four planes remain connected; 201 power/ground pads, 39 local,
33 thermal and 32 front-control connections are retained. Closest added-track
foreign copper gap is 0.201543 mm; nonexempt drill/SMD minimum remains
0.154984 mm. SD spread is 5.999239 mm and 21 EP process holds remain.

This is explicitly a connectivity checkpoint: SERIAL_1 is 340.912 mm with
eight vias; CONTROL30 grows from 53.336 to 196.563 mm, although its via count
falls from four to two. These long detours need optimization and electrical
qualification. The selected four-layer DC04 remains unchanged at 143 opens.

All 53 focused tests pass, including seven closure boundary checks and four
serialization checks. Eight layer plots and both four-layer detail sets were
visually inspected. Recursive verification checks 7,295 bindings across
754 JSON records, with only the two previously disclosed historical NF
test mismatches. All 213 current unit-source bindings match.

Remaining digital routing: SERIAL_0 and 29 LED outputs. Audio/NF routing, ESS
inputs, stack/process and installed/first-article qualification remain open.
No release, order, commit or external message occurred. The full goal remains
active. Next priority is shortening SERIAL_1 and CONTROL30 while preserving
the native-clean connectivity, followed by the remaining digital nets.

Evidence: [30-open checkpoint](staging/digital-serial1-closed-native-03/README.md).

## SERIAL_1 and CONTROL30: costed shortening checkpoint

The eight-layer comparison remains at 30 opens with zero native layout,
parity or ERC findings and all checks enabled. SERIAL_1 falls from 340.912 to
129.919 mm with eight vias retained. CONTROL30 falls from 196.563 to 132.458 mm
and two vias to zero. Every prior pad group is preserved. Only these two nets
change; all other net records, footprints, authored zones and board geometry
remain exact. The board now has 3,276 tracks and 530 vias.

The finite costed search measures actual planar paths and retains complete
incumbents. Earlier native via seeds were screened as extra candidates. The
two proposals were replayed together, an intermediate vertex was centered on
its own via, and CONTROL30's receiving return tail was removed. Two attempted
compact original-branch restorations emitted no candidate. These searches do
not prove global optimum or global infeasibility.

Independent actual-copper verification checks 54 added tracks and six new vias;
minimum measured nearby foreign-track gap is 0.201397 mm. All four planes remain
connected; 201 power/ground pads, 39 local, 33 thermal and 32 front-control
connections remain intact. Drill/SMD minimum is 0.154984 mm, SD spread 5.999239 mm,
and 21 exposed-pad process holds remain. Eight layers and four detail regions
were visually inspected. All 69 focused tests pass.

Recursive verification checks 7,606 bindings across 770 JSON
records, with only the same two historical NF test mismatches. All 213 current
unit-source bindings match. Selected four-layer DC04 stays at 143 opens.

The comparison still needs SERIAL_0 and 29 LED outputs. CONTROL30 retains a
perimeter detour and is still longer than its 53.336 mm pre-SERIAL_1-closure
route. Electrical, timing, EMC, installed and manufacturing qualification remain
open, as do audio/NF routing and ESS inputs. No release, order, commit or external
message occurred. The full goal remains active.

Evidence: [shortening checkpoint](staging/digital-costed-shortening-native-01/README.md).

## LED09: native-clean 29-open connectivity checkpoint

LED09 now closes in the eight-layer development comparison: 30 to 29 opens,
zero native layout/parity/ERC findings, with all checks enabled. Every prior
pad connection is preserved and only LED09's pad groups merge. LED02, LED39
and CONTROL13 were explicitly restored. All footprints, authored zones, board
geometry and unrelated copper are exact. The prior SERIAL_1/CONTROL30
shortening remains unchanged.

The change removes four tracks and one via and adds 40 tracks and four vias,
leaving 3,312 tracks and 533 vias. LED09 totals 195.907 mm with one via, a long
In5.Cu detour requiring optimization and electrical qualification. LED02 grows
69.729 to 70.820 mm with six vias retained. LED39 grows 133.676 to 133.826 mm
and five to seven vias. CONTROL13 changes 42.316 to 42.305 mm with four vias.

Independent auditing confirms all four actual plane unions connected; 201
power/ground pads, 39 local, 33 thermal and 32 front-control connections remain
intact. Minimum measured new-track foreign-copper clearance is 0.202481 mm;
nonexempt drill/SMD minimum remains 0.154984 mm. SD spread is 5.999239 mm and
21 exposed-pad process holds remain. Eight layers and two regions on all four
signal layers were visually inspected. Seven new boundary tests pass; the
parent's source-bound 69-test evidence is preserved.

Eleven diagnostic/construction receipts document the retained-copper survey,
failed LED70 fanout/serial-wall restoration, failed LED30 global access and
successful LED09 repair. The first LED09 proposal missed a retained LED39
obstruction; removing and explicitly restoring that segment enabled closure.
Finite searches do not prove global infeasibility or global route optimality.

Recursive verification checks 7,936 bindings across 789 JSON records, with
7,934 matching and only the same two disclosed historical NF test mismatches.
All 213 current unit-source bindings match. No existing sealed source receipt
was rewritten. Selected four-layer DC04 remains at 143 opens; audio has 208
and NF 138, with its two isolated-ground warnings preserved.

Continue with LED09 shortening and SERIAL_0 plus the remaining 28 LED outputs.
Audio/NF routing, approved ESS inputs, stack/process and installed/first-article
qualification remain outstanding. No release, order, commit or external message
occurred. The full-unit goal remains active.

Evidence: [LED09 checkpoint](staging/digital-led09-closed-native-01/README.md).

## LED09 shortening: 124.070 mm with native-clean connectivity

The previous turn made verified progress by closing LED09. This turn shortens
that net from 195.907 to 124.070 mm, a 71.837 mm reduction, retaining its single
via. The eight-layer comparison stays at 29 opens with zero native layout,
parity or ERC findings and every rule category enabled. Every native pad group
is exact. Only the In5.Cu LED09 chain changes; all other copper, the front
escape, vias, footprints, authored zones and board geometry remain exact.

The first screened shortcut candidate retained connectivity but produced one
native copper-sliver warning. It remains unadopted and its evidence is retained.
Keeping the original upper-turn vertices resolves the warning without relaxing
rules. Twenty-seven tracks are replaced by thirteen; the board has 3,298 tracks
and 533 vias. A perimeter detour remains and global shortest-path optimality
or electrical performance is not claimed.

All eleven focused tests pass (eight change-boundary tests and three shortcut
planner tests). Actual-copper checking measures at least 0.202481 mm nearby
foreign-track clearance. All four plane copper unions remain connected;
201 power/ground pads, 39 local, 33 thermal and 32 front-control connections
remain intact. Drill/SMD minimum is 0.154984 mm, SD spread 5.999239 mm, and
21 exposed-pad via process holds remain. Eight layer overviews and two In5.Cu
detail regions were visually inspected.

Recursive verification checks 8,083 bindings across 802 JSON records, with
8,081 matching and only the same two historical NF test mismatches. All 213
current unit-source bindings match. Both proposed geometries and the rejected
native result are retained and source-bound.

SERIAL_0 and 28 LED outputs remain open. Selected DC04 remains at 143 opens,
audio 208, NF 138 with its isolated-ground warnings. The user was asked where
manufacturer-approved ES9292QPRO package/land/stencil and final interface
requirements can be found; routing continues independently of that input.
Stack/process, receiving, installed and first-article electrical/thermal/EMC
qualification remain open. No release, order, commit or external message
occurred. The full-unit goal remains active.

Evidence: [shortened LED09 checkpoint](staging/digital-led09-shortened-native-02/README.md).

## LED10: native-clean 28-open checkpoint with CONTROL13 tradeoff

The previous turn made verified progress by shortening LED09. LED10 now closes
in the eight-layer comparison: 29 to 28 opens, zero native layout/parity/ERC
findings, with every check category enabled. Only LED10's pad groups merge;
every prior connection remains intact. CONTROL13's displaced layer change is
explicitly restored. All footprints, authored zones, board geometry and unrelated
copper are exact, including LED09, SERIAL_1 and CONTROL30 shortening.

LED10 totals 173.462 mm/four vias. CONTROL13 grows from 42.305 to 107.197 mm and
four to six vias; its replacement portion is 69.664 mm/three new vias. This is
an explicit unresolved length/loading/scan-performance tradeoff, not electrical
acceptance. The initial complete LED10 proposal used about 330 mm with a short
CONTROL13 restoration; the longer bounded search reduced LED10 length but forced
the longer control detour. Both raw proposals and their independently replayed
shortcut refinements are retained. The chosen geometry removes three tracks and
one via and adds 59 tracks/seven vias: 3,354 tracks and 539 vias total.

Local continuous one-via searches found no shared admissible region in three
windows, up to x=0.61..20 mm and y=10..32 mm. Multilayer searches restricted to
those windows likewise found no complete proposal. These bounded searches do
not establish global infeasibility or route optimality. Next, optimize the full
CONTROL13 net between J2001.14 (27.24,4.46) and U2001.7 (11.635,23.65), rather
than requiring restoration between the two old stub endpoints.

All eleven focused tests pass, including eight mutation-boundary checks and
three shortcut-planner tests. Independent actual-copper verification measures
at least 0.201024 mm nearby foreign-track clearance and rechecks seven new vias.
All four actual plane unions remain connected; 201 power/ground pads, 39 local,
33 thermal and 32 front-control connections remain intact. Drill/SMD minimum is
0.154984 mm, SD spread 5.999239 mm, and 21 exposed-pad process holds remain.
Eight layers and four detail regions on all four signal layers were visually
inspected. Recursive verification checks 8,320 bindings across 816 JSON records,
with 8,318 matching and only the two disclosed historical NF test mismatches.
All 213 current unit-source bindings match.

SERIAL_0 and 27 LED outputs remain open. Selected DC04 remains at 143 opens,
audio at 208, NF at 138 with its isolated-ground warnings. Approved ESS inputs,
stack/process, receiving, installed and first-article qualification remain open.
No release, order, commit or external message occurred. The full-unit goal remains active.

Evidence: [LED10 checkpoint](staging/digital-led10-closed-native-01/README.md).

## CONTROL13 full-net shortening and LED16 closure: 27 opens

The CONTROL13 search continued after the user pause and was polled to its terminal
result after the user asked to keep going; it was not restarted. The resulting
candidate reroutes the entire net between J2001.14 and U2001.7. CONTROL13 falls
from 107.197 to 40.498 mm and six vias to one, with every native pad group exact.
It is also shorter than its 42.305 mm/four-via route before LED10 closure.
Thirty-nine tracks and six vias become fifteen tracks and one via, leaving
3,330 tracks and 534 vias at the shortened checkpoint. Only CONTROL13 changes.

Native checks confirm 28 opens and zero layout/parity/ERC findings, all checks
enabled. Independent actual-copper checking measures at least 0.201248 mm nearby
foreign-track clearance. All eleven focused tests pass. Eight layers and two
regions on four signal layers were visually inspected. The shortening checkpoint
checks 8,465 source bindings across 826 JSON records, with only the two previously
disclosed historical NF test mismatches; all 213 current unit bindings match.

A fresh retained-copper survey finds individual potential access for LED13,
LED14 and LED16. All six sequential routing orders were tried, with complete
mutual-copper replay; each produced one connected net. LED16 was the shortest
successful route and is the adopted additive candidate. This finite search does
not establish a global one-route capacity limit or global optimality.

LED16 closes through 53.962 mm and one via: U3001.21 on F.Cu, around the lower
side of U3001, through a via near (6.521747,21.670815), then In5.Cu to J3002.8.
Twelve tracks and one via are added. Every original copper object, footprint,
authored zone and board geometry remains exact relative to the shortened parent.
The board now has 3,342 tracks and 535 vias. Only LED16's pad groups merge;
all prior connections remain intact, including CONTROL13, LED09 and LED10.

Native checks confirm 27 opens with zero layout/parity/ERC findings and every
check category enabled. All eleven focused tests pass. Minimum measured new-track
foreign-copper gap is 0.203657 mm; the new via is independently checked against
native capture. Four plane copper unions remain connected; 201 power/ground pads,
39 local, 33 thermal and 32 front-control connections are preserved. Drill/SMD
minimum is 0.154984 mm; SD spread is 5.999239 mm; 21 exposed-pad process holds remain.
Eight layers and two regions on all four signal layers were visually inspected.

The final recursive audit checks 8,597 bindings across 835 JSON records, with
8,595 matching and only the two historical NF test mismatches. All 213 current
unit-source bindings match. No sealed historical receipt was rewritten.

SERIAL_0 and 26 LED outputs remain open. LED13/14 require different escape planning
or adjacent-copper rework. Selected DC04 remains at 143 opens, audio at 208 and
NF at 138 with isolated-ground warnings. Approved ESS inputs, manufacturing and
assembly acceptance, receiving, installed and first-article qualification remain
unfinished. No release, order, commit or external message occurred.

Evidence: [CONTROL13 shortening](staging/digital-control13-shortened-native-01/README.md)
and [LED16 closure](staging/digital-led16-closed-native-01/README.md).

## Routing continuation and rejected LED30 trial: verified board remains at 27 opens

Twelve source-bound search records examine whole LED02 rerouting, joint
LED01/02/03 escapes, whole LATCH/MCU_PERMIT restoration, restricted inner/back
LED30 routing, minimal cuts, retained-via crossings and native-group leaf
repairs. None produces a completed candidate accepted by this continuation.
The finite searches do not establish global infeasibility.

Restricting the global LED30 section to In3/In5/B reduces its proposed total
from 244.130 to 210.681 mm and its conflicts from fourteen LATCH objects to
five tracks and one via. A 6.548 mm F.Cu boundary repair succeeds, but the other
connection does not. A deliberately provisional native board confirms LED30
connected and U3002.30 isolated from the five other LATCH pads. Native counts
are 27 opens, two track-dangling warnings and zero parity/ERC findings, with
all categories enabled. The provisional board is explicitly rejected.

The warning-retaining native capture is diagnostic, not a waiver. Rebuilding
the isolated leaf after trimming eight old leaves fails. A further search
retains both original leaf vias, trims only three loose tracks in its planning
copy, and searches between actual native groups; it also fails. The verified
LED16 PCB, its native evidence and the selected unit sources remain unchanged.
The previous eleven focused tests are inherited; no new passing-board tests
are claimed.

The manufacturer handoff now cites the verified 27-open/535-via digital
comparison instead of the older 31-open/525-via comparison. Its local links and
current PCB hash/counts were checked. On 2026-11-04 the official ESS listing
still links the 183-page v0.1 datasheet; a connected-Drive ES9292 search returns
no matches and the focused public search finds no required revisioned
package/land/stencil drawing. The user was asked for an accessible approved
drawing or footprint location; no answer or manufacturer approval is assumed.

The full unit remains unfinished and unreleased: selected DC04 has 143 opens,
latest audio partial 208, NF 138 with its isolated-domain warnings. A complete
reviewed prototype design, accepted process inputs and first-article/bring-up
package are still needed. No vendor message, order, commit or push occurred.

Evidence: [continuation and recursive source audit](staging/digital-routing-continuation-27-01/README.md).


## HC01 — housing and board consolidation review (2026-11-04)

User requested mechanical fit work and questioned the eight-board partition.
Captured the latest accepted digital LED16 board, audio controls-06 and the six
AP04 support/power selections. All eight nominal slabs are mutually clear.
Screened 656 declared receivers and 348 actual-pad-derived tail envelopes for
audio, digital and monitor; both AP04 context and the explicitly separate EI02
raised-jack scenario have no checked intersections. Five other boards still
need complete current component/mate/tail models; full native assembly was not
rebuilt and no complete fit claim is made.

A combined audio/digital outline is 268 × 63 mm. Common underside Z6.75 mm
raises audio 0.25 and lowers digital 0.25. The declared envelope screen leaves
0.55 mm above the floor and 0.59 below the monitor; additional 0.25 mm context
and cross-board receiver comparisons are clear. Audio THT projection 3.2 mm is
a new provisional assembly requirement, not a previously approved audio limit.
Three common-height scenarios pass the listed checks and each detects a
deliberately lowered monitor. The power/disconnect union is only a planar
320 × 60.5 mm study; component and thermal fit remain unchecked. Combining the
two pairs alone would reduce eight main boards to six, not two. A two-main-board
target requires placing monitor, inlet, NF and fan functions; one-board feasibility
is not ruled out, but no complete layout exists.

Corrected the preceding chat's historical-clash implication: EI02 repaired the
three EI01 interfaces and passed its captured geometry cases. Those older board
sources do not validate the latest eight-board assembly. The earlier 12-board
tally is also not final: the angle-sensor reserve, emitter partition and bought-in
modules remain separate accounting items.

The initial optional matplotlib renderer was unavailable; geometry JSON was
saved successfully. A PIL renderer and inspected label-corrected v2 figure are
provided. Exact geometry replay and 22 source bindings pass; all local review
links resolve. No PCB, schematic, selected partition, fabrication flag, vendor
message or order was changed.

Evidence: [HC01 report and comparison](staging/housing-consolidation-review-01/README.md).


## TB05 — two-main-board placement candidate (2026-11-05)

User authorized the two-main-board placement study before further routing.
All 1,543 currently placed electrical parts from the eight main-board sources
are now placed on two conditional PCB outlines. Signal main is 268 × 63 mm at
underside Z6.75; power/protection is one C-shaped 320 × 181.1 mm outline at
Z7.9, reaching the unchanged exterior power jack and switch. U201 is absent
and explicitly reserved; panel boards and bought-in modules are additional.

TB01–03 exposed an existing inlet-J3/service-USB receiver clash, old H1 head
clash and inadequate NF force/strain receiver spacing. J3 moves, old inlet
mounts are replaced, J4 shifts +1.5 mm and H102 +3 mm within the relocated force
group. TB04 packed every known part; native KiCad caught six underside courtyard
clashes and one hole-clearance issue. TB05 adds both-face courtyard and NPTH
reserves and repacks successfully. It also captures eleven new power mounts and
two Ø9 mm touch-post openings. Those supports and force/strain interfaces remain
proposed and unqualified. All earlier trial files remain intact.

The final pinned Linux native-04 run has zero geometry/library findings and
zero warnings for 477 signal and 1,092 power footprints, no ignored categories.
The files are placement-only: 0 tracks/zones; 1,190/2,634 uncapped opens. Exact
existing package-internal VSSOP/RPY 0.15 mm rules are mapped to new references;
general clearance remains 0.20 mm. Fifty-six actual source libraries are bundled;
missing-library warnings were resolved without suppressions.

Independent receiving audit covers 2,116 entries and finds no listed component,
tail, cross-board, control-context or floor intersections. Native validation
adds the opposite-face/drill checks the original screen missed. Independent
source comparison verifies all 1,556 retained source footprints and 5,327 pads,
including values, angles, sides, intrinsic geometry and separate source-net
namespaces. Missing-pad, wrong-net-namespace and shifted-pose mutations fail.
Twenty-two obsolete mounts were retired and thirteen mechanical footprints added.
Front/back review figures were visually inspected.

This is conditional mechanical packing, not integrated electrical equivalence
or full housing fit. Local feedback, decoupling, Kelvin and switching-loop
placement must be reviewed; source nets are not cross-connected and no merged
schematic or old copper is inherited. Current cooling, power hardware, airflow,
bosses/supports, real mates, harnesses, removal and strength checks remain open.
The larger power board changes airflow and thermal paths. Selected eight-board
sources and readiness flags remain unchanged. No release, order, vendor message,
commit or push was made.

Evidence and CAD links: [TB05 two-board review](staging/two-board-review-01/README.md).

## 2026-11-05 — integrated signal circuit and retained source routing

Continued the user's two-board fabrication preparation. Confirmed the current
module is Daisy Seed 3, U1001 in the source digital circuit and D_U1001 in the
merged design, using the retained 40-pin socket. Updated the GitHub About
description as explicitly requested, then read it back successfully. The local
README introduction and current hardware section were updated; no commit/push
was made.

TBI03 creates a nine-leaf-sheet signal schematic from the exact TB05 audio and
digital sources. The existing AC04 schedule authorizes 19 pin pairs / 16 shared
nets. Native export compares all 467 electrical components and 1,680 pin entries,
including source values and mapped footprint identifiers. Swapped SAI pins,
missing CODEC_RUN and an undeclared source-5V join are detected by mutation
controls. All physical connectors remain. Redundant nonphysical audio 3V3 and
digital-ground flags and their orphan labels were removed after actual ERC
findings. No physical power stage or rule category was removed.

The corrected copper transfer restores 5,767 source segments and 917 vias,
translates source outlines' component/copper coordinates by A(30,42) and
D(184,44), and preserves source layer names on the provisional eight-layer
template. Source keepouts and zone definitions transfer with renewed fills.
Final `two-board-signal-routed-native-03` has 251 opens, zero native geometry
findings, zero ERC findings, one missing-codec-footprint parity item, and no
ignored categories. The 251 opens are 208 source audio + 27 source digital +
16 new cross-section shared nets. The bridge and its common return are not routed.

Independent native audit preserves all 406 audio and 270 digital physical pad
groups (1,631 pad instances), with no missing/extra track/via geometry. The
rejected initial plane-import trial had four unassigned digital planes, 383
opens and 119 warnings; the audit detects its two regressed digital connection
groups. `copper-retention-v2.json` supersedes the first audit's deprecated
layerless via-width API. Eight native copper SVGs and corrected full-board PNG
previews were visually inspected. Initial Quick Look thumbnails clipped the
wide board; square-viewport derivatives correct that rendering issue without
changing the native SVG geometry.

The power-interface audit checks 30 proposed pin pairs against the six actual
power-source netlists and excludes seven direct-join bypasses. It records the
NF negative-force insertion, FPC current-limited NF raw5 and fan-health RUN
interlock. The old direct negative-rail and raw5/RUN wiring cannot be adopted.
NF GLOBAL_MASTER requires the contract's buffered U12.11 ALL_RAILS_ALLOW path;
U29.7 E28_MASTER_ENABLE is not equivalent. Full NF clamp/fault/auxiliary/sense
integration and the guarded module feed/return are still design holds.

Approved ESS package/land/stencil drawings and the intended manufacturer were
requested from the user; no answer was available during this work. No supplier
message/order was sent. Complete power integration, critical placement, routing,
stack/process acceptance, cooling/support redesign and full installed fit remain
open. This is a source-bound engineering checkpoint, not a fabrication release.

Current evidence: [signal integration and routing](staging/two-board-signal-routed-native-03/README.md)
and [power interface reconciliation](staging/two-board-power-interface-audit-01/README.md).

## 2026-11-05 — TBP02 native power schematic composition

User activated the goal "make the 2 board design fab ready". Revalidated the
previous checkpoint and continued independent engineering work; the preceding
turn was progress, not a wait or a blocked turn. The goal remains active.

Authored one six-section power/protection schematic from the exact six TB05
sources. Thirty reconciled pin pairs form 24 shared nets / 29 source-net merges.
All 1,077 electrical components and 3,379 schematic pin entries match the native
exported partition, values and footprint identities. The actual fan-health
contract confirms its series RUN path and operating RAW5 branch; the NF path
uses FPC U401's current-limited output. Source/protected rails, negative-stage
boundaries and the separate module return remain distinct.

The first native composition found thirteen redundant external-power flags.
TBP02 removes only those nonphysical assertions and their direct labels, keeping
every physical component and actual driver. Fresh isolated Linux KiCad reports
2,663 opens, zero geometry/parity findings, zero ERC errors and the two unchanged
isolated-reference warnings. No categories are ignored. The native audit rejects
seven incorrect wiring mutations including source/protected shorts, bypassed
protection, wrong GLOBAL_MASTER and reversed negative force pins.

The independent delta audit checks all 1,092 complete footprint geometries,
3,440 physical pad-to-schematic mappings, board outline, mounts and setup.
Only declared net/path changes and mechanical board-only flags differ. Shifted
placement, changed land size and component substitution mutations are rejected.
This does not qualify the mechanically packed critical power loops or routing.

Current netlists expose two spare E_U42 SN74AUP3G17 channels. The manufacturer
electrical pages were rendered and visually checked: the full-range VCC-0.1V
output row applies at 20uA, whereas N_R15's existing 47k complete +/-3% pull-down
alone requires up to 59.2235uA at the declared 2.7V receiving maximum. Discrete
higher-current output and HCS threshold rows were not interpolated into an
unsupported local-AUX/hot guarantee. The spare-buffer path is not implemented;
stronger buffering or a deliberately verified load/default/partial-power redesign
is the next source-interface decision. Current evidence preserves the exact
PDF bytes, native pin maps and unresolved receiving assumptions.

Full NF AUX/AUX_VALID, OV/reference/protected feedback, clamp and split native/
combined fault integration remain open. Guarded module input/return, physical
GLOBAL-OFF interval and fault-latched UV recovery also require design work.
No current pin is silently merged to a similarly named but different signal.
The signal checkpoint remains at 251 opens. No fabrication package/order,
vendor message, commit or push was made.

Evidence: [TBP02 circuit composition](staging/two-board-power-native-02/README.md)
and [current two-board status](staging/two-board-fabrication-status-02/status.json).

## 2026-11-05 — TBP03–05 NF interfaces, fault reset and source-sense correction

Resumed the fabrication goal after verifying the requested GitHub description.
That description-only response did not advance fabrication. Revalidated the
native TBP04 process: its handle was terminal/missing, and its completed review,
netlist, ERC and DRC artifacts were present. No native job was restarted.

TBP03 adds fifteen explicit NF interfaces: auxiliary supply/reference, negative
OV status and sense, protected outputs, actual bank gate/common clamp terminals,
inverted E28 fault state and native/combined fault requests. The native E28
fault output is split from latch SET before inserting NF's OR result. Only one
redundant nonphysical AUX flag is removed; all 1,077 physical parts remain.

TBP04 reuses N_U46's unused fourth OR between N_U34's existing inverter stages
to mask SET during RESET. An independent audit evaluates the native pin graph
for all 32 input combinations and all four latch equilibria per combination.
Five mutations, including TBP03's unmasked topology, are rejected. The proof is
limited to settled Boolean behavior: propagation timing, minimum reset/OFF width
and UV recovery remain unqualified. All 1,092 full footprint geometries and
3,440 pad mappings were checked against the original placement.

Integration review then found a real startup deadlock. E_R49.1 and E_R53.1 had
inherited E28's input nodes, now downstream of the added NF switches. NF's
source-UV monitors therefore held the permit flip-flops cleared while waiting
for their own disabled switch outputs to rise. TBP05 moves only those two
high-impedance sense feeds to the raw P03 negative sources. NF drain monitoring,
E28 force inputs, protected-output monitoring and bank clamps remain downstream.

A fresh isolated Linux KiCad run reports 1,077 parts, 3,440 mapped pads, 2,677
opens, zero geometry/parity findings, zero ERC errors and the two unchanged
floating-reference warnings. No categories were waived. The independent
source-sense audit checks resistor/op-amp/comparator paths, traces UV-low through
the actual AND gates to both asynchronous clears, verifies the exact two-pin
partition delta and rejects four regressions. All 32 fault/reset combinations
pass again on TBP05. Its nominal voltage comparison is explanatory, not full
corner or startup qualification.

The next circuit work remains qualified MASTER/AUX_VALID receiving, loaded
reference/sense/clamp and AUX review, guarded module feed/return and fault-latched
UV recovery with a real minimum GLOBAL-OFF interval. Signal routing, critical
power placement/routing, ESS package inputs, manufacturing and installed-fit work
remain open. No order, supplier message, commit or push was made. Goal active.

Evidence: [TBP05 checkpoint](staging/two-board-power-native-05/README.md),
[source-sense audit](staging/two-board-power-native-05/source-sense-audit.json),
[fault-mask audit](staging/two-board-power-native-04/fault-mask-audit.json).

## 2026-11-05 — TBP06 enable buffers and end-to-end UV fault review

Revalidated TBP05 and classified the preceding goal turn as progress: it changed
the source-sense circuit and completed independent native checks. The goal remains
active; no external blocker prevents the remaining local engineering work.

Connected E_U12.11 ALL_RAILS_ALLOW to E_U42.3/.5 and NF GLOBAL_MASTER, and
E_U31.3 AUX_VALID to E_U42.6/.2 and NF AUX_VALID. Replaced only E_U42's AUP triple
buffer with SN74LVC3G17DCUR. The physical pin map and existing DCU0008A lands
match the primary manufacturer drawing; the original ANA_PG2 channel remains.
All 1,077 parts and 1,092 placement geometries remain, with one declared MPN change.

The current-drive screen inventories every receiver. With the existing 47k ±3%
pull-downs, 1uA HCS receiving leakage, 1uA PCB reserve and ×1.2 guard, each new
output requires 73.468uA against the LVC 100uA VCC−0.1V row. The AUP 20uA row
could not cover that load. Source-side E_U31 fan-out requires 15uA guarded using
85°C leakage rows but 55.8uA using 125°C rows; the latter cannot use the AUP
light-load guarantee. The old fan-out already failed that 125°C screen. Full
temperature/threshold/default/timing and AUX-pool acceptance remain open.

The selected NF source is 265-part NF05R and already includes U58's retained-ARM
UV-to-fault circuit. The older 261-part contract does not describe its full
recovery path or current allocations. The construction now binds the correct
265 contract with 11mA normal/14mA fault AUX receiving allocations. The common
90mA source pool remains unqualified; no current was silently removed from it.

An independent actual-pin Boolean audit checks 64 UV/source/ARM/AUX_VALID/RUN/
other-fault combinations, then traces normal operation, captured UV fault,
GLOBAL disable, ARM clear, UV recovery and RUN reset. While RUN and AUX_VALID
stay high, E28 retains the fault even after NF's request clears and UV recovers.
Five erroneous wiring variants are rejected. The first audit attempt exposed
that the mutation harness did not yet check ARM's reset connection; adding the
explicit native GLOBAL-to-ARM-reset invariant made the UV-clears-ARM mutation
fail as intended. No candidate schematic changed to accommodate a test.

Loss of AUX_VALID still resets the E28 fault latch, as an explicit counterexample
shows. Settled logic does not qualify deep AUX corruption, minimum captured UV
pulse, actual cutoff timing or minimum physical GLOBAL-OFF duration. Those
remain work, rather than being declared closed by a nominal supervisor delay.

Fresh isolated Linux KiCad reports 2,679 opens, zero geometry/parity/ERC errors
and the same two floating-reference warnings, with all check categories enabled.
The independent delta covers all 3,440 pads and the full placement, allowing only
four declared enable terminal changes plus one MPN substitution. The prior
32 fault/reset cases and two upstream sense channels pass on TBP06. No supplier
message, order, commit or push was made. Complete fabrication readiness remains open.

Evidence: [TBP06 checkpoint](staging/two-board-power-native-06/README.md) and
[enable/recovery audit](staging/two-board-power-native-06/enable-recovery-audit.json).

## 2026-11-05 — Module feed captured; post-short cutoff gap identified

The preceding turn verified the separately requested GitHub description but
made no hardware progress. Revalidated TBP06 and resumed the available local
engineering work; there is no blocked-goal condition.

Designed and captured a 13-part independent module-input branch sourced from
P03 VIN_PROTECTED. It includes a TPS259474LRPWR, independent UV/OV dividers,
current/slew/timer settings, local bypasses, transient clamps and a copper return
star. Both TMR 1-1215 primaries retain their separate force return. No existing
physical part, secondary isolation reference or original pin partition changes.

The first native TBP07 run caught nine new-cell geometry errors, three Datasheet
field mismatches and 46 off-grid schematic warnings. TBP08 fixes them, retaining
the failed checkpoint as evidence. Fresh isolated Linux KiCad reports 1,090
parts, 3,478 mapped physical pads, 2,707 opens, zero geometry/parity/ERC errors
and the same two floating-reference warnings. The independent audit preserves
all 1,092 previous footprint geometries, checks the complete new branch, rejects
seven miswirings and reruns the prior 32 reset/fault, two source-sense and 64 UV
cases. The TI RPW copper and stencil dimensions were visually and numerically
checked. Actual native SVG review found long net-tie pin names overlapping;
shorten those in the next circuit revision. Initial page-filter export selected
the cover sheet; the direct G sheet export is the correct schematic view.

Numerical review explicitly distinguishes specified thresholds from assumptions.
The 0.5% complete resistor budget gives UV-on 10.466–11.111 V, UV-off
9.515–10.143 V and OV-off 13.879–14.710 V. The current-limit row scaling and slew
projection are model screens. The 0.35 A load and 60 uF capacitance limits are
receiving requirements, not confirmed module behavior. Native geometry does
not qualify the provisional cell position or unrouted return star.

Fault review changes the next action: TPS259474 can restart in current limit
after fast trip, and thermal trip is not guaranteed for every low-output load
state. A recorded 12 V / 8.7 V example yields only about 96 C using a typical
thermal model. Do not release this branch unchanged. The primary TPS2660
datasheet identifies TPS26601RHFR with MODE open as a candidate with fault-timer
cutoff and retained latch-off, including post-short restart. Its stated 4 ms
delay is nominal, not a guaranteed upper bound. Exact pin/land/reference/current/
slew implementation remains next; RTN must remain distinct from GND. Prototype
fault/startup measurements belong in the first-article plan, not claims about
an unbuilt unit. Per-module fault containment also remains to be assessed.

Archived primary TI/Vishay sources and bound the calculations, native results
and independent audit. TRACO's official indexed tables were available, but its
original PDF download returned 403; no local original or full package review
is claimed. Updated the current two-board status without changing the old
reference-board inventory. No supplier message, order, commit or push was made.
The full fabrication goal remains active.

Evidence: [TBP08](staging/two-board-power-native-08/README.md),
[module audit](staging/two-board-power-native-08/module-feed-audit.json),
[cutoff follow-up](staging/two-board-module-cutoff-review-01/README.md).

## 2026-11-05 — Timed module cutoff implemented and checked

The immediately preceding chat turn verified the GitHub description and made
no hardware change. Revalidated the worktree and polled the saved TBP09 builder
handle to completion rather than restarting it. The goal has available local
work and no blocked-goal condition.

TBP09 replaces the provisional module protector with TPS26601RHFR, MODE open,
22.1k current setting and two parallel 100nF C0G ramp capacitors. Both IN and OUT
terminals are connected. RTN, exposed pad and support-network returns remain
separate from force GND; the original return star and isolated secondaries remain.
The exact RHF0024A copper/stencil pattern replaces the RPW land. The manufacturer
pin, land and stencil pages had been rendered and checked during construction.
The new cell still needs critical electrical placement and thermal RTN routing.

Native TBP09 found one ERC error: both internally common OUT terminals were
modeled as independent power drivers. TBP10 keeps pin 23 power_out and declares
parallel pin 24 passive, preserving both connections. The native partition is
unchanged, and the failed TBP09 evidence is retained. No ERC category is ignored.

Fresh isolated Linux KiCad reports 1,090 components, 3,428 schematic terminals,
3,489 mapped physical pads and 2,709 opens. Geometry/parity/ERC errors are zero;
the same two isolated-reference warnings remain. The independent audit preserves
all 1,077 original component values/footprints and their pin partition, all
1,092 original footprint geometries and the board outline/setup. It checks the
new land/stencil dimensions, all mapped pads, control/reference and power paths,
and rejects 16 deliberate miswirings, substitutions and land errors. The earlier
32 fault/reset cases, two source-sense channels and 64 UV cases pass again.

Independent numerical checks reproduce the native-value divider corners and
448–746 V/s ramp. The 0.35 A/60uF receiving assumptions yield 394.8 mA startup
against a modeled 404.2 mA lower breaker limit: only 9.5 mA margin. This current
envelope is not a guaranteed datasheet row at 22.1k. The 4 ms fault timer remains
nominal without a published maximum. First-article criteria explicitly separate
the provisional 10 ms test-abort limit from a manufacturer guarantee. No physical
test is claimed and no unbuilt-prototype measurement is made a prerequisite to
building that first prototype.

Exported and visually reviewed the actual G sheet. Shorter net-tie pin labels
resolve the earlier overlap; both ramp capacitors and distinct RTN/GND paths
are legible. A hash-bound square-canvas PNG preview accompanies the unchanged
native SVG. The sheet's TBP09 circuit title is retained; the root project is
TBP10 for the pin-type correction.

Added a concrete module first-article procedure covering low-energy bring-up,
threshold sweeps, moderate and hard faults, startup into a short, latch/reset,
actual-module startup, individual-module faults and system UV/thermal behavior.
Individual module containment and startup/current receiving remain next, along
with all wider circuit, critical placement, routing, manufacturing and installed
housing work. The TRACO manufacturer-authored November 2022 datasheet was readable
through the RS mirror's web index, but direct PDF retrieval still returned 403;
no new module-package visual qualification or footprint alteration is claimed.

Updated the current two-board status and repository documentation. The capture
verifies 569 direct source/artifact hash bindings. No supplier message, order,
commit or push was made. The complete fabrication goal remains active.

Evidence: [TBP10](staging/two-board-power-native-10/README.md),
[independent audit](staging/two-board-power-native-10/module-cutoff-audit.json),
[first-article plan](staging/two-board-power-native-10/MODULE-FIRST-ARTICLE.md),
[current status](staging/two-board-fabrication-status-06/status.json).

## 2026-11-05 — First clean power-board copper restoration

Classified the preceding goal turn as progress: it implemented and independently
checked the timed module cutoff. Revalidated all saved TBP10 status bindings.
The fabrication goal remains active with substantial available local work.

Reviewed individual module fuse choices against the native UV budget. After
allocated switch, route and RTN losses, only 0.354 V remains above the 9 V module
floor. The published rated-current drops for the reviewed SCHURTER UMT 250 and
Bel 0679L0250 candidates exceed that allocation. This conservative screen does
not prove their lower-current behavior fails, but it rules out silently adding
one while retaining an unsupported drop assumption. The Bel quick-acting
characteristic also differs from TRACO's slow-fuse recommendation. Saved the
candidate/source/voltage-budget screen; no fuse or threshold was changed.
Direct primary PDF downloads were unsuccessful, so no package/derating visual
qualification is claimed. Startup/current and individual containment remain open.

A bounded whole-cell placement search could not fit the existing G footprint
group close to the source without displacing other circuits. Its nearest
front placement remains about 96 mm from the source target; a mirrored back
group is still about 62 mm away. No such move was adopted as an improvement
to critical placement. A future cell re-layout must address the actual bypass,
clamp and RTN connections, rather than merely making a packing check pass.

The layout review found that 99 supply and 156 disconnect components retain a
common source translation. Added a source-copper constructor that selects nets
only where every terminal retains one translation, face, orientation and land
shape, and where the current schematic has not split the source net. Planes are
excluded. The first candidate restores 102 source nets but fails 1,046 native
geometry checks: clearance, shorts, hole/mask spacing, source track widths and
source drill sizes. All findings touch 52 candidate nets. This failed native
checkpoint remains available; none of its failing routes is selected.

The clean successor excludes those 52 complete nets, leaving 50 restored nets,
1,689 tracks and 68 through vias. Fresh isolated KiCad closes 56 connections:
opens fall from 2,709 to 2,653. Geometry/parity/ERC errors remain zero with the
same two isolated-reference warnings, and every native check category enabled.
No component value, schematic partition, footprint pose, board outline, mount
or setup changed. Original layer names remain; no original plane was imported.

The independent native audit verifies all 50 physical source connection groups
and confirms that every selected terminal set is fully connected. Actual copper
positions, widths, layers, drills, via type/span and net mapping match the source
under the declared translation. It preserves all 1,105 footprint geometries and
1,090 electrical parts, rechecks the module branch and repeats the earlier
32 fault/reset, two source-sense and 64 UV cases. Audit development caught two
comparison issues: appended native schematic-path annotations are not footprint
geometry, and an eight-layer through via has a different enabled-layer bitmask
from a six-layer source. The final audit compares physical front/back via
endpoints and type; it does not claim the new physical stack is qualified.

Exported all eight actual copper-layer SVGs, rendered and visually inspected the
front/back views and six inner views, and saved hash-bound PNG previews. No
planes appear in these views; large unrouted regions remain. The lower-side
view uses top-view coordinates, not a mirrored assembly drawing.

Updated root/fabrication documentation and the current status. The status
capture verifies 377 direct source/artifact bindings and retains all module,
loaded-circuit, manufacturing and installed-fit release holds. The signal board
is unchanged at 251 opens and one missing ESS footprint. The 52 rejected power
nets need deliberate repair or new routes; there are still 2,653 power opens.
No supplier message, order, commit or push was made.

Evidence: [clean power copper](staging/two-board-power-routed-native-02/README.md),
[physical copper audit](staging/two-board-power-routed-native-02/copper-audit.json),
[fuse voltage-budget screen](staging/two-board-module-protection-followup-01/review.json),
[current status](staging/two-board-fabrication-status-07/status.json).

Prepared [native routing inputs](staging/two-board-power-routing-inputs-2653/capture.json)
for the next pass. The earlier small-board capture utility rejected this board
because it assumed the DRC unconnected-item list was exhaustive. The whole-board
DRC list contains 499 records, while native connectivity reports 2,653 opens
(the TBP10 predecessor also had 499 DRC records). A new capture walks the complete
native pad/copper graph instead of deriving open nets from that shorter list.
It captures 5,488 objects, 588 open nets and 3,241 open-net clusters. Independently
summing the cluster gaps gives exactly 2,653, matching native ratsnest counting.
The published open count is unchanged and was never based on the 499-item list.
The board is read-only throughout capture; its hash and zero geometry findings
remain verified.

## 2026-11-05 — Mounting-aware control routes and current-design README

The preceding turn verified that native-04 completed at 2,619 opens; this was
new evidence for the next audit, not a fabrication release. Continued the
active goal by capturing its complete native graph and independently checking
the local routing delta. No background CAD process was restarted.

The full capture contains 5,564 objects, 584 open nets and 3,203 open-net
clusters. The independent cluster-gap sum and uncapped native ratsnest agree
at 2,619; the DRC item list still contains only 499 unconnected records.
The additive audit verifies 34 physical endpoint joins across 26 nets, 76
new 0.20 mm outer-layer segments and no additional vias. It preserves all
1,105 footprint geometries, 1,090 component values, the schematic partition,
5,488 original native objects and 3,389 physical connection groups.

An initial UUID-only comparison rejected 55 module pads whose authored pads
have no UUID field. KiCad assigns new IDs on loading them. The final comparison
first requires identical complete authored footprint geometry, then uniquely
matches each affected native pad by its entire physical geometry and net.
It does not waive geometry or connectivity differences.

The first local trial passed electrical DRC but its N12_PERMIT path entered
the provisional N_H101 tool/head reserve. The successor keeps all 34 joins
and routes around that reserve. The independent audit measures every new
track against all 15 provisional mount reserves. Native geometry/parity/ERC
errors remain zero with the same two isolated-reference warnings.

Exported all eight current copper SVGs, rendered the previews and visually
inspected both outer faces and the six-layer inner contact sheet. Inner copper
is unchanged; no planes were added. Adopted routed-native-04 as the current
power routing checkpoint. Status-08 verifies 361 direct source/artifact bindings
and retains every outstanding electrical, mechanical and manufacturing hold.

At the user's request, replaced the root README's historical hardware gallery
with the current signal and power PCB images, board sizes, Daisy Seed 3
architecture, native routing counts and remaining housing/fabrication work.
Removed the old housing hero and superseded board images from that README.
Historical assets remain with their evidence records. Software usage/build
content is retained. Checked 42 root README local link targets and 19 new
checkpoint targets; both sets resolve. Verified all current preview/export
hashes (28 power bindings and 27 signal bindings). The updated README and
images are local worktree changes; no commit or push was made.

Evidence: [current power checkpoint](staging/two-board-power-routed-native-04/README.md),
[independent additive audit](staging/two-board-power-routed-native-04/additive-audit.json),
[complete routing capture](staging/two-board-power-routing-inputs-2619/capture.json),
[current status](staging/two-board-fabrication-status-08/status.json).

Next: continue short control links between opposite board faces with conventional
vias and full native copper/drill/mount checks; then complete broader routing,
module/loaded-circuit review, ESS inputs, manufacturing and installed fit.
The two-board fabrication goal remains active.

## 2026-11-05 — Opposite-face controls and checked surface detours

Classified the preceding goal turn as progress: it adopted the independently
verified 2,619-open power board and completed the user's README/image update.
Revalidated status-08 and its native capture before starting new work. The full
fabrication goal remains active; no release or blocked status is claimed.

The opposite-face constructor finds 26 candidate pad pairs within 20 mm on
104 named control nets with a native output/open-collector driver and no power
terminals. It joins 20 independent groups on 12 nets using 63 new 0.20 mm tracks
and 20 conventional 0.60/0.30 mm through vias. Via screening covers all eight
native copper layers, every old plated/NPTH drill, same-net SMD lands, board
edges and all 15 provisional mount reserves. Native-05 reports 2,599 opens,
zero geometry/parity/ERC errors and the same two isolated-reference warnings.

The independent additive audit verifies all 20 physical joins and preserves
all 1,105 footprint geometries, 1,090 component values, 5,564 native objects,
the schematic partition and 3,355 prior physical connection groups. Its exhaustive
via measurements do not reuse the constructor's spatial search. Inspection of
actual KiCad 10 capture values showed through-via enum 4; the new audit version
corrects the previously unused via branch's enum 3 assumption. The earlier
no-via audit remains valid and unchanged. The 55 transient module-pad IDs still
require uniquely matching native geometry after authored-footprint equality.

A surface-contact pass uses actual pad, track and via contacts from the checked
2,599-open board. Simple candidate paths alone find only two joins. A successor
adds bounded grid detours (6,000 nodes per contact pair, two sampled pairs per
native group pair), while retaining the same widths, clearances, mount screens
and length limits. It selects 27 joins across 23 nets with 143 tracks and no
additional vias; 29 local group-pair attempts remain deferred. The first two-join
trial is unselected, not a parent whose copper was discarded.

Native-06 reports 2,572 opens with zero geometry/parity/ERC errors and two
retained warnings. Its independent audit verifies all 27 joins and preserves
all 5,647 parent native objects and 3,335 parent physical connection groups.
The combined pass closes 47 connections and adds 206 tracks plus 20 vias,
bringing totals to 1,971 tracks and 88 vias. No components, schematic nets,
placements, board rules or outlines changed. Every new route clears the same
15 provisional mounting reserves; these do not establish installed mechanics.

Rechecked the 20 new vias against the entire final native geometry after the
surface additions. Minimum drill-edge-to-SMD copper remains 0.250000 mm,
hole-edge-to-hole-edge 0.790000 mm, via copper to foreign copper 0.210043 mm,
and via copper to board edge 4.2 mm. Both the receiving and native checks pass.
The complete final capture contains 5,790 objects, 574 open nets and 3,146
open-net clusters. Its cluster-gap sum agrees with the uncapped native count
of 2,572; the DRC list is still capped at 499 unconnected records.

Exported all eight final native copper SVGs. A reusable source-checked preview
renderer creates square Quick Look canvases and crops only unused lower canvas.
Visually inspected front and back previews plus the six inner-layer contact
sheet, then recorded the visual/source bindings. No planes have been added.
Updated the root README's current image and status references while retaining
its new two-board focus and removal of historical images. All 42 root local
links and 20 new checkpoint links resolve; diff whitespace checks pass.

Status-09 verifies 681 direct source/artifact bindings and retains the
full electrical, ESS, routing, manufacturing, thermal/support and installed-fit
holds. The signal PCB remains at 251 opens and one missing codec footprint.
No manufacturing outputs are released, and no order, vendor message, commit
or push was made.

Evidence: [current power board](staging/two-board-power-routed-native-06/README.md),
[surface delta audit](staging/two-board-power-routed-native-06/additive-audit.json),
[retained via receiving](staging/two-board-power-routed-native-06/retained-via-clearance.json),
[complete current capture](staging/two-board-power-routing-inputs-2572/capture.json),
[current status](staging/two-board-fabrication-status-09/status.json).

Next available work includes layer-changing routes for the deferred local
controls, deliberate repair of the 52 rejected source nets, and critical module
cell placement/return routing. Broader loaded-circuit, ESS, stack/BOM/process
and full installed-housing work remain required for the fabrication goal.

## 2026-11-05 — Layer detours and inherited via-in-pad repair

Classified the preceding goal turn as progress: it closed 47 control connections
and adopted the 2,572-open checkpoint with independent geometry/connectivity
and via receiving evidence. Revalidated status-09 and its complete native
capture before continuing. The fabrication goal remains active.

The new bounded two-via router joins 18 nearby control groups on 14 nets,
adding 85 outer-layer tracks and 36 conventional 0.60/0.30 mm through vias.
It screens all eight copper layers, SMD lands, old/new plated and NPTH drills,
board edges and 15 provisional mounting reserves. Local escapes are limited
to 5.5 mm and total route length to 32 mm; actual maximum is 26.441 mm. Nine
local group-pair attempts remain deferred. Native-07 reaches 2,554 opens with
zero geometry/parity/ERC errors and the same two isolated-reference warnings.

The multi-via additive audit preserves every footprint, component value,
schematic partition, 5,790 parent native objects and 3,308 physical connection
groups. It verifies all 18 physical joins and every new track/via. A second
receiving audit rechecks all 56 newly routed control vias, including the earlier
20, against the complete successor geometry and same-net drills/SMD lands.

Reconciled the old rejected-source list against current native groups. Eight
of the 52 originally rejected source nets are now fully connected; 44 still
have gaps totaling 82 opens. Seven were already complete at native-06, so the
carried-forward 52-needing-repair figure in status-09 was stale. The new report
records each original source net, terminal set and current group count. It
updates connectivity scope only; it does not qualify electrical behavior or
claim restoration of the rejected copper shapes.

Expanded the assembly screen to all 124 vias. Ten inherited source via drills
intersected SMD lands: nine had centres inside land copper and one overlapped
an edge. These were not introduced by the new control routes, and same-net
native DRC did not flag their assembly arrangement. No filled/capped via-in-pad
process is selected. Repaired the geometry instead of waiving the finding.

The repair moves those ten existing 0.60/0.30 mm vias by 0.313–1.303 mm, without
changing their size, drill, net or span. Forty-one short 0.20 mm tracks reconnect
every original copper contact on its already contacted layer. The longest
individual reconnect is 1.303 mm. All component placements, existing tracks,
schematic nets, outlines and rules are unchanged. Native-08 retains 2,554 opens
and zero geometry/parity/ERC errors with the same two warnings.

The independent repair audit verifies every via translation and reconnect,
all 1,105 footprint geometries and 1,090 electrical parts, and all 3,290 parent
native connection groups. It preserves 5,901 native objects exactly; only the
ten declared via positions/polygons change. Its exhaustive check covers all
124 vias. No via drill intersects SMD copper; minimum drill-to-SMD gap is
0.165067 mm, hole-to-hole edge gap 0.520061 mm, and via copper to foreign native
polygon gap 0.204 mm. Native DRC separately retains the exact 0.20 mm rule;
no clearance was weakened. The geometric receiving screen does not establish
manufacturing tolerances, assembly-process or loaded electrical qualification.

The final board has 2,097 tracks and 124 vias. Its complete capture contains
5,952 objects, 566 open nets and 3,120 open-net clusters; the independent gap
sum and uncapped native count both equal 2,554. The DRC list remains 499 records.

Exported all eight actual native copper views, rendered previews and inspected
the front/back images plus inner contact sheet. An initial preview invocation
ran before the existing export finished and exited without artifacts; polled
the same export handle to completion, then rendered successfully. No live CAD
process was restarted. Updated root/fabrication documentation with current
images, routing count, the repaired inherited vias and the reconciled source
work list. All 42 root, five detour-checkpoint and 20 final-checkpoint local
links resolve; whitespace checks pass.

Status-10 verifies 695 direct source/artifact bindings. The signal board remains
at 251 opens and one missing ESS codec footprint. Full power/return and critical
placement review, module protection/startup and loaded circuit bounds, remaining
routing, ESS inputs, accepted stack/BOM/process, manufacturing outputs, cooling/
supports and installed fit remain required. No order, vendor message, commit or
push was made, and no fabrication release is claimed.

Evidence: [current repaired board](staging/two-board-power-routed-native-08/README.md),
[independent repair/whole-board via audit](staging/two-board-power-routed-native-08/via-repair-audit.json),
[control-detour audit](staging/two-board-power-routed-native-07/additive-audit.json),
[reconciled source work](staging/two-board-power-routed-native-07/rejected-source-net-status.json),
[current full capture](staging/two-board-power-routing-inputs-2554-via-repair/capture.json),
[current status](staging/two-board-fabrication-status-10/status.json).

Next: review the remaining source/critical power cell placement and route
requirements, then repair or replace incomplete source nets without disturbing
checked connections. Remaining controls may need a different layer-access or
placement approach; bounded search failures are not impossibility proofs.

### Critical buck placement and internal inlet-cable retirement

The previous goal turn completed the requested README cleanup. This continuation
returns to fabrication engineering and makes a verified placement/circuit change.
Revalidated the selected native-08 source before working on it. The size-first
placement had separated regulator neighbours: U20 capacitors reach 66 mm from
their IC; U23's high-frequency bypass pair reaches 16.92/19.73 mm. Reviewed TI
TPS543620 SLUSDR5C sections 9/10.1 against these actual saved poses. Compact local
power cells must precede further power routing; nominal capacitance still needs
an effective-capacitance review.

Saved two source-bound surveys. The second searches two ten-component templates
at four rotations on a 0.5 mm grid across the lower C-board arm. No template has
a free site with every other component fixed. This bounded result is not an
impossibility claim. An otherwise suitable U23 region is occupied by P_J101.
The current interface map and native netlist establish I_J2/P_J101 as the two
parallel terminal sets of the former inlet-to-supply cable on PWR_DC_IN/AGND.

Constructed a successor removing only those two connectors, four schematic
pins, their port-local label/wire stubs, and three copper tracks forming the
old I_F1.2-to-I_J2.1 leaf. Upstream inlet/fuse/polarity protection and every
remaining pin/net assignment are unchanged. Regrouped U23, its six local
capacitors, inductor and two feedback resistors at (295,127) mm, rotated 90
degrees. All ten had no connection to external copper before moving. Source
relative positions receive explicit small spacing corrections. U23's HF pair
is now 2.61 mm from its centre; boot/input-cap distances also decrease.

Native checks pass: 1,088 electrical parts, 1,103 footprints, 3,424 schematic
pin entries, 3,485 mapped pad instances, 2,551 opens, zero geometry/parity/ERC
errors and the same two isolated-reference warnings. The three-open reduction
is connector-terminal retirement, not added routes. The complete native capture
independently sums 2,551 opens across 566 open nets / 3,117 open-net clusters;
the DRC list remains capped at 499. It contains 5,945 actual copper/pad objects.

The independent audit preserves all 3,287 retained native connection groups,
all retained copper and all remaining schematic pin/net assignments. It verifies
all 48 moved pad instances as exact rigid transforms (maximum polygon deviation
below 0.000001 mm), with no changed lands, apertures, values or board rules.
The moved courtyards satisfy 0.30 mm receiving margins, 0.50 mm board-edge gap
and the existing provisional height/context envelopes. All 124 vias are checked
again against SMD lands; minimum measured drill-to-SMD gap remains 0.165067 mm.
These geometric checks do not accept actual supplier heights or complete fit.

Exported/rendered all eight native layers and visually reviewed front/back and
the inner-layer contact sheet. Updated the root README to the new PCB/image and
status-11 while retaining only the two current board images. Status-11 verifies
650 direct source/artifact bindings and leaves fabrication/goal completion false.
No board order, vendor message, commit or push was made.

Current evidence: [power checkpoint](staging/two-board-power-buck-cell-native-01/README.md),
[independent audit](staging/two-board-power-buck-cell-native-01/buck-cell-audit.json),
[placement survey](staging/two-board-buck-cell-survey-02/survey.json),
[full capture](staging/two-board-power-routing-inputs-2551-buck-cell/capture.json),
[status-11](staging/two-board-fabrication-status-11/status.json).

Next: optimize U23's quiet feedback/BP5/AGND region and route its local input,
boot, switching, output and return paths. Regroup U20/AUX and remaining critical
cells; audit additional redundant internal connectors before removing them.
Effective capacitance, remaining electrical/fault/startup checks, ESS inputs,
accepted stack/BOM/process, manufacturing outputs and full installed fit remain
required. The signal PCB remains at 251 opens with a missing ESS footprint.

### U23 feedback/boot placement and sixteen local connections

The previous goal turn made verified progress by retiring the internal inlet
cable pair and regrouping U23. Revalidated status-11 and its selected board.
This continuation moves the feedback divider away from the IC-to-inductor SW
path. The unrouted N_U28 logic buffer occupied the quiet-side receiving region;
it and its nearby N_C67 bypass are now placed together at the source-relative
(-1.45,-1.10) mm offset. The first proposed buffer site touched existing copper;
the independent polygon screen rejected it before a candidate was written. The
selected buffer position is (311.75,133) mm, with its capacitor on the back.

Replaced generic 0603 C221 with the existing TDK C1005X7R1H104K050BB 100 nF,
50 V X7R 0402 MPN/land template used by C230. TI section 8.2.1.2.7 specifies a
0.1 uF ceramic boot capacitor rated at least 10 V; the current TDK product page
confirms this part's nominal values and size. Full derating/land/stencil/process
acceptance remains open. The smaller package fits close to BOOT and its designated
return pin. Its pins/nets remain unchanged. Mechanical and copper screens precede
every candidate; no board clearance rule is reduced.

Constructed 17 bounded front-side routing sections: local VIN/PGND branches,
nearby input-cap connections, BOOT/return, BP5/AGND, feedback and SW. A 0.4 mm
package neck widens to 1.0 mm toward L23. The boot path uses a bounded fine-grid
escape within its 3.5 mm length ceiling; the saved paths are 2.017/1.786 mm.
The initial construction reused eleven footprint-graphic UUIDs from C230. That
unselected trial was superseded by buck-local-02, which assigns fresh graphic
IDs and verifies all 21,166 authored board UUIDs are unique. Native verification
ran only on the corrected successor.

The new native checkpoint has 2,535 opens: 16 real connections closed, with
22 added tracks and no new vias. There are 1,088 circuit parts, 1,103 footprints,
3,424 schematic pin entries and 3,485 mapped pad instances. Geometry/parity/ERC
errors remain zero, with the same two isolated-reference warnings. Totals are
2,116 tracks and 124 vias. The complete native capture contains 5,967 objects,
563 open nets and 3,098 open-net clusters; its independent gap sum agrees with
the uncapped open count. The DRC list is still capped at 499 records.

The independent audit preserves every prior connection group (3,287), all old
tracks/vias and the complete schematic pin/net map. It checks every new section's
actual native endpoints, width, length and connected membership. Four footprints
move and C221 changes package; all 13 affected native pad instances match the
declared transforms or native 0402 template within 0.000001 mm. Courtyard/context,
mount and board-edge checks pass. All 124 via drills retain at least 0.165067 mm
clearance to SMD copper. Reconciled the original rejected-source list against the
new graph: eight of 52 source nets are complete, 44 incomplete with 82 opens.

Exported eight actual copper layers, rendered and visually inspected front/back,
the six-layer contact sheet and a magnified U23 viewport. The detail clearly shows
the switching path above the IC and the feedback network below. The magnified
SVG changes only viewport/output dimensions. Updated root/fabrication README
links and current board images; status-12 verifies 382 direct source/artifact
bindings and leaves fabrication/goal completion false. No order, vendor message,
commit or push was made.

Evidence: [current checkpoint](staging/two-board-power-buck-local-native-01/README.md),
[independent audit](staging/two-board-power-buck-local-native-01/buck-local-audit.json),
[complete native capture](staging/two-board-power-routing-inputs-2535-buck-local/capture.json),
[local copper detail](staging/two-board-power-buck-local-native-01/plots/local-cell.png),
[status-12](staging/two-board-fabrication-status-12/status.json).

Next: complete U23's output capacitors/output sensing, FSEL/MODE/enables and
input/AGND/PGND network with plane access. Reconcile the internally common
BOOT-return SW pin in the final schematic/layout without adding an unnecessary
external loop just to silence a native open. Route N_U28/N_C67 local bypass.
Regroup U20/AUX and other critical cells. I_J3/P_J104 share all three switch
interface nets and are candidates for a separate terminal/copper retirement
audit; P_J2/E_J1 and the NF force ports need care because the negative-rail
source and protected-side nets are intentionally distinct. No further connector
removal was performed. Remaining routing, ESS inputs, effective capacitance and
loaded power/fault/startup verification, stack/BOM/process, manufacturing outputs
and complete installed fit remain required. Signal still has 251 opens and one
missing ESS footprint.

## Bootstrap return model — TBP13

Confirmed TI SLUSDR5C Table 5-1 through the official document viewer: TPS543620
pin 13 is the bootstrap return and connects internally to force-SW pin 10.
Created dedicated U20/C201 and U23/C221 return nets, plus an explicit schematic
note. Only four schematic pin assignments and the two existing U23 return
tracks change nets; no physical geometry changes. All existing copper net IDs
are remapped by name before the native check, avoiding a legacy verifier's
assumption that the sorted net list is unchanged.

Native checks report 2,533 opens, zero geometry/parity/ERC errors and the same
two isolated-reference warnings. The decrease from 2,535 is a model correction,
not two routed connections. U20's local bootstrap return remains unrouted.
Complete capture agrees with the uncapped native count and preserves 5,967
objects. Independent comparison proves all 3,271 prior physical connection
groups and all board geometry unchanged; collapsing the declared internal
bridges restores the entire original schematic pin partition. Parts, lands,
track widths, vias, outline and mounts are unchanged. Bare-board continuity
must treat the split nets separately because the bridge exists inside the IC.

Adopted [boot-return-native-01](staging/two-board-power-boot-return-native-01/README.md),
[its independent audit](staging/two-board-power-boot-return-native-01/boot-return-audit.json)
and [status-13](staging/two-board-fabrication-status-13/status.json), with 581 direct
source/artifact bindings. Original rejected-net reconciliation remains eight
complete and 44 incomplete, with 82 opens. Copper previews/clearance evidence
are explicitly reused from the physically identical prior checkpoint; no
rerender is needed for unchanged geometry. Updated the root/fabrication README.

Next: complete U23 output capacitance and sensing, configuration/enables and
supply/return network; route the paired buffer bypass and regroup U20/AUX.
All remaining electrical, codec, routing, process and installed-fit holds remain.
Signal stays at 251 opens and missing codec land. No fabrication release,
order, commit or push; the full two-board fab-ready goal remains active.

## U23 output-bank placement and routing — TBP14

Moved only C226/C227/C228/C229, preserving their component/footprint selections
and all schematic nets. C227 is now front-side at (295,111.35); the back-side
bank lies at x=295 and y=111.35/114.85/118.35 mm. The prior positions lay beyond
the regulator's feedback region. One millimetre output/ground buses connect the
bank to L23 and U23 PGND, with paired 0.60/0.30 mm vias at output, capacitor
return and regulator return. A short 0.4 mm approach enters the PGND package.

Construction-01 established the output bank; -02 added the return. Its first
native trial had one copper-sliver warning. Construction-03 changed the joins;
-04 removed overlapping branches and used shared trunks. Adopted only native-02
from construction-04: zero geometry/parity/ERC errors, two retained reference
warnings, 2,525 uncapped opens (eight actual connections closed). There are
2,133 tracks and 130 vias: 17 tracks and six vias added in 16 route sections.
No source/report belonging to a preceding checkpoint was overwritten.

Independent audit checks all eight moved native pad shapes against the declared
transforms (maximum error 6.36e-14 mm), the full unchanged pin/net map and every
new track/via. All old copper and all 3,271 physical groups remain connected.
All four output pins join L23.2; all four capacitor ground pins join U23.9.
Courtyard/context, board edge and mounting reserves pass. All 130 vias retain
at least 0.165067 mm drill-to-SMD clearance. Native capture contains 5,990 objects,
563 open nets and 3,088 open-net clusters; its independent gap sum agrees with
2,525 opens. DRC's capped 499-record list is not the full count. The 52 originally
rejected source nets remain eight complete, 44 incomplete with 82 opens.

Exported and inspected all eight native copper layers plus front/back local
views. Local detail uses SVG coordinates (280,106,26,26), corresponding to board
coordinates (288,107.4)–(314,133.4); only the viewport/canvas changes. The initial
preview omitted the origin offset and was corrected before visual adoption.
Updated root README to the actual current PCB images, with no historical gallery.
Status-14 verifies 350 direct source/artifact bindings and retains release=false.

Evidence: [current checkpoint](staging/two-board-power-buck-output-native-02/README.md),
[independent audit](staging/two-board-power-buck-output-native-02/buck-output-audit.json),
[visual review](staging/two-board-power-buck-output-native-02/plots/visual-review.json),
[status-14](staging/two-board-fabrication-status-14/status.json).

Next: route the output sense and FSEL/MODE/enable, complete the input/AGND/PGND
network and plane access, route the relocated N_U28 bypass, and regroup U20/AUX.
Existing output capacitor values have not been newly qualified for effective
capacitance or loop stability. Full electrical/thermal, ESS, interfaces,
stack/BOM/process, manufacturing outputs and installed-fit work remain open.
Signal stays at 251 opens with the codec footprint absent. No fabrication order,
commit or push; the full two-board fab-ready goal remains active.

## U23 sense/configuration and N_U28 bypass — TBP15

Moved back-side R222 to (293.8,131.2) and R223 to (293.5,126), preserving their
values and footprints. R223 rotates 180 degrees. Routed FSEL/MODE through short
package escapes and returned both configuration resistors to the C220/U23 AGND
group. The MODE via fits the pad-free package interior; all drill-to-SMD checks
remain enabled. A failed first-choice via site was rejected by the projected
PGOOD/FSEL lands, not accepted by reducing clearance. The quiet return reaches
C220 using an In1 trace, with its deliberate PGND-plane connection still pending.
TI SLUSDR5C sections 7.3.4/7.3.8/10.1 were consulted through the official viewer.

R220.1 now senses the output at C228. The first complete construction/native
trial passed DRC but its B.Cu sense route passed beneath the SW inductor land.
Rejected that candidate for adoption. The successor uses a dedicated In2 route
around the left of the switching region, two through vias and short tap/front
escapes: approximately 25.63 mm total at 0.2 mm width. Independent cross-layer
projection of every new sense track/via to SW, BOOT and boot-return copper gives
1.15 mm minimum edge clearance against a declared 1 mm layout allocation.
This is not noise qualification; reference planes remain unfinished, and the
sense branch must not become a force-current path for later load routing.

Connected the previously moved N_U28/N_C67 local VCC and ground bypass through
two conventional vias without further placement changes. An initially considered
via intersected an existing inner POWER_READY track and was rejected. The
selected sites clear all captured copper layers and SMD lands. Wider buffer
supply/ground distribution remains open.

Adopted only buck-control-native-02 from construction-02. Native results:
2,518 opens (seven real joins), zero geometry/parity/ERC errors, two retained
isolated-reference warnings. Totals are 2,154 tracks and 138 vias; 21 tracks and
eight vias were added in 15 sections. Complete capture records 6,019 objects,
561 open nets and 3,079 open-net clusters; its gap sum matches the uncapped native
count. DRC output remains capped at 499 records. Independent audit preserves
all earlier copper and all 3,263 native connection groups; the four moved pad
polygons match declared transforms within 6.36e-14 mm. Full pin/net mapping,
component values and land patterns are unchanged. Courtyard/context/mount/edge
checks pass. All 138 via drills retain at least 0.165067 mm SMD clearance.

Exported eight native copper layers, rendered and inspected front/back, the
inner-layer contact sheet and local F/B/In1/In2 views. Local viewport changes
only canvas/viewBox, corresponding to board coordinates (288,108.4)–(318,138.4).
Updated current README images and status-15, with 356 direct source/artifact
bindings. Original rejected-source reconciliation is unchanged: eight complete,
44 incomplete, 82 opens. No fabrication release, order, commit or push.

Evidence: [current checkpoint](staging/two-board-power-buck-control-native-02/README.md),
[independent audit](staging/two-board-power-buck-control-native-02/buck-control-audit.json),
[visual review](staging/two-board-power-buck-control-native-02/plots/visual-review.json),
[status-15](staging/two-board-fabrication-status-15/status.json).

Next: U23 enable/input bypass, deliberate PGND/AGND/reference planes and
current/thermal return paths; regroup U20/AUX and other critical cells. Remaining
routing, ESS inputs, effective capacitance and loaded power/fault/startup checks,
interfaces, stack/BOM/process, manufacturing outputs and full installed fit remain
open. Signal remains at 251 opens with missing codec footprint. Goal active.

## U23 local input planes — TBP16

Adopted `two-board-power-buck-input-native-01`: C224/C225 move beside U23;
R40 moves clear of C225 and closer to U6. Fifteen tracks and twelve 0.60/0.30 mm
through vias connect the bulk capacitors and local VIN/PGND/AGND groups.
Native-filled In1 AGND and In3 VIN regions are each one connected polygon,
352.609 and 91.854 mm², respectively. All twelve new vias join the intended
plane. In1 covers the 0.2 mm In2 sense-trace projection except its two intentional
signal-via clearances. Field-width/impedance/noise qualification is still open.

Native checks: 2,511 opens, zero geometry/parity/ERC errors, two retained isolated
reference warnings. Totals: 2,169 tracks, 150 vias; minimum drill-to-SMD gap
0.165067 mm. Independent audit preserves all old copper, all 3,256 physical
groups and the entire pin/net map. Six transformed pads agree with native
geometry. Full capture v4 includes real filled-zone holes and 6,046 ordinary
objects; its 561 open nets / 3,072 clusters reconcile to the uncapped open count.

Regenerated and inspected front/back and the six inner-layer contact sheet for
the README. Local magnified details have not been recorded for this revision.
Status-16 verifies 587 direct file bindings; release and goal completion remain
false. Original source-net reconciliation remains eight connected, 44 incomplete,
82 opens. Future via edits must remove stale fill, refill natively and recheck
plane continuity and earlier connections. The old no-zone via screen alone is
insufficient for accepting copper against filled planes.

Next: coordinated U23 enable/pull-down routing, wider source feed, other critical
cells, full power/thermal/ESS/interface/stack/process and housing-fit review.

## U23 enable and coordinated MODE escape — TBP17

Moved R225 from (307.5,141.5) to (301.5,130.6) mm on B.Cu, rotating −90° without
changing the 22 kΩ part or its land pattern. Connected U23.7 to R224.2/R225.1
and returned R225.2 to the existing quiet AGND via. A search with all ordinary
copper fixed found no short front escape for EN. Moving MODE from its package
interior via (294.9,127.525) to (294.5,129.05) permits EN at (295.3,127.525).
Replaced three MODE tracks and one via, adding eleven tracks and two vias.
The EN front escape is 0.997 mm; all new tracks use 0.2 mm and vias 0.60/0.30 mm.
No clearance rule was reduced. All other copper and all 3,249 previous physical
connection groups remain intact. Complete schematic pin/net mapping is unchanged.

Removed stale filled polygons and refilled both planes natively. Three explicit
foreign-plane clearance sites were recorded. KiCad removes a 0.01194 mm² thin
web beyond the simple 0.54 mm antipad envelopes beside the new MODE via and
existing FSEL via. The independent audit therefore checks the physically
appropriate radius of via copper + clearance + existing zone minimum thickness
+ polygon allowance (0.76 mm); no fill change lies outside those local envelopes.
This is a minimum-width fill effect, not a relaxed electrical clearance. Both
planes remain single polygons; all twelve prior ground-plane contacts and six
VIN-plane contacts remain connected. In1 area is 351.790879 mm², In3 area is
91.853620 mm². In2 sense projection coverage remains intact.

Native results: 2,508 opens (three real joins), zero geometry/parity/ERC errors,
two retained isolated-reference warnings. Totals: 2,177 tracks and 151 vias.
Minimum all-via drill-to-SMD gap remains 0.165067 mm. Capture records 6,055 ordinary
objects, two zones, 560 open nets and 3,068 open-net clusters; the uncapped count
agrees with the independent cluster-gap sum. The rejected-source subset stays
eight complete / 44 incomplete / 82 opens.

The shared POWER_READY DC calculation includes both buck enable branches, the
1 kΩ pull-up, two 10 kΩ series resistors and two 22 kΩ pull-downs. Nominal unloaded
EN-source-current results are 2.35294 V POWER_READY and 1.61765 V EN. The 2,048
explicit scenarios pass 1.25 V rising / 1.05 V falling screens, but the proposed
AUX range, 25 µA EN-source allocation, logic leakage envelope, initial-only
resistor tolerance and absent external connector loads are not guaranteed
whole-unit bounds. Loaded AUX, guaranteed sourcing current, drift, partial-power
clamps and dynamics remain release holds. Official TI TPS543620, TPS2663 and
SN74LVC1G97 datasheets were consulted; sources and limitations accompany results.

Exported eight native layers and rendered/inspected front/back, inner contact
sheet and five local F/B/In1/In2/In3 details. Updated the current README images
and status-17; 625 direct bindings verify. No fabrication release, order, commit
or push. The full goal remains active.

Evidence: [checkpoint](staging/two-board-power-buck-enable-native-01/README.md),
[delta audit](staging/two-board-power-buck-enable-native-01/buck-enable-audit.json),
[DC screen](staging/two-board-power-buck-enable-native-01/enable-dc-screen.json),
[status-17](staging/two-board-fabrication-status-17/status.json).

Next: wider U23 source feed and board-wide power/return distribution, U20/AUX
placement repair, and continued electrical/ESS/interface/stack/process/housing
qualification. Signal main remains 251 opens with its codec footprint absent.


## U20 local placement/routing and internal-port retirement — TBP18

The preceding goal turn made documentation progress: the README now presents
only the two current main-board images and separates earlier variants. Resumed
native U20 work from the saved candidate; its native process had completed
successfully. Captured actual connectivity in an isolated, network-disabled,
read-only-root KiCad container. No observation timeout was treated as failure.

The placement survey considered four orientations in the lower board arm.
The selected upward-facing cell at (177.5,136.5) mm is blocked only by P_J20,
P_J21 and P_J106. Surveys limited to displaced small SMD components found no
solution; expanding to large devices introduced nine negative-startup parts.
A bounded receiving search found no free placement for the three connectors.
Retiring these legacy internal ports implements the two-board consolidation
without moving E_C24, E_J7 or nearby regulators. Their source-to-protection
terminal roles, retained consumers/drivers and separate protected return nets
were checked. No external signal-board port is retired. The original analog
and digital return-bar functions remain hard release requirements: they need
qualified PCB replacement paths and revised bar/harness/support CAD.

Moved the complete 20-part U20 cell, retaining sides. P_C201 alone changes to
P_C221's native 0402 100nF50V X7R template and TDK C1005X7R1H104K050BB value.
The remaining values, packages and complete surviving pin/net map are unchanged.
Added 17 front route sections / 22 segments / zero vias, connecting paired local
VIN/PGND ceramics, BOOT/BOOT_RETURN, BP5, feedback bottom/trim and SW to L20.
The bulk input/output banks are placed but not connected. FSEL/MODE/enable,
feedback top/sense and force/quiet returns remain open. The full U20 stage is
not yet complete or electrically qualified.

The independent audit checks all 68 changed native pad polygons (maximum
Hausdorff error 6.36e-14 mm), exact remaining footprint and copper identity,
all surviving schematic pins, source driver/receiver witnesses, changed-part
courtyard/context/mount/height clearance, and every retained native group.
Six removed numbered terminals were singleton groups; two unnumbered pads
also disappear. All 3,240 remaining earlier groups are preserved. Authored
zones and actual native saved fill compare unchanged, and all moved/removed
footprint copper is more than 2 mm from existing U23 zone outlines. All 151
vias pass the drill-to-SMD screen at a minimum 0.165067 mm.

Native results: 2,486 opens, zero geometry/parity/ERC errors and two retained
isolated-reference warnings. Totals: 1,085 electrical parts / 1,100 footprints,
3,418 schematic pins / 3,479 mapped pads, 2,199 tracks / 151 vias. The open-count
reduction is explicitly 16 routed connections plus six retired terminal opens.
Capture has 6,069 ordinary objects, two zones, 555 open nets and 3,041 open-net
clusters; uncapped native and cluster-gap counts agree. The original rejected
source-net subset remains eight complete / 44 incomplete / 82 opens.

Exported eight native copper layers and rendered/inspected front, back, the
six-layer contact sheet and magnified U20 front/back views. Saved source-bound
visual observations. Status-18 verifies 384 direct bindings and retains all
release holds. The historical 47 retained header-pin-pair tally is no longer
used as a current physical interface manifest after connector retirement;
that manifest must be reconciled with the revised assembly. Updated the root
README to the new images and counts, keeping exactly two PCB images. No order,
commit, push or fabrication release. The full two-board goal remains active.

Evidence: [checkpoint](staging/two-board-power-u20-local-native-01/README.md),
[independent audit](staging/two-board-power-u20-local-native-01/u20-local-audit.json),
[status-18](staging/two-board-fabrication-status-18/status.json).

Next: complete U20's output/input and control/return topology, U23 source feed,
AUX/other critical placement, and board-wide routing. ESS inputs, loaded
power/thermal/fault behavior, final interfaces, stack/BOM/process/manufacturing
outputs and complete installed housing fit remain unresolved.


## U20 output-bank routing — TBP19

The previous goal turn made verified progress: adopted TBP18 with 20 U20 parts
regrouped, 16 real joins and six separately accounted retired terminal opens.
Revalidated status-18 and the actual 2,486-open capture before further changes.

Connected front C208/C209 and back C206/C207 to L20.2 and U20.9 PGND. All
component poses, packages, values, schematic pins and existing copper remain
unchanged. The local output and capacitor-bank buses use 1 mm tracks; output
and ground face transitions each use paired 0.60/0.30 mm vias with 0.6 mm buses.
The back-side ground trunk runs 9.465 mm to paired regulator return vias, with
a short 0.4 mm PGND approach. No full current/thermal qualification is inferred
from those widths. Input and full quiet/force return planes remain incomplete.

Construction-01/native-01 closed eight connections but had one copper-sliver
warning without located DRC items. Preserved that failed trial. Construction-02
replaces overlapping diagonal branches with shared trunks and transverse via
buses, including a front output elbow through the paired-via bus. Native-02
passes with zero geometry/parity/ERC errors and two retained isolated-reference
warnings. No rule is relaxed. Adopted 16 sections / 17 tracks / six vias.

The isolated, network-disabled KiCad capture records 2,478 uncapped opens,
6,092 ordinary objects, two zones, 555 open nets and 3,033 open-net clusters.
The independent cluster-gap sum agrees. The audit verifies every prior copper
object and all 3,224 earlier connection groups; every capacitor positive is in
L20.2's group and every capacitor return is in U20.9's group. All new copper
belongs to those two groups, lies more than 2 mm from the existing U23 zone
outlines, and leaves authored/saved native zone geometry unchanged. All 157
vias pass the drill-to-SMD screen at a minimum 0.165067 mm. Totals are 2,216
tracks, 157 vias, 1,085 parts, 1,100 footprints, 3,418 pins and 3,479 mapped pads.
The previously rejected source-net subset stays eight complete / 44 incomplete /
82 opens. No connectors are retired in this pass.

Consulted the official TI TPS543620 SLUSDR5C datasheet, sections 9 and 10.1:
https://www.ti.com/lit/ds/symlink/tps543620.pdf . Its 4uF effective local input
requirement is split at least 2uF per side. The older source model's 1uF effective
allocation per 2.2uF local part alone does not establish that requirement.
Exact input MPN/derating and bulk topology require reconciliation before
acceptance; the output 47uF parts also lack final effective-capacitance/stability
qualification. This is an electrical design hold, not a reason to count a
connected output bank as a qualified complete regulator.

Exported eight native layers and rendered/inspected front, back, all six inner
layers and magnified front/back U20 views. Recorded visual observations and
updated root README to the current images, retaining exactly two PCB images.
Status-19 verifies 373 direct bindings. No order, commit, push or fabrication
release; goal remains active. Signal main stays at 251 opens with codec absent.

Evidence: [checkpoint](staging/two-board-power-u20-output-native-02/README.md),
[audit](staging/two-board-power-u20-output-native-02/u20-output-audit.json),
[status-19](staging/two-board-fabrication-status-19/status.json).

Next: U20 effective input capacitance/topology, feedback-top sense,
FSEL/MODE/enable, quiet/force returns; U23 wider feed, AUX and other critical
cells. Full board routing, ESS inputs, source/load/fault/thermal checks,
interfaces, accepted stack/BOM/process, manufacturing outputs and installed
housing fit remain release requirements.


## U20 sense/configuration and capacitor evidence — TBP20

Previous goal turn: progress, with TBP19's audited eight output-bank joins.
Revalidated status-19 source hashes and actual native capacitor values. The
netlist has 22uF50V X7R TDK C3225X7R1H226M250AC bulk inputs and 47uF25V X7S
TDK C3225X7S1E476M250AC outputs; older generic source descriptions must not
replace these actual selections in derating or current/thermal calculations.

Created a source-bound capacitor review from the native parts and manufacturer
ratings. A 2.2uF plus100nF pair has a 1.7595uF engineering allocation after
initial -10% and dielectric -15% factors, before bias/aging. This alone does
not establish TI's 2uF-per-side target. The complete two22uF bulk network and
its connection impedance still matter; this is not proof that the whole input
network fails or that a local part must be replaced. The 4.7uF50V0805 TDK
C2012X7R1H475K125AC candidate would require at least55.6251% remaining factor
after its initial/temperature budget to retain2uF without HF credit. Its listed
maximum2.25x1.50x1.50mm body requires receiving/land/context reconciliation.
No capacitor is substituted or accepted. Output-bank initial/temperature-only
budget is117.312–275.232uF using X7S±22%, not the obsolete genericX7R±15%.

Used the PDF skill for attempted manufacturer curve inspection. Official TDK
PDF/model curl requests returned403; the manufacturer-authored Farnell mirror
transfer timed out. Web text supplies ratings and reference-only graph caveats,
but the tool did not supply a readable graph image or numeric bias model.
No plotted curve was visually inspected and no curve-derived guarantee is
claimed. These access failures do not block independent routing progress.
Pre-fabrication design margins and later first-article measurements are distinct
requirements; no already-built unit is demanded to order a prototype.

Routed the fixed U20 cell: C207.1 sense tap through In2 to R200.1, R200.2 through
a separate via to R206.1, FSEL/MODE to their existing resistors, and both
configuration returns to the BP5/AGND group. Sense route lengths are2.366mm
back tap +24.05mmIn2 +2.152mmback finish; native projected switching-copper gap
is1.15mm across all layers. The trim via is(177.8,142.5); FSEL/MODE vias are
(176,138.55)/(177,138.55). The initial quiet-via candidate(181.75,141.7)
conflicted with the current front enable resistor; selected(182.8,141.1).
The FSEL back route uses an elbow at(176,140.7) to clear MODE-ground via
(175.3,139.3). The latter joins the quiet via on In1. Quiet-to-PGND copper and
sense-reference plane coverage remain pending, explicitly checked as incomplete.

Added13route sections/16tracks/7vias. Native checks:2472opens, zero geometry,
parity or ERCerrors; two retained isolated-reference warnings. Totals2232tracks,
164vias,1085parts,1100footprints,3418pins,3479mapped pads. Capture6115ordinary
objects,2zones,552open nets,3024open-net clusters; uncapped native and cluster-gap
counts agree. The audit verifies all3216earlier physical groups, complete pin/net
map, all values/poses/packages and old copper. New objects belong only to the
specified sense/trim/FSEL/MODE/quiet-ground groups. Both U23 zone outlines and
saved fills stay unchanged; all new copper is more than2mm from their boundaries.
All164vias pass drill-to-SMD at minimum0.165067mm. The rejected-source subset
remains8complete/44incomplete/82opens.

Exported eight native layers; inspected front/back, six-layer contact sheet and
four local F/B/In1/In2 views. Status-20 verifies389direct bindings. Updated README
counts, links and the power image; exactly two current main-board images remain.
No order, commit, push or release. Goal stays active; signal251opens and missing
ESS footprint remain unresolved.

Evidence: [checkpoint](staging/two-board-power-u20-control-native-01/README.md),
[audit](staging/two-board-power-u20-control-native-01/u20-control-audit.json),
[capacitor review](staging/two-board-input-capacitor-review-01/README.md),
[status-20](staging/two-board-fabrication-status-20/status.json).

Next: complete U20 enable, local VIN/PGND/reference topology and useful capacitor
bias/aging evidence; U23 wider feed, AUX/other critical cells and board routing.
ESS inputs, whole-unit power/fault/thermal design, final interfaces, stack/BOM/
process/manufacturing outputs and installed housing fit remain release holds.


## 2026-11-06 — U20 enable and pull-down native checkpoint (TBP21)

Previous goal turn: **no progress toward fabrication**; it only rechecked and
reported the already updated README. Revalidated the TBP20 source/capture before
taking the next available routing action. This turn: **progress**, with new
native-verified U20 enable copper and an adopted current checkpoint.

Connected U20.7 to a through via at(177.8,137.025) using a0.997mm front dogleg.
A7.318mm In4 branch reaches(180.8,143.7), then a1.336mm front trace reaches
R205.1. R204 remains fixed because its POWER_READY terminal is already connected;
R204.2 routes1.200mm on the back to(223.2,126.1). A49.690mm In4 feed detours
around the mounting reserve to the local branch. R205.2 joins the existing
quiet-ground via(182.8,141.1) through1.460mm front copper. The attempted direct
back-side local route was rejected by obstacle screening before output; the
selected inner-layer branch avoids the existing configuration return. All new
tracks are0.20mm, with three0.60/0.30mm through vias. No component or prior copper
moves. The shared feed and the divider's distinct nets remain intact.

Native checks:2469opens, zero geometry/parity/ERCerrors, two retained isolated-
reference warnings. Eight tracks and three vias make three real joins. Totals:
2240tracks,167vias,1085parts,1100footprints,3418pins,3479mapped pads. Independent
capture:6126ordinary objects,2zones,551open nets,3020open-net clusters; native
uncapped and independent cluster-gap counts agree. The audit preserves every
one of3210earlier physical groups, all old copper, component poses/values/packages
and the complete pin/net map. All167vias retain minimum0.165067mm drill-to-SMD.
Both authored/saved U23 planes are unchanged; new copper stays over2mm away.
The originally rejected-source subset remains8complete/44incomplete/82opens.

Exported all eight native layers. Inspected front/back, inner contact sheet and
local front/back/In4 views covering the full enable feed. Full-view rendering
initially collided with the renderer's no-existing-PNG precondition because the
independent local renderer finished first. Preserved the local PNGs temporarily,
rendered the full views and restored them unchanged; all render hashes verify.
Status-21 verifies389direct bindings. Root README and current fabrication index
now point to this revision, retaining exactly two current main-board images.

This is connectivity progress, not complete enable qualification. The In4 feed
needs its reference-plane/noise review with the final plane design. U20 quiet
AGND remains separate from PGND; bulk input/force return/sense planes are still
unfinished. The shared-enable DC screen remains allocated, not guaranteed over
full temperature/current/partial-power/timing. Signal remains251opens with its
ESS footprint absent. No fabrication order, commit, push or goal completion.

Evidence: [checkpoint](staging/two-board-power-u20-enable-native-01/README.md),
[audit](staging/two-board-power-u20-enable-native-01/u20-enable-audit.json),
[status-21](staging/two-board-fabrication-status-21/status.json).

Next: complete U20 local input and return/reference topology with native filled-
zone and connectivity preservation checks; obtain useful capacitor bias/aging
bounds, then wider supply distribution and AUX/other critical circuits. Whole-
unit electrical/thermal, ESS, stack/BOM/process/output and installed-fit release
requirements remain active.


## 2026-11-06 — U20 local input and return planes (TBP22)

Previous goal turn: **progress**, with the adopted TBP21 U20 enable routing.
Revalidated its current status hashes and native capture before proceeding.
This turn: **progress**: two filled planes, a checked bulk-capacitor relocation
and seven native physical joins. Goal remains active and unreleased.

Re-read TI TPS543620 SLUSDR5C sections9/10.1 from the official datasheet:
https://www.ti.com/lit/ds/symlink/tps543620.pdf . The input/PGND branches need low-
impedance internal connections; remaining ceramic input capacitance may be on
the back with multiple vias, and the AGND-to-PGND entry belongs near BP5. The
minimum4uF effective input and recommended2uFper-side requirements are still
unqualified by actual bias/aging data. No capacitor substitution was made.

The initial front C204 candidate(170.1,132.4) failed P_J104's mechanical reserve.
Selected back(173,132),0degrees, using the identical C205 back-side1210 geometry.
C204 was front(185,132),90degrees. All pin/net identities, value, MPN and package
remain unchanged. The construction record rotation0 is relative to C205's
geometry template; the independent audit explicitly checks the actual old/new
side and angle plus both native pad polygons. Other parts stay fixed. Moved
courtyard/body/tail/support/height and new copper clearance checks pass.

Added16route sections/16tracks/13through vias. Paired VIN vias serve both input
sides and C204; paired PGND vias serve the left regulator side and both bulk
returns. Short bulk-cap escapes are0.8mm, paired buses0.6mm, local VIN entries
0.35mm and PGND approaches0.4mm. Existing output/enable/control routes remain.
Added a second BP5 quiet-return via(183.6,141.1), bus-linked to(182.8,141.1).

Authored an In1 ground outline with a lower recess: the MODE-ground via and
remote configuration link remain outside the force plane, entering only near
BP5. Its left extension references the In2 sense trace. In3 supplies both VIN
sides. New native fills are single polygons: In1area450.6925317707563mm2 with
7holes and7newvia contacts; In3area85.51334425253516mm2 with4holes and6newvia
contacts. Both source and saved U23 planes stay identical. The new fill helper
supports4zones and canonicalizes each existing native polygon including holes
to prove a fresh refill does not change those older planes. An initial helper
import failed before writing output because isolated KiCad has no Shapely;
replaced that unnecessary dependency with exact native polygon normalization.

Native checks:2462opens,0geometry/0parity/0ERCerrors,2retained isolated-reference
warnings. Totals2256tracks,180vias,4zones,1085parts,1100footprints,3418pins and
3479mapped pads. Capture6155ordinary objects,551open nets,3013open-net clusters;
uncapped native opens equal the independent group-gap sum. All3207earlier
physical groups are preserved; complete pin/net map, all tracks/vias and all
other pads/footprints are unchanged. All180vias retain minimum0.165067mm drill-
to-SMD. Sense projection has0uncovered area across its0.2mm width after excluding
its own antipads. New captured foreign-copper minimum0.199675mm is consistent
with the0.001mm expanded native capture error and native0.2mm-clearance DRC.
The52originally rejected nets remain8complete/44incomplete/82opens.

Exported and visually inspected full front/back, six-layer contact sheet and
local front/back/In1/In2/In3 images. Status-22 verifies652direct bindings. The
fill artifact hashes are verified at their filled-source directory; the native
stage subsequently normalizes board syntax, so its copied fill report is not
misused as a hash of the final board. Native-zone equality is independently
checked across that normalization. Updated README images/links/counts and the
fabrication inventory; exactly two current main-board images remain.

Evidence: [checkpoint](staging/two-board-power-u20-input-native-01/README.md),
[audit](staging/two-board-power-u20-input-native-01/u20-input-audit.json),
[fill](staging/two-board-power-u20-input-filled-01/local-plane-fill.json),
[status-22](staging/two-board-fabrication-status-22/status.json).

Next: wider U20/U23 feed/output/force-return distribution and enable reference
coverage; actual capacitor/current/thermal/stability qualification; review U23
quiet-return plane entry against the same near-BP5 criterion; regroup AUX/other
critical cells. Signal remains251opens and lacks the ESS codec footprint.
Stack/BOM/process, complete circuit/routing, manufacturing outputs and full
installed mechanical fit remain release holds. No order, commit or push.


## 2026-11-06 — U23 quiet return and AUX candidate (TBP23)

Previous goal turn: **progress**, with checked U20 input/return planes and the
C204 back-side relocation. Current turn: **progress**, with a native-verified
U23 return-topology correction and an evidence-backed AUX placement candidate.
Revalidated the status-22 source bindings before editing its successor.

U23's old In1 rectangle directly contacted the remote MODE-ground via
(292.8,129.8), bypassing the intended near-BP5 quiet-link entry. Recessed that
outline around the remote via/link, retaining a lower-left shelf for the In2
sense path. Added one0.60/0.30mm via at(300.05,132.2) and a0.8mm-long0.4mm front
bus to the existing(299.25,132.2)quiet via. No existing ordinary copper or part
moves. The affected zone UUID remains unchanged; its stale fill was removed
before native refill. The fill helper proves the other3zone polygons remain
identical after a fresh fill, including both U20 planes and U23's VIN plane.

Native checks:2462opens unchanged,0geometry/0parity/0ERCerrors,2intentional
isolated-reference warnings. Totals2257tracks,181vias,4zones,1085electrical
parts,1100footprints,3418pins and3479mapped pads. Capture6157ordinary objects,
551open nets and3013open-net clusters; independent gap count equals uncapped
native opens. All3200earlier physical groups remain intact. All181vias retain
minimum0.165067mm drill-to-SMD clearance. The revised ground fill remains one
polygon, area321.56442978772054mm2 versus351.79087908495325mm2. All old direct
ground-via contacts except the deliberately removed MODE contact remain; that
via stays connected through the quiet trace. The new BP5 via replaces its direct
plane-contact count,12before/12after. Quiet-link geometry outside the BP5 entry
region clears the force plane. The0.2mm sense-trace projection has0uncovered
area except its own antipads. Whole-field impedance/noise remains unqualified.
The originally rejected-source subset remains8complete/44incomplete/82opens.
Exported and inspected full front/back, six-layer sheet and local F/B/In1/In2.

Identified AUX regulator P_U102 as TPS7A1601DGNR; P_U8 is the unrelated LT3080
positive12V source. Read official TPS7A16 SBVS171F sections9/10:
https://www.ti.com/lit/ds/symlink/tps7a16.pdf . Main input/output/delay capacitors
should remain on the regulator face, output return direct to GND, and input/
output ground regions join there. FB requires protection from coupled signals.
AUX total load, thermal dissipation, effective caps and startup remain unqualified.

Screened a compact eight-part cell with seven moves: U102F(190.5,130)90;
C113F(187.8,124.1)90; C106F(190.5,135.5)0; C107F(195.5,138.6)0;
C110F(190.175,125)90; R109F(186.9,134)90; R108B(189,134)0;
R130B(193,132)0unchanged. Early trial placements conflicted with P_D101 and
N_R73/N_R75; the saved candidate clears them. Every numbered cell terminal is
isolated in existing native copper. Current pad/track/via, drill/mount and
courtyard/body/support/height screens pass. The historical placement capture's
C204 side was refreshed from its identical C205 back-side package using the
TBP22 audit; no receiving obstacle was ignored. Straight input/output/delay
pad-center distances3.289/3.387/2.075mm are placement metrics, not route proofs.
This candidate is saved separately and has not modified the adopted board.

Status-23 verifies657direct bindings. Updated current README images/links and
fabrication inventory, retaining exactly two current main-board images. No
order, commit, push or goal completion. Signal remains251opens with missing ESS
footprint. No change to the unaccepted stack/BOM/process/installed-fit status.

Evidence: [checkpoint](staging/two-board-power-u23-quiet-native-01/README.md),
[audit](staging/two-board-power-u23-quiet-native-01/u23-quiet-audit.json),
[AUX candidate](staging/two-board-aux-cell-survey-01/README.md),
[status-23](staging/two-board-fabrication-status-23/status.json).

Next: implement and route the AUX cell with native placement/copper verification,
controlled input/output returns and thermal pad/vias; then source protection and
wider supply distribution. Continue capacitor/load/thermal/enable qualification,
remaining circuit/routing and full manufacturing/housing requirements.

## 2026-11-06 — AUX placement and local routing (TBP24)

Previous turn: **progress**, updating the user-requested README to the current
two-board architecture and removing the old image gallery and hero references.
Current goal turn: **progress**, implementing and natively validating the AUX
cell. The unbounded fabrication goal remains active and incomplete.

Revalidated the TBP23 capture and AUX survey source hashes. Moved U102 to
F(190.5,130)90, C113 F(187.8,124.1)90, C106 F(190.5,135.5)0,
C107 F(195.5,138.6)0, C110 F(190.175,125)90, R109 F(186.9,134)90,
R108 B(188.7,129.5)0 and R130 B(193,132)180. All values, footprints and sides
are unchanged. R108 and R130 deliberately differ from the seven-move survey to
avoid crossing the back-side feedback and trim paths. Native courtyard/body,
support/height, copper, mounting and drill screens pass. The historical
placement model's C204 record is corrected from its identical C205 receiving
geometry to reflect the already-adopted back-side relocation.

The original draft's 0.5 mm output trace failed the adjacent-lead clearance
screen; 0.4 mm input/output/GND traces now clear the actual 0.65 mm-pitch lands.
No rules were relaxed. The initial EN-feed via was too close to the input-cap
land, and the initial FB via conflicted with the output-return trace. Both
sites were moved before writing a candidate. The output-sense branch takes a
9.194 mm back-side path around the FB via and C205; the front bypass path uses
the corridor between C106 and N_R75. Only the passing construction was saved.

Twenty local route sections add 32 tracks and five 0.60/0.30 mm conventional
vias. The main input/output/delay paths are 3.289/3.387/2.075 mm on the front;
the output capacitor returns directly to U102.4 and the exposed pad. The input
ground and feedback-ground branches also reach that pad. VIN-to-EN uses a
short In4 link. Native connectivity verifies the input/EN, output, ground,
delay, feedback and trim terminal groups; PG remains unrouted and NC isolated.
Ground regions, thermal vias, reference shielding and full load/thermal/
derating/startup behavior are explicitly incomplete.

Native checks: **2,447 opens**, down 15; zero geometry/parity/ERC errors and
two retained isolated-reference warnings. Totals: 2,289 tracks, 186 vias,
four zones, 1,085 electrical components, 1,100 footprints, 3,418 schematic pins
and 3,479 mapped pads. The capture contains 6,194 ordinary objects, 548 open
nets and 2,995 open-net clusters; uncapped native opens and independent cluster
gap sum agree. All 3,200 earlier groups are preserved. All old tracks/vias,
unmoved pads and the complete pin/net map are unchanged. All 27 moved native
pad instances match independent transforms, maximum polygon error
3.18e-14 mm. All 186 vias retain minimum 0.165067 mm drill-to-SMD clearance.

All four authored zones and native filled polygons remain exactly unchanged,
including a fresh native refill comparison. Reviewed full front/back and the
six-inner-layer sheet, plus local F/B/In1/In4. The rejected-source subset is
unchanged at eight complete nets, 44 incomplete and 82 opens. Status-24 verifies
656 direct source/artifact bindings. Updated the root README's power-board
image, links and counts while retaining only the two current board images.

Evidence: [checkpoint](staging/two-board-power-aux-local-native-01/README.md),
[native delta audit](staging/two-board-power-aux-local-native-01/aux-local-audit.json),
[full capture](staging/two-board-power-routing-inputs-2447-aux-local/capture.json),
[status-24](staging/two-board-fabrication-status-24/status.json).

Next: implement AUX ground regions and thermal stitching, protect the feedback
network, connect source/output/PG distribution and verify load, effective
capacitance, dissipation and startup. Continue remaining source/protection
placement, U20/U23 distribution, signal routing, approved ESS package inputs,
accepted stack/BOM/process, mechanical fit and manufacturing outputs. No order,
commit, push, goal completion or first-article qualification is claimed.

## 2026-11-06 — AUX ground/reference copper and thermal stitching (TBP25)

Previous goal turn: **progress**, implementing and independently validating
the AUX cell's placement and 15 local connections. Current turn: **progress**,
with checked ground topology, reference copper and thermal stitching. Rechecked
status-24 source bindings before construction. The full fabrication goal stays
active; no completion or blocked state is warranted.

Read TI TPS7A16 SBVS171F sections 10.1–10.4 at
https://www.ti.com/lit/ds/symlink/tps7a16.pdf . Separate IN/OUT ground regions
should join at the regulator GND pin, output capacitance should return directly
there, and ground copper can shield the high-impedance feedback node. Actual
heatsinking depends on load, voltage drop, copper and ambient conditions.

Added front input/EP ground (41.490588 mm²), front output return
(15.637225 mm²), back feedback-ground copper (28.319373 mm²) and In1
thermal/reference copper (48.380402 mm²). Each is a single contiguous native
polygon. Four 0.60/0.30 mm vias sit at (188.4,130.8), (189.1,130.8),
(192.4,129.2) and (193.2,129.2), outside all SMD lands. Four 0.6 mm front
straps join them to the exposed-pad copper; no via-in-pad processing is used.

The initial ground-01 candidate passed native DRC/parity/ERC but left
0.167595 mm² of FB trace projection outside the local reference. It remains
an unselected trial. Revised ground-02 recesses U20's In1 edge by a declared
0.6 × 2.6 mm rectangle at x186.4..187, y134.3..136.9. Native fill's rounded
outer corners remove 1.567739 mm² total, entirely inside the rectangle and
two half-minimum-thickness corner envelopes. The receiving check confirms no
ordinary copper intersects the recess plus 0.3 mm margin. The AUX reference
extends left to x186.7 at y134.6..136.6, maintaining separation from U20.

U20 ground area changes from 450.692532 to 449.124793 mm², stays contiguous,
retains all 12 direct ground-via contacts and preserves its entire 0.2 mm
sense projection except own via antipads. The other three prior zones/fills
are unchanged, confirmed by native fresh refill. No component, old track,
via, pad, value, package or logical pin/net assignment changes.

An independent multilayer geometric cut removes only U102.4's native copper
land plus a 2 µm numerical margin. It proves C106/C107 output grounds then
disconnect from C113/C110 input/timing grounds, R109 feedback ground and the
exposed pad, including all via/layer paths. Only the intended seven local
ground pads belong to this group. All FB trace-width projections are covered
by the new In1 region except the two FB via antipads; uncovered area is zero.
This is topology/projection evidence, not a field/noise/thermal qualification.

The v4 capture initially stopped because native Unfracture changed the output
return's computed area by 0.0000012248 mm², above its fixed 0.000001 mm² limit.
Read-only diagnostics show boundary displacement below 0.708 nm. Added v5
capture retaining raw and unfractured polygons, and an independent verifier
for boundary displacement (maximum 2 nm), symmetric copper difference bounded
by perimeter × displacement, raw/native area and connected-region count.
The raw zero-width slit normalization preserves area. Three focused tests pass:
accept sub-nanometre rounding, reject a removed clearance hole, and reject an
equal-area translated polygon. All eight selected zone comparisons pass.
No DRC, clearance, drill or manufacturing rule was weakened; old v4 is unchanged.

Selected native totals: 2,447 opens, 2,293 tracks, 190 vias, eight zones,
1,085 electrical components, 1,100 footprints, 3,418 schematic pins and
3,479 mapped pads. Zero geometry/parity/ERC errors, two retained isolated
reference warnings. All 3,185 earlier physical groups are preserved. All
190 vias pass the 0.15 mm drill-to-SMD requirement; minimum is 0.165067 mm.
Capture: 6,202 ordinary objects, 548 open nets, 2,995 open-net clusters;
uncapped native and independent cluster-gap counts agree. The originally
rejected-source subset remains eight complete, 44 incomplete and 82 opens.

Inspected full F/B, six-inner-layer sheet and local F/B/In1 plots. Status-25
verifies 647 direct source/artifact bindings. Root README now shows the selected
ground revision, retaining exactly two current PCB images and valid links.

Evidence: [checkpoint](staging/two-board-power-aux-ground-native-02/README.md),
[audit](staging/two-board-power-aux-ground-native-02/aux-ground-audit.json),
[capture diagnostic](staging/two-board-aux-unfracture-review-01/README.md),
[status-25](staging/two-board-fabrication-status-25/status.json).

Next: connect AUX source/output/PG with the split return topology preserved;
verify total load, effective capacitors, regulator dissipation, startup and
shared enable limits. Continue source/protection cells, U20/U23 distribution,
remaining signal routing, ESS approved package inputs, manufacturing stack,
BOM/process/output review and installed housing fit. No hardware order,
commit, push or fabrication release is claimed.

## AUX load reconciliation — 2026-11-06

Previous goal turn: progress (current-design README and hardware-guide update,
with old homepage imagery removed and local links/images verified). This turn
returns to the active two-board fabrication goal; no release is claimed.

Added a native-netlist-bound [AUX inventory and sensitivity review](staging/two-board-aux-load-review-01/README.md).
All 229 AUX terminals are classified: 81 IC supply pins, 13 tied inputs,
86 capacitor terminals, 45 resistor terminals, two connectors, a clamp diode
and the regulator output. The 86 direct AGND-return capacitors total 28.4 µF
nominal. A 1 ms charge to 2.7 V would consume 76.68 mA average before loads;
this is not an actual regulator ramp or tolerance bound.

The historical AX03 budget has eight AUP triple buffers. Native TBP25 has
seven AUP triples and E_U42 LVC; its formerly grounded second/third inputs
now drive NF enable paths. Replacing the old one-input allocation with three
500 µA input allocations and the package-current difference raises the old
89.357 mA overlap sensitivity to 91.048 mA. At 250 µA it is 90.148 mA;
100 µA gives 89.608 mA. The break-even allocation is 208.84 µA/input.
These are conditional sensitivities, not manufacturer-guaranteed currents:
TI's 500 µA delta-ICC row starts at 3 V and does not cover the actual AUX rail.
The selected LVC part remains necessary for the existing drive requirement;
its stale AUP datasheet metadata must be corrected in the next native revision.

The released POWER_READY branch draws 158.824 µA at 2.7 V, nominal resistor
values and zero EN source current, versus the old 2 µA leakage allocation.
Its asserted-state pull-up load must not be counted twice. Four Si8751 TT
resistors are confirmed at 10 kΩ, 1%; the 38 mA four-device datasheet sum is
conditional on IN=VDD and exact TT=10k, not a full actual-state current bound.

At assumed 13.2 V input, 2.3 V AUX, 90 mA output and 100 µA ground-current
allocation, dissipation is 0.98232 W. The thermal path must be at most
40.72°C/W for 125°C junction at 85°C local ambient. TI's standard DGN
66.2°C/W figure would yield 150.03°C in that scenario; it is not a prediction
for this board. Required installed ambient and actual heat path remain open.

Verified native source bindings, independent complete terminal/capacitor
coverage and arithmetic; current reports retain no qualification/release
claim. Current PCB sources remain TBP25 and signal-native-03, with 2,447 and
251 opens. Next: reconcile all current E/P/N state loads and effective
capacitance, establish supply/startup/thermal design margins, correct the
E_U42 metadata, then continue AUX source/distribution/PG routing. Remaining
routing, ESS package inputs, manufacturing outputs and installed housing fit
are still part of the full goal. No order, commit or push was made.

## TBP26 — AUX PG escape and input-capacitor link, 2026-11-06

Previous goal turn: progress (verified current AUX inventory, stale budget and
metadata findings, and conditional load/startup/thermal screens). This turn
makes a checked physical routing change without claiming those limits closed.

Selected `two-board-power-aux-pg-native-01`. Connected U102.3 PG to U101.12
SHDN with two conventional 0.60/0.30 mm through vias, a direct 11.402 mm In4
segment and front escapes; total path is about 15.09 mm. Connected C102.1 to
the existing AUX VIN via with a 6.287 mm, 0.4 mm back trace. This joins the
input capacitor to the local cell; the upstream VIN source is still unrouted.

The FB via moves from (190.6,133.6) to (190.3,133.4) mm, a 0.361 mm change.
Its three attached tracks are replaced. Three AUX ground regions refill
around the rework and PG escape, with unchanged authored outlines/settings.
The other five fills remain exactly unchanged, including a fresh native
refill comparison. All four AUX regions stay contiguous with the same direct
ground contacts; the independent multilayer GND-pin-land cut preserves
input/output return separation. All five FB trace-width projections retain
In1 reference except their own via antipads; uncovered area is zero.
U20/U23 planes and their contacts are unchanged.

E_U42 stays SN74LVC3G17DCUR. Corrected the stale AUP datasheet in its board and
schematic properties and added the correct LVC link to its previously unset
embedded/local library properties. Complete pin/net mapping, values, poses
and lands remain unchanged. The constructor initially expected a preexisting
Datasheet property in both library representations; inspection showed neither
had one. It now explicitly adds the property there, and the native export and
independent schematic/library comparison verify the result. No rule changed.

Native totals: 2,445 opens (two closed), 2,300 tracks, 192 through vias,
eight filled zones, 1,085 electrical components, 1,100 footprints, 3,418 pins
and 3,479 mapped pads. Capture contains 6,211 ordinary objects, 548 open nets
and 2,993 open-net clusters; native and independent gap counts agree. Zero
geometry/parity/ERC errors, two intentional isolated-reference warnings.
All 3,185 previous connection groups survive the rework; all other retained
ordinary copper is exact. Every via meets 0.15 mm drill-to-SMD clearance;
minimum remains 0.165067 mm. The rejected-source subset remains eight whole
nets complete, 44 incomplete and 82 opens.

Inspected full F/B, six-inner-layer sheet and local F/B/In1/In4 plots.
Status-26 verifies 661 direct source/artifact bindings. Root and hardware
READMEs point to the current native project and status, with the root showing
exactly the current signal and power PCB images.

Evidence: [native revision](staging/two-board-power-aux-pg-native-01/README.md),
[independent audit](staging/two-board-power-aux-pg-native-01/aux-pg-audit.json),
[status-26](staging/two-board-fabrication-status-26/status.json).

Next: finish upstream input/protection placement and VIN routing, AUX output
distribution and the complete RUN net; reconcile present-state load,
capacitance, startup and thermal requirements. The longer PG/RUN network
still needs its final reference environment and loaded timing review. The
remaining signal/power routing, ESS approved package inputs, stack/BOM/
process, manufacturing outputs and installed housing fit remain in scope.
No order, commit, push or fabrication release is claimed.


## TBP27 — local input eFuse ILIM/dVdT controls and references

The previous goal turn made progress: native trial 02 passed geometry/parity
checks at 2,440 opens, and its uncapped capture independently agreed. This
turn completed the independent geometry, placement, topology and visual
review and adopted that candidate in status-27; the full goal remains active.

C105 moves to F(195.5,127.2), angle 270; R107 moves to F(198.5,127.4), angle
270. No values, packages, sides or logical nets change. All four original
pad groups were isolated. The dVdT and ILIM traces are 2.098 and 3.511 mm.
Thirteen front tracks and two conventional 0.60/0.30 mm vias connect the
controls and local GND/EP/passive returns. Two new solid F/In1 ground regions
provide continuous reference beneath both full-width control traces.

Trial 01 was rejected for two dangling-via warnings; its GND vias connected
only front copper. Trial 02 adds the local ground regions and resolves both
warnings without disabling checks. Its fills are each contiguous and contact
exactly the intended ground pads/vias. Their closest old-plane gaps are
0.35 mm front and 0.40 mm In1. All eight old fills and authored zones are exact;
all 3,183 prior connection groups and all old tracks/vias survive. AUX group
membership/topology is unchanged. Placement/context and all 194 via drill-to-
SMD checks pass (minimum 0.165067 mm). V5 raw/unfractured geometry agrees.

Native totals: 2,440 opens, 2,313 tracks, 194 vias, ten zones, 1,085 electrical
parts, 1,100 footprints and 3,479 mapped pads. Capture has 6,226 ordinary
objects, 546 open nets and 2,986 open clusters. Zero geometry/parity/ERC
errors; two retained isolated-reference warnings. Previously rejected source
nets remain eight whole nets closed, 44 incomplete, 82 opens. Full F/B,
six-inner-layer sheet and local F/B/In1/In4 views inspected. Status-27 checks
668 direct source/artifact bindings. Root/hardware READMEs now point to this
project and its current images, with the unchanged signal-board image.

Evidence: [native revision](staging/two-board-power-input-controls-native-02/README.md),
[independent audit](staging/two-board-power-input-controls-native-02/input-controls-audit.json),
[status-27](staging/two-board-fabrication-status-27/status.json).

Next: input blocking-FET loop, bypass capacitors and voltage thresholds,
high-current paths and system return; full AUX distribution/load/startup/
thermal reconciliation; other cells and all remaining routing; approved ESS
package inputs, stack/BOM/process, manufacturing outputs and full installed
housing fit. No order, commit, push or fabrication release is claimed.


### Next input stage — placement investigation

Created a source-bound [five-part placement screen](staging/two-board-input-stage-survey-01/README.md)
after adopting TBP27. This survey changes no PCB. Q101/Q102 move near U101,
C104 moves near OUT, C103 shifts to a clear bulk-capacitor location and the
unrouted bare return net tie moves below the controls. The generic placement
helper lacks records for that later-added net tie, so this survey explicitly
models it as zero-height copper after checking that no 3D model is fitted.
It separately checks the moved through-hole C103's opposite-face lead reserves,
which the generic moved-part courtyard check does not cover. Current C204
receiving geometry uses the already-verified identical back-side C205 template.

Early candidates conflicted with J23/J22 hardware, an AUX ground region and
the existing POWER_READY via. The final survey clears all of those without
moving any PCB objects or ignoring findings. Minimum moved-pad/other-drill
edge gap is 0.700001 mm. However, its Q101 drain-to-IN straight pad-center
distance is 8.226 mm and C103-to-OUT is 20.039 mm. Neither is accepted merely
because geometry passes: prove the Q101/Q102 gate/DRV/return routing and a
short adequate force plane, compare FET rotations, and assess the local C104
plus remote C103 loop before adoption. C101 input bypass placement and the
voltage dividers remain part of that coordinated source-stage work.

Also observed that native_two_board_power.py appends a footprint path on
every pass, leaving repeated identical path properties in the staged boards.
KiCad parity currently passes, but the next native exporter should replace
that property with one canonical symbol path and verify this is the only
metadata difference. Do not edit the already hash-bound historical exporter.


## TBP28 — blocking FET, pulldown and output-capacitor routing

The previous goal turn made progress: TBP27 was independently audited/adopted,
and a source-bound input-stage placement survey identified the next physical
constraints. This turn compared orientations, constructed/routed the source
cell, corrected a split native plane and completed native, independent and
visual checks. Status-28 now selects the result; the full fab-ready goal
remains active and far from complete.

Final moves: Q101 F(190.7,116.5) at 270°; Q102 F(190.7,110.9) at 180°;
C103 F(218.5,121) at 0°; G_NT1 F(198.7,132.2) at 0°; C104 B(202.2,122.4)
at 0°, using the identical C102 back-side package. C104 remains 1uF 50V X7R;
all values, package identifiers and logical pin/net assignments stay unchanged.
The independent audit matches all 27 moved native pad instances (including
LFPAK non-copper apertures), screens both-side body/courtyard/height/context
and C103 lead-tail reserves, and preserves every unmoved pad. R111 is unchanged.

The front Q102 drain-to-Q101-gate link is 3.087 mm and the pulldown source
return is 5.404 mm. Driver and gate In2 paths are 11.478 and 8.741 mm, with
short front escapes. New source-pin, drain-to-IN and output-front regions
join the local power nodes. A 2 mm front output bus runs 18.221 mm to C103;
C104's back feed/ground links are 2.034 and 1.825 mm. Six conventional
0.60/0.30 mm vias serve those local connections. Three old back PG tracks
are retired and replaced by a 10.4 mm detour below C104. Twenty-four new
segments yield a net increase of 21. Every retained segment/via remains exact.

Three existing ground regions refill: the AUX front input region, recessed
U101 front ground and expanded In1 reference. Seven original regions remain
exact, with fresh native refill confirmation. All 13 final filled regions
are contiguous. The first written trial (01) was rejected: its thin drain-
to-input plane entry filled into two pieces and left 2,428 opens despite
zero DRC geometry findings. Trial 02 was constructed with a wider entry but
not run natively; trial 03 widens it further to a 1.9 mm authored joining
edge and is the adopted native result. No rule or check was weakened.

Independent topology checks preserve all 3,178 prior connection groups,
including the rerouted PG branch. The AUX multilayer cut still separates
input and output returns at its GND-pin land. Full control-trace reference
coverage remains intact; full output-bus coverage passes except its own
output pad/via antipads. The input blocking source, gate, driver, local VIN,
output and output-ground groups contain exactly their intended terminals.
Actual copper capacity, complete source/reference environment, transient and
thermal behavior are not qualified by these geometry/connectivity checks.

The revised native exporter (native_two_board_power_v2.py) verifies existing
symbol paths and replaces duplicates with one canonical path. It removes
24,955 repeated identical properties across 1,085 electrical footprints.
Independent exact tree comparison proves that this normalization is the only
filled-board/native-board difference. The old hash-bound exporter is unchanged.

Native totals: 2,427 opens (13 closed), 2,334 tracks, 200 through vias,
13 filled zones, 1,085 electrical parts, 1,100 footprints and 3,479 mapped
pads. Capture: 6,253 ordinary objects, 544 open nets and 2,971 open clusters;
uncapped native and cluster-gap totals agree. Zero geometry/parity/ERC errors;
two isolated-reference warnings retained. All 200 vias meet drill-to-SMD
clearance (minimum 0.165067 mm). Rejected-source subset remains eight whole
nets connected, 44 incomplete and 82 opens. Full F/B, six-layer sheet and
local F/B/In1/In2 views inspected. Status-28 verifies 679 direct source/artifact
bindings. Root and hardware READMEs use the current project, counts and images.

Evidence: [native revision](staging/two-board-power-input-source-native-03/README.md),
[complete audit](staging/two-board-power-input-source-native-03/input-source-audit.json),
[plane/connectivity review](staging/two-board-power-input-source-native-03/input-source-plane-review.json),
[status-28](staging/two-board-fabrication-status-28/status.json).

Next: C101 IN_SYS bypass placement/loop, input UV/OV/PGTH dividers and clamp,
input-cable DC feed, local VIN connection to the retained AUX input network,
full system return and gate/driver reference environment. The return net tie
is still isolated. Resolve exact parts/derating, accepted stack/current and
thermal/transient limits (2 mm is not a demonstrated 8 A rating), AUX loaded
startup/thermal review, all remaining signal/power routing, ESS approved
package inputs, manufacturing outputs and complete installed housing fit.
No order, commit, push or fabrication release is claimed.


## TBP29 — local IN_SYS bypass and PGTH divider

Adopted `two-board-power-input-bypass-native-03` through status-29. The
previous turn only reported status; this turn revalidated TBP28 and made
new placement/routing progress. Signal main remains unchanged at 251 opens.

C101 retains its 2.2u/100V C1210 value/package but moves from F(195.5,133.5),
90 degrees, to B(196.1,121.9), zero degrees, using the identical C102
back-side template. R110 moves to B(191.3,123.5), R111 to B(196,118.3),
zero degrees, and R106 to B(196.1,126.5), 270 degrees. Four footprints/eight
pad instances change; values, packages and the complete pin/net map remain
unchanged. Native and independent courtyard/body/height/context checks pass.

IN_SYS has a 1.3375mm front escape and 1.997mm back capacitor feed; C101's
ground link is 2.833mm. A separate 0.35mm source-sense path uses a 1.373mm
front escape and 9.735mm In3 branch to join Q101 source bank to IN_SYS.
This is not the main load-current feed. The PGTH pin, receiver, divider,
return and output-sense routes measure 1.288/2.384/3.428/1.197/6.361mm.
R105/R106 and U101 PGTH now form one local divider group. UV/OV remain open.

The original PG source via at (199.5,122.5) blocked the PGTH escape; the
replacement at (199.6,122.2) clears it. Two In3 branches and back escapes
preserve the R110 and distribution connections. Five old tracks and one
via are explicitly retired; 25 tracks and eight 0.60/0.30mm through vias
are added. The net increases are 20 tracks and seven vias. All retained
tracks/vias and unmoved pads remain exact. No rule is relaxed.

The first fill trial stopped because removing C101 also changes the AUX
output front fill. Trial02 explicitly included that region and filled
successfully; trial03 corrects the flip's recorded rotation from 0 to -90
before the native validation. Six old regions refill: DC source bank,
OUT front, U101 F/In1 ground and AUX F input/output. All authored zone
outlines and settings remain exact. Seven old fills are independently
confirmed unchanged; all thirteen native regions are contiguous.

All 3,165 previous connection groups survive. AUX input/output returns
remain separate after the GND-land multilayer cut. Existing ILIM/dVdt
reference projections and bulk-output reference excluding its own antipads
remain covered. The bypass and PGTH return vias contact local U101 ground.
Full loop inductance and final adjacent-layer reference are not qualified.

Native totals: 2,420 opens (seven closed), 2,354 tracks, 207 through vias,
13 filled regions, 1,085 electrical components, 1,100 footprints and
3,479 mapped pads. Capture: 6,280 ordinary objects, 543 open nets and
2,963 open clusters; native and cluster-gap counts agree. Zero native
geometry/parity/ERC errors; two retained isolated-reference warnings.
All 207 via drills clear SMD lands (minimum 0.165067mm). The complete
independent footprint/copper/placement/fill audit passes. The canonical
native exporter makes no physical board change and removes no further
paths. Eight rejected-source nets remain fully connected, 44 incomplete
and 82 opens on that subset. Full F/B, six-inner sheet and local F/B/In1/In3
views inspected. Status-29 verifies 683 direct bindings. Root/hardware
READMEs now point to the selected project and current copper images.

Evidence: [native revision](staging/two-board-power-input-bypass-native-03/README.md),
[complete audit](staging/two-board-power-input-bypass-native-03/input-bypass-audit.json),
[plane review](staging/two-board-power-input-bypass-native-03/input-bypass-plane-review.json),
[status-29](staging/two-board-fabrication-status-29/status.json).

Next: coordinated UV/OV divider/clamp placement and routing, remaining
AUX-passive connections, input-cable feed, VIN link to AUX and full system
return. Qualify exact passive MPN/derating and thresholds, final bypass
and gate/driver reference environment, stack/current/thermal/transient
limits, loaded AUX startup, remaining signal/power routing, approved ESS
package inputs, manufacturing outputs and complete installed housing fit.
G_NT1 remains isolated; the 2mm bus is not an established 8A rating.
No order, commit, push or fabrication release is claimed.


## TBP30 — input thresholds, clamp and adjacent back-side reference

Selected `two-board-power-input-thresholds-native-03`: **2,405 opens**,
15 fewer than TBP29. Local UV/OV dividers, clamp, AUX bypass/bleed and
PG pull-up supply are connected. Seven resistor poses change, including
three flips using the retained R102 package. Values, packages and pin/net
mapping remain unchanged. R115 moves but FAST_OV_SENSE remains unrouted.

Fourteen tracks/two vias retired; 50 tracks/14 vias added. Final counts:
2,390 tracks, 219 vias, 14 filled regions, 1,085 electrical components,
1,100 footprints and 3,479 mapped pads. Native geometry/parity/ERC errors
are zero; two isolated-reference warnings remain. Uncapped native and
cluster-gap counts agree. All 3,158 prior connection groups are preserved.
Independent complete geometry/placement/copper audit passes, including
all via-to-SMD drill clearances (minimum 0.165067 mm).

All 14 filled regions remain contiguous; six old regions remain exact,
seven refill, the U101 In1 outline expands, and a new In6 ground reference
covers 16 checked back-route projections except their own signal-via
antipads. AUX split-return topology and prior reference projections pass.
The first fill trial stopped on a changed VIN fill; the final construction
explicitly declares the native refill, with 0.434 micrometre boundary delta.
No geometry rule was relaxed. Native export makes no physical board change.
The full F/B, six-inner sheet and eight local views have been inspected.

Status-30 verifies 707 source/artifact bindings. Root and hardware READMEs
now link the selected revision and its current KiCad copper images. Earlier
checkpoints remain historical evidence. These are local changes; no commit,
push, order or fabrication release is claimed.

Next: input-cable feed, VIN link to AUX, system return and fast overvoltage
monitoring; exact passive MPN/derating and threshold qualification; stack,
current/thermal/transient limits and loaded AUX startup; all remaining
routing, approved ESS inputs, manufacturing outputs and installed fit.
The signal board retains 251 opens. G_NT1 remains isolated; the 2 mm output
bus is not an established 8 A rating.


## TBP31 — fast overvoltage circuit and protected AUX input feed

Previous goal turn classified as progress: TBP30 was selected with checked
routing, refreshed images and documentation. This turn advances the active
full two-board fabrication objective; no completion or release is claimed.

Selected `two-board-power-fast-ov-native-03`: **2,383 opens**, 22 fewer than
TBP30. U103/Q103 and eight passives are regrouped without flips. The fast
sense/reference dividers, feedback/output/gate paths and RUN pull-down are
connected. The local VIN group joins the AUX regulator input network, and
C102 ground joins U101's return. Added C114 uses C401's native package and
100nF/50V C0603C104K5RACTU part number as a same-face comparator bypass;
its supply and ground escapes are 1.791 and 1.800 mm. Existing values and
pin/net assignments remain unchanged. Full loop qualification is pending.

Final counts: 1,086 electrical components, 1,101 footprints, 3,420 schematic
pin entries, 3,481 mapped pads, 2,448 tracks, 234 vias and 14 filled regions.
58 tracks and 15 vias added, with no retired copper. Complete independent
geometry/placement/copper audit passes; 24 moved pads and two added pads
verified. All 3,143 prior groups remain connected. Native and independent
uncapped/cluster-gap counts agree. Zero geometry/parity/ERC errors; two
retained isolated-reference warnings. All via drills clear SMD pads, minimum
0.165067 mm. Rejected-source subset remains eight whole nets connected,
44 incomplete and 82 opens.

The first candidate passed native net-based checks but incorrectly joined
AUX and U101 ground through a shutdown ground via touching the AUX guard.
It is explicitly rejected. Moving that via and rerouting its connections
restores the split-return topology. Final In1/In6 references expand; six
regions refill and eight stay exact. All 14 are contiguous. The original
AUX GND-land cut test passes. All prior reference projections and 22 new
surface projections pass. A further review screens every remaining route:
the inner reference is covered, while output, gate, RUN and supply paths
retain documented reference gaps. No broad electrical qualification follows
from these geometry checks.

AUX census: 230 rail terminals, 81 IC supply pins and 28.5uF direct nominal
capacitance. Added C114 contributes 0.27mA average for an assumed 2.7V/1ms
ramp; this is nominal arithmetic, not a loaded startup bound. Existing AUX
state-load, effective-capacitance and thermal issues remain open.

Full front/back, all eight local copper views and six-inner contact sheet
inspected. Status-31 verifies 721 source/artifact bindings. Root/hardware
README links and images now select TBP31. The earlier ten-part survey is
preliminary only: final construction rotates U103, shifts C109, adds C114,
and uses separately audited routes and reference outlines.

Next: resolve recorded fast-OV reference gaps and loaded response, external
input cable feed and full system return, exact passive MPN/derating and
thresholds, accepted stack/current/thermal/transient limits, AUX startup,
remaining signal/power routing, approved ESS inputs, manufacturing outputs
and complete installed housing fit. G_NT1 remains isolated. Signal remains
251 opens. No order, commit, push or fabrication release is claimed.


## TBP32 — fast overvoltage return references

Previous goal turn classified as progress: the placement check identified a
Q103/R107 spacing conflict and changed the next action. This turn corrects
that conflict and selects `two-board-power-fast-ov-return-native-02` after
native, independent and visual review. The full fabrication goal remains
active and incomplete.

Q103 moves to (196.2, 131.15), rotates 180 degrees, and receives a 2.133 mm
front-side gate path. G_NT1 moves to (199.65, 132.3) for spacing; both pads
remain isolated. The source trace is 1.463 mm. The drain escape is 1.331 mm,
with an 8.451 mm In2 connection to SHDN. Comparator AUX moves to In2; VIN
sense/AUX branches move to In5. U101 In1/In6 references extend and AUX's
In1/back reference outlines receive notches.

The first return candidate passed native checks but retained a 0.020168 mm²
drain-reference projection gap. Its report remains evidence, not selection.
The second candidate bends the drain escape and extends the lower In1 edge
by 0.1 mm, closing that gap while preserving AUX separation. Final independent
review covers all 33 current fast-OV route sections against an adjacent
U101-connected ground region, excluding only own signal-via antipads. The
16 prior back-route projections and full AUX feedback/trim projections pass.
Copper coverage is not a cutoff-time, impedance or inductance qualification.

Native and independent uncapped counts agree at 2,383 opens, unchanged.
All 3,121 prior groups remain connected. Zero geometry/parity/ERC errors;
two isolated-reference warnings remain. No circuit, value or package changes.
1,086 electrical components, 1,101 footprints, 2,444 tracks, 234 vias and
14 contiguous regions. Twenty tracks and three vias retire; sixteen tracks
and three vias replace them. Five moved pads are independently verified,
maximum polygon error 4.0194e-14 mm. Nine fills remain exact; five refill;
four outlines change. All via drills pass, minimum SMD clearance 0.165067 mm.
AUX's separate return group and GND-land cut topology survive. Rejected-source
subset remains eight complete nets, 44 incomplete nets and 82 opens.

Full front/back, all eight local layers and six-inner contact sheet inspected.
Status-32 verifies 709 direct source/artifact bindings. Root/hardware README
projects and images now select TBP32. The manufacturer-inputs document no
longer incorrectly says the power board lacks an integrated routed circuit.
No commit, push, order or fabrication release is claimed.

Next: external inlet feed and full current returns, exact passive and loaded
fast-OV/AUX limits, accepted stack and current/thermal/transient design,
remaining power/signal routing, approved ESS inputs, manufacturing outputs,
bring-up plan and complete installed housing fit. Signal retains 251 opens.
The inlet fuse output is at (278.455, 21.9), while the input-protection cell
is near (190.7, 116.5); its long feed and return require a coordinated path
and current-capacity design. G_NT1 remains isolated; 2 mm output copper is
not an established 8 A rating.

The subsequent inlet-feed survey confirms that I_F1.2, I_J1.2 and both
P_D101 pads are isolated. The retained jack-to-fuse route includes a 1.2 mm
wide, 2.545 mm long neck. Outline-only visibility paths measure 489.0 mm
for the feed and 508.1 mm for the return at 0.5 mm edge clearance; an 8 mm
corridor model measures 506.5 and 526.6 mm. These mitred-outline models ignore
obstacles and do not establish a legal or current-rated route. Evidence is
in `two-board-inlet-feed-survey-01`; compare paired PCB copper with a short,
mechanically reviewed paired jumper before committing the full power path.
TI TPS2663 revision G section 9.6.1 was checked for its short-path and
at-least-twice-full-load copper guidance. No architecture change is adopted.


## TBP33 — paired inlet feed and return

Previous goal turn classified as progress: native validation of the first
inlet candidate completed, establishing 2,374 opens and zero geometry/parity
findings. This turn completes independent capture, delta/connectivity and
visual reviews, then widens the internal paths at mounting holes and selects
`two-board-power-inlet-corridor-native-02`. The full fabrication goal remains
active and incomplete.

Two DC planes on In2/In3 connect I_F1.2 to Q101 through twelve inlet vias and
five source vias (four new, one retained). In4/In5 connect the jack return
to U101, U20 and six formerly isolated ground terminals. Exact merged groups
are recorded; this is not full system current-return qualification. Sixteen
vias and five zones are added; no tracks, footprints, values or pin maps
change. All 3,121 earlier connection groups remain intact. Eleven earlier
fills remain exact, three refill, and the source front-plane outline expands.
Every new filled piece contacts its intended group; In5 has two pieces.
The AUX group and local copper remain unchanged and separate. G_NT1 and the
input TVS remain isolated. All 33 fast-OV projections retain adjacent ground.

Candidate 01 applied a 3.91 mm surface-fastener reserve to inner copper,
leaving two 0.58 mm strips around H_NEW2. Candidate 02 preserves surface
fastener reserves and all holes, but uses drill radius plus 0.51 mm for the
four new internal planes. Captured minimum drill-edge gap is 0.509871 mm;
H_NEW2 has two 2.78 mm paths per layer, 5.56 mm total. Epec/Eurocircuits
manufacturer guidance and the conditional rationale are recorded in
`parts/inlet-jumper-01/INTERNAL-MOUNT-COPPER.md`. No stack/process acceptance
or current rating follows from this geometry change.

Native and independent uncapped counts agree at 2,374 opens: nine closed.
Zero geometry/parity/ERC errors; two isolated-reference warnings remain.
2,444 tracks, 250 vias, 19 zones. Every via drill passes the SMD-land check,
minimum gap 0.165067 mm. Full front/back, six-inner overview, eight source-cell,
four corrected mounting-hole and five corrected inlet views are inspected.
Native SVG exports translate the PCB origin by (-8, -1.4) mm; the corrected
mount/entry crops supersede earlier clipped neck/inlet crops. Status-33
verifies 707 direct bindings. Root/hardware README projects and images now
select TBP33. No commit, push, order or fabrication release is claimed.

Next: route and qualify the input TVS and surge return, then qualify the
complete inlet force path, transitions, jack/fuse limits, voltage drop and
thermal/transient behavior against actual loads and accepted stack. Complete
remaining distribution/return and power/signal routing, resolve ESS package
inputs, manufacturing outputs and installed housing fit. Signal still has
251 opens. Five source vias, the 1.2 mm jack-to-fuse neck and 2 mm output bus
have no established 8 A rating. The active objective is not complete.


## TBP34 — input TVS placement and copper

Previous goal turn classified as progress: TBP33 connected the inlet feed
and return, widened internal mounting-hole paths and completed native,
independent and visual checks. This turn selects
`two-board-power-input-tvs-native-01` after moving and connecting the TVS.
The full fabrication objective remains active and incomplete.

Vishay SMBJ document 88392 (09-Jan-2024) and TI TPS2663 SLVSE94G (June 2024)
were checked and retained in `parts/input-tvs-01`. The SMBJ33CA part is
unchanged: its stated 25 °C clamp point leaves limited negative-input margin
against the eFuse's regular absolute limit. The source review records that
this is not a temperature/surge/fuse-coordination qualification. The package
page confirms 2.44 mm maximum height, within the existing 2.8 mm allocation;
the power/temperature plots and package drawing were visually inspected.

D101 moves on B.Cu from (193.5, 137.5), 90 degrees to (186, 112), 180 degrees.
No other footprint, value, package, pin assignment, track or earlier via
changes. Two back zones and twelve 0.6/0.3 mm through vias are added, six per
terminal. The source zone also directly contacts two existing source-bank
vias. New source/return regions are 32.1480/38.0069 mm², each contiguous.
All new vias directly contact both paired internal force planes. The ten
PWR_DC_IN pads are now one native group. Irregular copper/vias do not prove
equivalence to the TVS datasheet's thermal test geometry.

Native and independent uncapped connectivity agree at 2,372 opens, closing
two. Zero geometry/parity/ERC errors; the two isolated-reference warnings
remain. All 3,112 earlier native groups survive. All 1,100 unmoved footprints
are exact, and both moved pad polygons are independently verified. Thirteen
earlier fills remain exact; six refill without outline changes. All filled
pieces contact their intended native group. AUX remains separate, and G_NT1
remains isolated. Every previously complete full-width track projection onto
an adjacent AGND region is checked against its corresponding native ground
group: 228 cases pass. Status-34 also rechecks all 33 fast-OV route projections.
All 262 via drills pass the SMD-land check, minimum 0.165067 mm.

Full front/back, the six-inner contact sheet and eight TVS-cell copper views
were inspected. Status-34 verifies 674 direct bindings. Current README links
and images select TBP34. Signal remains 251 opens. No commit, push, order or
fabrication release is claimed.

Next: qualify full inlet current sharing, resistance/voltage drop, temperature
and surge envelope using actual loads and an accepted manufacturing stack;
include source/return via transitions, fuse/adapter behavior and the retained
jack/fuse neck and output bus. Complete wider distribution, force/quiet return
connections and remaining signal/power routing. ESS package inputs, exact BOM,
manufacturing files, bring-up plan and full installed housing fit remain open.


## TBP35 — correct the inlet fuse to a supported orderable part

The previous goal turn was a status-only reply and is classified as no
progress. This turn revalidated TBP34 and began the full inlet-loss review.
Checking the actual fuse source found that the current manufacturer 451/453
rating table has 6.3 A, not the previously specified 6 A entry. The official
part certificate confirms 045106.3MRL. The copper resistance solver has not
yet been implemented; the component error changed the immediate next action.

Selected `two-board-power-inlet-fuse-native-01`: I_F1 is now
045106.3MRL 6.3 A 125 V. Corrected schematic/cached library symbol values,
board Value/MPN and expected-circuit contract. TBP34 and earlier source
artifacts remain historical. No routing or footprint geometry changed.

Native checks pass with zero geometry/parity/ERC errors and the same two
isolated-reference warnings. The independent review restores the whole PCB
exactly by undoing only the two declared properties; all 6,427 physical copper
objects, 21 filled zones, 3,110 native connection groups and 3,420 pin-net
entries are unchanged. Fifty-five native-generated pad UUIDs are independently
matched by unique full physical equivalence. All 226 copied CAD/support files
are checked. Existing lands match nominal manufacturer dimensions; maximum
package body/height fit the prior allocation. Full installed fit is unproven.

The fuse-source review records 9.6 mOhm nominal cold resistance, giving a
conditional 38.4 mV/153.6 mW at 4 A. The 25 C continuous allowance after the
stated 25% derating is 4.725 A; a 4 A load requires temperature rerating of at
least 0.84656. These estimates do not bound hot resistance or establish safe
fault clearing. A 6.3 A backup fuse cannot itself enforce the jack's 5 A limit.
The official PDF was read through the web tool; direct downloads were blocked
by the host, and no local PDF/visual inspection is claimed.

Status-35 verifies 975 direct bindings. README selections now identify TBP35;
TBP34 copper images are retained and explicitly identified as geometrically
identical. Power still has 2,372 opens; signal still has 251. No commit, push,
order or fabrication release. The full objective remains active.

Next: extract actual inlet copper resistance/voltage drop across plausible
stack scenarios, resolve transition/current-sharing limits and thermal/fault
coordination for the corrected fuse, then complete supply/return distribution
and remaining routing. Missing ESS package inputs, exact manufacturing stack,
BOM/process, whole-unit fit and prototype bring-up requirements remain open.


## Inlet resistance screen — TBP35 geometry, no new PCB revision

Previous goal turn classified as progress: the unsupported inlet fuse entry
was corrected, independently reviewed and selected as TBP35. This turn
revalidated status-35 source bindings and implemented the previously missing
actual-copper resistance screen. The full fabrication goal remains active.

The new sheet solver uses a four-neighbour finite-volume resistor grid over
conservatively retained cells. Actual captured filled-zone polygons, tracks
and contacts define four inlet planes and five local front-copper cases.
Ports are ideal equipotential terminals. Three mesh sizes plus a shifted fine
grid check sensitivity; source/sink KCL, interior residual, energy and the
passive-network voltage maximum principle are checked at every solve.
Analytical rectangle/parallel tests, rotation/floating copper and invalid
open/overlapping-port cases pass (four tests).

The coarse result is retained in two-board-inlet-resistance-01. A refinement
run was deliberately interrupted with confirmed exit 130 after recognizing
that distant surface copper islands forced very large mostly empty arrays.
The unfinished v2 script had no output report and was corrected to remove
only surface components unable to carry current between its selected ends.
The restarted run completed as two-board-inlet-resistance-02. No timeout was
mistaken for process completion, and no partial report was selected.

Final plane grids are 0.0625 mm, local grids 0.00625 mm. All nine cases have
less than 2% final refinement and shifted-grid differences; maximum 1.3319%.
The independent review binds all native contacts/nets/groups and checks
conservation, energy and scenario arithmetic. An initial unit-conversion
error in the independent checker was detected and fixed before its report
was written; the original calculation's SI conversion was correct.

At the assumed 4 A, modeled copper-only drop/loss at 85 C are 186.65 mV /
0.74660 W for 35 um and 93.32 mV / 0.37330 W for 70 um. Both thicknesses are
scenarios, not accepted stack minima; imposed temperature is not a thermal
prediction. Ideal source-via current is nonuniform, up to 1.740 A at
(189.95,112.75); ideal return-via current reaches 1.841 A at (197.95,111.3).
These do not establish actual barrel currents. The isolated In5 piece at
(194,126.7) contributes no separate inlet conduction in the single-sheet
model, despite native connection through other layers.

The calculation excludes barrel/contact/solder, hot fuse, device resistance,
local bulk return, downstream distribution and intermediate layer coupling.
It is not a full-loop bound or current/thermal qualification. Keep the
current corridor while resolving actual stack, whole-unit loads and the
coupled return/distribution network; the copper-drop screen alone does not
justify a new C-board layout. README and fabrication inventory link the
result. Native geometry is unchanged; power/signal opens remain 2372/251.
No commit, push, order or fabrication release.

Next: complete actual force/quiet return and supply distribution, including
local bulk return and U20/U23 source paths; reconcile state/startup loads and
use accepted copper/plating plus component/contact losses for the complete
input-loop review. Continue remaining routing, ESS package inputs, exact BOM,
manufacturing output, whole-unit fit and prototype inspection/bring-up work.


## TBP36 — main regulator feed and return distribution

Previous goal turn classified as progress: the native-copper inlet resistance
screen was implemented, refined and independently checked. This turn returns
to actual routing, from selected TBP35, and selects
`two-board-power-regulator-distribution-native-04` after native, independent
and visual validation. The fabrication objective remains active/incomplete.

One In2 supply zone now joins the U101/C103 protected supply with both U20
and U23 local input groups. Existing vias and local In3 planes join the three
In2 pieces. Two In1 ground bridges provide adjacent return copper and join
U23's local ground to the main ground. The U20 ground already belonged to the
main group; its new bridge improves the adjacent return route. No tracks,
vias, components, values/packages or schematic pin assignments change. Three
connections close: power now has 2369 opens, signal still 251.

Candidate 01 stopped at the native-fill preservation assertion because KiCad
also refilled the existing In2 inlet zone. Candidate 02 declared that refill
but native DRC found four same-net zone-priority intersections, and the PGTH
trace blocked the U20 feed. Candidate 03 gave ground bridges priority 1 and
routed around PGTH; native DRC was clean with 2369 opens. Independent reference
review found 36.0273 mm² of the feed unreferenced. Candidate 04 extends the
return bridge and trims two small unreferenced feed edges. Earlier candidates
are not selected; no checks were disabled or findings waived.

The selected native project reports zero geometry/parity/ERC errors and the
same two isolated-reference warnings. Independent comparison proves the full
non-zone board tree, all 6427 captured objects, all 3110 prior groups and all
3420 schematic pin/net entries preserved. Only the declared three group joins
occur. All old zone outlines are exact. Seventeen prior fills remain exact;
four refill. AUX local copper/group and G_NT1 isolation survive. P_J22.2 is
explicitly excluded from the new return region. Its rounded exclusion contour
is checked within sub-micrometre coordinate serialization tolerance, not
silently equated to unrounded construction coordinates.

New feed/ground areas are 705.4976, 16.9138 and 785.5362 mm². All pieces connect
to intended native groups, including ground bridges with no direct pad of
their own. All 228 prior complete adjacent-ground projection cases pass with
native ground identity preserved. Status-36 separately rechecks all 33 full
fast-OV routes. New-feed In1 coverage is 99.99364% after contact antipad
exclusions; eight remaining regions total 0.043961 mm² at supply-via banks
and the isolated header reserve. These are quantified, not called full area
coverage or qualified impedance/noise. The In2 inlet refill means the TBP35
resistance model is historical rather than an exact new-distribution model.

Full front/back, the six-inner overview and six local distribution details
were inspected (nine recorded views). Status-36 verifies 824 direct bindings.
README project/status links now select TBP36, with its actual In2 supply image.
The original rejected-net subset is still 8 complete/44 incomplete/82 opens.
No commit, push, order or fabrication release.

Next: complete regulator output distribution, remaining module inputs and
force/quiet returns; qualify new branches against actual load/startup states,
effective capacitance, accepted stack/current sharing, thermal and noise
requirements. Continue power/signal routing, ESS package inputs, exact BOM,
manufacturing files, full installed housing fit and prototype bring-up plan.

## TBP37 — digital source distribution and eFuse quiet islands

Revalidated the selected TBP36 project after a status-only turn (no routing
progress in that preceding turn; its README caption correction was minor).
Continued the available output-distribution work. TBP37 selects
`two-board-power-digital-distribution-native-02` and capture
`two-board-power-routing-inputs-2340-digital-distribution-02`.

The digital regulator output now reaches four eFuse input pairs, E_J11 and
four existing input capacitors. Forty-seven tracks, 38 through vias and six
zones close 29 native connections: 2369 -> 2340. Source/protected outputs
remain separate. The full source rail is still incomplete, including P_J23.
Native geometry/parity/ERC errors are zero; the two isolated-reference warnings
remain. No component, package, value or circuit pin assignment changes.

Candidate 01 was native-clean but used a shared In1 field. Manufacturer
TPS25948 Rev. D sections 5/8.9 prompted a better quiet-return layout before
selection. Candidate 02 uses four separate In1 islands, each contacted only by
its own OVLO, RCBCTRL and GND vias. The GND-pin via is the single plane connection
to system return. Eight control vias are excluded from existing In4/In5 ground
and the new In5 return extension. Initial island envelopes overlapped; the
constructor stopped before emitting a candidate, then used rounded 0.32 mm
expanded envelopes with explicit inter-island clearance. No failed board was
selected and no native finding was waived. Pin 4 is RCBCTRL, not GND; the
existing low tie disables steady-state reverse blocking and is retained.

Independent review preserves all 6427 prior physical objects and 3107 prior
native groups; only the declared 14 source groups and 17 ground groups merge.
Protected outputs, AUX return and both isolated G_NT1 pads survive. Twenty
old fills are exact, four refill, two old ground outlines gain exclusions.
The native zone capture is checked against unfractured KiCad polygons. All
300 via barrels clear SMD lands by at least 0.163872 mm. Audit development
corrected Python float-versus-serialized endpoint comparisons to a 0.1 nm
coordinate tolerance and the capture's scalar via-drill representation before
its first successful report; no routing geometry was changed to hide failures.

All 229 prior complete adjacent-ground track projections are preserved by
physical ground identity. Status-37 rechecks all 33 full fast-OV routes.
Source In6 fill is one 828.030631 mm² piece. Its In5 reference screen excludes
source-contact antipads; 0.331629/811.971954 mm² remains uncovered in 17 small
regions near via-bank/quiet-reserve/hole boundaries. This is about 99.9592%
coverage, not complete reference coverage or an impedance/current rating.

Twelve native views were inspected: front/back, six-inner overview, five eFuse
local views and four U20-source views. Status-37 verifies 843 direct bindings.
Root/hardware/fabrication READMEs select TBP37 and its In6 image. The original
52 rejected-net subset remains 8 complete/44 incomplete/82 opens; it is not
the board-wide open count. No commit, push, order or fabrication release.

Next: finish eFuse outputs/support networks using each quiet island, improve
local bypass placement and establish exact capacitor effective values. Size
U20's output transition, source plane and eFuse escapes for actual loads,
startup/fault states and accepted stack/plating. Continue analog output,
remaining source/module supplies and force/quiet returns, signal routing,
approved ESS package inputs, BOM/manufacturing outputs, installed housing fit
and prototype bring-up preparation. The whole goal remains active and incomplete.

## TBP38 — digital eFuse support cells

Selected `two-board-power-digital-cells-native-03` after native and independent
review. Twelve ILM/DVDT/DVDT_CAP nets and eight quiet returns close 20 more
connections: power 2340 → 2320, signal unchanged at 251 plus missing ESS.
Fifteen passives move, five change side; component values and 3420 circuit
pin entries remain unchanged. Retired 19 tracks/16 vias, added 95 tracks/24
vias; final totals 2567 tracks, 308 vias, 30 zones. Six outlines and ten fills
change; twenty fills stay exact. All 3078 earlier connection groups survive.

Candidate 01 failed native clearance/dangling-via checks and had a split quiet
island. Candidate 02 fixed those but independent review found 0.025767 mm² of
lost reference below an existing U16 input trace. Candidate 03 restores the
old island extent and passes. No failed candidate selected or check waived.
Native geometry/parity/ERC errors are zero with two retained warnings. All
308 via drills pass the SMD screen, minimum 0.163872 mm; all 233 previously
complete ground-reference projections pass. The status script's draft expected
229 from TBP37's prior-parent screen; the current exhaustive TBP37 baseline has
233 and the unbound status script was corrected before its first report.

Eight current native views inspected. Status-38 verifies 834 direct bindings
and rechecks all 33 fast-OV sections. Source-plane In5 reference screen leaves
0.351827/828.869102 mm² uncovered. New support routes do not all have complete
adjacent ground coverage; quiet returns reach 13.258 mm. These require further
reference/parasitic review and shortening or qualification. Moved-component
mechanical screen passes; complete installed fit remains unverified.

Root/hardware/fabrication READMEs select TBP38 and current images. The earlier
rejected-net subset remains 8 complete/44 incomplete/82 opens. No commit, push,
order or fabrication release. Next: support reference/parasitics, output and
PG/follower controls, remaining distribution and signal routing, load/startup/
thermal/fault limits, ESS package, exact BOM, full fit and manufacturing outputs.
The fabrication goal remains incomplete.


## TBP39 — adjacent digital quiet references

Previous goal turn classified as progress: TBP38 was independently verified and
selected. This turn selects `two-board-power-digital-reference-native-02`.
Digital source moves In6 → In4, preserving its one 845.055569 mm² fill and all
20 contacts. Four In1 quiet fields expand; four In6 quiet fields and two In6
main-return regions are added. In4 main ground reserves the source area.
Five ground outlines change and one source changes layer; 24 prior zone records
remain exact. All four devices retain one star connection through their GND via.

A planning-only attempt to insert quiet fields directly into the In6 source
split source contacts; that approach was rejected before any board was emitted.
The layer change preserves source distribution instead. Initial native fill
invocation expected 35 zones but construction produced 36 (two connected main
return pieces); the count assertion stopped it before filling. A separate output
with the verified count passed, preserving 24 fills. Native candidate 01 passed
DRC and independent checks. Candidate 02 replaces six E_U17 DVDT tracks with
six tracks over its own In1 quiet field, increasing 4.700 → 6.146 mm. A further
native fill verifies all 36 fills unchanged by that surface-only reroute.

Final native geometry/parity/ERC errors: zero, with two retained warnings.
Power opens remain 2320; signal remains 251 plus missing ESS. All 3058 existing
connected groups survive, with 6590 unchanged objects and six replaced tracks.
All 1101 footprints and 3420 circuit pin assignments remain unchanged. Capture
regenerates 55 old G_* pad identities; independent review matches only unique,
complete physical/net data and verifies the entire remaining non-zone tree.
All 234 earlier complete adjacent-ground projections and 33 fast-OV routes pass.

Reference coverage improves 2/28 → 24/28 full route-section screens, with summed
uncovered area 10.661113 → 0.001294 mm². The four residual screens are confined
to 0.25 mm beyond nominal same-signal via copper edges; the two C48 screens
overlap and the sum is not a unique physical area. Full reference remains false.
Twenty of 22 support sections have complete reference to their own quiet field;
two retain via-edge residuals. The rerouted DVDT section has full own-field
coverage. Source In5 screen stays 828.869102 mm² with 0.351827 mm² uncovered.

Nine final views inspected. Automatic rendering approval timed out once before
execution; its permitted retry succeeded. Status-39 verifies 1300 direct
bindings. Root/hardware/fabrication READMEs and current images select TBP39.
Earlier rejected-net subset remains 8 complete/44 incomplete/82 opens.
No commit, push, order or fabrication release.

Next: shorten or qualify quiet returns (still up to 13.258 mm), establish actual
ILM/support parasitics and local bypass loops/effective capacitance, then finish
protected outputs, PG/follower controls, remaining distribution and signal
routes. Current/thermal/fault limits, accepted stack, ESS package, exact BOM,
full installed fit, manufacturing outputs and bring-up plan remain incomplete.


## 2026-11-08 — TBP40 digital startup fanout selected

Previous goal turn classified as no progress: it restated verified TBP39 status.
This turn makes concrete progress and selects
`two-board-power-digital-startup-native-02` through status-40. The full goal
remains active and incomplete; no fabrication release, commit, push or order.

The joint placement/routing plan moves seven existing bottom resistors and
connects four PG pull-ups, three follower EN pull-downs and three quiet returns.
Their AUX supply ends, receivers, gated drivers and the full startup chain are
still incomplete. Mechanical-only packing failed routability; restricted return
targets and greedy route order also missed valid paths. The accepted plan uses
existing owned quiet copper and one extra R112 quiet via, routing its ground
branch before the EN branch. A 0.5 mm master-enable trace shift frees the R112
pocket. PG routing searches are widened around the existing body/tail reserves;
all final bottom PG branches remain 1.505–13.429 mm. Search inputs and outputs
are archived in `two-board-digital-startup-plan-01`.

Eight control-ground escapes are replanned; the U17 GND8 star shifts 0.25 mm.
C47's old 9.031 mm bottom return becomes a 1.600 mm local branch; R112's new
local return is 1.077 mm. Both new return vias contact only U17's In6 field.
All four quiet fields keep one main-return connection through their own star.
62 tracks/18 vias are added; 27 tracks/10 vias are retired. Final counts are
2602 tracks, 316 vias, 36 zones and 6639 captured physical objects.

Docker was stopped; its initial native invocation failed before starting a
container. Starting Docker restored the isolated native service. First fill
then stopped on a retained In4 fill's integer-grid difference (3.05712e-7 mm²,
1.1554e-6 mm Hausdorff displacement). An explicit additional refill preserves
its outline; all 21 remaining retained fills compare exactly. An authored
U15 quiet-field extension initially had two components; an explicit bridge to
its star resolves this before board emission. No clearance rule is waived.

Native candidate 01 closed the expected ten connections with zero geometry or
parity findings and two retained ERC warnings. Its independent audit confirmed
the ten joins, no other partition changes, exact undeclared board trees, seven
rigid resistor moves and unchanged circuit values/pins. Audit implementation
needed serialization normalization for numeric S-expression atoms. Existing
same-layer ground bridge zones contact neighboring zones, so the audit checks
their actual merged copper components instead of requiring every zone record
to contain a pad/via; the quiet fields still have direct, explicit star checks.

Reference review exposed stale holes at retired ground vias. Candidate 03's
first restoration also enlarged unrelated NPTH reserves, so it was rejected
before native fill. Candidate 04 limits protective cuts to restored copper;
about 4.658 mm² of authored In5 return is recovered without that unrelated
change. Native candidate 02 passes again at 2310 opens, zero geometry/parity/ERC
errors and two warnings. Exactly ten joins reduce 3058 groups to 3048; all
other previous connections and all 1086 electrical components/3420 pin entries
are preserved. The 55 generated G_* pad IDs are aliased only by unique complete
physical/net data. Independent surface ownership and new-via drill checks pass.

All 274 complete TBP39 ground projections, all 33 fast-OV sections and all 22
own-field ILM/DVDT screens survive. Retained support coverage stays 24/28 full;
new startup coverage is only 7/16 full and remains unfinished. Source plane
keeps one 838.584705 mm² fill and all 20 contacts. Its In5 uncovered projection
falls from candidate 01's 2.462734 to 0.355273 mm² after restoration; this is
not current/thermal qualification. The two prior own-field via-edge gaps remain.
Minimum new-via drill-to-SMD copper is 0.166926 mm, hole-to-hole 0.515648 mm,
and non-owned surface quiet-ground spacing is 0.212646 mm.

Nine final views are checked: seven are pixel-identical to inspected candidate
01 views, and the changed In5 detail and inner overview are directly inspected.
Status-40 verifies 1351 direct bindings. Root and hardware READMEs now point to
status-40, current native images and the startup checkpoint; stale status-37
links and the old In6-source description are corrected. The rejected-source
subset remains 8 complete / 44 incomplete / 82 opens, not the board total.

Next: finish U40/U41 Schmitt receivers, U29/U30/U34 gate inputs/outputs, pull-up
AUX supplies and local decoupling, together with PG/EN references. Then finish
protected outputs, thermal copper, remaining analog/module supply and return
paths and signal routing. Actual loads/startup/fault limits, accepted stack,
ESS land/stencil/package inputs, exact BOM, complete installed fit, reviewed
manufacturing outputs and prototype bring-up plan remain required.


## TBP41 — relocated startup logic and verified supply/return joins

Progress: constructed, natively checked, independently audited and selected
`two-board-power-startup-logic-native-02` through status-41. The previous search
had terminated with no candidate; it was not a live job. Reproducing and
instrumenting it exposed two fanout-template defects: early diagonal escape
beside the 0.5 mm pitch pads and C74 pad crowding beside a neighboring via.
Straight pad exits and a capacitor offset pass unchanged clearance screens in
all four orientations. A wider body/tail/courtyard-aware search then places
U29/C74 and U40/C83 together while reserving all eight pin escapes per IC.

The selected revision moves U29 to (140,139) B/90°, C74 to (142.1,134.2) B/90°,
U40 to (133,156.5) F/270° and C83 to (135.1,161.3) F/270°. It restores both U29
master-enable pins to their previous group, connects the three U40 PG inputs,
three Schmitt outputs, U29 FOLLOW1 and AUX_VALID, two AUX branches, two bypass
supply pins and four main-return pins. U29 ALL_RAILS_ALLOW remains unrouted;
its reserved but unused escape is not emitted. No values/packages/nets change.

Initial routing through In2/In3 could not reach old vias enclosed by supply
planes. Allowing In6 reached them but native candidate-01 showed 2296 rather
than expected 2294 opens despite zero geometry/parity/ERC errors. Captured
partitions proved C47.2 and R112.2 had disconnected from U17's quiet star; the
In6 field split into three pieces. Six previously complete ground projections
were also lost. Candidate-01 is rejected and retains its evidence.

The revised plan reserves FOLLOW1 first, then routes FOLLOW1, PG0 and PG2 from
existing bottom branches to new transition vias outside quiet fields and inner
supply enclosures. This avoids the In6 cuts. Native candidate-02 reports 2294
opens, zero geometry/parity/ERC errors and the same two ERC warnings. The
independent audit proves exactly sixteen joins, no prior group splits, exact
undeclared board trees, four rigid moves, 1086 electrical parts/3420 pin entries,
all four star-only quiet returns, 299 prior complete reference projections,
22 own-field support sections and all 20 source-plane contacts. New tracks and
vias pass independent geometry, drill-to-SMD and hole-separation screens.

83 tracks/22 vias are added; two old U29 terminal tracks are retired. Current
counts are 2,683 tracks, 338 vias, 36 zones, 6,742 captured objects and 3,032 groups.
One In5 main-return outline extends to the logic; seven zones refill and 29
retained fills compare exactly. In4 source copper remains one 836.210216 mm²
field with all 20 contacts; its In5 uncovered area stays 0.355273 mm². All 33 fast-OV
sections retain reference. New logic coverage is only 2/32 full; retained support
is 24/28 and retained TBP40 startup is 6/15 after retiring its old master tie.
These are geometry screens, not noise/timing/current/thermal qualification.

All eleven current views were directly inspected. Status-41 verifies 875 direct
bindings; root/hardware/fabrication READMEs point to the current images, project
and status. The rejected-source subset stays 8 complete / 44 incomplete / 82 opens
and is not the board total. No commit, push, fabrication release or order.

Next: complete new logic and retained PG/EN reference paths, U29 ALL_RAILS_ALLOW,
U30/U34/U41 supply/bypass and remaining gate/receiver paths, plus PG pull-up AUX
ends. Continue protected outputs, thermal copper, analog/module distribution,
force/quiet returns and signal routing. ESS package inputs, actual startup/load/
fault limits, accepted stack/plating, exact BOM, complete installed fit,
reviewed manufacturing outputs and prototype bring-up plan remain required.
The full fabrication-readiness goal remains active and incomplete.


## TBP42 — complete current logic ground projections and controlled supply refill

Progress: selected `two-board-power-logic-references-native-02` through status-42.
The preceding status turn yielded diagnostic evidence: unexpected source-plane
changes occurred around existing clearances far from the new ground outline.
This turn compared reproducible native refills of the unchanged baseline, the
candidate without added zones, the full candidate, a source-priority variant
and a reroute-only control. All processes terminated; no live handle remains.

The added priority-1 ground field caused a 0.038572 mm² difference versus the
same reroutes without new zones. Giving the existing In4 source priority 2
eliminated that difference. A separate control substitutes only the declared
tracks/vias into the original board, preserving every original zone definition.
The corrected candidate source fill matches that control exactly. A separate
0.000255 mm² remeshing difference outside 0.8 mm via neighborhoods is reproduced
by the control and explicitly recorded; it is not hidden by a looser threshold.
The source remains one 836.210249 mm² field with all 20 original contacts.

Three ground zones are added on In1/In4 and two main In5/In6 outlines extend.
PG1 now transitions below the supply field. FOLLOW1 uses the existing enable
via and routes around quiet boundaries. Eighteen tracks and two vias replace
eight tracks and one via. No footprints, values, pin nets or native connection
partitions change. There are 2,693 tracks, 339 vias, 39 zones, 6,753 physical
objects, 3,032 native groups and 2,294 open connections. Native geometry/parity/
ERC errors are zero; the two isolated-reference warnings remain.

All 33 current non-ground U29/U40 logic sections have full adjacent-ground
projection with the recorded same-net via-antipad exclusions (TBP41: 2/32;
PG1 adds one section). All four star-only quiet returns, 305 retained complete
ground projections, 22 own-field ILM/DVDT sections and 33 fast-OV sections are
preserved. Thirty prior fills match exactly; six original fields refill.
Retained support coverage remains 24/28 and retained TBP40 startup improves to
7/15. Source In5 uncovered projection remains 0.355273 mm². These geometric
screens do not establish timing/noise/current/thermal performance.

All eleven current views were directly inspected, including eight detail views
covering the logic and complete long AUX/AUX_VALID paths. Status-42 verifies
920 direct bindings. Root/hardware/fabrication READMEs point to the current
project, images and status. The rejected-source subset remains 8 complete /
44 incomplete / 82 opens, distinct from the board-wide count. No commit, push,
fabrication release or order.

Next: complete U29 ALL_RAILS_ALLOW, U30/U34/U41 supply/bypass and remaining
startup gate/receiver and PG pull-up AUX paths. Preserve the new references
while closing retained PG/EN gaps, protected outputs and wider supply/return
and signal routing. ESS package inputs, actual startup/load/fault limits,
accepted stack/plating, exact BOM, full installed fit, manufacturing outputs
and a reviewed prototype bring-up plan remain required. The full goal stays
active and incomplete.


## TBP43 — U30/U34/U41 interconnects and adjacent ground coverage

Progress: selected `two-board-power-startup-completion-native-06` through
status-43. The preceding status-only turn verified the stopped route search
and reported current evidence; this turn completed, corrected and independently
validated the next routing checkpoint. All native/search/render processes
started in this turn terminated and were observed; no live handle remains.

Moves U30/U34/U41 and their existing C75/C77/C84 bypass capacitors. All 23
targeted interconnects now route, including FOLLOW3, analog enable, PG receivers
and analog pull-up signal ends. Five prior connections are restored; with six
main-ground joins and three local bypass joins, 27 net new connections close.
Values, packages, schematic pin assignments and every other connection remain.
The power board has 2,267 opens, 2,857 tracks, 386 vias, 39 zones, 6,964 objects
and 3,005 native groups. Six footprints / 30 pads move; all 1,101 footprints,
1,086 electrical parts and 3,420 schematic pin entries remain. Native geometry,
parity and ERC errors are zero; two retained isolated-reference warnings remain.

Candidate 03 closed 26 connections but left one obsolete PG2 stub dangling.
Candidate 04 retires that segment. A layer-hop search permitting both legs to
use screened grid paths found FOLLOW3, which candidate 05 validated as the 27th
join. Five reference gaps remained: existing In1 signal copper, tight via exits
and an In6 trace near a new bottom fanout. Candidate 06 reroutes those five paths
using native In1 ground projection and a wider bottom-reference guard. All 70
new non-ground sections now have complete adjacent-ground projection with only
recorded same-net via-antipad exclusions. No check or clearance was waived.

All four star-only eFuse quiet returns, 486 retained complete reference cases,
22 own-quiet sections and 33 fast-OV sections are preserved. In4 source copper
is unchanged with all 20 contacts. Four main-ground outlines extend, including
same-owner In5 overlap to eliminate an artificial gap between main fields.
Thirty previous fills remain exact; nine refill. Retained support coverage
remains 24/28 and TBP40 startup coverage remains 7/15. Source In5 uncovered
projection remains 0.355273 mm². These are geometry/ownership screens, not
complete timing/noise/current/thermal qualification.

All eleven current views were directly inspected. Status-43 verifies 907 direct
bindings. Root/hardware/fabrication READMEs now point to current project, plots
and evidence. The previously rejected source-net subset remains 8 complete /
44 incomplete / 82 opens, not the board-wide count. No commit, push, order or
fabrication release was made. The fabrication-readiness goal remains active.

Next: U29 ALL_RAILS_ALLOW, remaining gate/receiver paths, pull-up AUX ends,
pulldown returns, retained reference gaps, protected outputs/thermal copper,
analog/module distribution, force/quiet returns and signal routing. ESS package
inputs, real load/startup/fault limits, accepted stack/plating, exact BOM,
complete installed mechanical fit, manufacturing outputs and reviewed prototype
bring-up planning remain required.


## TBP44 — permission, pull-up and NF header routing — 2026-11-09

Selected two-board-power-permission-native-04 with two-board-fabrication-status-44.
The preceding user-facing status turn made no design change; this continuation
revalidated candidate 02 and completed native, independent and visual review.
The active fabrication-readiness goal remains incomplete and active.

U42 and C85 move; U31/C76 remain placed. Twenty-five targeted interconnects,
four main returns and one local bypass close 30 native connections, reducing
power opens from 2,267 to 2,237. Seven targeted control nets are complete:
ALL_RAILS_ALLOW, native AUX_VALID, NF_AUX_VALID, NF_GLOBAL_MASTER, ANA_PG2,
ANA_PG2_SCHMITT and E28_ANA_FOLLOW. All seven PG pull-up AUX ends join the
existing AUX group. Values, packages and schematic pin assignments are unchanged.

Candidate 02 exposed a dangling R119 via after its surface escape moved. Candidate
03 removed the obsolete proposed branch, passing native checks but leaving one
retained-reference regression and one new reference gap. Candidate 04 reroutes
one existing ANA_PG0 In6 segment around R95's supply projection and reuses the
existing AUX via at (141.5, 136.5) for R107, removing its extra transition via.
The earlier cleanup also rerouted long In6 paths, shortened R115's supply branch
and added a main-ground stitch near PG0. No clearance or quiet-return rule was waived.

Current copper has 3,039 tracks, 435 vias, 39 zones, 7,195 objects and 2,975 native
groups. The pass adds 183 tracks and 49 vias and retires one replaced track.
Two footprints / ten pads move; all 1,101 footprints, 1,086 electrical parts and
3,420 schematic pin entries remain. Four main-ground outlines extend; 28 old
fills remain exact and eleven refill. Native geometry/parity/ERC errors are zero,
with the same two isolated-reference ERC warnings.

The independent audit verifies all 30 joins and every other native group,
1,015 retained complete reference cases, 22 own-quiet sections and all four
star-only returns. All 72 new/replacement non-ground route sections have complete
adjacent ground projection with explicit same-net via and plated-pad antipad
exclusions. All 70 TBP43 sections (including restored ANA_PG0) and 33 fast-OV
sections pass their follow-up screen. Retained support remains 24/28; TBP40
startup remains 7/15. These are geometric screens, not timing/noise qualification.

In4 source copper remains one connected field with all 20 contacts, now
834.498043 mm². Its 1.712206 mm² refill change includes 0.0160289 mm² beyond the
ordinary local-via screen. A controlled unchanged refill reproduces the baseline
exactly; the correct isolated AUX via reproduces that extra area. The first
experiment was rejected after the audit caught KiCad reassigning its unattached
via to ground. The second locks the AUX net and asserts it before/after filling;
the saved net is also independently checked. Unexplained change is below 1e-6 mm².
Source In5 uncovered projection is now 0.349983 mm²; source qualification is pending.

Nineteen current copper views were directly inspected. Status-44 checks 977 direct
source/artifact bindings. Root/hardware/fabrication READMEs now select the new
project and current images. The historical rejected-net subset remains eight
complete / 44 incomplete / 82 opens, not the board-wide count. No commit, push,
order or fabrication release was made. All processes started this turn have
terminated and their results were observed.

Next: analog/digital pulldown returns with reviewed local ownership, full startup
review, retained reference gaps, protected outputs/thermal copper, analog/module
supplies, force/quiet returns and signal routing. Approved ESS inputs, real
load/startup/fault limits, accepted stack/plating, exact BOM, installed housing/
cooling/harness fit, manufacturing outputs and reviewed prototype bring-up planning
remain required. The signal board still has 251 opens and an unplaced ESS codec.

Final TBP44 verification checked 996 source/artifact bindings and 204 local
documentation links; the scoped git diff whitespace check passed.

## Analog local-control construction — 2026-11-09

Previous goal turn made progress by completing native placement checks. This
turn kept TBP44 selected and developed the next analog-control routing candidate.
No goal completion or fabrication release is claimed.

Native KiCad poses confirm twelve local component moves and three face changes
for U13/U14/U32 support parts. All 24 pad positions, sides and net names match
the planned transforms. Native-footprint mechanical screens pass for the moved
parts within the provisional placement envelope; complete installed fit is still
unverified. R98 was reversed after routing showed its original orientation
forced a 6.994 mm detour; the revised controller route is 2.802 mm.

Existing U13/U14 power-good escapes blocked their ground-pin fanouts. Replacing
those escapes allowed all three controllers' control-ground, ILM and DVDT pins
to escape without relaxing clearance. The initial complete candidate passed
geometry screening but its reference check found retained PG1 copper beneath
U14 support routes and a proposed PG1 restoration beneath U32 support routes.
These interrupted 0.274093 and 0.140223 mm² of required quiet reference. The
revised plan removes the obstructing PG1 branch and restores both PG1 branches
around the required regions.

`staging/two-board-analog-cell-plan-03` now contains a reproducible 43-path
candidate with 100 proposed tracks and nineteen vias, replacing 83 tracks and
nine vias. The independent geometry review passes 593 nearby-copper/route-pair
checks, native pose identity, separate ground-owner clearance, mechanical
placement and physical retained-net restoration contacts. Six minimum In1/In6
quiet-reference/contact regions pass ownership and foreign-copper screens.
These are candidate screens, not new board-wide DRC or connectivity results.

Next: construct connected quiet regions with pin-8-only main-ground stars,
review/shorten the long surface returns (R100's candidate is 14.137 mm), trim
main fields around non-star quiet copper, refill and verify source/inlet copper,
all retained groups and old/new references. Then run native DRC/parity/ERC,
recapture connectivity and inspect actual copper before selecting a revision.
The current selected counts remain 2,237 power opens and 251 signal opens;
the ESS footprint, remaining routing, load/fault/thermal review, accepted
manufacturing stack, full installed fit and fabrication package remain open.

## Analog quiet-ground construction and native checks — 2026-11-09

The previous goal turn made progress by completing routing-plan and reference
screens. This turn built and natively checked the analog quiet-ground candidate.
TBP44 remains selected because the broader reference audit identifies gaps.

Reversed R100 and replaced nine 4.389–14.137 mm surface returns with local
1.000–1.281 mm quiet-via escapes. Seven owned regions now serve U13/U14/U32;
U32's separate capacitor reference field reaches its pin-8 star through an
explicit quiet stitch and the In1 field. The three stars alone contact main
In5 ground. Non-star vias are excluded from pre-existing ground fields.

Native candidate 01 caught a shared enable backbone retired with the remote
R100 branch, plus two redundant U13 same-face vias. Plan 05 restores original
objects 101622d7-ffbf-5fc2-bebb-235a4d8bb14c,
8a98ed6e-abed-5551-8c60-662a068b4343 and
99db5e9c-4e5b-5c0b-89f8-e11491e7bd2b, and omits those two vias.
No rule was disabled. Small unanchored authored fragments left by main-zone
trimming were discarded only after proving each lies wholly inside a declared
foreign-copper clearance and has no ground contact.

Candidate `two-board-power-analog-cells-native-02` adds 73 tracks, 27 vias and
seven zones, retiring 81 tracks/eight vias and moving twelve footprints/24 pads.
It has 46 zones and 7,206 copper objects. Native geometry/parity findings are
zero; ERC retains two warnings. It closes 26 connections: 2,237 -> 2,211 opens.
Thirty-one old zone fills remain exact; eight existing zones refill.

The independent connectivity audit proves all 26 joins, every other native
group, unchanged part/netlist identities, three new star-only quiet networks,
four retained digital islands, and complete own-quiet coverage of all analog
ILM/DVDT routes. The native pose comparison accounts only for the validator's
known relocation of an unchanged canonical path field; all other footprint
content is compared exactly.

The broader reference audit finds two regressions in 1,569 retained cases:
ANA_FOLLOW2 track 9770d677-f9b1-5431-97a0-f8f2ad480648 loses 0.045128 mm² on
In1; AUX track 43a4da19-9273-5f60-977c-c7474fca0eea loses 0.106226 mm² on In6.
Four new control paths also have gaps: U13/U14 PG escapes and the R96/R100
enable connections. Exact geometry/areas are in analog-reference-review.json.
These six gaps are the immediate next work; the candidate is not selected.

Five complete local copper views (F/B/In1/In6/In5) were directly inspected.
The first viewport omitted western geometry because SVG export offsets the
board origin; corrected analog-complete views show all three controllers.
This is not full-board visual or installed-fit acceptance. All processes
started this turn reached terminal state and were observed. No commit, push,
order or fabrication release was made. The wider fabrication goal remains
active, with the signal board's 251 opens, ESS input, remaining routing and
manufacturing/mechanical/electrical qualification still unfinished.

## TBP45 selected — analog reference corrections — 2026-11-09

The preceding user-status turn did not change the design. This goal turn
revalidated the placement-search evidence and made concrete design progress.
Plan 06 and native candidate 03 are now selected as TBP45 (status 45).

Repositioned/reversed R100 to (51.75, 114.5) mm, replacing its reference-crossing
enable route with a 2.200 mm local path. Its quiet escape is 3.097 mm; the other
local passive ground escapes retain their shorter plan-05 routes. Reconstructed
PG0 in two branches around retained/new back-layer reference projections, keeping
the old pull-up via, monitor backbone and shared enable trunk. Two additional
old PG0 segments retire. Extended the U13/U14 front references and retained
U32 enable reference. R96's isolated In6 reference now connects through the
existing R97 quiet via and U13 In1 field; eight owned regions replace seven.

Native candidate 03 has 2,211 opens, zero geometry/parity/ERC errors and two
retained warnings. It preserves the 26 joins from TBP44, every other native
group, all part/pin identities, three star-only analog quiet networks and four
retained digital quiet networks. All ILM/DVDT own-field projections pass.
The broader audit reports zero gaps in 1,567 retained reference cases and all
26 new non-ground paths. The prior six gaps are resolved. The retained-case
count drops by two because two old PG0 segments are replaced; their replacement
branches are checked among the new paths.

Current counts: 1,101 footprints, 1,086 electrical components, 3,420 schematic
pin entries, 3,481 mapped pad instances, 3,029 tracks, 454 vias, 47 zones,
7,204 captured objects and 2,949 native connection groups. This pass adds
73 tracks/27 vias/eight zones, retires 83 tracks/eight vias, moves twelve
footprints/24 pads and flips three passives. Six existing outlines change,
eight old zones refill and 31 old fills remain exact.

A separate supply-plane review preserves all eleven contact sets and region
counts with unchanged authored supply outlines. Only In2/In3 inlet fills
change (now 5,503.766457 and 5,527.235161 mm², respectively); each remains one
connected region. These checks do not qualify current sharing or resistance.
The earlier TBP35 resistance model remains historical.

Inspected sixteen current views: five complete analog details, eight wider
views covering the full former/retired copper extent, front/back overviews and
the six-inner-layer contact sheet. Status 45 verifies 901 direct bindings.
Root, hardware and fabrication READMEs now identify TBP45 and current native
images. Frozen earlier scripts/reports remain intact; new builders/reviewers
and plan/pose/native directories retain reproducible evidence.

All started processes reached observed terminal states. No commit, push,
order or fabrication release was made. The goal remains active: 2,211 power
opens and 251 signal opens remain, along with R104/other startup returns,
earlier support/PG gaps, protected outputs, source/input and load/return loops,
ESS footprint inputs, accepted stack/BOM, complete installed mechanical fit,
loaded electrical/thermal verification and reviewed manufacturing/bring-up work.

## TBP46 and TBP47 selected — digital return and reference repairs — 2026-11-09

The preceding user-status turn was no progress: it inspected and reported the
saved state without changing the design. This goal turn revalidated the saved
TBP45 baseline and the failed digital-return candidate, then completed two
checked design revisions. TBP47 is now the selected power-board checkpoint.

TBP46 relocates R104 to (141.75, 111.5) mm on the back face without rotation or
face change. The 2.010 mm enable trace reaches the existing master-enable via;
the 1.482 mm ground trace reaches U15's existing owned surface quiet copper.
No new via is added. The remote R104 leaf branch and via retire. The preceding
candidate's two retained-reference regressions are corrected by replacing the
B-layer dogleg at (139.5, 112.5) with a direct segment between the retained
(139.5, 113) via and (132.25, 112.5) bend. This avoids the extended quiet-field
boundary without expanding the reference audit's excluded areas.

Author 03, filled 03, native 03 and capture 2210-digital-return-03 pass. The
independent audit proves exactly one join, from R104 ground to U15's owned
return, and preserves every other native group. All seven quiet networks
retain their original contacts, connected graphs and pin-8-only main-ground
stars. All eleven supply planes are unchanged. Three tracks replace four;
one via retires. Two authored outlines change, five zones refill, and 42 fills
remain exact. Both new non-ground paths and all 1,610 retained complete
reference cases pass. The twelve earlier incomplete paths show no regression.
Fourteen current views were directly inspected. Status 46 binds 869 direct
sources/artifacts; its final check verified 885 bindings and 201 local links.

A native startup survey now records every pad group on 91 nets containing
E28_, ANA_PG or DIG_PG, plus PWR_ALL_RAILS_ALLOW. Thirty-two nets require 60
additional joins. MASTER_ENABLE still has five groups; TIMEOUT_CT has six;
RESET has five. Nearby pad-pair distances are survey hints, not accepted
routes. This scope does not include every supply/ground connection required
by the startup circuit and does not establish functional correctness.

TBP47 then repairs the four small support-reference gaps by rerouting the
U17 ILM approach, the R114-C47 DVDT capacitor link and both C48 supply-via
approaches. The new paths stay over existing filled ground; the via-clearance
exclusions remain unchanged. Six surface segments are replaced by nine, with
no component moves, added/removed vias, zone changes or refills. The native
board and independent full-topology audit preserve every group, other object,
zone outline and filled plane exactly. All four new paths and 1,610 retained
complete reference cases pass. All 22 digital ILM/DVDT own-field paths are now
complete. Four of the twelve recorded incomplete cases are repaired; eight
startup-reference gaps remain unchanged.

The remaining-reference plan binds the TBP47 capture and records those eight
paths. Trial 0.4 mm field extensions conflict with another controller's quiet
field for five paths: U16 PG/enable and R108/R107 conflict with U17, and R103
conflicts with U16/U17. The report separately records actual projection overlap.
U15 PG, U17 enable and U33 enable have no competing-field intersection in that
trial. This is diagnostic geometry, not an authored or accepted zone repair.
Further work must preserve owned ground graphs, star isolation and every
retained signal reference; longer back-face PG paths may require rerouting.

TBP47 native checks report 2,210 power opens, zero geometry/parity/ERC errors
and two retained isolated-reference warnings. Counts are 1,101 footprints,
1,086 electrical parts, 3,420 schematic pin entries, 3,481 mapped pad instances,
3,031 tracks, 453 vias, 47 zones, 7,205 captured objects and 2,948 native groups.
Eight current views were directly inspected, covering every replaced segment
and the full copper overviews. Status 47 verifies 594 direct bindings. The
final verification checks 609 bindings and 206 local documentation links.
Root, hardware and fabrication READMEs now identify TBP47 and current images.
Historical scripts, reports and selected-board snapshots remain frozen.

All processes started this turn reached observed terminal states. No commit,
push, order or fabrication release was made. The full goal remains active:
2,210 power opens and 251 signal opens remain, plus the eight recorded startup
reference gaps, startup functional verification, protected outputs, source/load
loops, analog/module and force/quiet-return distribution, approved ESS package
inputs, accepted stack/BOM, complete installed mechanical/cooling/harness fit,
loaded electrical/thermal verification, manufacturing outputs and whole-unit
prototype inspection/bring-up requirements.

## 2026-11-09 — TBP48 coordinated startup-reference repair

The preceding status-only turn was no progress toward the board changes. This
turn revalidated the active TBP47 checkpoint and the completed trial-02 supply
review, then continued the five reference defects found in that candidate.

Trial 03 moved the PG1 transition, corrected the PG0 back route, rerouted the
FOLLOW3 departure and added a main-ground via at (146.75, 125.25). Native fill
confirmed that this restored the disconnected In1 lobe. Three remaining
reference defects around U33 required a coordinated transition/backbone change.
The strict topology reviewer also rejected duplicate electrical-footprint path
syntax inserted by the historical native validator: the diagnosis records
1,086 identical duplicate path entries and no other undeclared nonrouting,
nonzone syntax changes. Trial 03 remains unselected; later validation uses
native_two_board_power_v2. The independent syntax check was not relaxed.

Trial 04 relocates U33's enable transition to (146.8, 126.6), restores its
front enable and back pull-up branches, reroutes the FOLLOW3 departure and the
PG0 In2 backbone, and keeps the PG0/PG1 repairs and ground-lobe anchor. It
replaces 17 tracks and three vias with 25 tracks and five vias. Seven ground
outlines change, 16 existing zones are explicitly refilled and 31 other fills
remain exact. No components, pad positions, values or schematic pin nets change.

Native checks pass at 2,210 opens with zero geometry/parity/ERC errors and two
retained isolated-reference warnings. The independent audit preserves every
native connection group, every other physical object and all seven quiet
networks' contacts, ownership connectivity and pin-8-only main-ground stars.
All eleven supply-plane contact sets, region counts and authored outlines are
preserved; three supply fills change locally. This is not current, thermal,
noise, parasitic or resistance qualification.

The complete coverage audit passes 1,611 retained reference cases, nine new
paths, all eight previously incomplete startup paths and all 22 digital
ILM/DVDT own-field paths. The moved U33 via physically overlaps the retained
FOLLOW3 back trace by 0.11507721051108749 mm² and shares its native group. The
new audit compares retained routes against current via geometry: a new via's
standard 0.515 mm exclusion is allowed only after direct copper contact and
same native group are verified. Existing tolerances and exclusion radii are
unchanged. This avoids counting a required same-net transition antipad as a
missing reference, while also removing exclusions for retired vias.

Nine native copper views were directly inspected: six local layer details,
both surface overviews and the six-inner-layer contact sheet. TBP48 selects
power-startup-references-native-04. Counts are 1,101 footprints, 1,086 electrical
components, 3,420 schematic pin entries, 3,481 mapped pads, 3,039 tracks,
455 vias, 47 zones, 7,215 captured objects and 2,948 native connection groups.
Status 48 verifies 620 direct bindings; final verification checks 636 bindings
and 204 documentation links. The root, hardware and fabrication READMEs now
identify TBP48 and its current images. Bound scripts, plans and reports are
frozen; earlier trial snapshots remain diagnostic evidence.

All processes started this turn reached observed terminal states. No commit,
push, order or fabrication release was made. The full goal remains active.
No new electrical joins were closed this pass: 2,210 power opens and 251 signal
opens remain. Next is the 60 surveyed startup joins across 32 nets and startup/
fault behavior verification, followed by the remaining protected outputs,
source/load loops, analog/module and force/quiet-return distribution and signal
routing. Approved ESS inputs, accepted stack/plating/BOM/process, full installed
housing/support/cooling/harness fit, loaded electrical/thermal qualification,
manufacturing outputs and whole-unit prototype inspection/bring-up requirements
also remain unfinished.

## TBP49 — local startup bypass/ground cells and feedback joins

Continued the active two-board fabrication-readiness goal from TBP48. The
preceding pass repaired the eight recorded startup-reference gaps without
closing electrical joins. This pass closes 11 native connections while
preserving those repairs. The goal remains active and incomplete.

A fresh TBP48 named-net survey confirmed 60 missing joins across 32 of 91
startup nets. A separate U18–U28 supply/bypass/ground inventory exposed work
outside that named-net selection. Planning targeted local cells before source
distribution. Early plans failed to find safe reference/placement combinations
for all cells. The first routed native trial had nine geometry findings:
C66 overlapped existing FAULT routing and C73 overlapped a retained transition.
The planner now checks complete moved-pad copper against retained surface
copper, with regression assertions for both rejected placements. Trial 01
remains unselected. Plan 05 and native trial 03 are the selected sources.

C66 moves to (41.6125, 153.95); C73 moves to (97.15, 157.95) with a 90-degree
rotation delta. U21/C66, U25/C70 and U28/C73 gain local bypass links and both
IC/capacitor ground returns. Bypass traces are approximately 2.30, 3.30 and
2.30 mm. U21.3–.4 and U22.3–.4 gain adjacent feedback links. Four U21 FAULT
back tracks are replaced with a back fanout, via at (39.7, 152.2) and front
continuation to J9.4. The pass adds 20 tracks and seven vias, retires four
tracks, moves two capacitors and changes no ICs, values or schematic pin nets.
Four main-ground zones are refilled; 43 other fills and all outlines remain
exact. These ICs are not yet connected to the auxiliary regulator's output.

Native trial 03 passes at 2,199 opens with zero geometry/parity/ERC errors and
two retained isolated-reference warnings. Independent review confirms all 11
intended merges and preserves every other native group and physical object.
All seven quiet-ground networks retain their contacts, connected ownership
graphs and pin-8-only main returns. The reviewer compares transformed footprint
syntax canonically, avoiding a Python-float versus parsed numeric-atom mismatch
without weakening the native pad-position or metadata checks.

The first reference-review execution stopped because an existing In1 polygon
had no direct native-object contact. The prior reference reviewer already
excluded such polygons. The corrected reviewer explicitly records and excludes
this 16.91382794871698 mm² fragment in zone d5d0775a-fea7-5f03-bf2b-e5c7ca690024,
and requires exact before/after preservation. It does not credit this copper
as usable return coverage. The completed review passes 1,637 retained reference
cases, eight new non-ground paths and nine previous startup-repair paths.
All eleven supply-plane fields and all seven quiet-ground fields remain exact.
The new same-net FAULT transition and plated J9.4 contact receive the standard
clearance exclusions; no tolerance or exclusion radius was widened.

Thirteen native copper views were directly inspected: ten local details, both
surface overviews and the six-inner-layer contact sheet. No additional visual
findings were recorded. TBP49 selects power-startup-cells-native-03. Counts are
1,101 footprints, 1,086 electrical parts, 3,420 schematic pin entries, 3,481
mapped pads, 3,055 tracks, 462 vias, 47 zones, 7,238 objects and 2,937 native
connection groups. Status 49 verifies 650 direct bindings. Final verification
checks 671 bindings and 210 local documentation links. Current root/hardware/
fabrication READMEs identify TBP49 and use its current native power images.
Bound scripts, reports, plans and prior snapshots remain frozen.

The updated named-net survey records 58 missing joins across 32 of 91 nets.
The cell survey separately records missing bypass/ground work for U18/U19/U20
and U22/U23/U24/U26/U27. Existing In6 traces obstruct reference coverage at
U22/U23/U27; U26 needs a coordinated ground-outline review, and U24 needs a
clear referenced bypass route. Sense and timing placement remains to be
reviewed. All surveyed ICs still lack AUX regulator source connectivity.
Continue this work and startup/fault verification before protected outputs,
source/load loops, analog/module distribution, force/quiet returns and the
remaining signal routing. Approved ESS inputs, accepted stack/plating/BOM,
complete installed housing/support/cooling/harness fit, loaded electrical/
thermal qualification, manufacturing outputs and prototype bring-up remain
unfinished. Signal retains 251 opens and its missing codec footprint.

All processes started for this checkpoint reached observed terminal states.
No commit, push, order or fabrication release was made. The active goal is
still to make the complete two-board design fabrication ready.


### TBP50 candidates — remaining local startup cells; reference audit unresolved

TBP49 remains the selected checkpoint. The remaining-cell candidate completes
local bypass and both ground returns for U18/U19/U20/U22/U23/U24/U26/U27,
preserving the three previously completed cells. U19 gains its additional
AUX pin tie and U22 its additional grounded inputs. All eleven U18–U28 cells
still lack source connectivity to the AUX regulator. Native candidate 02
(`two-board-power-startup-remaining-native-02`) closes 27 connections, reducing
power-board opens from 2,199 to 2,172, with zero geometry/parity/ERC errors
and two retained warnings. Independent topology review preserves every other
native group and object, including all seven quiet-ground networks.

The candidate moves five capacitors, adds 69 tracks and 20 vias, and retires
112 tracks. Six In6 signal detours preserve the new local routes' reference
coverage; U20 also receives a front-layer master-enable bridge. One main In6
ground outline is extended near U26. Four main-ground fills change, while the
other 43 fills remain exact. The first remaining-cell reference audit found
three retained AUX_RESET_N reference regressions. Candidate 02 reserves both
back and In5 reference corridors, reducing but not eliminating those gaps.
Its completed audit checks 1,555 retained reference cases, 18 new non-ground
paths and nine earlier startup paths. All new and prior startup paths pass,
but three retained In5 AUX_RESET_N tracks still lose In6 ground coverage:
0.0008372158998315204, 0.001083161691655573 and 0.0012962537660680786 mm².
These exceed the unchanged 1e-6 mm² threshold. Candidate 02 is not selected.
Its report and successful builders/reviewers remain frozen. Current candidate
02 visual review has inspected only four west detail views (back, front,
In1 and In5); its remaining nine views have not yet been reviewed.

The current AUX distribution inventory records 81 IC supply pins: eight
connected to the regulator and 73 unconnected. Nominal attached capacitance
is 28.5 µF. Actual current, startup loading, effective capacitance and installed
thermal performance remain unqualified; no source-distribution acceptance is
inferred from this inventory. Named startup nets still have 58 missing joins
across 32 of 91 surveyed nets. Signal routing still has 251 opens and the
missing approved ESS codec footprint.

A follow-up geometric inspection found the remaining reset-reference gaps
beside the timeout detour and reset via clearance. The main In6 zone has a
0.25 mm minimum copper thickness, so clearance-only planning can leave copper
slivers removed by native filling. Planner v4 first tried a global extra
margin, stopping before any output because it encountered an unrelated
ANA_PG0 internal branch. The corrected unbound script scopes the additional
0.125 mm routing margin to the three recorded regression corridors, retaining
the original retirement set and the unchanged reference-audit thresholds.
`two-board-startup-remaining-plan-06/plan.json` now contains six resolved
detours, including a 26.159 mm timeout route. It is a plan only: no candidate
03 board has been authored, filled or natively verified yet. Next: author
from plan 06, refill, run native/topology/reference audits, then complete
visual review and status selection only if all pass. Prepared status-50 and
checkpoint-v4 scripts still point at rejected candidate 02 and must be updated
before use. All processes from this progress pass reached terminal states.
No commit, push, order or fabrication release was made.


### TBP50 selected — all U18–U28 local bypass and ground cells complete

The previous goal turn made progress: the completed candidate-02 reference
audit established three remaining AUX reset coverage regressions, and the
geometric diagnosis changed the next routing action. This continuation
implemented plan 06 as candidate 03 and verified the resulting native board.
All three previously failing retained reference areas now measure exactly
0.0 mm² uncovered, without changing the 1e-6 mm² audit threshold, exclusions
or nominal design clearance. The additional planning space accommodates the
main In6 plane's 0.25 mm minimum copper thickness.

The isolated KiCad refill verifies all 43 untouched zone fills. Native
candidate `two-board-power-startup-remaining-native-03` passes at 2,172 opens,
with zero geometry/parity/ERC errors and two retained isolated-reference
warnings. The independent topology review confirms all 27 intended merges
and preserves every other native group and physical object. All seven quiet
networks retain connected ownership and pin-8-only main returns. All eleven
supply-plane fields and all seven quiet-ground fields remain exact. The
reference review passes 1,555 retained cases, 18 new non-ground paths and nine
previous startup-repair paths. The historical unanchored In1 ground fragment
remains exact and is excluded from credited reference copper.

The pass adds 69 tracks and 20 vias, retires 112 tracks, moves C57/C59/C67/C71/
C72, extends one main In6 ground outline near U26, and refills four main-ground
zones. No ICs, values or schematic pin nets change. Final counts are 1,101
footprints, 1,086 electrical parts, 3,420 schematic pin entries, 3,481 pads,
3,012 tracks, 482 vias, 47 zones, 7,215 captured objects and 2,910 native
connection groups. All eight remaining U18–U28 local bypass/ground cells are
complete, preserving the previous U21/U25/U28 cells. U19's extra supply pin
and U22's additional grounded inputs are connected. None of these eleven ICs
has AUX regulator source connectivity yet.

Thirteen candidate-03 copper views were directly inspected: both surface
overviews, all six inner layers on the contact sheet, and ten west/east local
details. No additional visual findings were recorded. The visual report binds
those current images and render/native/topology reports. New startup-net,
cell and AUX inventories bind the current candidate. The named-net survey
still records 58 missing joins across 32 of 91 nets. The AUX inventory has
230 terminals, 81 IC supply pins (eight source-connected, 73 unconnected),
87 direct capacitors totaling 28.5 µF nominal, eleven source-connected
capacitors and twenty main-ground-return-connected capacitors.

Status 50 selects candidate 03 after checking 654 direct source/artifact
bindings. Final verification passes 675 bindings and 216 local documentation
links. Root, hardware and fabrication READMEs now identify TBP50 and use its
current native power images; earlier images remain historical evidence only.
Bound builders, reviewers, plans, reports and selected documentation snapshots
remain frozen. The three earlier candidate-02 regression records are retained
and explicitly compared in the candidate-03 report.

Next work is the current AUX electrical budget and source acceptance: resolve
actual startup/run/fault and transition loads for the present IC families,
resistor/output ownership (including NF loads), effective capacitor/startup
requirements and installed LDO thermal limits. The historical 90 mA budget
cannot be transferred directly. U42 metadata is corrected, but its changed
family/active inputs and the real POWER_READY load still need current-budget
reconciliation. Then complete AUX distribution and the remaining startup
connections, protected outputs, source/load loops, analog/module distribution,
force/quiet returns and signal routing. Signal retains 251 opens and the
missing approved ESS codec footprint. Complete installed housing/support/
cooling/harness fit, accepted stack/plating/BOM, loaded electrical/thermal
qualification, manufacturing outputs and prototype bring-up remain unfinished.

All processes started in this continuation reached observed terminal states.
No commit, push, order or fabrication release was made. The original complete
two-board fabrication-readiness goal remains active and incomplete.


### AUX current reconciliation — explicit output ownership and READY load

The previous goal turn was progress: TBP50 selected and independently verified
the remaining startup-cell routing, repaired three reference regressions and
updated the current documentation. This continuation keeps TBP50 copper and
its bound documentation unchanged and begins the actual source-load ledger.

[Current reconciliation](staging/two-board-aux-current-reconciliation-01/README.md)
binds TBP50's current netlist, status and AUX inventory. It identifies 25
direct ground resistors driven by packages with an AUX supply connection:
22 logic-output resistors belong to AUX, two (N_R61/N_R78) belong to RAW5,
and E_R94 belongs to the separate reference-output load calculation. The two
dual-supply translators must use their actual output-side supply: N_U16's
B outputs use RAW5 at pin 8, while N_U27's B outputs use AUX at pin 8. Both
DIR pins are tied to their own VCCA. Counting every output of an AUX-connected
package as an AUX load is incorrect.

At the existing conditional 2.7 V / 97%-of-nominal resistor requirements,
the 22 direct logic-output loads total 1.55709692433621 mA. Twelve NF-side
AUX branches contribute 0.6193912871350693 mA inside that sum. U42's two
47 kΩ NF pulldowns contribute 0.1184470278569862 mA inside both applicable
subsets. These are not additive subtotals. The historical nine-pulldown term
has no complete per-reference ownership proof for today's circuit, so no
amount is deducted from the NF aggregate reserve or the E28 external-output
reserve. The new ledger explicitly records R3/R10, R15–R22 and R68/R85.
Raw resistor values, actual driver pins, connected receivers and source rails
are bound to the netlist. Input leakage and dynamic currents are excluded,
and ordinary E-side total-drift bounds remain receiving requirements.

The present shared POWER_READY divider draws 158.823529 µA nominally at
2.7 V with zero injected currents. The old 2 µA released-state allowance does
not cover that path. Across 512 combinations of initial 1% resistor corners,
2.3–2.7 V, allocated 0–25 µA EN sourcing per buck and ±10.15 µA READY-node
current, AUX current is 92.04868957484004–169.98074866310175 µA. These are
conditional allocations, not guaranteed device envelopes. J103/J22 external
loads are assumed absent. The asserted-state full pullup is already present
in the historical fault budget and must not be added again.

Official TI LVC3G17, HCS08, LVC2T45 and TPS7A16 PDFs were fetched into a new
primary-evidence folder. The PDF skill was used to visually inspect six
relevant pages. LVC3G17 delta-ICC's specified supply range begins at 3 V;
HCS08 input-leakage maximum is specified at 6 V with rail-valued inputs.
Neither becomes an actual-AUX-band transition guarantee. TPS7A16's DELAY
capacitor sets PG assertion timing after the output threshold; its internal
output soft start is distinct. P_C110 cannot supply a validated AUX ramp for
the capacitor-charge calculation. Native PDF rendering emitted a font-cache
warning but produced legible inspected pages; no install or approval rejection
occurred. No PDF was authored or edited.

Independent verification checks exact coverage and ownership, rejects missing,
duplicate and VCCA-for-all-outputs mutations, recalculates resistor sums, and
checks all 512 READY matrix cases against a separate eliminated-node closed
form and KCL. Final review verifies 29 report bindings, three local links and
unchanged TBP50 status/documentation snapshots. Successful scripts and reports
are frozen. All spawned shell processes reached terminal states; no subagents
were used. No PCB changes, commit, push, order or fabrication release occurred.

Continue with the 45 direct AUX resistor terminals' complete network/state
accounting, then reference/OPA/isolated-driver paths, package and input currents,
external/clamp behavior, switching loads, capacitor derating/ramp and installed
thermal limits. Source current remains unqualified; historical aggregate
budgets cannot yet be accepted. The complete two-board goal remains active:
2,172 power opens, 251 signal opens, the approved ESS footprint, installed
housing fit, accepted manufacturing inputs, loaded unit qualification and
reviewed manufacturing outputs remain unfinished.

### AUX direct resistor networks — conditional DC accounting

The next AUX analysis follows all 45 direct AUX resistors through 44 disjoint
networks containing 77 resistors. Its conditional sum of network maxima is
15.47489444762223 mA across 1,044 cases. It includes shared feedback paths,
POWER_READY, and RUN switch ON/OFF with released or clamped RUN. The independent
verifier checks exact coverage, closed forms, KCL, power conservation and 107
leakage transfer coefficients. All checks pass; the largest closed-form current
difference is 2.88e-18 A.

The [saved analysis](staging/two-board-aux-resistor-networks-01/README.md) records
the assumptions and exclusions. Zero input leakage, ideal sinks and independent
3% resistor receiving bounds do not establish a complete actual rail-current
limit. No historical reserve is deducted. These networks are disjoint from
the previously reconciled output resistors. The next electrical work is the
remaining device, reference, driver, external and dynamic current accounting,
followed by startup and installed thermal acceptance.

No PCB routing changed in this calculation. TBP50 remains selected, with 2,172
power opens and 251 signal opens. The README already reflects the two main
PCBs, retained Daisy Seed 3 and current layout images. No commit, push, order
or fabrication release occurred. The fabrication goal remains active.

### AUX reference and amplifier output ownership

The previous goal turn was progress: it completed and saved the direct-resistor
analysis summary, binding checks and worklog. This continuation adds the
[reference and amplifier analysis](staging/two-board-aux-reference-amplifier-01/README.md)
from the current TBP50 netlist. No copper or selected documentation changed.

All 14 direct reference branches are traced through 39 resistors. Twenty-one
are the same seven feedback/pullup networks already covered from the AUX port;
their AUX currents are not counted again. The remaining 18 resistors are newly
covered here. With ideal comparator sinks, zero leakage, fixed reference
1.2375–1.2625 V, AUX 2.3–2.7 V and independent ±3% resistor receiving factors,
the reference's sum-of-branch-extrema interval is 0.1874374948269624 to
0.20407881684910448 mA. It stays a net source in this model even when released
feedback paths inject current. Comparator pins, external connectors and
capacitor charging remain separate loads.

E_U8 and N_U13 contain four AUX-powered OPA2333 channels. Their 17 input,
feedback and sense resistors are disjoint from both previous inventories.
The E-side N19 input chain is E_R49 + E_R50 = 156.2 kΩ. At nominal source and
protected rails of −19/−12 V, ideal linear amplifier output current totals
0.4780359832793554 mA, with a conditional sum of corner maxima of
0.4928206013189233 mA. Sense branches have zero DC current only under the
zero-leakage assumption. Twelve pin-injection transfer coefficients support
later leakage accounting. Rail extrema, saturation, startup, input clamp and
dynamic loads remain outside this model.

Independent verification checks exact netlist paths and values, all 632
reference cases and 80 amplifier cases, four nominal amplifier cases, the
12 transfer coefficients, KCL and power conservation. The maximum difference
against independent closed-form currents is 6.39e-18 A. During development,
checks required explicitly treating the passive-labelled source rail as a
boundary and correcting the expected amplifier-resistor count to the actual
17. Both were corrected before the first successful report was emitted;
successful scripts and evidence are frozen.

The PDF skill was reused for read-only visual inspection of REF35 page 5 and
OPA333 page 7. Existing primary PDFs match revisions of the official TI sources
opened this turn. OPA quiescent current is per amplifier; four channels give a
112 µA sum at the full-temperature table condition, not a complete actual-unit
bound. Its full-temperature input-bias entry is typical only. REF35 EN current
also needs ownership because EN is tied to AUX. The primary review retains
test conditions; no package-current acceptance is inferred. A font-cache
warning did not prevent rendering. No PDFs were authored or edited.

Final review checks 17 report bindings, four local links and unchanged TBP50
status/documentation. No live processes remain, no subagents were used and no
commit, push, order or fabrication release occurred. Continue with isolated
driver input/supply ownership, remaining package and pin currents, switching
and external loads, startup and thermal limits. The complete two-board goal
remains active with 2,172 power opens, 251 signal opens, missing approved ESS
footprint and unfinished installed fit/manufacturing acceptance.

### AUX isolated drivers — shared enable and actual gate loading

The previous goal turn was progress: it completed the current reference and
four-amplifier output accounting with independent checks. This continuation
adds [four isolated-driver networks](staging/two-board-aux-isolated-drivers-01/README.md)
from the selected TBP50 netlist. Each Si8751 input has a 100 Ω series resistor
and 10 kΩ pulldown, driven by E_U29.7 on the common E28_MASTER_ENABLE net.
The four branches add 1.1023782790650209 mA at 2.7 V and independent −3%
resistor receiving factors. E_R104/E_R141 add 0.33757402939241064 mA already
present in the earlier output ledger. Their combined resistive demand is
1.4399523084574315 mA; the older two branches must not be counted twice.

With fixed MASTER HIGH ≥1.85 V and LOW ≤0.45 V, zero input leakage and
independent ±3% resistor factors, driver-input extrema are 1.8305620728348464 V
HIGH and 0.4458016735596807 V LOW. These give 0.4805620728348463 V HIGH and
0.12919832644031926 V LOW conditional margins against the strictest Si8751
thresholds over AUX 2.3–2.7 V. The 3.1 mA output-current screen has
1.6600476915425684 mA residual after resistors. These are receiving envelopes,
not qualification of all master receivers, leakage, connectors or transitions.

The four 10 kΩ TT resistors are on internal timing pins, not direct AUX
resistors. Gate-side inventory verifies two CSD18540Q5B MOSFETs per driver,
22 Ω series gate resistance, 20 MΩ bleed and eight 10 pF Miller capacitors
with 15 kΩ drain-side limiters. N19/N12 also have TLP4590AF clamp paths through
220 Ω N_R7/N_R14 and connector contacts. The initial extraction correctly
stopped when its assumed direct capacitor-to-drain edge failed; the actual
15 kΩ series paths were inspected and incorporated before a report was saved.

Official Skyworks/TI PDFs were opened and matched to the existing local
primary revisions. The PDF skill was reused for four visually inspected
pages. Si8751's 9.5 mA maximum is a TT10k/IN=VDD table condition; OFF140nA
is typical only, and the measurement note uses a 100 pF gate load. The actual
MOSFET pair's table capacitance is 6.50/8.46 nF typical/maximum, and its 10 V
gate-charge sum is 82/106 nC at a different stated condition. These values
do not establish installed timing, hot leakage or driver/clamp overlap
current. No timing limit was transferred to the real gate network and no TT
component change was made. A font-cache warning did not prevent rendering;
no PDF was authored or edited.

Independent verification uses a separate five-node/source-current matrix for
all 4,096 cases, verifies 16 leakage-transfer pairs and exact current/gate
ownership, and agrees within 4.99e-17 A. Final review verifies 21 report
bindings, three local links and unchanged selected TBP50 status/documentation.
Successful scripts/reports are frozen. All commands are terminal; no subagents,
commit, push, order or fabrication release occurred. Continue with remaining
package/pin currents and actual driver startup/fault loads, then source startup
and thermal acceptance. The full goal remains active: 2,172 power opens,
251 signal opens, approved ESS footprint, complete housing fit and accepted
manufacturing outputs remain unfinished.

### AUX monitor outputs and source-voltage requirements

The previous goal turn was progress: it completed the four isolated-driver
input-resistor and gate-load ownership checks. This continuation follows the
remaining power-monitor and fast-OV output networks in the current TBP50
netlist and binds every pin of all 81 AUX-powered ICs across 29 families.
The [saved review](staging/two-board-aux-monitor-loads-01/README.md) adds 11
resistors disjoint from the previous AUX/output/reference/driver inventories.

P_U25's internal reference supplies P_R310–P_R315, including the shared 590 Ω
feed and 1 kΩ ground return for the negative-rail sense dividers. Nominal
output current is 0.6516156785709252 mA. Across reference0.985–1.020 V,
independent ±3% receiving resistor factors, ±30 nA input-current allocations
and N19/N12 points spanning −30..0 V, it is 0.6022883786828465–
0.7072088454037385 mA. The chosen −30 V domain is not an accepted installed
fault envelope. This output current is separate from package quiescent
current and from the E_U7 reference previously analyzed.

P_U103's five-resistor output/feedback circuit draws −9.516549755852917 to
+36.734197478868 µA across independent ideal output and inlet cases. No
negative current is credited to AUX. Of 896 cases, 144 lie outside the
comparator's operating input interval, including low-input startup and some
30 V cases. These prevent interpreting the linear calculation as a fault
or clamp-current guarantee. The existing P_R118/P_R119 AUX divider is not
added again. P_U26's output feeds P_U25.5 directly, leaving its input current
for the package/pin ledger.

Independent eliminated-node formulas, KCL and power checks cover all 4,608
monitor-reference and 896 fast-OV cases, agreeing within 5.18e-18 A. Exact
inventory checks cover 81 supply pins, 29 families, every connected IC pin
and all 11 new resistors. Package current acceptance remains false.

The LTC2910 minimum operating supply is 2.3 V, so simply assuming 2.3 V at
the AUX source leaves no distribution allowance. A new calculation uses the
actual P_R10811.7k + P_R13049.9 / P_R10910k network, TPS7A16 overall ±2%
accuracy and signed ±0.1 µA feedback current. Nominal output is 2.59476307 V.
A proposed complete ±1% bound for each feedback resistor gives
2.514502037636634–2.676729886075758 V, leaving 214.502 mV to the monitor's
minimum. A blanket ±3% assumption reaches 2.736310 V and fails the existing
2.7 V upper screen. The proposed 1% requirement needs exact MPN/drift/aging
acceptance; routed voltage drop, transient and thermal performance remain
unqualified. All 96 voltage cases agree with a separate two-node KCL solution
within 9.64e-14 V; 96 deliberately reversed feedback-current signs are rejected
by independent FB-node KCL residuals. Typical line/load terms are not added
on top of the overall accuracy bound.

Two official TI PDFs were downloaded. The PDF skill was reused to inspect
TLV7011 page7, LVC1G97 page5 and existing TPS7A16 page6 visually. The official
LTC2910 web PDF supplied extracted page2/3 evidence; two direct downloads
closed remotely, and a distributor response failed its PDF signature check.
No invalid PDF was saved. Web screenshot calls returned references without
usable images, so no LTC2910 visual inspection is claimed. Primary review
records these limits and exact test conditions. No PDF was authored or edited.
All command handles reached terminal states; no approval rejection occurred.

Final review verifies 25 report bindings, five local links and unchanged
TBP50 status/documentation. Successful scripts and reports are frozen. No
copper, commit, push, order or fabrication release occurred. Continue the
remaining package/pin-current ledger, actual driver/startup/fault behavior,
feedback resistor acceptance, routed source/drop limits and installed thermal
checks. The full two-board goal remains active; routing, the approved ESS
footprint, complete installed housing fit and manufacturing outputs are still
unfinished.
